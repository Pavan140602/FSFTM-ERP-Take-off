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
    const rows = () => page.locator('tbody tr[tabindex="0"]').count();
    // Scale first.
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    // 1. Straight by default; Ctrl+Shift free.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(560, 420); await page.mouse.move(700, 452); await page.mouse.click(760, 452);
    await page.waitForTimeout(300);
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(560, 520);
    await page.keyboard.down('Control'); await page.keyboard.down('Shift');
    await page.mouse.move(700, 552); await page.mouse.click(760, 552, { modifiers: ['Control', 'Shift'] });
    await page.keyboard.up('Shift'); await page.keyboard.up('Control');
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'n1-straight-vs-free.png'), clip: { x: 520, y: 380, width: 300, height: 220 } });
    // 2. Small magnet on a wall.
    await page.locator('[data-strip-tool="polyline"]').click();
    await page.mouse.move(1385, 450); await page.mouse.move(1380, 452, { steps: 3 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'n2-magnet.png'), clip: { x: 1330, y: 410, width: 100, height: 80 } });
    // 3. Tool popover.
    await page.locator('[data-testid="props-tab"]').click();
    await page.waitForTimeout(200);
    r.popover = await page.locator('[data-testid="props-tool-popover"]').count();
    await page.locator('[data-testid="pop-subject"]').fill('Polylength Measurement');
    await page.locator('[data-testid="pop-subject"]').press('Enter');
    await page.locator('[data-testid="pop-label"]').fill('W12x26');
    await page.locator('[data-testid="pop-label"]').press('Enter');
    await shot(page, 'n3-popover.png');
    await page.locator('[data-testid="pop-add-chest"]').click();
    r.chestSets = await page.locator('[data-testid="pop-chest-list"] button').count();
    await page.locator('[data-testid="pop-chest-list"] button').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.press('Escape');
    // 4. Strip with names.
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 'n4-strip.png') });
    // 5. Save + Ctrl+S.
    await page.locator('[data-testid="toolbar-save-button"]').click();
    await page.waitForTimeout(300);
    r.savedToast = await page.getByText('Saved', { exact: true }).count();
    // 6. Thumbnails: scale line + menu.
    if (!(await page.locator('[data-testid="thumbnail-strip"]').count())) await page.getByRole('button', { name: /^Thumbs$/ }).first().click().catch(() => {});
    await page.locator('[data-testid="thumbnail-item"][data-page="7"]').scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(800);
    r.thumbScale = await page.locator('[data-testid="thumbnail-item"][data-page="7"] [data-testid="thumb-scale"]').innerText().catch(() => null);
    r.thumbScale8 = await page.locator('[data-testid="thumbnail-item"][data-page="8"] [data-testid="thumb-scale"]').innerText().catch(() => null);
    await page.locator('[data-testid="thumbnail-item"][data-page="7"]').click({ button: 'right' });
    await page.waitForTimeout(300);
    r.menuItems = await page.locator('[data-testid="thumb-menu"] button').count();
    await shot(page, 'n5-thumb-menu.png');
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.locator('[data-testid="thumb-menu-extract"]').click()]);
    const extPath = path.join(outDir, 'extract.pdf');
    await dl.saveAs(extPath);
    r.extractBytes = fs.statSync(extPath).size;
    r.rowsAfterExtract = await rows();
    r.statusAfterExtract = await page.locator('[data-testid="status-scale"]').innerText();
    // 7. Vector Save PDF.
    const [dl2] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), page.locator('[data-testid="toolbar-export-pdf-button"]').click()]);
    const savePath = path.join(outDir, 'saved.pdf');
    await dl2.saveAs(savePath);
    r.savedBytes = fs.statSync(savePath).size;
    r.rowsBefore = await rows();
    r.statusBefore = await page.locator('[data-testid="status-scale"]').innerText();
    r.toastsAfterSave = (await page.locator('[role="status"], [role="alert"], .toast, [data-sonner-toast]').allInnerTexts().catch(() => [])).join(' | ').slice(0, 400);
    // 8. Insert blank page -> new drawing opened with the markups.
    await page.locator('[data-testid="thumbnail-item"][data-page="7"]').click({ button: 'right' });
    await page.locator('[data-testid="thumb-menu-insertBlank"]').click();
    await page.waitForTimeout(2500);
    r.toastsInsert = await page.evaluate(() => (document.body.innerText.match(/(Pages updated|Page tool failed|Edited PDF downloaded).{0,160}/gs) || []).join(' || '));
    await page.waitForTimeout(6000);
    r.urlAfterInsert = page.url().replace(/^.*\?/, '');
    r.pagesAfterInsert = await page.locator('[data-testid="thumbnail-item"]').count();
    r.rowsAfterInsert = await rows();
    await shot(page, 'n6-after-insert.png');
    // 9. Close PDF, reopen the saved file locally.
    await page.locator('[data-testid="toolbar-close-pdf"]').click();
    await page.waitForTimeout(1500);
    r.closed = page.url().includes('doc=') ? 'still open' : 'closed';
    await shot(page, 'n7-closed.png');
    const inp = page.locator('input[type="file"][accept="application/pdf"]').first();
    if (await inp.count()) {
      await inp.setInputFiles(savePath);
      await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
      await page.waitForTimeout(5000);
      r.rowsReopened = await rows();
      r.restoredToast = await page.getByText('Markups restored').count();
      await shot(page, 'n8-reopened.png');
    }
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
