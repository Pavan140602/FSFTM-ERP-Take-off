// Drive the running dev app (localhost:5173) in headless Chrome and check
// Revu-style zoom anchoring, split-pane zoom and label rendering.
// Usage: node e2e_zoom.cjs <frontendDir> <outDir>
const path = require('path');
const fs = require('fs');
const frontend = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3]);
fs.mkdirSync(out, { recursive: true });
const { chromium } = require(path.join(frontend, 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const log = (...a) => console.log(...a);

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  try {
    await page.goto(BASE + '/login');
    const res = await page.request.post(BASE + '/api/v1/users/auth/demo-login/', {
      headers: { 'Content-Type': 'application/json' },
      data: { email: 'demo@openconstructionerp.com' },
    });
    log('demo-login', res.status());
    const body = await res.json();
    await page.evaluate(({ tok, refresh }) => {
      for (const st of [sessionStorage, localStorage]) {
        st.setItem('oe_access_token', tok);
        if (refresh) st.setItem('oe_refresh_token', refresh);
      }
      localStorage.setItem('oe_user_email', 'demo@openconstructionerp.com');
      localStorage.setItem('oe_onboarding_completed', 'true');
    }, { tok: body.access_token, refresh: body.refresh_token });
    await page.goto(BASE + '/takeoff');
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    await page.keyboard.press('Escape').catch(() => {});
    const tab = page.getByRole('button', { name: /measurements/i }).first();
    if (await tab.isVisible().catch(() => false)) await tab.click();
    await page.waitForTimeout(1500);
    await page.locator('input[type="file"]').first().setInputFiles(path.join(frontend, 'e2e/fixtures/multipage-test.pdf'));
    await page.locator('text=/^\\s*\\d+\\s*\\/\\s*\\d+\\s*$/').first().waitFor({ state: 'visible', timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.keyboard.press('Escape').catch(() => {});
    await page.screenshot({ path: path.join(out, '01-loaded.png') });

    // ── Main view: wheel zoom must keep the page point under the cursor ──
    const canvas = page.locator('canvas.block').first();
    const frac = async (cx, cy) => {
      const r = await canvas.boundingBox();
      return { fx: (cx - r.x) / r.width, fy: (cy - r.y) / r.height, w: r.width };
    };
    let r = await canvas.boundingBox();
    const cx = r.x + r.width * 0.3;
    const cy = r.y + r.height * 0.35;
    await page.mouse.move(cx, cy);
    const f0 = await frac(cx, cy);
    const results = [];
    for (const [label, dy, n] of [['in x5', -100, 5], ['out x3', 100, 3], ['in x8', -100, 8], ['out x10', 100, 10]]) {
      for (let i = 0; i < n; i++) {
        await page.mouse.wheel(0, dy);
        await page.waitForTimeout(60);
      }
      await page.waitForTimeout(700);
      const f = await frac(cx, cy);
      const r2 = await canvas.boundingBox();
      const driftPx = Math.hypot((f.fx - f0.fx) * r2.width, (f.fy - f0.fy) * r2.height);
      results.push({ step: label, pageWidthPx: Math.round(r2.width), driftPx: +driftPx.toFixed(2) });
    }
    log('MAIN wheel anchor drift (px, want < 2):', JSON.stringify(results));
    await page.screenshot({ path: path.join(out, '02-main-after-zoom.png') });

    // ── Labels: draw a distance and an area, screenshot ──
    await page.keyboard.press('Control+0').catch(() => {});
    await page.waitForTimeout(800);
    r = await canvas.boundingBox();
    const P = (fx, fy) => [r.x + r.width * fx, r.y + r.height * fy];
    await page.keyboard.press('d');
    for (const [fx, fy] of [[0.2, 0.3], [0.6, 0.3]]) { const [x, y] = P(fx, fy); await page.mouse.click(x, y); await page.waitForTimeout(150); }
    await page.keyboard.press('a');
    for (const [fx, fy] of [[0.2, 0.5], [0.6, 0.5], [0.6, 0.8]]) { const [x, y] = P(fx, fy); await page.mouse.click(x, y); await page.waitForTimeout(150); }
    { const [x, y] = P(0.2, 0.8); await page.mouse.dblclick(x, y); }
    await page.waitForTimeout(800);
    await page.keyboard.press('Escape');
    await page.screenshot({ path: path.join(out, '03-labels.png') });
    // zoom in on the labels at the distance midpoint
    { const [x, y] = P(0.4, 0.3); await page.mouse.move(x, y); for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, -100); await page.waitForTimeout(60); } }
    await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(out, '04-labels-zoomed.png') });

    // ── Split pane ──
    const splitBtn = page.locator('[aria-pressed][title*="plit" i], button[aria-label*="plit" i]').first();
    if (await splitBtn.isVisible().catch(() => false)) {
      await splitBtn.click();
      await page.waitForTimeout(2500);
      const sc = page.locator('canvas.rounded-\\[2px\\]').last();
      const sr = await sc.boundingBox();
      if (sr) {
        const sx = sr.x + sr.width * 0.4;
        const sy = sr.y + Math.min(sr.height * 0.4, 300);
        await page.mouse.move(sx, sy);
        const g0 = { fx: (sx - sr.x) / sr.width, fy: (sy - sr.y) / sr.height };
        const sres = [];
        for (const [label, dy, n] of [['in x5', -100, 5], ['out x7', 100, 7]]) {
          for (let i = 0; i < n; i++) { await page.mouse.wheel(0, dy); await page.waitForTimeout(60); }
          await page.waitForTimeout(700);
          const b = await sc.boundingBox();
          const d = Math.hypot(((sx - b.x) / b.width - g0.fx) * b.width, ((sy - b.y) / b.height - g0.fy) * b.height);
          sres.push({ step: label, pageWidthPx: Math.round(b.width), driftPx: +d.toFixed(2) });
        }
        log('SPLIT wheel anchor drift (px, want < 2):', JSON.stringify(sres));
        await page.screenshot({ path: path.join(out, '05-split.png') });
      } else log('split canvas not found');
    } else log('split button not found');
  } catch (e) {
    log('SCRIPT ERROR', e.message);
    await page.screenshot({ path: path.join(out, 'zz-error.png') }).catch(() => {});
  }
  log('page errors:', JSON.stringify(errors.slice(0, 8)));
  await browser.close();
})();
