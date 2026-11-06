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
    const rows = () => page.locator('tbody tr[tabindex="0"]').count();
    // Calibrate from Set Scale: snap ring near a drawing line.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300); await page.mouse.click(800, 300);
    await page.waitForTimeout(600);
    await page.locator('[data-testid="set-scale-calibrate"]').click();
    await page.waitForTimeout(500);
    await page.mouse.click(1376, 330);
    for (let k = 1; k <= 6; k++) await page.mouse.move(1376 + 3 * k, 330 + 30 * k);
    await page.mouse.move(1379, 560);
    await page.waitForTimeout(400);
    r.snapRingCal = await page.evaluate(() => !!document.querySelector('[data-testid*="snap"]'));
    await shot(page, 'z0-calibrate-snap.png');
    await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    // Apply a scale so nothing else asks.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300); await page.mouse.click(800, 300);
    await page.waitForTimeout(600);
    if (await page.locator('[data-testid="set-scale-apply"]').count()) await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    const r0 = await rows();
    // Cloud+ by clicks, ghost line, Enter closes, leader, click, type.
    await page.locator('[data-strip-tool="cloudPlus"]').click();
    await page.waitForTimeout(200);
    r.barMode = await page.locator('[data-testid="revu-properties-bar"]').getAttribute('data-mode').catch(() => null);
    r.barHasWidth = await page.locator('[data-testid="props-width"]').count();
    r.barHasOpacity = await page.locator('[data-testid="props-opacity"]').count();
    await page.mouse.click(650, 420); await page.waitForTimeout(120);
    await page.mouse.click(850, 420); await page.waitForTimeout(120);
    await page.mouse.click(850, 560); await page.waitForTimeout(120);
    for (let k = 1; k <= 5; k++) await page.mouse.move(850 - 25 * k, 560 + 4 * k);
    await page.waitForTimeout(250);
    await shot(page, 'z1-cloudplus-ghost.png');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    r.rowsAfterEnter = (await rows()) - r0;
    for (let k = 1; k <= 6; k++) await page.mouse.move(950 + 10 * k, 380 - 5 * k);
    await page.waitForTimeout(250);
    await shot(page, 'z2-leader.png');
    await page.mouse.click(1010, 350);
    await page.waitForTimeout(300);
    r.editor = await page.locator('[data-testid="callout-inline-editor"]').count();
    await page.keyboard.type('Revise per RFI 12');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    r.rowsAfterComment = (await rows()) - r0;
    await shot(page, 'z3-done.png');
    // Polygon closes with Enter.
    await page.locator('[data-strip-tool="polygon"]').click();
    await page.mouse.click(450, 600); await page.mouse.click(550, 600); await page.mouse.click(520, 680);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    r.rowsAfterPolygon = (await rows()) - r0;
    // Strip.
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'z4-strip.png') });
    r.stripMore = await page.locator('[data-testid="revu-tool-strip-more"]').count();
    if (r.stripMore) {
      await page.locator('[data-testid="revu-tool-strip-more"]').click();
      await page.waitForTimeout(600);
      r.stripUpAfter = await page.locator('[data-testid="revu-tool-strip-up"]').count();
      r.dynFillVisible = await page.locator('[data-strip-tool="dynamicFill"]').isVisible();
      await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'z5-strip-scrolled.png') });
    }
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
