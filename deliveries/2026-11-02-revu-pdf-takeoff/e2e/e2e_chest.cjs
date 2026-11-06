// Markups list follows sheet units; Subject/Label columns; Revu Tool Chest.
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
  const has = (sel) => page.locator(sel).count();
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
    r.headers = (await page.locator('[data-testid="takeoff-ledger-bar"] thead th').allInnerTexts()).map((x) => x.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 9);
    const rows = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]');
    const cells = async (i) => (await rows.nth(i).locator('td').allInnerTexts()).map((x) => x.trim());
    r.row0Default = (await cells(0)).slice(0, 10);
    // status bar unit = ft-in -> list must read ft-in too
    await page.locator('select').filter({ hasText: 'Units: as calibrated' }).first().selectOption({ label: 'Units: ft-in' }).catch(async () => {
      const sel = page.locator('select').filter({ hasText: 'as calibrated' }).first();
      const opts = await sel.locator('option').allInnerTexts();
      r.unitOpts = opts;
      const ftin = opts.find((o) => /ft-in/i.test(o));
      if (ftin) await sel.selectOption({ label: ftin });
    });
    await page.waitForTimeout(500);
    r.row0GlobalFtIn = (await cells(0)).slice(0, 10);
    // per-markup unit mm via Properties bar
    await rows.first().click();
    await page.waitForTimeout(500);
    await page.locator('[data-testid="props-unit"]').selectOption('mm');
    await page.waitForTimeout(400);
    r.row0MarkupMm = (await cells(0)).slice(0, 10);
    r.totalsMm = await page.locator('[data-testid="props-totals"]').innerText().catch(() => null);
    await page.locator('[data-testid="props-unit"]').selectOption('');
    await page.waitForTimeout(300);
    await shot(page, 'c1-list.png');

    // Tool Chest
    await page.locator('[data-testid="rail-tools"]').click();
    await page.waitForTimeout(400);
    r.chest = await has('[data-testid="revu-tool-chest"]');
    r.sets = await page.locator('[data-testid="revu-tool-chest"] section header').allInnerTexts();
    await page.locator('[data-testid="props-add-to-chest"]').click();
    await page.waitForTimeout(400);
    r.setsAfterAdd = await page.locator('[data-testid="revu-tool-chest"] section header').allInnerTexts();
    await shot(page, 'c2-chest.png');
    const item = page.locator('[data-testid="chest-set-my-tools"] [data-testid^="chest-item-"]').first();
    r.itemTitle = await item.getAttribute('title');
    // draw with it
    await page.mouse.move(900, 400);
    await page.keyboard.press('Escape');
    await item.click();
    await page.waitForTimeout(300);
    r.activeAfterItem = await page.locator('[data-strip-tool][aria-pressed="true"]').getAttribute('data-strip-tool');
    const before = await rows.count();
    const cb = await page.locator('canvas.block').first().boundingBox();
    void cb;
    await page.mouse.click(800, 470);
    await page.waitForTimeout(250);
    await page.mouse.click(1050, 470);
    await page.waitForTimeout(1200);
    r.rowsBeforeAfter = [before, await rows.count()];
    r.recent = await page.locator('[data-testid="chest-set-recent"] [data-testid^="chest-item-"]').count();
    r.newRow = (await page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]').allInnerTexts()).map((x) => x.replace(/\s+/g, ' ')).filter((x) => !/Beams: W12X26/.test(x) || /^\s*81/.test(x)).slice(-1);
    await shot(page, 'c3-drawn.png');
    // list view
    await page.locator('[data-testid="chest-view-list"]').click();
    await page.waitForTimeout(200);
    await shot(page, 'c4-list-view.png');
    await page.locator('[data-testid="chest-view-icons"]').click();
    // undo the test line
    await page.keyboard.press('Escape');
    await page.keyboard.press('Control+KeyZ');
    await page.waitForTimeout(1500);
    r.rowsAfterUndo = await rows.count();
    await page.locator('[data-testid="rail-scale"]').click();
    await page.waitForTimeout(300);
    r.scalePresets = await page.locator('[data-testid="revu-scale-presets"]').count();
    await page.locator('[data-testid="rail-tools"]').click();
    await page.waitForTimeout(300);
    r.scaleInChest = await page.locator('[data-testid="measurements-panel"] >> text=Imperial').count();
    await shot(page, 'c5-chest-clean.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'cz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
