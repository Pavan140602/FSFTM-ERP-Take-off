// Markups list (Revu style), no profile text / column markers on the sheet, status bar.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('takeoff.sidebarTab', 'auto');
      localStorage.setItem('takeoff.rightPanelWidth', '380');
      localStorage.setItem('takeoff.ledgerHeight', '330');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(5000);
    // Ledger rows: Label + Material/Profile filled for auto markups
    const ledger = page.locator('[data-testid="takeoff-ledger-bar"]');
    const firstRows = await ledger.locator('tbody tr').evaluateAll((trs) => trs.slice(0, 6).map((tr) => tr.innerText.replace(/\s+/g, ' ').slice(0, 140)));
    r.ledgerRows = firstRows;
    r.labelCells = await page.locator('[data-testid^="ledger-label-"]').evaluateAll((els) => els.slice(0, 4).map((e) => e.textContent || e.value));
    r.materialCells = await page.locator('[data-testid^="ledger-material-"]').evaluateAll((els) => els.slice(0, 4).map((e) => e.textContent || e.value));
    await page.screenshot({ path: path.join(outDir, 'l1-workspace.png') });

    // Status bar cursor readout
    const c = await page.locator('canvas.block').first().boundingBox();
    await page.mouse.move(c.x + c.width * 0.5, c.y + c.height * 0.4); await page.mouse.move(c.x + c.width * 0.52, c.y + c.height * 0.42, { steps: 5 });
    await page.waitForTimeout(300);
    r.statusCursor = await page.locator('[data-testid="revu-status-cursor"]').innerText();
    r.statusText = (await page.locator('[data-testid="revu-status"]').innerText()).replace(/\s+/g, ' ');

    // Zoom into columns: there should be no column marker drawn, only highlight.
    const cols = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
    const heads = cols.locator(':scope > div > div > button.flex-1');
    await heads.first().click();
    await page.waitForTimeout(300);
    await cols.locator('[data-testid="auto-list-row"]').nth(1).click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(outDir, 'l2-column-selected.png') });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(outDir, 'l3-columns-hidden.png') });

    // Edit a profile from the Markups list Material/Profile cell.
    const mat = page.locator('[data-testid^="ledger-material-"]').first();
    await mat.click();
    await page.waitForTimeout(200);
    const input = page.locator('[data-testid^="ledger-material-"] input, input[data-testid^="ledger-material-"]').first();
    if (await input.count()) {
      await input.fill('w12x26');
      await input.press('Enter');
    } else {
      await page.keyboard.press('Control+A');
      await page.keyboard.type('w12x26');
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(800);
    r.beamGroupsAfterLedgerEdit = (await page.locator('[data-testid="auto-list-cat-beams"]').locator('xpath=..').locator(':scope > div > div > button.flex-1').allInnerTexts()).map((x) => x.replace(/\s+/g, ' ').slice(0, 40));
    await page.screenshot({ path: path.join(outDir, 'l4-ledger-edit.png') });
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await page.screenshot({ path: path.join(outDir, 'lz-error.png') }).catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
