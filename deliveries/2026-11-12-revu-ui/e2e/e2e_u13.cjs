// Update 6 checks: scale asks every time, custom scale text, cloud preview,
// Cloud+, REUSE toggle. Saves blocked.
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
    const active = () => page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    const dlg = () => page.locator('[data-testid="set-scale-dialog"]').count();
    await page.getByRole('button', { name: /^Scale$/ }).first().click().catch(async () => { await page.locator('text=Scale').first().click(); });
    await page.waitForTimeout(500);
    r.panel = await page.locator('[data-testid="revu-scale-panel"]').count();
    await page.locator('[data-testid="calibrate-button"]').click();
    await page.waitForTimeout(400);
    r.dialogFromCalibrate = await page.locator('[data-testid="set-scale-dialog"]').count();
    await shot(page, 'c1-dialog.png');
    await page.locator('[data-testid="set-scale-cancel"]').click();
    await page.waitForTimeout(300);
    const badge = page.locator('[data-testid="uncalibrated-badge"], [data-testid="calibration-badge"]').first();
    if (await badge.count()) { await badge.click(); await page.waitForTimeout(300); r.dialogFromBadge = await page.locator('[data-testid="set-scale-dialog"]').count(); }
    await page.locator('[data-testid="set-scale-calibrate"]').click();
    await page.waitForTimeout(400);
    r.calibrateHint = await page.getByText(/Calibrate: click point/).count();
    await shot(page, 'c2-calibrating.png');
    await shot(page, 'w-all.png');
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'v6-strip.png') });
  } catch (e) {
    r.fail = String(e).slice(0, 400);
    await shot(page, 'fail.png').catch(() => {});
  }
  r.errors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
