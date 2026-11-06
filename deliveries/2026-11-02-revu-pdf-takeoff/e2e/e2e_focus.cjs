const path = require('path');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  await page.goto(BASE + '/login');
  const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
  await page.evaluate(({ tok }) => { for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok); localStorage.setItem('oe_onboarding_completed', 'true'); localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' })); localStorage.setItem('takeoff.sidebarTab', 'auto'); }, { tok: body.access_token });
  await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`); await page.waitForFunction(() => document.querySelector('[data-testid="auto-list"]') || true);
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(4000);
  // close the intro banner to get room
  await page.locator('[data-testid="sidebar-tab-auto"]').first().click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, 'f-start.png') });
  const beams = page.locator('[data-testid="auto-list-cat-beams"]').locator('xpath=..');
  await beams.locator(':scope > div > div > button.flex-1').first().click();
  await page.waitForTimeout(300);
  await beams.locator('[data-testid="auto-list-row"]').nth(3).click();
  for (const t of [500, 1500, 3000]) { await page.waitForTimeout(t); await page.screenshot({ path: path.join(outDir, `f-beam-${t}.png`) }); }
  const info = await page.evaluate(() => ({ zoom: document.querySelector('input[aria-label*="oom" i]')?.value }));
  console.log(JSON.stringify(info));
  const cols = page.locator('[data-testid="auto-list-cat-columns"]').locator('xpath=..');
  const heads = cols.locator(':scope > div > div > button.flex-1');
  await heads.last().click();
  await page.waitForTimeout(300);
  await cols.locator('[data-testid="auto-list-row"]').last().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(outDir, 'f-col.png') });
  await browser.close();
})();
