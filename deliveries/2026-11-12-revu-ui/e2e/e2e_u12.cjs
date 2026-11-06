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
    // Status-bar scale opens Apply Scale to Pages; apply 1/8".
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(400);
    r.scaleDlgFromStatus = await page.locator('[data-testid="set-scale-dialog"]').count();
    await shot(page, 'q0-status-scale.png');
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(400);
    r.statusLabel = await page.locator('[data-testid="status-scale"]').innerText();
    const r0 = await rows();
    // Cloud by clicks: straight track lines, scallops after Enter.
    await page.locator('[data-strip-tool="cloud"]').click();
    await page.mouse.click(600, 420); await page.waitForTimeout(100);
    await page.mouse.click(800, 420); await page.waitForTimeout(100);
    await page.mouse.click(800, 540); await page.waitForTimeout(100);
    for (let k = 1; k <= 5; k++) await page.mouse.move(800 - 30 * k, 540 + 5 * k);
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(outDir, 'q1-cloud-track.png'), clip: { x: 540, y: 380, width: 340, height: 230 } });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'q2-cloud-done.png'), clip: { x: 540, y: 380, width: 340, height: 230 } });
    // Cloud+ by drag: dashed box while dragging; empty comment kept.
    await page.locator('[data-strip-tool="cloudPlus"]').click();
    await page.mouse.move(950, 420); await page.mouse.down();
    for (let k = 1; k <= 8; k++) await page.mouse.move(950 + 20 * k, 420 + 12 * k);
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(outDir, 'q3-cloudplus-drag.png'), clip: { x: 900, y: 380, width: 300, height: 180 } });
    await page.mouse.up();
    await page.waitForTimeout(400);
    await page.mouse.move(1150, 360);
    await page.mouse.click(1160, 350);
    await page.waitForTimeout(300);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    r.rowsAfterEmptyComment = (await rows()) - r0;
    await shot(page, 'q4-empty-comment.png');
    // Double-click the empty box, type, Enter.
    await page.mouse.click(1195, 349);
    await page.waitForTimeout(120);
    await page.mouse.click(1195, 349);
    await page.waitForTimeout(400);
    r.editorOnDbl = await page.locator('[data-testid="callout-inline-editor"]').count();
    await page.keyboard.type('Filled in later');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    r.rowsAfterEdit = (await rows()) - r0;
    await shot(page, 'q5-filled.png');
    // Polylength magnet near a wall corner.
    await page.locator('[data-strip-tool="polyline"]').click();
    for (let k = 1; k <= 5; k++) await page.mouse.move(1392 - 2 * k, 358 - 3 * k);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'q6-magnet.png'), clip: { x: 1300, y: 250, width: 200, height: 140 } });
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
