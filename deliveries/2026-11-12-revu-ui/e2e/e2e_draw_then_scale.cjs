// Legend Setup round (OE-DELIVERY 2026-11-12-revu-ui): manual markups ->
// right-click -> Legend -> Create New Legend -> setup -> place -> live ->
// shrink -> edit setup. Saves blocked.
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
  const rowsText = async () => (await page.locator('tbody tr[tabindex="0"]').count());
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
    const checked = () => page.evaluate(() => [...document.querySelectorAll('tbody input[type="checkbox"]')].filter((x) => x.checked).length);
    const lenCell = () => page.evaluate(() => { const tr = document.querySelector('tbody tr[tabindex="0"]'); return tr ? tr.innerText.replace(/\s+/g, ' ').slice(0, 120) : null; });
    // Draw a Length on the sheet with no scale: it must be drawn, then asked.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300);
    await page.waitForTimeout(400);
    r.dialogAfterFirstClick = await page.locator('[data-testid="set-scale-dialog"]').count();
    for (let k = 1; k <= 6; k++) await page.mouse.move(620 + 33 * k, 300);
    await page.mouse.click(820, 300);
    await page.waitForTimeout(800);
    r.dialogAfterDrawn = await page.locator('[data-testid="set-scale-dialog"]').count();
    r.reason = await page.locator('[data-testid="set-scale-reason"]').innerText().catch(() => null);
    r.rowBefore = await lenCell();
    await shot(page, 'a1-drawn-then-ask.png');
    await page.locator('[data-testid="set-scale-preset"]').selectOption('1/8" = 1\'-0"');
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(1200);
    r.rowAfter = await lenCell();
    await shot(page, 'a2-after-scale.png');
    // A second Length on the same sheet: no question now.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 360);
    await page.mouse.click(760, 360);
    await page.waitForTimeout(800);
    r.dialogSecond = await page.locator('[data-testid="set-scale-dialog"]').count();
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
