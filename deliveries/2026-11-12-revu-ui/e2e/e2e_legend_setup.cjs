// Legend Setup round (OE-DELIVERY 2026-11-12-revu-ui): manual markups ->
// right-click -> Legend -> Create New Legend -> setup -> place -> live ->
// shrink -> edit setup. Saves blocked.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile, docId, pageNo] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const shot = (page, n) => page.screenshot({ path: path.join(outDir, n) });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  const rowsText = async () => (await page.locator('tbody tr[tabindex="0"]').count());
  try {
    await page.route('**/measurements**', (route) => (route.request().method() === 'GET' ? route.continue() : route.abort()));
    await page.goto(BASE + '/login', { timeout: 120000 });
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${docId}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 180000 });
    await page.waitForTimeout(3000);
    if (pageNo) {
      const pin = await page.evaluateHandle(() => { for (const i of document.querySelectorAll('input')) { const t = i.parentElement?.innerText || ''; if (/of\s*\d+/.test(t)) return i; } return null; });
      await pin.asElement().fill(String(pageNo));
      await pin.asElement().press('Enter');
      await page.waitForTimeout(3000);
    }
    // Three Length markups by hand (tool locked).
    await page.locator('[data-strip-tool="distance"]').dblclick();
    await page.waitForTimeout(300);
    for (const y of [260, 320, 380]) {
      await page.mouse.click(620, y);
      await page.waitForTimeout(150);
      await page.mouse.click(820, y);
      await page.waitForTimeout(300);
    }
    await page.keyboard.press('Escape');
    await page.locator('[data-strip-tool="select"]').click();
    await page.waitForTimeout(500);
    const rows = page.locator('tbody tr[tabindex="0"]');
    r.rowsAfterDraw = await rows.count();
    await rows.nth(0).click();
    await rows.nth(1).click({ modifiers: ['Control'] });
    await rows.nth(2).click({ modifiers: ['Control'] });
    await rows.nth(1).click({ button: 'right' });
    await page.waitForTimeout(400);
    await page.locator('[data-testid="context-legend"]').hover();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="context-legend-create-new"]').click();
    await page.waitForTimeout(500);
    r.dialog = await page.locator('[data-testid="legend-setup-dialog"]').count();
    await shot(page, 'l1-setup.png');
    await page.locator('[data-testid="legend-setup-col-area"]').uncheck();
    await page.locator('[data-testid="legend-setup-border-horizontal"]').click();
    await page.locator('[data-testid="legend-setup-title"]').fill('Wall Legend');
    await shot(page, 'l2-setup-picked.png');
    await page.locator('[data-testid="legend-setup-ok"]').click();
    await page.waitForTimeout(400);
    await page.mouse.click(620, 470);
    await page.waitForTimeout(1200);
    await shot(page, 'l3-placed.png');
    // Live: one more Length.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 440);
    await page.waitForTimeout(150);
    await page.mouse.click(760, 440);
    await page.waitForTimeout(800);
    r.toolAfterOne = await page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    await shot(page, 'l4-live.png');
    // Select the legend, then drag its bottom-right handle in (smaller).
    await page.mouse.click(860, 560);
    await page.waitForTimeout(500);
    await shot(page, 'l5a-selected.png');
    const br = await page.evaluate(() => null);
    await page.mouse.move(1120, 692);
    await page.mouse.down();
    for (let k = 1; k <= 10; k++) await page.mouse.move(1120 - 22 * k, 692 - 8 * k);
    await page.mouse.up();
    await page.waitForTimeout(800);
    await shot(page, 'l5-shrunk.png');
    // Edit the setup: right-click the legend.
    await page.mouse.click(700, 560, { button: 'right' });
    r.menuAfterRight = await page.locator('[data-testid="measurement-context-menu"]').count();
    await page.waitForTimeout(400);
    r.legendSetupItem = await page.locator('[data-testid="context-legend-setup"]').count();
    if (r.legendSetupItem) {
      await page.locator('[data-testid="context-legend-setup"]').click();
      await page.waitForTimeout(400);
      await page.locator('[data-testid="legend-setup-border-vertical"]').click();
      await page.locator('[data-testid="legend-setup-show-title"]').uncheck();
      await page.locator('[data-testid="legend-setup-ok"]').click();
      await page.waitForTimeout(800);
      await shot(page, 'l6-edited.png');
    }
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
