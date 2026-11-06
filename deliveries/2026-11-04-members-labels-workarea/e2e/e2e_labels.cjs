// Auto labels: profile + length centred on the line, turned with it.
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
    await page.waitForTimeout(2500);
    const rows = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]');
    r.rows = await rows.count();
    const pick = async (i, name) => {
      await rows.nth(i).locator('td').nth(1).click();
      await page.waitForTimeout(300);
      await page.keyboard.press('Shift+Digit3');
      await page.waitForTimeout(1800);
      await page.screenshot({ path: path.join(outDir, name) });
    };
    await pick(0, 'l1.png');
    // find a row whose markup is drawn vertically: try a few beams
    await pick(20, 'l2.png');
    await pick(45, 'l3.png');
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r));
  await browser.close();
})();
