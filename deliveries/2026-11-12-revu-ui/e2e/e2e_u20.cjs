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
    // 1. Copy / paste markups across pages (Home2).
    await page.locator('[data-testid="status-scale"]').click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="set-scale-pages-menu"]').click();
    await page.locator('[data-testid="set-scale-pages-all"]').click();
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    await page.locator('[data-strip-tool="cloud"]').click();
    await page.mouse.move(620, 420); await page.mouse.down(); await page.mouse.move(820, 520, { steps: 6 }); await page.mouse.up();
    await page.waitForTimeout(400);
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 600); await page.mouse.click(820, 600);
    await page.waitForTimeout(500);
    await page.locator('[data-strip-tool="select"]').click();
    const n0 = await rows();
    await page.locator('tbody tr[tabindex="0"]').nth(0).locator('td').nth(2).click();
    await page.locator('tbody tr[tabindex="0"]').nth(1).locator('td').nth(2).click({ modifiers: ['Shift'] });
    await page.waitForTimeout(200);
    await page.mouse.move(1000, 300);
    await page.keyboard.press('Control+Shift+C');
    await page.waitForTimeout(300);
    r.copiedToast = await page.getByText(/markups? copied/).count();
    const pin = await page.evaluateHandle(() => { for (const i of document.querySelectorAll('input')) { const t = i.parentElement?.innerText || ''; if (/of\s*\d+/.test(t)) return i; } return null; });
    await pin.asElement().fill('8'); await pin.asElement().press('Enter');
    await page.waitForTimeout(3000);
    await page.mouse.click(1000, 300);
    await page.keyboard.press('Control+Shift+V');
    await page.waitForTimeout(600);
    r.rowsAdded = (await rows()) - n0;
    r.pastedPages = await page.locator('tbody tr[tabindex="0"]').allInnerTexts().then((a) => a.map((t) => (t.match(/S-\d\.\d\d/) || [''])[0]));
    await shot(page, 'c1-pasted-p8.png');
    // 2. Delete Pages window (cancel) and Extract Pages window.
    await page.locator('[data-testid="thumbnail-item"][data-page="8"]').click({ button: 'right' });
    await page.locator('[data-testid="thumb-menu-delete"]').click();
    await page.waitForTimeout(300);
    r.deleteDlg = await page.locator('[data-testid="delete-pages-dialog"]').count();
    r.deleteLabel = await page.locator('[data-testid="pages-picker-input"]').inputValue();
    await shot(page, 'c2-delete.png');
    await page.locator('[data-testid="delete-pages-dialog"] button:has-text("Cancel")').click();
    await page.locator('[data-testid="thumbnail-item"][data-page="7"]').click();
    await page.locator('[data-testid="thumbnail-item"][data-page="8"]').click({ modifiers: ['Control'] });
    await page.locator('[data-testid="thumbnail-item"][data-page="8"]').click({ button: 'right' });
    await page.locator('[data-testid="thumb-menu-extract"]').click();
    await page.waitForTimeout(300);
    r.extractLabel = await page.locator('[data-testid="pages-picker-input"]').inputValue();
    await page.locator('[data-testid="ex-separate"]').check();
    await page.locator('[data-testid="ex-use-labels"]').check();
    await page.locator('[data-testid="ex-open-after"]').uncheck();
    await shot(page, 'c3-extract.png');
    const dls = [];
    page.on('download', (d) => dls.push(d.suggestedFilename()));
    await page.locator('[data-testid="ex-ok"]').click();
    await page.waitForTimeout(5000);
    r.extractFiles = dls;
    // 3. Page labels from the PDF itself.
    await page.locator('[data-testid="toolbar-close-pdf"]').click();
    await page.waitForTimeout(1500);
    await page.locator('input[type="file"][accept="application/pdf"]').first().setInputFiles(path.join(path.dirname(outDir), 'labels_A.pdf'));
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    r.labels = await page.locator('[data-testid="thumb-sheet-label"]').allInnerTexts();
    await page.locator('[data-testid="thumbnail-strip"]').screenshot({ path: path.join(outDir, 'c4-labels.png') });
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
