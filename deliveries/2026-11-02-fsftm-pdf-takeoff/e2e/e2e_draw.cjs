const path = require('path');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const stats = (page) => page.evaluate(() => [...document.querySelectorAll('canvas')].map((c) => {
  let n = 0; let size = `${c.width}x${c.height}`;
  try { const ctx = c.getContext('2d'); if (c.width && c.height && c.width * c.height < 40e6) { const d = ctx.getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4 * 7) if (d[i] > 0) n++; } } catch (e) { size += ' ERR'; }
  return `${c.className.slice(0, 30)}|${size}|css ${c.style.width}x${c.style.height}|opaque~${n}|vis ${getComputedStyle(c).display}`;
}));
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  await page.goto(BASE + '/login');
  const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
  await page.evaluate(({ tok }) => { for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok); localStorage.setItem('oe_onboarding_completed', 'true'); localStorage.setItem('takeoff.sidebarTab', 'auto'); localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' })); }, { tok: body.access_token });
  await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(5000);
  console.log('A fit', JSON.stringify(await stats(page), null, 1));
  await page.screenshot({ path: path.join(outDir, 'd-a.png') });
  const beams = page.locator('[data-testid="auto-list-cat-beams"]').locator('xpath=..');
  await beams.locator(':scope > div > div > button.flex-1').first().click();
  await beams.locator('[data-testid="auto-list-row"]').nth(3).click();
  await page.waitForTimeout(3000);
  console.log('B after focus', JSON.stringify(await stats(page), null, 1));
  await page.screenshot({ path: path.join(outDir, 'd-b.png') });
  const c = await page.locator('canvas.block').first().boundingBox();
  await page.mouse.move(c.x + 200, c.y + 100); await page.mouse.wheel(0, -100); await page.waitForTimeout(1500);
  console.log('C after wheel', JSON.stringify(await stats(page), null, 1));
  await page.screenshot({ path: path.join(outDir, 'd-c.png') });
  await browser.close();
})();
