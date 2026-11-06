// Wrap-up checks: menu opens Auto Takeoff, labelled rail, structural Tool Chest, new tool, scale label, toolbar.
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
    r.rail = await page.locator('[data-testid="revu-rail"] button').allInnerTexts();
    const tb = await page.locator('.takeoff-toolbar').first().boundingBox();
    r.toolbarHeight = tb && Math.round(tb.height);
    await shot(page, 'w1-default.png');

    // Tools menu > Auto Takeoff with the panel closed
    await page.locator('[role="menubar"] button', { hasText: 'Tools' }).first().click();
    await page.locator('[data-testid="revu-tools-auto"]').click();
    await page.waitForTimeout(800);
    r.autoPanelFromMenu = await has('[data-testid="auto-takeoff-panel"]');
    r.activeGroupShown = await page.locator('text=ACTIVE GROUP').count() + await page.locator('text=Active Group').count();
    await shot(page, 'w2-auto.png');

    // Tool Chest
    await page.locator('[data-testid="rail-tools"]').click();
    await page.waitForTimeout(500);
    r.sets = (await page.locator('[data-testid="revu-tool-chest"] section header').allInnerTexts()).map((x) => x.split('\n')[0]);
    r.materialLibrary = await page.locator('text=Material Library').count();
    await page.locator('[data-testid="chest-set-lib-w-shapes"] header button').first().click().catch(async () => {
      const first = page.locator('[data-testid^="chest-set-lib-"] header button').nth(0);
      await first.click();
    });
    await page.waitForTimeout(300);
    r.wTiles = await page.locator('[data-testid^="chest-set-lib-"] [data-testid^="chest-item-"]').count();
    // New tool in My Tools
    await page.locator('[data-testid="chest-new-my-tools"]').click();
    await page.locator('[data-testid="chest-new-subject"]').fill('');
    await page.locator('[data-testid="chest-new-label"]').fill('wt9x25');
    await page.waitForTimeout(150);
    r.newShowsAs = await page.locator('[data-testid="chest-new-tool"] p').innerText().catch(() => null);
    await page.locator('[data-testid="chest-new-save"]').click();
    await page.waitForTimeout(300);
    r.myTools = await page.locator('[data-testid="chest-set-my-tools"] [data-testid^="chest-item-"]').evaluateAll((els) => els.map((e) => e.getAttribute('title')));
    await shot(page, 'w3-chest.png');

    // Scale tab
    await page.locator('[data-testid="rail-scale"]').click();
    await page.waitForTimeout(300);
    r.scaleText = await page.locator('[data-testid="revu-scale-panel"]').innerText().then((t) => t.split('\n').slice(0, 6).join(' | ')).catch(() => null);
    await shot(page, 'w4-scale.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'wz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
