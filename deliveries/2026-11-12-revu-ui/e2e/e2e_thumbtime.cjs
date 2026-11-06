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
  page.on('console', (m) => { if (m.text().includes('TEMP-PERF')) console.error(m.text()); });
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
    const t0 = Date.now();
    const marks = {};
    for (let k = 0; k < 120; k++) {
      const n = await page.locator('[data-testid="thumbnail-strip"] img').count();
      for (const want of [1, 3, 5, 8, 12]) if (n >= want && !marks[want]) marks[want] = Date.now() - t0;
      if (n >= 12) break;
      await page.waitForTimeout(250);
    }
    r.thumbMs = marks;
    r.visibleItems = await page.evaluate(() => { const s = document.querySelector('[data-testid="thumbnail-strip"]'); if (!s) return 0; const sr = s.getBoundingClientRect(); return [...s.querySelectorAll('[data-testid="thumbnail-item"]')].filter((e) => { const r = e.getBoundingClientRect(); return r.bottom > sr.top && r.top < sr.bottom + 300; }).length; });
    // Scroll the strip down: how fast do far pages fill?
    console.error('TEMP-PERF ==== SCROLL at', await page.evaluate(() => Math.round(performance.now())));
    await page.evaluate(() => { const s = document.querySelector('[data-testid="thumbnail-strip"]'); if (s) s.scrollTop = s.scrollHeight / 2; });
    const t1 = Date.now();
    const before = await page.locator('[data-testid="thumbnail-strip"] img').count();
    let after = before; let tFill = null;
    for (let k = 0; k < 80; k++) { after = await page.locator('[data-testid="thumbnail-strip"] img').count(); if (after >= before + 4) { tFill = Date.now() - t1; break; } await page.waitForTimeout(250); }
    r.scrollFill4Ms = tFill; r.afterScroll = after - before;

    // Warm: reload the same drawing (IndexedDB cache).
    await page.reload();
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 180000 });
    const t2 = Date.now();
    const warm = {};
    for (let k = 0; k < 80; k++) {
      const n = await page.locator('[data-testid="thumbnail-strip"] img').count();
      for (const want of [1, 5, 8]) if (n >= want && !warm[want]) warm[want] = Date.now() - t2;
      if (n >= 8) break;
      await page.waitForTimeout(150);
    }
    r.warmMs = warm;
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
