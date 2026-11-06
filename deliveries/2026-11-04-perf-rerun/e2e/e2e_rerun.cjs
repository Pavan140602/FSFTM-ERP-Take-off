// Select all auto beams -> Delete -> re-run Auto Takeoff (beams) -> they come back, selectable.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  const beamRows = () => page.locator('[data-testid="takeoff-ledger-bar"] tbody tr[data-testid="ledger-row"]', { hasText: 'Beam' }).count();
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
    await page.waitForTimeout(3000);
    r.beamsBefore = await beamRows();
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(800);
    // select every auto beam (Detected markups: Beams group)
    await page.locator('[data-testid="auto-list-select-beams"]').first().click();
    await page.waitForTimeout(500);
    r.selected = await page.locator('[data-testid="takeoff-ledger-bar"] tbody input[type="checkbox"]:checked').count();
    await page.mouse.move(1000, 400);
    await page.keyboard.press('Delete');
    await page.waitForTimeout(1500);
    r.beamsAfterDelete = await beamRows();
    // re-run beams only
    const types = await page.locator('[data-testid^="auto-type-"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-testid').slice(10)));
    for (const t of types) {
      const cb = page.locator(`[data-testid="auto-type-${t}"]`);
      if ((await cb.isChecked()) !== (t === 'beam')) await cb.click();
    }
    await page.locator('[data-testid="auto-run"]').click();
    await page.waitForTimeout(12000);
    r.result = (await page.locator('[data-testid="auto-result"]').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 220);
    r.beamsAfterRerun = await beamRows();
    // can the re-placed beams be selected?
    await page.locator('[data-testid="auto-list-select-beams"]').first().click();
    await page.waitForTimeout(500);
    r.reselected = await page.locator('[data-testid="takeoff-ledger-bar"] tbody input[type="checkbox"]:checked').count();
    await page.keyboard.press('Escape');
  } catch (e) {
    r.error = String(e).slice(0, 400);
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
