// End-to-end check of Auto Takeoff in the running app (headless Chrome).
// Usage: node e2e_auto.cjs <frontendDir> <outDir> <docId> <email> <password>
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
const out = path.resolve(outDir);
fs.mkdirSync(out, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const log = (...a) => console.log(...a);
const shot = (page, name) => page.screenshot({ path: path.join(out, name) });

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const results = {};
  try {
    await page.goto(BASE + '/login');
    const res = await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } });
    const body = await res.json();
    log('login', res.status());
    await page.evaluate(({ tok, refresh, email }) => {
      for (const st of [sessionStorage, localStorage]) {
        st.setItem('oe_access_token', tok);
        if (refresh) st.setItem('oe_refresh_token', refresh);
      }
      localStorage.setItem('oe_user_email', email);
      localStorage.setItem('oe_onboarding_completed', 'true'); localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
      localStorage.setItem('takeoff.sidebarTab', 'auto');
    }, { tok: body.access_token, refresh: body.refresh_token, email: EMAIL });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf&project=c36f0df4-3be0-4dee-a063-64212295c1c3`);
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(3000);
    results.detectTabPresent = await page.locator('[data-testid="sidebar-tab-detect"]').count();
    const autoTab = page.locator('[data-testid="sidebar-tab-auto"]');
    results.autoTabPresent = await autoTab.count();
    if (results.autoTabPresent) await autoTab.first().click();
    await page.waitForTimeout(800);
    await shot(page, '01-auto-tab.png');

    // Run on this sheet (page 1 = AC Retreat framing plan).
    await page.locator('[data-testid="auto-run"]').click();
    await page.locator('[data-testid="auto-result"]').waitFor({ timeout: 120000 });
    await page.waitForFunction(() => !document.querySelector('[data-testid="auto-run"]')?.textContent?.includes('Reading'), null, { timeout: 180000 }); await page.waitForTimeout(800);
    await page.waitForTimeout(1500);
    results.firstRun = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    await shot(page, '02-after-run.png');

    // List: expand Columns + Beams groups.
    results.listCats = await page.locator('[data-testid^="auto-list-cat-"]').allInnerTexts();
    const colGroupBtns = page.locator('[data-testid="auto-list-cat-columns"] + div button.flex-1');
    // open every columns size group
    const colCat = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
    const groupHeads = colCat.locator(':scope > div > div > button.flex-1');
    const ng = await groupHeads.count();
    for (let i = 0; i < ng; i++) await groupHeads.nth(i).click();
    await page.waitForTimeout(500);
    results.columnGroups = (await groupHeads.allInnerTexts()).map((t) => t.replace(/\s+/g, ' '));
    const rows = page.locator('[data-testid="auto-list-row"]');
    results.rowsVisible = await rows.count();
    await page.locator('[data-testid="auto-list"]').screenshot({ path: path.join(out, '03-list.png') });

    // Click the first column row -> selected + zoom on the sheet.
    const firstColRow = colCat.locator('[data-testid="auto-list-row"]').first();
    results.firstColRowText = (await firstColRow.innerText()).replace(/\s+/g, ' ');
    await firstColRow.click();
    await page.waitForTimeout(1500);
    results.rowSelectedAfterListClick = await colCat.locator('[data-testid="auto-list-row"].bg-oe-blue\\/15, [data-testid="auto-list-row"][class*="bg-oe-blue/15"]').count();
    await shot(page, '04-row-click-zoomed.png');

    // Height: type on the first column row, then on a group.
    const h = colCat.locator('[data-testid="auto-col-height"]').nth(2);
    await h.fill(`12'-6"`);
    await h.press('Enter');
    await page.waitForTimeout(500);
    results.heightAfterEnter = await h.inputValue();

    // Fit page, then click a column on the canvas: pick a column point from the API.
    await page.keyboard.press('Control+0').catch(() => {});
    await page.waitForTimeout(1500);
    const api = await page.request.post(`${BASE}/api/v1/takeoff/documents/${DOC}/auto-takeoff/`, {
      headers: { Authorization: `Bearer ${body.access_token}` },
      data: { pages: [1], categories: ['columns'] },
    });
    const apiJson = await api.json();
    const cols = apiJson.pages[0].items.filter((i) => i.category === 'columns');
    const target = cols[Math.min(9, cols.length - 1)];
    const canvas = page.locator('canvas.block').first();
    const box = await canvas.boundingBox();
    const k = box.width / 2592; // AC Retreat sheet width in PDF points
    // Make sure the select tool is active.
    await page.keyboard.press('v').catch(() => {});
    await page.mouse.click(box.x + target.points[0][0] * k, box.y + target.points[0][1] * k);
    await page.waitForTimeout(1200);
    const selRows = page.locator('[data-testid="auto-list-row"][class*="bg-oe-blue/15"]');
    results.canvasClickSelectsRows = await selRows.count();
    results.canvasClickRowText = results.canvasClickSelectsRows ? (await selRows.first().innerText()).replace(/\s+/g, ' ') : null;
    results.canvasClickTarget = target.label;
    await shot(page, '05-canvas-click.png');

    // Delete exactly that one column from the list (two clicks).
    const before = await page.locator('[data-testid="auto-list-cat-columns"]').innerText();
    if (results.canvasClickSelectsRows) {
      const del = selRows.first().locator('[data-testid="auto-list-delete"]');
      await del.click();
      await del.click();
      await page.waitForTimeout(800);
    }
    const after = await page.locator('[data-testid="auto-list-cat-columns"]').innerText();
    results.columnsBeforeAfterDelete = [before.replace(/\s+/g, ' '), after.replace(/\s+/g, ' ')];

    // Re-run: nothing doubles, deleted one stays deleted.
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(500); await page.waitForFunction(() => !document.querySelector('[data-testid="auto-run"]')?.textContent?.includes('Reading'), null, { timeout: 180000 }); await page.waitForTimeout(800);
    results.rerun = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    results.columnsAfterRerun = (await page.locator('[data-testid="auto-list-cat-columns"]').innerText()).replace(/\s+/g, ' ');
    await shot(page, '06-rerun.png');

    // Persistence: wait for save, reload, check the height is still there.
    await page.waitForTimeout(5000);
    await page.reload();
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(4000);
    const at = page.locator('[data-testid="sidebar-tab-auto"]');
    if (await at.count()) await at.first().click();
    await page.waitForTimeout(1000);
    const colCat2 = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
    const heads2 = colCat2.locator(':scope > div > div > button.flex-1');
    for (let i = 0; i < (await heads2.count()); i++) await heads2.nth(i).click();
    await page.waitForTimeout(500);
    const heights = await colCat2.locator('[data-testid="auto-col-height"]').evaluateAll((els) => els.map((e) => e.value).filter(Boolean));
    results.heightsAfterReload = heights;
    results.columnsAfterReload = (await page.locator('[data-testid="auto-list-cat-columns"]').innerText().catch(() => '')).replace(/\s+/g, ' ');
    await shot(page, '07-after-reload.png');

    // Zoom into the highlighted profile text near a beam.
    await page.locator('[data-testid="auto-list-cat-beams"]').click().catch(() => {});
  } catch (e) {
    results.error = String(e).slice(0, 500);
    await shot(page, 'zz-error.png').catch(() => {});
  }
  log(JSON.stringify(results, null, 1));
  log('page errors:', JSON.stringify(errors.slice(0, 6)));
  await browser.close();
})();
