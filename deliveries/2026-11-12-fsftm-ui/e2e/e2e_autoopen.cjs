const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile, pdfPath] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const r = {};
  try {
    await page.goto(BASE + '/login', { timeout: 120000 });
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    for (const url of [`${BASE}/takeoff?tab=measurements`, `${BASE}/takeoff?tab=documents`, `${BASE}/takeoff`]) {
      await page.goto(url);
      await page.waitForTimeout(4000);
      r.inputs = await page.locator('input[type="file"][accept="application/pdf,.pdf"]').count();
      r.from = url.replace(BASE, '');
      if (r.inputs) break;
    }
    await page.screenshot({ path: path.join(outDir, 'a0-before.png') });
    await page.locator('input[type="file"][accept="application/pdf,.pdf"]').first().setInputFiles(pdfPath);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(3000);
    r.url = page.url().replace(BASE, '');
    r.viewerOpen = await page.locator('canvas.block').count();
    r.pages = await page.locator('[data-testid="thumbnail-item"]').count();
    await page.screenshot({ path: path.join(outDir, 'a1-after.png') });
    await page.reload();
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(2000);
    r.afterReloadPages = await page.locator('[data-testid="thumbnail-item"]').count();
    r.afterReloadUrl = page.url().replace(BASE, '');
  } catch (e) { r.fail = String(e).slice(0, 300); }
  console.log(JSON.stringify(r));
  await browser.close();
})();
