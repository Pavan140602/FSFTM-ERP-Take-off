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
    await rows.nth(0).locator('td').nth(2).click();
    await rows.nth(1).locator('td').nth(2).click({ modifiers: ['Control'] });
    await rows.nth(2).locator('td').nth(2).click({ modifiers: ['Control'] });
    await page.waitForTimeout(300);
    // Right-click a selected markup ON THE PDF.
    await page.mouse.move(720, 320);
    await page.waitForTimeout(300);
    await page.mouse.click(720, 320, { button: 'right' });
    await page.waitForTimeout(400);
    r.menu = await page.locator('[data-testid="measurement-context-menu"]').count();
    r.menuCount = await page.locator('[data-testid="context-count"]').innerText().catch(() => null);
    await page.locator('[data-testid="context-legend"]').hover();
    await page.waitForTimeout(400);
    r.subVisible = await page.locator('[data-testid="context-legend-sub"]').isVisible().catch(() => false);
    r.subItems = await page.locator('[data-testid="context-legend-sub"] button').allInnerTexts().catch(() => []);
    await shot(page, 'b1-legend-side-window.png');
    await page.locator('[data-testid="context-legend-create-new"]').hover();
    await page.locator('[data-testid="context-legend-create-new"]').click();
    await page.waitForTimeout(400);
    await page.mouse.click(620, 470);
    await page.waitForTimeout(1200);
    r.barAfterPlace = await page.locator('[data-testid="legend-props"][data-layout="bar"]').count();
    await shot(page, 'b2-placed.png');
    // Click the legend: properties in the top bar.
    await page.mouse.click(5, 500);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await page.mouse.click(760, 520);
    await page.waitForTimeout(600);
    r.barOnClick = await page.locator('[data-testid="legend-props"][data-layout="bar"]').count();
    await page.locator('[data-testid="legend-props-title-button"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="legend-props-title-size-plus"]').click();
    await page.locator('[data-testid="legend-props-title-style-italic"]').click();
    await page.waitForTimeout(400);
    await shot(page, 'b3-top-bar-title.png');
    await page.locator('[data-testid="legend-props-style-button"]').click();
    await page.waitForTimeout(300);
    await shot(page, 'b4-top-bar-style.png');
    await page.locator('[data-testid="legend-props-style-vertical"]').click();
    await page.waitForTimeout(400);
    // Navbar Legend button with markups selected (select on the sheet: Escape
    // then click the two lower Lengths with Ctrl).
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const checked = () => page.evaluate(() => [...document.querySelectorAll('tbody input[type="checkbox"]')].filter((x) => x.checked).length);
    const rws = page.locator('tbody tr[tabindex="0"]');
    for (let attempt = 0; attempt < 3 && (await checked()) < 2; attempt++) {
      await rws.nth(1).locator('td').nth(2).click({ modifiers: ['Control'] });
      await page.waitForTimeout(300);
      await rws.nth(2).locator('td').nth(2).click({ modifiers: ['Control'] });
      await page.waitForTimeout(400);
    }
    r.checkedBeforeNavbar = await checked();
    await page.locator('[data-testid="legend-toggle"]').click();
    await page.waitForTimeout(500);
    r.placingToast = await page.locator('text=Click the PDF to place the legend').count();
    await page.mouse.click(1050, 330);
    await page.waitForTimeout(1200);
    r.legendBarAfterNavbar = await page.locator('[data-testid="legend-props"][data-layout="bar"]').count();
    await shot(page, 'b5-navbar-legend.png');
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
