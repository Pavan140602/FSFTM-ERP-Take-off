// Legend Setup round (OE-DELIVERY 2026-11-12-revu-ui): manual markups ->
// right-click -> Legend -> Create New Legend -> setup -> place -> live ->
// shrink -> edit setup. Saves blocked.
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
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  const rowsText = async () => (await page.locator('tbody tr[tabindex="0"]').count());
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
    const checked = () => page.evaluate(() => [...document.querySelectorAll('tbody input[type="checkbox"]')].filter((x) => x.checked).length);
    // 1. Length on a sheet with no scale -> Set Scale.
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300);
    await page.waitForTimeout(600);
    r.setScaleOpen = await page.locator('[data-testid="set-scale-dialog"]').count();
    r.pagesOptions = await page.locator('[data-testid="set-scale-pages"] option').allInnerTexts();
    await page.locator('[data-testid="set-scale-pages"]').selectOption('all');
    await page.locator('[data-testid="set-scale-preset"]').selectOption('1/8" = 1\'-0"');
    await page.locator('[data-testid="set-scale-precision"]').selectOption('16');
    await shot(page, 's1-set-scale.png');
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(600);
    r.scaleBadge = await page.evaluate(() => [...document.querySelectorAll('select')].map((x) => x.selectedOptions[0]?.textContent || '').find((t) => /=|calibrat/i.test(t)) || null);
    // 2. Draw a Length: preview while moving.
    await page.mouse.click(620, 300);
    for (let k = 1; k <= 8; k++) await page.mouse.move(620 + 25 * k, 300 + 3 * k);
    await page.waitForTimeout(400);
    await shot(page, 's2-preview.png');
    await page.mouse.click(820, 324);
    await page.waitForTimeout(600);
    r.afterLength = await active();
    // 3. Polyline markup.
    await page.locator('[data-strip-tool="polylineMarkup"]').click();
    await page.mouse.click(620, 400);
    await page.mouse.click(700, 360);
    await page.mouse.click(780, 420);
    await page.mouse.dblclick(860, 380);
    await page.waitForTimeout(700);
    r.afterPolyline = await active();
    await shot(page, 's3-polyline.png');
    // 4. Next sheet: Length without a prompt (scale set on all pages).
    await page.keyboard.press('PageDown');
    await page.waitForTimeout(3000);
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(620, 300);
    await page.waitForTimeout(400);
    r.promptOnNext = await page.locator('[data-testid="set-scale-dialog"]').count();
    await page.mouse.click(800, 300);
    await page.waitForTimeout(600);
    // 5. Markups list: all sheets, shift range.
    await page.locator('[data-testid="ledger-scope-all"]').click();
    await page.waitForTimeout(500);
    const rws = page.locator('tbody tr[tabindex="0"]');
    r.rowsAll = await rws.count();
    r.pagesInList = await page.evaluate(() => [...new Set([...document.querySelectorAll('tbody tr[tabindex="0"]')].map((tr) => tr.innerText.match(/S-\d\.\d+/)?.[0]))]);
    await rws.nth(0).locator('td').nth(2).click();
    await page.waitForTimeout(300);
    await rws.nth(r.rowsAll - 1).locator('td').nth(2).click({ modifiers: ['Shift'] });
    await page.waitForTimeout(500);
    r.shiftChecked = await checked();
    await shot(page, 's4-list-shift.png');
    // 6. Recent tools + strip.
    r.recent = await page.locator('[data-testid="recent-tool"]').allInnerTexts();
    if (r.recent.length) {
      await page.keyboard.press('Escape');
      await page.locator('[data-testid="recent-tool"]').first().click();
      await page.waitForTimeout(300);
      r.afterRecent = await active();
    }
    await page.locator('[data-testid="revu-tool-strip"]').screenshot({ path: path.join(outDir, 's5-strip.png') });
    await shot(page, 's6-recent.png');
  } catch (e) {
    r.error = String(e).slice(0, 600);
    await shot(page, 'l-error.png').catch(() => {});
  }
  r.pageErrors = errors.slice(0, 6);
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
