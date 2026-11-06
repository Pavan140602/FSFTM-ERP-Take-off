// Revu default layout, vertical icon tabs, sheet-number thumbnails, first-page-first, sync & compare.
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
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    // A fresh user: no saved panel layout -> the default (Revu) screen.
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    const t0 = Date.now();
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=ac_full.pdf`);
    // First page painted = the main canvas has a real bitmap.
    await page.waitForFunction(() => {
      const c = document.querySelector('canvas.block');
      return c && c.width > 400;
    }, null, { timeout: 120000 });
    r.firstPageMs = Date.now() - t0;
    await page.waitForTimeout(800);
    r.thumbsAtFirstPage = await page.locator('[data-testid="thumbnail-item"] img').count();
    await shot(page, 'b1-first-page.png');
    await page.waitForTimeout(9000);
    r.thumbsAfter10s = await page.locator('[data-testid="thumbnail-item"] img').count();
    r.sheetLabels = (await page.locator('[data-testid="thumb-sheet-label"]').allInnerTexts()).slice(0, 8);
    r.tabRail = await page.locator('[role="tablist"][aria-orientation="vertical"] [role="tab"]').evaluateAll((els) => els.map((e) => `${e.getAttribute('aria-label')}:${(e.textContent || '').trim()}`));
    r.thumbImg = await page.locator('[data-testid="thumbnail-item"] img').first().evaluate((im) => `${im.naturalWidth}x${im.naturalHeight} shown ${Math.round(im.getBoundingClientRect().width)}px`).catch(() => null);
    await shot(page, 'b2-default-screen.png');
    // Close-up of the strip
    await page.locator('[data-testid="revu-left-panel"]').screenshot({ path: path.join(outDir, 'b3-strip.png') });

    // Edit a sheet label on a thumbnail
    const lbl = page.locator('[data-testid="thumb-sheet-label"]').nth(1);
    await lbl.click();
    await page.locator('[data-testid="thumb-sheet-input"]').fill('S0.01');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(300);
    r.editedLabel = await page.locator('[data-testid="thumb-sheet-label"]').nth(1).innerText();

    // Sync & compare from the status bar
    await page.locator('[data-testid="status-sync"]').click();
    await page.waitForTimeout(3500);
    r.splitOn = await page.locator('[data-testid="viewmode-split-vertical"]').getAttribute('aria-pressed');
    r.syncPressed = await page.locator('[data-testid="status-sync"]').getAttribute('aria-pressed');
    await page.locator('[data-testid="pager-next"]').click();
    await page.waitForTimeout(4000);
    await shot(page, 'b4-sync.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'bz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
