// Sync alignment: both panes centred on the same sheet spot after each action.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2000);
    await page.locator('[data-testid="status-sync"]').click();
    await page.waitForTimeout(3500);
    const centres = () => page.evaluate(() => {
      const frac = (canvas) => {
        if (!canvas) return null;
        let sc = canvas.parentElement;
        while (sc && getComputedStyle(sc).overflow.indexOf('auto') === -1 && getComputedStyle(sc).overflowX !== 'auto') sc = sc.parentElement;
        if (!sc) return null;
        const cr = canvas.getBoundingClientRect();
        const vr = sc.getBoundingClientRect();
        return [+((vr.left + vr.width / 2 - cr.left) / cr.width).toFixed(3), +((vr.top + vr.height / 2 - cr.top) / cr.height).toFixed(3)];
      };
      const cs = [...document.querySelectorAll('canvas')].filter((c) => c.getBoundingClientRect().width > 200);
      const main = document.querySelector('canvas.block');
      const split = cs.filter((c) => c !== main && !c.className.includes('absolute')).pop();
      return { main: frac(main), split: frac(split) };
    });
    r.start = await centres();
    const mb = await page.locator('canvas.block').first().boundingBox();
    // main wheel zoom in at an off-centre point
    await page.mouse.move(Math.max(mb.x, 320) + 150, Math.max(mb.y, 200) + 120);
    for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -100); await page.waitForTimeout(70); }
    await page.waitForTimeout(1500);
    r.afterMainZoom = await centres();
    // split wheel zoom
    const splitBox = await page.evaluate(() => {
      const main = document.querySelector('canvas.block');
      const cs = [...document.querySelectorAll('canvas')].filter((c) => c !== main && !c.className.includes('absolute') && c.getBoundingClientRect().width > 200);
      const s = cs.pop();
      const pane = s.closest('[class*="overflow"]') || s.parentElement;
      const b = pane.getBoundingClientRect();
      return [b.left, b.top, b.width, b.height];
    });
    await page.mouse.move(splitBox[0] + splitBox[2] * 0.3, splitBox[1] + splitBox[3] * 0.4);
    for (let i = 0; i < 2; i++) { await page.mouse.wheel(0, 100); await page.waitForTimeout(70); }
    await page.waitForTimeout(1500);
    r.afterSplitZoom = await centres();
    // main scroll (pan)
    await page.mouse.move(Math.max(mb.x, 320) + 150, Math.max(mb.y, 200) + 120);
    await page.keyboard.down('Shift'); await page.mouse.wheel(0, 300); await page.keyboard.up('Shift');
    await page.waitForTimeout(1200);
    r.afterMainPan = await centres();
    r.zooms = await page.locator('text=/^\\d+%$/').allInnerTexts();
    await page.screenshot({ path: path.join(outDir, 's1.png') });
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r));
  await browser.close();
})();
