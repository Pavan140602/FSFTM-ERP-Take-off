// Why are the screenshots blank during an upload? Snapshot every 2 s.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, PDF, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const logs = [];
  page.on('pageerror', (e) => logs.push('PAGEERROR ' + String(e).slice(0, 300)));
  page.on('console', (m) => { if (m.type() === 'error') logs.push('console ' + m.text().slice(0, 200)); });
  await page.goto(BASE + '/login');
  const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
  await page.evaluate(({ tok }) => {
    localStorage.clear();
    for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
    localStorage.setItem('oe_onboarding_completed', 'true');
    localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
  }, { tok: body.access_token });
  await page.goto(`${BASE}/takeoff?tab=measurements`);
  await page.waitForTimeout(4000);
  const snap = async (name) => {
    const info = await page.evaluate(() => ({
      text: document.body.innerText.length,
      progress: document.querySelector('[data-testid="upload-progress-text"]')?.textContent ?? null,
      url: location.href,
    }));
    await page.screenshot({ path: path.join(outDir, name + '.png') });
    return { name, ...info };
  };
  const out = [await snap('before')];
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 20, downloadThroughput: -1, uploadThroughput: 1.5 * 1024 * 1024 });
  await page.locator('input[type=file][multiple]').last().setInputFiles(PDF);
  for (let i = 1; i <= 7; i++) {
    await page.waitForTimeout(2000);
    out.push(await snap('t' + i * 2));
  }
  console.log(JSON.stringify(out, null, 1));
  console.log(JSON.stringify(logs.slice(0, 8), null, 1));
  await browser.close();
})();
