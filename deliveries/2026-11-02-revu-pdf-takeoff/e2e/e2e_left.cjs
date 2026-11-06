// Left panel (thumbnails / page index / layers), status scale + units, label font, overlay, sync.
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
    await page.evaluate(({ tok }) => {
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('takeoff.sidebarTab', 'colours');
      localStorage.setItem('takeoff.leftStripWidth', '240');
      localStorage.setItem('takeoff.showThumbnails', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(7000);
    r.leftPanel = await page.locator('[data-testid="revu-left-panel"]').count();
    r.thumbImgs = await page.locator('[data-testid="thumbnail-item"] img').count();
    r.thumbNatural = await page.locator('[data-testid="thumbnail-item"] img').first().evaluate((im) => `${im.naturalWidth}x${im.naturalHeight} shown ${Math.round(im.getBoundingClientRect().width)}px`).catch(() => null);
    r.thumbCaptions = (await page.locator('[data-testid="thumbnail-item"] > span').allInnerTexts()).map((x) => x.replace(/\s+/g, ' '));
    await shot(page, 'a1-thumbs.png');

    await page.locator('[data-testid="left-tab-index"]').click();
    await page.waitForTimeout(400);
    r.indexNums = await page.locator('[data-testid="page-index-num"]').evaluateAll((els) => els.map((e) => e.value));
    r.indexTitles = await page.locator('[data-testid="page-index-title"]').evaluateAll((els) => els.map((e) => e.value));
    const t3 = page.locator('[data-testid="page-index-title"]').nth(2);
    await t3.fill('ROOF FRAMING PLAN (edited)');
    await t3.press('Enter');
    await page.waitForTimeout(300);
    r.editedTitle = await page.locator('[data-testid="page-index-title"]').nth(2).inputValue();
    await shot(page, 'a2-index.png');
    await page.locator('[data-testid="left-tab-layers"]').click();
    await page.waitForTimeout(300);
    r.layerRows = await page.locator('[data-testid="layer-row"]').count();
    await page.locator('[data-testid="layer-row"]').first().click();
    await page.waitForTimeout(300);
    await shot(page, 'a3-layers.png');
    await page.locator('[data-testid="layer-row"]').first().click();
    await page.locator('[data-testid="left-tab-thumbs"]').click();

    // Status bar scale + units
    r.statusScale = await page.locator('[data-testid="status-scale"]').evaluate((s) => s.options[s.selectedIndex].text);
    await page.locator('[data-testid="status-units"]').selectOption('mm');
    await page.waitForTimeout(600);
    await page.locator('[data-testid="status-units"]').selectOption('ftin');
    await page.waitForTimeout(400);
    // Label font
    await page.locator('[data-testid="label-font"]').selectOption('Courier New');
    r.labelFont = await page.locator('[data-testid="label-font"]').inputValue();

    // Overlay page 3 over page 1
    await page.locator('[data-testid="revu-menu-document"]').click();
    await page.locator('[data-testid="revu-doc-overlay"]').click();
    await page.locator('[data-testid="overlay-page-select"]').selectOption('2');
    await page.waitForTimeout(5000);
    r.overlayImg = await page.locator('[data-testid="overlay-page-img"]').count();
    await shot(page, 'a4-overlay.png');
    await page.getByRole('button', { name: 'Remove overlay' }).click();
    await page.locator('[data-testid="overlay-panel"] button').first().click();

    // Split + Sync
    await page.locator('[data-testid="viewmode-split-vertical"]').click();
    await page.waitForTimeout(2500);
    r.syncBtn = await page.locator('[data-testid="status-sync"]').count();
    if (r.syncBtn) {
      await page.locator('[data-testid="status-sync"]').click();
      await page.waitForTimeout(500);
      await page.locator('[data-testid="revu-menu-document"]').click();
      await page.getByRole('menuitem', { name: /Next Page/ }).click();
      await page.waitForTimeout(3000);
      r.splitPageAfterSync = await page.locator('[data-testid="viewmode-split-vertical"]').getAttribute('aria-pressed');
    }
    await shot(page, 'a5-sync.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'az-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
