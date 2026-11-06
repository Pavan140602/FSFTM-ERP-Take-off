// Revu UI round (OE-DELIVERY 2026-11-12-revu-ui): legend look, markups-list
// right-click, cloud drag, tool auto-exit. Saves are blocked.
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
  try {
    await page.route('**/measurements**', (route) => (route.request().method() === 'GET' ? route.continue() : route.abort()));
    await page.goto(BASE + '/login');
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
    // Make a few markups: Auto Takeoff on this sheet.
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(500);
    await page.locator('[data-testid="auto-run"]').click();
    await page.locator('[data-testid="auto-result"]').waitFor({ timeout: 300000 });
    await page.waitForFunction(() => !document.querySelector('[data-testid="auto-run"]')?.disabled, null, { timeout: 300000 });
    await page.waitForTimeout(2000);
    r.auto = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    // Markups list: tick 3 rows, right-click one.
    const rows = page.locator('tbody tr[tabindex="0"]');
    r.rows = await rows.count();
    await rows.nth(0).click();
    await rows.nth(1).click({ modifiers: ['Control'] });
    await rows.nth(2).click({ modifiers: ['Control'] });
    await page.waitForTimeout(400);
    await rows.nth(1).click({ button: 'right' });
    await page.waitForTimeout(500);
    r.menuOpen = await page.locator('[data-testid="measurement-context-menu"]').count();
    r.menuCount = await page.locator('[data-testid="context-count"]').innerText().catch(() => null);
    await shot(page, 'r1-list-menu.png');
    await page.locator('[data-testid="context-status"]').click();
    await page.waitForTimeout(300);
    await shot(page, 'r2-status.png');
    await page.locator('[data-testid="context-status-accepted"]').click();
    await page.waitForTimeout(400);
    // Colour via menu.
    await rows.nth(1).click({ button: 'right' });
    await page.locator('[data-testid="context-colour"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="context-colour-pick"]').first().click();
    await page.waitForTimeout(400);
    await shot(page, 'r3-colour-picklist.png');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    // Cloud: select tool, drag a box.
    await page.keyboard.press('Escape');
    await page.locator('[data-strip-tool="cloud"]').click();
    await page.waitForTimeout(300);
    const cv = await page.locator('canvas.block').first().boundingBox();
    // A blank spot of the sheet that is on screen.
    const x0 = 820, y0 = 300;
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    for (let k = 1; k <= 10; k++) await page.mouse.move(x0 + 18 * k, y0 + 10 * k);
    await page.mouse.up();
    await page.waitForTimeout(800);
    r.toolAfterCloud = await page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    await shot(page, 'r4-cloud-drag.png');
    // Tool lock: double-click Rectangle, draw two.
    await page.locator('[data-strip-tool="rectangle"]').dblclick();
    await page.waitForTimeout(300);
    r.rectLocked = await page.locator('[data-strip-tool="rectangle"]').getAttribute('data-locked');
    for (const dy of [0, 140]) {
      await page.mouse.move(x0 - 200, y0 + dy);
      await page.mouse.down();
      for (let k = 1; k <= 6; k++) await page.mouse.move(x0 - 200 + 20 * k, y0 + dy + 12 * k);
      await page.mouse.up();
      await page.waitForTimeout(500);
    }
    r.toolAfterLockedRects = await page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    await page.keyboard.press('Escape');
    await shot(page, 'r5-locked-rects.png');
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'r6-icons.png') });
    // Legend as it is now.
    await page.locator('[data-testid="legend-toggle"]').click();
    await page.waitForTimeout(800);
    await shot(page, 'r7-legend-panel.png');
    const place = page.locator('[data-testid="legend-place-button"]');
    if (await place.count()) {
      await place.first().click();
      await page.waitForTimeout(300);
      await page.mouse.click(700, 600);
      await page.waitForTimeout(1200);
      await shot(page, 'r8-legend-placed.png');
    }
  } catch (e) {
    r.error = String(e).slice(0, 500);
    await shot(page, 'r-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
