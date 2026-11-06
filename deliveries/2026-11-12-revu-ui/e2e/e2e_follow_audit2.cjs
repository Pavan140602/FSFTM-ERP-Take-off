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
    // Give the sheet a scale first (so the scale question never covers the page).
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(600, 600);
    await page.mouse.click(700, 600);
    await page.waitForTimeout(600);
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    await page.keyboard.press('Control+z');
    const tools = (process.env.TOOLS || 'callout,cloud,rectangle,ellipse,polygon,pen,highlight').split(',');
    const clip = { x: 560, y: 260, width: 360, height: 220 };
    r.preview = {};
    for (const tl of tools) {
      const btn = page.locator(`[data-strip-tool="${tl}"]`);
      if (!(await btn.count()) || !(await btn.isVisible())) {
        const more = page.locator('[data-testid="revu-tool-strip-more"]');
        if (await more.count()) { await more.click(); await page.waitForTimeout(200); }
      }
      await page.locator(`[data-strip-tool="${tl}"]`).first().click();
      await page.waitForTimeout(200);
      await page.mouse.move(820, 400);
      await page.waitForTimeout(150);
      const before = await page.screenshot({ clip });
      if (tl === 'pen') { await page.mouse.move(620, 300); await page.mouse.down(); } else await page.mouse.click(620, 300);
      await page.waitForTimeout(150);
      if (['radius3Point', 'arc', 'angle'].includes(tl)) { await page.mouse.click(700, 330); await page.waitForTimeout(120); }
      for (let k = 1; k <= 3; k++) await page.mouse.move(620 + 33 * k, 300 + 16 * k);
      await page.waitForTimeout(250);
      const mid = await page.screenshot({ clip });
      for (let k = 4; k <= 7; k++) await page.mouse.move(620 + 33 * k, 300 + 22 * k);
      await page.waitForTimeout(250);
      const after = await page.screenshot({ clip });
      r.preview[tl] = !mid.equals(after);
      await page.screenshot({ path: path.join(outDir, `pa-${tl}.png`), clip });
      if (tl === 'pen') await page.mouse.up();
      if (!r.preview[tl]) await page.screenshot({ path: path.join(outDir, `pv-${tl}.png`), clip });
      await page.keyboard.press('Escape');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
      // Undo anything that got placed.
      await page.keyboard.press('Control+z');
      await page.waitForTimeout(150);
    }
    // Strip + more menu.
    r.recentBar = await page.locator('[data-testid="recent-tools-bar"]').count();
    r.stripCols = await page.locator('[data-testid="revu-tool-strip"]').getAttribute('data-cols');
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'strip.png') });
    if (await page.locator('[data-testid="revu-tool-strip-more"]').count()) {
      await page.locator('[data-testid="revu-tool-strip-more"]').click();
      await page.waitForTimeout(300);
      await shot(page, 'strip-more.png');
      r.moreItems = await page.locator('[data-testid="revu-tool-strip-menu"] [data-strip-tool]').count();
      await page.keyboard.press('Escape');
      await page.mouse.click(900, 700);
    }
    // Area by dragging a rectangle.
    const rows0 = await page.locator('tbody tr[tabindex="0"]').count();
    await page.locator('[data-strip-tool="area"]').click();
    await page.mouse.move(640, 420); await page.mouse.down();
    for (let k = 1; k <= 8; k++) await page.mouse.move(640 + 25 * k, 420 + 15 * k);
    await page.waitForTimeout(300);
    await shot(page, 'area-drag.png');
    await page.mouse.up();
    await page.waitForTimeout(800);
    r.areaRowsAdded = (await page.locator('tbody tr[tabindex="0"]').count()) - rows0;
    r.areaLastRow = await page.locator('tbody tr[tabindex="0"]').last().innerText().catch(() => '');
    await shot(page, 'area-done.png');
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
