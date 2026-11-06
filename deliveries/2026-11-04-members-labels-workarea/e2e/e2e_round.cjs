// Compact work area, member types, on-line labels, Create account.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
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
  const box = async (sel) => { const b = await page.locator(sel).first().boundingBox().catch(() => null); return b ? [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] : null; };
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
    await page.waitForTimeout(1500);
    const ws = page.locator('[data-testid="revu-workspace-toggle"]');
    if ((await ws.innerText()).includes('Exit')) await ws.click();
    await page.waitForTimeout(1000);
    r.normal = { viewerCanvasArea: await box('[data-testid="revu-tool-strip"]'), filmstripCurrent: await page.locator('[data-testid="filmstrip-current"]').count() };
    await shot(page, 'n1-normal.png');
    // Auto Takeoff panel member types
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(700);
    r.types = await page.locator('[data-testid^="auto-type-"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-testid').slice(10)));
    // run beams only on this sheet
    for (const t of r.types) {
      const cb = page.locator(`[data-testid="auto-type-${t}"]`);
      const want = t === 'beam' || t === 'column';
      if ((await cb.isChecked()) !== want) await cb.click();
    }
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(12000);
    r.result = (await page.locator('[data-testid="auto-result"]').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
    await page.locator('[data-testid="rail-auto"]').click();
    await page.mouse.move(1000, 450);
    for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(80); }
    await page.waitForTimeout(1500);
    await shot(page, 'n2-labels.png');
    // Users: Create account form exists
    await page.goto(`${BASE}/users`);
    await page.waitForTimeout(2500);
    r.createButton = await page.locator('[data-testid="users-create-account"]').count();
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'nz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
