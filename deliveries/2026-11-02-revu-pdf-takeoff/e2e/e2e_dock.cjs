// Revu dock + two-way sync check.
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
  const box = async (sel) => { const b = await page.locator(sel).first().boundingBox().catch(() => null); return b ? [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] : null; };
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
    r.railIcons = await page.locator('[data-testid="revu-rail"] [role="tab"]').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
    r.default = { rail: await box('[data-testid="revu-rail"]'), left: await box('[data-testid="revu-left-panel"]'), side: await box('[data-testid="measurements-panel"]'), canvasCol: await box('canvas.block') };
    await shot(page, 'd1-default.png');

    await page.locator('[data-testid="rail-properties"]').click();
    await page.waitForTimeout(600);
    r.propsOpen = { left: await box('[data-testid="revu-left-panel"]'), side: await box('[data-testid="measurements-panel"]') };
    await shot(page, 'd2-properties-left.png');
    // drag the docked panel wider (handle sits to its right)
    const h = await box('[data-testid="takeoff-resize-handle-right"]');
    r.handle = h;
    if (h) {
      await page.mouse.move(h[0] + h[2] / 2, h[1] + 200);
      await page.mouse.down();
      await page.mouse.move(h[0] + h[2] / 2 + 150, h[1] + 200, { steps: 8 });
      await page.mouse.up();
      await page.waitForTimeout(400);
    }
    r.sideAfterDrag = await box('[data-testid="measurements-panel"]');
    await page.locator('[data-testid="rail-properties"]').click();
    await page.waitForTimeout(500);
    r.afterClose = { side: await box('[data-testid="measurements-panel"]'), left: await box('[data-testid="revu-left-panel"]'), rail: await box('[data-testid="revu-rail"]') };
    await shot(page, 'd3-closed.png');
    await page.locator('[data-testid="rail-thumbs"]').click();
    await page.waitForTimeout(400);

    // bottom panel: drag way up, must stay in the window
    const lh = await box('[data-testid="takeoff-ledger-resize-handle"]');
    if (lh) {
      await page.mouse.move(lh[0] + lh[2] / 2, lh[1] + 5);
      await page.mouse.down();
      await page.mouse.move(lh[0] + lh[2] / 2, lh[1] - 700, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(500);
    }
    r.ledgerAfterBigDrag = await box('[data-testid="takeoff-ledger-bar"]');
    await shot(page, 'd4-ledger.png');
    if (lh) {
      const nh = await box('[data-testid="takeoff-ledger-resize-handle"]');
      await page.mouse.move(nh[0] + nh[2] / 2, nh[1] + 5);
      await page.mouse.down();
      await page.mouse.move(nh[0] + nh[2] / 2, nh[1] + 450, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(400);
    }

    // two-way sync
    await page.locator('[data-testid="status-sync"]').click();
    await page.waitForTimeout(3000);
    const splitLabel = async () => (await page.locator('text=/^\\s*\\d+\\s*\\/\\s*\\d+\\s*$/').allInnerTexts()).map((x) => x.trim());
    r.afterSyncOn = { mainPage: await page.locator('[data-testid="pager-input"]').inputValue(), labels: await splitLabel() };
    await page.locator('[data-testid="pager-next"]').click();
    await page.waitForTimeout(2500);
    r.afterMainNext = { mainPage: await page.locator('[data-testid="pager-input"]').inputValue(), labels: await splitLabel() };
    // zoom the main view, read the split zoom label
    const mainCanvas = await box('canvas.block');
    await page.mouse.move(mainCanvas[0] + 200, mainCanvas[1] + 150);
    for (let i = 0; i < 3; i++) { await page.mouse.wheel(0, -100); await page.waitForTimeout(80); }
    await page.waitForTimeout(1500);
    r.zoomsAfterMainWheel = await page.locator('text=/^\\d+%$/').allInnerTexts();
    // zoom the split pane, read the main zoom
    const sp = await box('canvas.rounded-\\[2px\\] >> nth=-1');
    const splitCanvas = page.locator('canvas').last();
    const sb = await splitCanvas.boundingBox();
    if (sb) {
      await page.mouse.move(sb.x + 100, sb.y + 100);
      for (let i = 0; i < 2; i++) { await page.mouse.wheel(0, 100); await page.waitForTimeout(80); }
      await page.waitForTimeout(1500);
    }
    r.zoomsAfterSplitWheel = await page.locator('text=/^\\d+%$/').allInnerTexts();
    await shot(page, 'd5-sync.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'dz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
