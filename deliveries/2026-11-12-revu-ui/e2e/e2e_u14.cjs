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
    // Status scale -> Custom with Revu units.
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="set-scale-mode-custom"]').click();
    r.unitOptions = await page.locator('[data-testid="set-scale-real-unit"] option').allInnerTexts();
    await page.locator('[data-testid="set-scale-paper"]').fill('0.125');
    await page.locator('[data-testid="set-scale-paper-unit"]').selectOption('in');
    await page.locator('[data-testid="set-scale-real"]').fill('1');
    await page.locator('[data-testid="set-scale-real-unit"]').selectOption('ftin');
    r.read1 = await page.locator('[data-testid="set-scale-custom-read"]').innerText();
    await page.locator('[data-testid="set-scale-add-preset"]').click();
    await page.waitForTimeout(200);
    r.read2 = await page.locator('[data-testid="set-scale-custom-read"]').innerText();
    await shot(page, 'k1-custom.png');
    // Recalibrate: two clicks, then the Calibrate window.
    await page.locator('[data-testid="set-scale-calibrate"]').click();
    await page.waitForTimeout(400);
    await page.mouse.click(700, 400);
    await page.mouse.click(900, 400);
    await page.waitForTimeout(600);
    r.calTitle = await page.locator('[data-testid="set-scale-title"]').innerText().catch(() => null);
    r.calPaper = await page.locator('[data-testid="set-scale-paper"]').inputValue().catch(() => null);
    await page.locator('[data-testid="set-scale-real"]').fill(`12'-6"`);
    r.calRead = await page.locator('[data-testid="set-scale-custom-read"]').innerText();
    await shot(page, 'k2-calibrate.png');
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(600);
    r.status = await page.locator('[data-testid="status-scale"]').innerText();
    // Saved preset listed.
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(300);
    r.savedPreset = await page.locator('[data-testid="set-scale-preset"] optgroup[label="Saved"] option').allInnerTexts();
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
