// Revu Properties toolbar, left Measurements/Scale tabs, Revu shortcuts.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
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
  const attr = (sel, a) => page.locator(sel).first().getAttribute(a).catch(() => null);
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    r.rail = await page.locator('[data-testid="revu-rail"] button').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
    r.barMode0 = await attr('[data-testid="revu-properties-bar"]', 'data-mode');
    r.topMeasureToolsLeft = await page.locator('[data-guide="takeoff-tools"]').count();
    await shot(page, 'p1-default.png');

    // Measurements tab
    await page.locator('[data-testid="rail-measure"]').click();
    await page.waitForTimeout(400);
    r.measurePanel = await page.locator('[data-testid="revu-measure-panel"] [data-tool]').count();
    r.measureTotals = await page.locator('[data-testid="revu-measure-totals"]').innerText().catch(() => null);
    await page.locator('[data-testid="revu-measure-panel"] [data-tool="distance"]').click();
    await page.waitForTimeout(300);
    r.barModeTool = await attr('[data-testid="revu-properties-bar"]', 'data-mode');
    r.barTitleTool = await page.locator('[data-testid="revu-properties-bar"] > span').first().innerText();
    await shot(page, 'p2-measure-tab.png');

    // Scale tab
    await page.locator('[data-testid="rail-scale"]').click();
    await page.waitForTimeout(300);
    r.scalePanel = { calibrate: await page.locator('[data-testid="revu-scale-panel"] [data-testid="calibrate-button"]').count(), viewport: await page.locator('[data-testid="revu-scale-panel"] [data-testid="viewport-button"]').count() };
    await shot(page, 'p3-scale-tab.png');

    // Revu shortcuts
    await page.keyboard.press('Escape');
    await page.mouse.move(900, 300);
    await page.keyboard.press('Shift+Alt+KeyA');
    await page.waitForTimeout(200);
    r.afterShiftAltA = await page.locator('[data-testid="revu-properties-bar"] > span').first().innerText();
    await page.keyboard.press('KeyL');
    await page.waitForTimeout(200);
    r.afterL = await page.locator('[data-testid="revu-properties-bar"] > span').first().innerText();
    await page.keyboard.press('Alt+KeyX');
    await page.waitForTimeout(400);
    r.altX_toolChest = await attr('[data-testid="rail-tools"]', 'aria-selected');
    await page.keyboard.press('Alt+KeyU');
    await page.waitForTimeout(300);
    r.altU_measure = await attr('[data-testid="rail-measure"]', 'aria-selected');
    await page.keyboard.press('Escape');
    await page.keyboard.press('KeyV');

    // Select one markup from the bottom list
    const row = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr').first();
    await row.click();
    await page.waitForTimeout(600);
    r.barModeSel = await attr('[data-testid="revu-properties-bar"]', 'data-mode');
    r.labelBefore = await page.locator('[data-testid="props-label"]').inputValue().catch(() => null);
    r.totalsBefore = await page.locator('[data-testid="props-totals"]').innerText().catch(() => null);
    await page.locator('[data-testid="props-unit"]').selectOption('mm');
    await page.waitForTimeout(300);
    r.totalsMm = await page.locator('[data-testid="props-totals"]').innerText().catch(() => null);
    await page.locator('[data-testid="props-unit"]').selectOption('ftin');
    await page.waitForTimeout(300);
    r.totalsFtIn = await page.locator('[data-testid="props-totals"]').innerText().catch(() => null);
    await page.locator('[data-testid="props-width"]').selectOption('6');
    await page.locator('[data-testid="props-linestyle"]').selectOption('dashed');
    await page.locator('[data-testid="props-opacity"]').fill('60');
    await page.locator('[data-testid="props-text-size"]').selectOption('18');
    await page.locator('[data-testid="props-bold"]').click();
    await page.locator('[data-testid="props-underline"]').click();
    await page.locator('[data-testid="props-caption"]').click();
    r.captionOptions = await page.locator('[data-testid="props-caption-list"] label').allInnerTexts();
    r.captionTickedBefore = await page.locator('[data-testid="props-caption-list"] input:checked').count();
    await page.locator('[data-testid="props-caption-length"]').check();
    await page.locator('[data-testid="props-caption-label"]').check();
    await page.locator('[data-testid="props-caption-close"]').click();
    r.captionClosed = (await page.locator('[data-testid="props-caption-list"]').count()) === 0;
    await page.locator('[data-testid="props-label"]').fill('B-101 test');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    r.bold = await attr('[data-testid="props-bold"]', 'aria-pressed');
    r.ledgerFirstRow = (await row.innerText()).replace(/\s+/g, ' ').slice(0, 140);
    await shot(page, 'p4-selection.png');
    // zoom to the selection so the caption is visible
    await page.keyboard.press('Shift+Digit3');
    await page.waitForTimeout(1500);
    await shot(page, 'p5-selection-zoom.png');

    // Shortcut sheet
    await page.keyboard.press('Escape');
    await page.locator('[role="menubar"] button', { hasText: 'Help' }).first().click().catch((e) => { r.helpErr = String(e).slice(0, 120); });
    await page.waitForTimeout(200);
    await page.locator('[data-testid="revu-help-shortcuts"]').click().catch(() => {});
    await page.waitForTimeout(300);
    r.sheetRows = await page.locator('[data-testid="revu-shortcut-sheet"] kbd').count();
    await shot(page, 'p6-shortcuts.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'pz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
