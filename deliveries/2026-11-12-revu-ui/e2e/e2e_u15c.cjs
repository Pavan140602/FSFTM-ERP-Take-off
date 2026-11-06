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
  const bctx = await browser.newContext({ viewport: { width: 1700, height: 1000 }, acceptDownloads: true });
  const page = await bctx.newPage();
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
    const goto = async (n) => { const pin = await page.evaluateHandle(() => { for (const i of document.querySelectorAll('input')) { const t = i.parentElement?.innerText || ''; if (/of\s*\d+/.test(t)) return i; } return null; }); await pin.asElement().fill(String(n)); await pin.asElement().press('Enter'); await page.waitForTimeout(4500); };
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.locator('[data-strip-tool="cloud"]').click();
    await page.mouse.move(600, 420); await page.mouse.down(); await page.mouse.move(800, 520, { steps: 6 }); await page.mouse.up();
    await page.waitForTimeout(500);
    await goto(4);
    await shot(page, 'o1-orig-p4.png');
    await goto(7);
    const [dl2] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), page.locator('[data-testid="toolbar-export-pdf-button"]').click()]);
    const savePath = path.join(outDir, 'saved2.pdf');
    await dl2.saveAs(savePath);
    await page.locator('[data-testid="toolbar-close-pdf"]').click();
    await page.waitForTimeout(1500);
    await page.locator('input[type="file"][accept="application/pdf"]').first().setInputFiles(savePath);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(4000);
    await goto(7);
    await shot(page, 'o2-reopen-p7.png');
    await goto(4);
    await shot(page, 'o3-reopen-p4.png');
    r.rows = await page.locator('tbody tr[tabindex="0"]').count();
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
