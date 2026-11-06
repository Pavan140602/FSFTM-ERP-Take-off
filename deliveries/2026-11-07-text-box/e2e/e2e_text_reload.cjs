// Revu-style Text Box in the real viewer (OE-DELIVERY 2026-11-07-text-box).
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const shot = (page, n) => page.screenshot({ path: path.join(outDir, n) });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    if (!body.access_token) throw new Error('login failed: ' + JSON.stringify(body).slice(0, 200));
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${qa.doc}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    const canvas = page.locator('canvas.block').first();
    const box = await canvas.boundingBox();
    // Reload from the server only (local copy cleared at login).
    await page.waitForTimeout(6000);
    r.ledgerText1 = await page.locator('text=Text 1').count().catch(() => -1);
    r.ledgerTotal = await page.locator('text=/Ledger \(\d+/').first().innerText().catch(() => '');
    await page.locator('canvas.block').first().evaluate(() => 0);
    await shot(page, 'r1-reloaded.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 't-error.png').catch(() => {});
  }
  r.pageErrors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
