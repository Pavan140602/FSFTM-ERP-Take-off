// Up/Down + Ctrl+wheel page flips; zoomed page-flip time (until the new page is painted).
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  const pageNo = () => page.locator('[data-testid="pager-input"]').inputValue().catch(async () => (await page.locator('text=/^\\d+\\/\\d+$/').first().innerText()).split('/')[0]);
  const painted = (n) => page.waitForFunction((p) => document.querySelector('canvas.block')?.dataset.renderedPage === String(p), n, { timeout: 30000 }).then(() => true).catch(() => false);
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
    await page.waitForTimeout(2500);
    await page.mouse.move(1000, 450);
    await page.mouse.click(1000, 450); // focus the drawing, nothing selected
    await page.keyboard.press('Escape');
    r.start = await pageNo();
    await page.keyboard.press('ArrowUp');
    await page.waitForTimeout(600);
    r.afterUp = await pageNo();
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(600);
    r.afterDown = await pageNo();
    await page.keyboard.down('Control');
    await page.mouse.wheel(0, -100);
    await page.keyboard.up('Control');
    await page.waitForTimeout(600);
    r.afterCtrlWheelUp = await pageNo();
    await page.keyboard.down('Control');
    await page.mouse.wheel(0, 100);
    await page.keyboard.up('Control');
    await page.waitForTimeout(600);
    r.afterCtrlWheelDown = await pageNo();
    // zoom in, let the neighbours pre-render, then flip
    for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(60); }
    await page.waitForTimeout(1500);
    r.zoom = await page.locator('text=/^\\d+%$/').first().innerText().catch(() => '');
    await page.waitForTimeout(12000); // idle: next/previous pages render ahead
    const flips = [];
    for (const dir of ['ArrowUp', 'ArrowUp', 'ArrowDown']) {
      const before = Number(await pageNo());
      const want = dir === 'ArrowUp' ? before + 1 : before - 1;
      const t0 = Date.now();
      await page.keyboard.press(dir);
      await page.waitForTimeout(16);
      // something on screen: the canvas has non-white pixels in its centre
      await page.waitForFunction(() => {
        const c = document.querySelector('canvas.block');
        if (!c || !c.width) return false;
        const t = document.createElement('canvas');
        t.width = 240; t.height = 160;
        const g = t.getContext('2d');
        g.drawImage(c, 0, 0, 240, 160);
        const d = g.getImageData(0, 0, 240, 160).data;
        let dark = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 0 && d[i] < 200) dark++;
        return dark > 200;
      }, null, { timeout: 30000, polling: 30 }).catch(() => {});
      const shown = Date.now() - t0;
      const ok = await painted(want);
      flips.push({ to: want, previewMs: shown, sharpMs: Date.now() - t0, ok });
      await page.waitForTimeout(9000);
    }
    r.zoomedFlips = flips;
    await page.screenshot({ path: path.join(outDir, 'flip.png') });
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
