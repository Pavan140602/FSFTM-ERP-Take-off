// Right vertical tool strip, selection-only Properties bar with Subject/Label, trimmed rail.
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
    r.rail = await page.locator('[data-testid="revu-rail"] button').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
    const sb = await page.locator('[data-testid="revu-tool-strip"]').boundingBox();
    r.strip = { box: sb && [Math.round(sb.x), Math.round(sb.y), Math.round(sb.width), Math.round(sb.height)], fit: await page.locator('[data-testid="revu-tool-strip"]').getAttribute('data-fit'), buttons: await has('[data-testid="revu-tool-strip"] [data-strip-tool]'), more: await has('[data-testid="revu-tool-strip-more"]') };
    r.topMarkupGroup = await has('[aria-label="Markup tools"]');
    r.barNoSel = await has('[data-testid="revu-properties-bar"]');
    await shot(page, 's1-default.png');

    await page.locator('[data-strip-tool="area"]').click();
    await page.waitForTimeout(500);
    r.areaPressed = await page.locator('[data-strip-tool="area"]').getAttribute('aria-pressed');
    r.barToolOnly = await has('[data-testid="revu-properties-bar"]');
    const pop = await page.locator('[data-testid="area-popup"], [data-testid="area-tool-popup"]').first().boundingBox().catch(() => null);
    r.areaPopup = pop && [Math.round(pop.x), Math.round(pop.y), Math.round(pop.width)];
    await shot(page, 's2-area.png');
    if (r.strip.more) {
      await page.locator('[data-testid="revu-tool-strip-more"]').click();
      await page.waitForTimeout(200);
      r.moreItems = await page.locator('[data-testid="revu-tool-strip-menu"] button').allInnerTexts();
      await page.keyboard.press('Escape');
    }
    await page.mouse.move(900, 400);
    await page.keyboard.press('Escape');
    await page.keyboard.press('KeyV');

    // select a beam
    const rows = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr');
    await rows.first().click();
    await page.waitForTimeout(600);
    r.bar = await has('[data-testid="revu-properties-bar"]');
    r.tab = await page.locator('[data-testid="props-tab"]').innerText().catch(() => null);
    r.subject = await page.locator('[data-testid="props-subject"]').inputValue().catch(() => null);
    r.label = await page.locator('[data-testid="props-label"]').inputValue().catch(() => null);
    r.lineFields = { unit: await has('[data-testid="props-unit"]'), height: await has('[data-testid="props-height"]'), fill: await has('[data-testid="props-fill"]'), areaUnit: await has('[data-testid="props-area-unit"]'), line: await has('[data-testid="props-linestyle"]') };
    await page.locator('[data-testid="props-height"]').fill(`10'`);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    r.heightAfter = await page.locator('[data-testid="props-height"]').inputValue();
    r.areaUnitAfterHeight = await has('[data-testid="props-area-unit"]');
    r.totalsWall = await page.locator('[data-testid="props-totals"]').innerText().catch(() => null);
    await shot(page, 's3-beam.png');
    await page.locator('[data-testid="props-height"]').fill('');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(300);

    // select a count row
    const n = await rows.count();
    let countRow = -1;
    for (let i = 0; i < n; i++) {
      const tx = await rows.nth(i).innerText();
      if (/\bCount\b/.test(tx)) { countRow = i; break; }
    }
    if (countRow >= 0) {
      await rows.nth(countRow).click();
      await page.waitForTimeout(500);
      r.countTab = await page.locator('[data-testid="props-tab"]').innerText().catch(() => null);
      r.countFields = { unit: await has('[data-testid="props-unit"]'), line: await has('[data-testid="props-linestyle"]'), width: await has('[data-testid="props-width"]'), caption: await has('[data-testid="props-caption"]'), font: await has('[data-testid="props-font"]') };
      await shot(page, 's4-count.png');
    }
    // deselect -> bar hides
    await page.mouse.move(900, 400);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    r.barAfterEsc = await has('[data-testid="revu-properties-bar"]');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'sz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
