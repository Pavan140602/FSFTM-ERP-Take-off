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
    r.subItems = await page.locator('[data-testid="context-legend-sub"] button').allInnerTexts().catch(() => []);
    await page.mouse.click(620, 470);
    await page.waitForTimeout(1200);
    r.panel = await page.locator('[data-testid="legend-props"]').count();
    await shot(page, 'p1-placed-panel.png');
    const L = (id) => page.locator(`[data-testid="${id}"]`);
    // Title child pop-up.
    await L('legend-props-title').click();
    await L('legend-props-title-text').fill('Wall Legend');
    await L('legend-props-title-size-plus').click();
    await L('legend-props-title-size-plus').click();
    await L('legend-props-title-style-italic').click();
    await L('legend-props-title-style-underline').click();
    await page.waitForTimeout(300);
    await shot(page, 'p2-title-child.png');
    // Columns child pop-up: add Label (Edit Columns picklist).
    await L('legend-props-columns').click();
    await L('legend-props-col-label').check();
    await page.waitForTimeout(300);
    await shot(page, 'p3-columns-child.png');
    // Cells child pop-up.
    await L('legend-props-cells').click();
    await L('legend-props-cell-size-plus').click();
    await L('legend-props-cell-style-bold').click();
    // Legend style child pop-up.
    await L('legend-props-style').click();
    await L('legend-props-style-horizontal').click();
    await L('legend-props-style').click();
    // Line width, opacity, fill opacity.
    await L('legend-props-line-width-step-plus').click();
    await L('legend-props-line-width-step-plus').click();
    await L('legend-props-font-select').selectOption('Times New Roman');
    await L('legend-props-fill-opacity-range').fill('40');
    await page.waitForTimeout(800);
    await shot(page, 'p4-styled.png');
    r.panelText = (await L('legend-props').innerText()).replace(/\s+/g, ' ').slice(0, 300);
    // Legend > None on the first Length.
    const rows2 = page.locator('tbody tr[tabindex="0"]');
    await rows2.nth(0).click();
    await rows2.nth(0).click({ button: 'right' });
    await page.waitForTimeout(400);
    await page.locator('[data-testid="context-legend"]').hover();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="context-legend-none"]').click();
    await page.waitForTimeout(800);
    await page.mouse.click(860, 560);
    await page.waitForTimeout(600);
    await shot(page, 'p5-after-none.png');
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
