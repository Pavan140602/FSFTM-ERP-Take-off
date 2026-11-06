// Open + zoom timing: first page painted, markups loaded, main-thread busy time, zoom re-render.
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
  const reqs = [];
  page.on('requestfinished', async (rq) => {
    const u = rq.url();
    if (!u.includes('/api/')) return;
    const t = rq.timing();
    reqs.push({ u: u.replace(/^.*\/api/, '').slice(0, 90), ms: Math.round(t.responseEnd) });
  });
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.addInitScript(() => {
      window.__long = [];
      try {
        new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__long.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({ type: 'longtask', buffered: true });
      } catch {}
    });
    const t0 = Date.now();
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    r.firstPageMs = Date.now() - t0;
    await page.waitForFunction(() => document.querySelectorAll('[data-testid="ledger-row"]').length > 0, null, { timeout: 60000 }).catch(() => {});
    r.markupsMs = Date.now() - t0;
    await page.waitForTimeout(8000);
    const long = await page.evaluate(() => window.__long);
    r.longTasks = { count: long.length, totalMs: long.reduce((s, x) => s + x[1], 0), worst: long.sort((a, b) => b[1] - a[1]).slice(0, 6) };
    // zoom: time until the page bitmap is re-rendered at the new zoom
    const zoomCase = async (label, deltas) => {
      const w0 = await page.evaluate(() => document.querySelector('canvas.block').width);
      const ts = Date.now();
      await page.mouse.move(1000, 450);
      for (const d of deltas) { await page.mouse.wheel(0, d); await page.waitForTimeout(40); }
      const sinceInput = Date.now();
      await page.waitForFunction((w) => document.querySelector('canvas.block').width !== w, w0, { timeout: 30000 }).catch(() => {});
      const w1 = await page.evaluate(() => document.querySelector('canvas.block').width);
      r[label] = { rerenderMs: Date.now() - sinceInput, widthBefore: w0, widthAfter: w1, zoom: await page.locator('text=/^\\d+%$/').first().innerText().catch(() => '') };
    };
    await zoomCase('zoomIn', [-120, -120, -120, -120, -120]);
    await page.waitForTimeout(2500);
    {
      // deep zoom: time until the sharp visible-region tile is showing
      await page.evaluate(() => { const d = document.querySelector('canvas.pointer-events-none.absolute[aria-hidden="true"]'); if (d) d.style.display = 'none'; });
      await page.mouse.move(1000, 450);
      for (const d of [-120, -120, -120, -120, -120, -120]) { await page.mouse.wheel(0, d); await page.waitForTimeout(40); }
      const ts = Date.now();
      await page.waitForFunction(() => [...document.querySelectorAll('canvas.pointer-events-none.absolute[aria-hidden="true"]')].some((c) => c.style.display === 'block' && c.width > 100), null, { timeout: 30000 }).catch(() => {});
      r.zoomInDeep = { tileMs: Date.now() - ts, zoom: await page.locator('text=/^\d+%$/').first().innerText().catch(() => '') };
    }
    await page.waitForTimeout(2500);
    await zoomCase('zoomOut', [120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120]);
    await page.waitForTimeout(2500);
    const long2 = await page.evaluate(() => window.__long);
    r.longAfterZoom = { count: long2.length, totalMs: long2.reduce((s, x) => s + x[1], 0) };
    r.slowApi = reqs.sort((a, b) => b.ms - a.ms).slice(0, 8);
    r.apiCount = reqs.length;
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
