// Probe: grip click collapses? bottom drag resizes? split sync page/zoom.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const r = {};
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
    await page.waitForTimeout(2000);
    const box = async (sel) => { const b = await page.locator(sel).first().boundingBox().catch(() => null); return b ? [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] : null; };
    r.leftHandle = await box('[data-testid="takeoff-resize-handle-left"]');
    r.rightHandle = await box('[data-testid="takeoff-resize-handle-right"]');
    r.ledger = await box('[data-testid="takeoff-ledger-bar"]');
    r.ledgerHandle = await box('[data-testid="takeoff-ledger-resize-handle"]');
    // click left grip
    await page.locator('[data-testid="takeoff-resize-handle-left"]').click();
    await page.waitForTimeout(500);
    r.leftPanelAfterClick = await box('[data-testid="revu-left-panel"]');
    r.leftCollapsedTab = await box('[data-testid="takeoff-collapsed-tab-left"]');
    await page.screenshot({ path: path.join(outDir, 'p1.png') });
    // drag ledger handle up 300
    const lh = r.ledgerHandle;
    if (lh) {
      await page.mouse.move(lh[0] + lh[2] / 2, lh[1] + lh[3] / 2);
      await page.mouse.down();
      await page.mouse.move(lh[0] + lh[2] / 2, lh[1] + lh[3] / 2 - 300, { steps: 10 });
      await page.mouse.up();
      await page.waitForTimeout(500);
    }
    r.ledgerAfterDrag = await box('[data-testid="takeoff-ledger-bar"]');
    await page.screenshot({ path: path.join(outDir, 'p2.png') });
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r));
  await browser.close();
})();
