const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const shot = (page, n) => page.screenshot({ path: path.join(outDir, n) });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1700, height: 1000 }, acceptDownloads: true, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await ctx.newPage();
  const r = {};
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  const dls = [];
  page.on('download', async (d) => { const f = path.join(outDir, d.suggestedFilename()); await d.saveAs(f).catch(() => {}); dls.push(d.suggestedFilename()); });
  try {
    await page.goto(BASE + '/login', { timeout: 120000 });
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    await page.evaluate(({ tok }) => { localStorage.clear(); for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok); localStorage.setItem('oe_onboarding_completed', 'true'); }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements`);
    await page.waitForTimeout(3000);
    await page.locator('input[type="file"][accept="application/pdf"]').first().setInputFiles(path.join(__dirname, 'shots_u15', 'saved2.pdf'));
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    await page.waitForTimeout(4000);
    await page.locator('[data-testid="thumbnail-strip"]').screenshot({ path: path.join(outDir, 'd1-thumbs.png') });
    // Text select on page 1 (general notes).
    await page.locator('[data-testid="bottom-tool-text"]').click();
    await page.mouse.move(470, 290); await page.mouse.down(); await page.mouse.move(900, 360, { steps: 6 }); await page.mouse.up();
    await page.waitForTimeout(1500);
    r.textSelBoxes = await page.locator('[data-testid="text-sel-box"]').count();
    r.clip = (await page.evaluate(() => navigator.clipboard.readText().catch(() => ''))).slice(0, 120);
    await shot(page, 'd2-textsel.png');
    await page.locator('[data-testid="bottom-tool-select"]').click();
    // Highlight snaps to the words.
    const rows = () => page.locator('tbody tr[tabindex="0"]').count();
    const r0 = await rows();
    await page.locator('[data-strip-tool="highlight"]').click();
    await page.mouse.move(470, 400); await page.mouse.down(); await page.mouse.move(900, 450, { steps: 6 }); await page.mouse.up();
    await page.waitForTimeout(1500);
    r.highlightsAdded = (await rows()) - r0;
    await shot(page, 'd3-highlight.png');
    // Ctrl+C / Ctrl+V.
    await page.locator('[data-strip-tool="select"]').click();
    await page.locator('tbody tr[tabindex="0"]').last().locator('td').nth(2).click();
    await page.mouse.move(1200, 700);
    await page.keyboard.press('Control+c');
    await page.waitForTimeout(300);
    const pin = await page.evaluateHandle(() => { for (const i of document.querySelectorAll('input')) { const t = i.parentElement?.innerText || ''; if (/of\s*\d+/.test(t)) return i; } return null; });
    await pin.asElement().fill('2'); await pin.asElement().press('Enter');
    await page.waitForTimeout(2500);
    const r1 = await rows();
    await page.mouse.click(1200, 700);
    await page.keyboard.press('Control+v');
    await page.waitForTimeout(600);
    r.pasted = (await rows()) - r1;
    // Delete window: Custom option.
    await page.locator('[data-testid="thumbnail-item"][data-page="2"]').click({ button: 'right' });
    await page.locator('[data-testid="thumb-menu-delete"]').click();
    await page.locator('[data-testid="pages-picker-menu"]').click();
    r.pickerOptions = await page.locator('[data-testid^="pages-picker-"]').filter({ hasNot: page.locator('svg') }).allInnerTexts();
    await shot(page, 'd4-picker.png');
    await page.locator('[data-testid="pages-picker-current"]').click();
    await page.locator('[data-testid="delete-pages-dialog"] button:has-text("Cancel")').click();
    await page.waitForTimeout(300);
    // New PDF.
    await page.locator('[data-testid="toolbar-new-pdf"]').click();
    await page.locator('[data-testid="newpdf-custom-mode"]').check();
    await page.locator('[data-testid="newpdf-w"]').fill('24');
    await page.locator('[data-testid="newpdf-h"]').fill('36');
    await page.locator('[data-testid="newpdf-landscape"]').check();
    await page.locator('[data-testid="newpdf-pages"]').fill('2');
    r.newSize = await page.locator('[data-testid="newpdf-size"]').innerText();
    await shot(page, 'd5-newpdf.png');
    await page.locator('[data-testid="newpdf-ok"]').click();
    await page.waitForTimeout(2500);
    // Combine with a file.
    await page.locator('[data-testid="toolbar-combine"]').click();
    await page.locator('[data-testid="combine-file-input"]').setInputFiles(path.join(__dirname, 'labels_A.pdf'));
    await page.waitForTimeout(300);
    r.combineList = await page.locator('[data-testid="combine-list"] > div').count();
    await shot(page, 'd6-combine.png');
    await page.locator('[data-testid="combine-ok"]').click();
    await page.waitForTimeout(6000);
    r.downloads = dls;
  } catch (e) { r.fail = String(e).slice(0, 300); await shot(page, 'fail.png').catch(() => {}); }
  r.errors = errors;
  console.log(JSON.stringify(r));
  await browser.close();
})();
