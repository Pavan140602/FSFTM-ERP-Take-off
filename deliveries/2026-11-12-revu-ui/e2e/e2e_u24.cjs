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
  const ctx = await browser.newContext({ viewport: { width: 1700, height: 1000 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const r = {};
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  try {
    await page.goto(BASE + '/login', { timeout: 120000 });
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    await page.evaluate(({ tok }) => { localStorage.clear(); for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok); localStorage.setItem('oe_onboarding_completed', 'true'); for (const k of ['takeoff.showDimensions', 'takeoff.showLabels', 'takeoff.labelShowName.v2', 'takeoff.labelShowDimension']) localStorage.setItem(k, 'false'); }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements`);
    await page.waitForTimeout(3000);
    await page.locator('input[type="file"][accept="application/pdf"]').first().setInputFiles(path.join(__dirname, 'labels_A.pdf'));
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    await page.locator('[data-testid="status-scale"]').click();
    await page.locator('[data-testid="set-scale-preset"]').selectOption({ index: 5 });
    r.scalePicked = await page.locator('[data-testid="set-scale-preset"]').evaluate((s) => s.selectedOptions[0].textContent);
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    const draw = async (tool, pts, finish) => {
      await page.locator(`[data-strip-tool="${tool}"]`).click();
      for (const [x, y] of pts) { await page.mouse.click(x, y); await page.waitForTimeout(80); }
      if (finish) await page.keyboard.press('Enter');
      await page.waitForTimeout(400);
    };
    await draw('distance', [[560, 640], [760, 640]]);
    await draw('polyline', [[560, 300], [760, 300], [760, 230]], true);
    await draw('area', [[860, 420], [1060, 420], [1060, 560], [860, 560]], true);
    await draw('perimeter', [[1120, 420], [1300, 420], [1300, 560]], true);
    await draw('count', [[600, 480], [660, 480]]);
    await page.keyboard.press('Escape');
    await draw('diameter', [[1150, 640], [1300, 640]]);
    await page.locator('[data-strip-tool="select"]').click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, 'h1-all-tools.png'), clip: { x: 500, y: 200, width: 850, height: 480 } });
    r.rows = (await page.locator('tbody tr[tabindex="0"]').allInnerTexts()).map((t) => t.split('\t').filter(Boolean).slice(1, 2).join(''));
  } catch (e) { r.fail = String(e).slice(0, 300); await shot(page, 'fail.png').catch(() => {}); }
  r.errors = errors;
  console.log(JSON.stringify(r));
  await browser.close();
})();
