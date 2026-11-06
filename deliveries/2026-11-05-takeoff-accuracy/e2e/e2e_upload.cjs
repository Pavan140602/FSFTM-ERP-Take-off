// Upload progress bar: upload a PDF with throttled upload speed, record the bar text.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, PDF, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = { texts: [] };
  try {
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
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    // ~1.5 MB/s upload so the bar is visible
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 20, downloadThroughput: -1, uploadThroughput: 1.5 * 1024 * 1024 });
    const input = page.locator('input[type=file][multiple]').last();
    r.inputs = await page.locator('input[type=file]').count();
    const t0 = Date.now();
    await input.setInputFiles(PDF);
    let shot = 0;
    for (let i = 0; i < 400; i++) {
      const loc = page.locator('[data-testid="upload-progress-text"]');
      const n = await loc.count();
      if (n === 0 && i > 5) break;
      if (n > 0) {
        const t = await loc.first().innerText().catch(() => '');
        if (t && r.texts[r.texts.length - 1]?.t !== t) r.texts.push({ ms: Date.now() - t0, t });
        if ((shot === 0 && /%/.test(t)) || (shot === 1 && /reading/.test(t))) {
          await page.screenshot({ path: path.join(outDir, `upload_${shot}.png`) });
          shot++;
        }
      }
      await page.waitForTimeout(150);
    }
    r.totalMs = Date.now() - t0;
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(outDir, 'upload_done.png') });
    r.url = page.url();
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  // keep the log short: first, some middle, last
  const tx = r.texts;
  r.sample = tx.length > 12 ? [...tx.slice(0, 4), ...tx.slice(Math.floor(tx.length / 2), Math.floor(tx.length / 2) + 2), ...tx.slice(-5)] : tx;
  delete r.texts;
  r.count = tx.length;
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
