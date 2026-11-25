// Re-run Auto Takeoff (refresh highlight bands), reset the look, close-up screenshots.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('takeoff.sidebarTab', 'auto');
      localStorage.setItem('takeoff.rightPanelWidth', '420');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(4000);
    const set = async (i, v) => page.locator('[data-testid="auto-takeoff-panel"] input[type="range"]').nth(i).evaluate((el, val) => {
      const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      s.call(el, val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }, v);
    await set(0, '1.5');
    await set(1, '0.6');
    await page.waitForTimeout(600);
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(500);
    await page.waitForFunction(() => !document.querySelector('[data-testid="auto-run"]')?.textContent?.includes('Reading'), null, { timeout: 180000 });
    await page.waitForTimeout(1000);
    r.run = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    const beams = page.locator('[data-testid="auto-list-cat-beams"]').locator('xpath=..');
    const heads = beams.locator(':scope > div > div > button.flex-1');
    for (let i = 0; i < (await heads.count()); i++) {
      if ((await heads.nth(i).innerText()).startsWith('HSS8X6')) { await heads.nth(i).click(); break; }
    }
    await page.waitForTimeout(300);
    const rows = beams.locator('[data-testid="auto-list-row"]');
    await rows.last().click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(outDir, 'h1-diagonal.png') });
    await rows.first().click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(outDir, 'h2-beam.png') });
  } catch (e) {
    r.error = String(e).slice(0, 300);
  }
  console.log(JSON.stringify(r));
  await browser.close();
})();
