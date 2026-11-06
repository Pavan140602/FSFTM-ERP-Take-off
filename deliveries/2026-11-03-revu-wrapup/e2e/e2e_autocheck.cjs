// Why is Auto Takeoff not showing? Open it, list what renders, catch errors.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  const bad = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 200)); });
  page.on('response', (r) => { if (r.status() >= 400 && r.url().includes('/api/')) bad.push(`${r.status()} ${r.url().slice(0, 140)}`); });
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
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(1500);
    r.panel = await page.locator('[data-testid="measurements-panel"]').innerText().catch(() => null);
    r.autoTestIds = await page.locator('[data-testid^="auto-takeoff"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-testid')).slice(0, 20));
    await page.screenshot({ path: path.join(outDir, 'a1.png') });
    // try a run
    const run = page.locator('[data-testid="auto-takeoff-run"]');
    r.runBtn = await run.count();
    if (r.runBtn) {
      await run.first().click();
      await page.waitForTimeout(12000);
      r.afterRun = (await page.locator('[data-testid="measurements-panel"]').innerText().catch(() => '')).slice(0, 600);
      await page.screenshot({ path: path.join(outDir, 'a2.png') });
    }
    // fullscreen look of the toolbar
    await page.locator('[data-testid="rail-auto"]').click();
  } catch (e) {
    r.error = String(e).slice(0, 400);
  }
  r.errors = errors.slice(0, 8);
  r.badApi = bad.slice(0, 10);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
