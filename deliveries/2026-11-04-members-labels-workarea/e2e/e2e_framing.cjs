// Layout, on-line labels, Lay out framing (draw outline -> 24" O.C. members), then undo.
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
    await page.waitForTimeout(1200);
    r.videosBar = await page.locator('text=Videos for this step').count();
    r.ledgerBar = await box('[data-testid="takeoff-ledger-bar"]');
    await shot(page, 'f1-layout.png');
    // labels: select first beam row and zoom to it
    const rows = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]');
    await rows.first().click();
    await page.waitForTimeout(400);
    await page.mouse.move(900, 400);
    await page.keyboard.press('Shift+Digit3');
    await page.waitForTimeout(1600);
    await shot(page, 'f2-label.png');
    await page.keyboard.press('Escape');
    // fit page, draw an outline with the Area tool in an empty region (top-left of sheet)
    await page.keyboard.press('Control+Digit9');
    await page.waitForTimeout(1200);
    // leftover test outlines from an earlier run
    for (let k = 0; k < 3; k++) {
      const n0 = await rows.count();
      const t = (await rows.nth(n0 - 1).innerText());
      if (!/Area/.test(t) || !/Area \d/.test(t)) break;
      await rows.nth(n0 - 1).locator('td').nth(1).click();
      await page.mouse.move(900, 400);
      await page.keyboard.press('Delete');
      await page.waitForTimeout(800);
    }
    const before = await rows.count();
    r.before = before;
    await page.locator('[data-strip-tool="area"]').click();
    await page.waitForTimeout(300);
    const cb = await page.locator('canvas.block').first().boundingBox();
    const pt = (fx, fy) => [cb.x + cb.width * fx, cb.y + cb.height * fy];
    const poly = [pt(0.06, 0.10), pt(0.30, 0.10), pt(0.30, 0.30), pt(0.06, 0.30)];
    for (const [x, y] of poly) { await page.mouse.click(x, y); await page.waitForTimeout(150); }
    await page.mouse.dblclick(poly[0][0], poly[0][1]);
    await page.waitForTimeout(800);
    await page.keyboard.press('Escape');
    r.afterArea = await rows.count();
    // select the new area: last row
    await page.locator('[data-strip-tool="select"]').click();
    const lastRow = rows.nth((await rows.count()) - 1);
    r.lastRowText = (await lastRow.innerText()).replace(/\s+/g, ' ').slice(0, 80);
    await lastRow.locator('td').nth(1).click();
    await page.waitForTimeout(500);
    r.layoutBtn = await page.locator('[data-testid="props-layout-framing"]').count();
    if (r.layoutBtn) {
      await page.locator('[data-testid="props-layout-framing"]').click();
      await page.waitForTimeout(300);
      r.outline = await page.locator('[data-testid="framing-outline"]').innerText();
      await page.locator('[data-testid="framing-direction"]').selectOption('vertical');
      await page.locator('[data-testid="framing-spacing"]').fill('24');
      await page.locator('[data-testid="framing-create"]').click();
      await page.waitForTimeout(1200);
      r.afterFraming = await rows.count();
      await shot(page, 'f3-framing.png');
      // undo the members and the outline
      await page.mouse.move(900, 400);
      await page.keyboard.press('Control+KeyZ');
      await page.waitForTimeout(800);
      r.afterUndoMembers = await rows.count();
    }
    // remove the test outline
    const n = await rows.count();
    if (n > before) {
      await rows.nth(n - 1).locator('td').nth(1).click();
      await page.mouse.move(900, 400);
      await page.keyboard.press('Delete');
      await page.waitForTimeout(1500);
    }
    r.final = await rows.count();
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'fz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
