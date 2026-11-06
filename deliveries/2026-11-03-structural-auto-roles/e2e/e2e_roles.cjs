// Auto Takeoff roles -> Subject, column marks on sheet, structural Tool Chest sets.
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
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(800);
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(15000);
    r.result = (await page.locator('[data-testid="auto-result"]').innerText().catch(() => '')).slice(0, 200);
    const rows = page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]');
    const n = await rows.count();
    const subjects = {};
    for (let i = 0; i < Math.min(n, 120); i++) {
      const tds = await rows.nth(i).locator('td').allInnerTexts();
      const key = `${tds[2]?.trim()} | ${tds[3]?.trim()}`;
      subjects[key] = (subjects[key] || 0) + 1;
    }
    r.kindSubject = subjects;
    await shot(page, 'r1-after-run.png');
    // zoom into a column area
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(300);
    await page.mouse.move(1000, 500);
    for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(80); }
    await page.waitForTimeout(1500);
    await shot(page, 'r2-columns-zoom.png');
    // chest sets
    await page.locator('[data-testid="rail-tools"]').click();
    await page.waitForTimeout(500);
    r.sets = (await page.locator('[data-testid="revu-tool-chest"] section header').allInnerTexts()).map((x) => x.split('\n').slice(0, 2).join(' '));
    await page.locator('[data-testid="chest-set-zs-headers"] header button').first().click();
    await page.locator('[data-testid="chest-set-zs-lb-walls"] header button').first().click();
    await page.waitForTimeout(300);
    await shot(page, 'r3-chest.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'rz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
