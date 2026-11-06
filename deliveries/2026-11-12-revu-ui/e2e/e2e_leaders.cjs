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
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300); await page.mouse.click(800, 300);
    await page.waitForTimeout(600);
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(600);
    const rows = () => page.locator('tbody tr[tabindex="0"]').count();
    const r0 = await rows();
    // Cloud+: drag the cloud, leader follows the mouse round it, click, type.
    await page.locator('[data-strip-tool="cloudPlus"]').click();
    await page.mouse.move(700, 420); await page.mouse.down();
    for (let k = 1; k <= 8; k++) await page.mouse.move(700 + 25 * k, 420 + 12 * k);
    await page.mouse.up();
    await page.waitForTimeout(500);
    r.editorAfterCloud = await page.locator('[data-testid="callout-inline-editor"]').count();
    r.toolAfterCloud = await page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    for (let k = 1; k <= 6; k++) await page.mouse.move(640 - 10 * k, 380 - 5 * k);
    await page.waitForTimeout(250);
    await shot(page, 'y1-leader-topleft.png');
    for (let k = 1; k <= 8; k++) await page.mouse.move(980 + 5 * k, 600 + 5 * k);
    await page.waitForTimeout(250);
    await shot(page, 'y2-leader-bottomright.png');
    await page.mouse.click(1020, 640);
    await page.waitForTimeout(400);
    r.editorShown = await page.locator('[data-testid="callout-inline-editor"]').count();
    r.dialogShown = await page.getByText('Callout text').count();
    await page.keyboard.type('Check this beam size');
    await shot(page, 'y3-typing.png');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(600);
    r.rowsAfterCloudPlus = (await rows()) - r0;
    await shot(page, 'y4-cloudplus-done.png');
    // Callout: tip click, live arrow, second click, type.
    await page.locator('[data-strip-tool="callout"]').click();
    await page.mouse.click(620, 330);
    for (let k = 1; k <= 8; k++) await page.mouse.move(620 - 15 * k, 330 - 8 * k);
    await page.waitForTimeout(250);
    await shot(page, 'y5-callout-live.png');
    await page.mouse.click(500, 266);
    await page.waitForTimeout(400);
    r.calloutEditor = await page.locator('[data-testid="callout-inline-editor"]').count();
    await page.keyboard.type('Verify header');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(600);
    r.rowsAfterCallout = (await rows()) - r0;
    r.toolAtEnd = await page.evaluate(() => document.querySelector('[data-strip-tool][aria-pressed="true"]')?.getAttribute('data-strip-tool'));
    await shot(page, 'y6-callout-done.png');
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
