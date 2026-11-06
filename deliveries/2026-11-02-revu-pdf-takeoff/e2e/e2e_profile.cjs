// Browser check: change profiles in the Detected markups list, re-run, reload.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const notReading = "() => !document.querySelector('[data-testid=\"auto-run\"]')?.textContent?.includes('Reading')";

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
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    const open = async () => {
      await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
      await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
      await page.waitForTimeout(4000);
      const t = page.locator('[data-testid="sidebar-tab-auto"]');
      if (await t.count()) await t.first().click();
      await page.waitForTimeout(800);
    };
    const groups = async () => {
      const cat = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
      return (await cat.locator(':scope > div > div > button.flex-1').allInnerTexts()).map((x) => x.replace(/\s+/g, ' ').trim());
    };
    await open();
    r.before = await groups();

    // 1. Whole group: COLUMN -> HSS6X6X1/4
    const colCat = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
    const groupRows = colCat.locator(':scope > div');
    const n = await groupRows.count();
    let idx = -1;
    for (let i = 0; i < n; i++) {
      const txt = await groupRows.nth(i).locator('button.flex-1').first().innerText().catch(() => '');
      if (txt.startsWith('COLUMN') || txt.startsWith('C…') || txt.startsWith('C.')) { idx = i; break; }
    }
    if (idx < 0) idx = 0;
    await groupRows.nth(idx).locator('[data-testid="auto-profile-edit-group"]').click();
    await page.locator('[data-testid="auto-profile-input"]').fill('hss6x6x1/4');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(800);
    r.afterGroupEdit = await groups();

    // 2. One markup: open the HSS22 group, rename its first row
    const cat2 = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
    const g2 = cat2.locator(':scope > div');
    for (let i = 0; i < (await g2.count()); i++) {
      const head = g2.nth(i).locator('button.flex-1').first();
      if ((await head.innerText()).startsWith('HSS22')) { await head.click(); break; }
    }
    await page.waitForTimeout(400);
    const row = cat2.locator('[data-testid="auto-list-row"]').first();
    await row.hover();
    await row.locator('[data-testid="auto-profile-edit"]').click();
    await page.locator('[data-testid="auto-profile-input"]').fill('HSS16X16X5/8');
    await page.locator('[data-testid="auto-profile-save"]').click();
    await page.waitForTimeout(800);
    r.afterRowEdit = await groups();
    await page.screenshot({ path: path.join(outDir, 'p1-edited.png') });

    // 3. Re-run: profiles must stay
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(500);
    await page.waitForFunction(notReading, null, { timeout: 180000 });
    await page.waitForTimeout(800);
    r.rerun = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    r.afterRerun = await groups();

    // 4. Reload (server copy): profiles must stay
    await page.waitForTimeout(5000);
    await open();
    r.afterReload = await groups();
    await page.screenshot({ path: path.join(outDir, 'p2-reload.png') });
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await page.screenshot({ path: path.join(outDir, 'pz-error.png') }).catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
