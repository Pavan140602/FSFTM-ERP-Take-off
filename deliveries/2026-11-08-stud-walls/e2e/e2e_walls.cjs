// Stud walls in the real viewer (OE-DELIVERY 2026-11-08-stud-walls).
// The Auto Takeoff request is answered with the new engine's result for
// StudioRes S205 (the running backend predates it); saves are blocked so
// the QA project is not changed.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile, mockFile] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
const mock = fs.readFileSync(mockFile, 'utf8');
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
    await page.route('**/auto-takeoff/', (route) => {
      if (route.request().method() === 'POST') return route.fulfill({ status: 200, contentType: 'application/json', body: mock });
      return route.continue();
    });
    await page.route('**/measurements**', (route) => (route.request().method() === 'GET' ? route.continue() : route.abort()));
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${qa.doc}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    await page.locator('[data-testid="rail-auto"]').click();
    await page.waitForTimeout(600);
    await page.locator('[data-testid="auto-run"]').click();
    await page.locator('[data-testid="auto-result"]').waitFor({ timeout: 60000 });
    await page.waitForTimeout(1500);
    r.result = (await page.locator('[data-testid="auto-result"] p').first().innerText()).trim();
    await shot(page, 'w1-run.png');
    // Walls in the list: open the category and a group.
    const wallsCat = page.locator('[data-testid="auto-list-cat-walls"]');
    r.wallsCat = (await wallsCat.innerText()).replace(/\s+/g, ' ');
    r.roleChips = await page.locator('[data-testid="auto-wall-role"]').allInnerTexts();
    r.materials = (await page.locator('[data-testid="auto-group-material"]').allInnerTexts()).slice(0, 6);
    r.groupStuds = (await page.locator('[data-testid="auto-group-studs"]').allInnerTexts()).slice(0, 6);
    const grp = page.locator('[data-testid="auto-list-cat-walls"]').locator('xpath=../..').locator('button.text-left').first();
    await grp.click();
    await page.waitForTimeout(300);
    r.rowStuds = (await page.locator('[data-testid="auto-row-studs"]').allInnerTexts()).slice(0, 4);
    await page.locator('[data-testid="auto-list"]').screenshot({ path: path.join(outDir, 'w2-list.png') });
    // Only shear walls.
    await page.locator('[data-testid="auto-wall-role"]', { hasText: 'Shear Wall' }).first().click();
    await page.waitForTimeout(700);
    r.afterShear = (await wallsCat.innerText()).replace(/\s+/g, ' ');
    await shot(page, 'w3-shear-only.png');
    await page.locator('[data-testid="auto-wall-role"]', { hasText: 'All walls' }).first().click();
    await page.waitForTimeout(400);
    // Revu colour picklist on a group.
    await page.locator('[data-testid="auto-group-colour"]').first().click();
    await page.waitForTimeout(200);
    r.paletteCells = await page.locator('[data-testid="auto-group-colour-menu"] [data-testid="auto-group-colour-cell"]').count();
    await page.locator('[data-testid="auto-list"]').screenshot({ path: path.join(outDir, 'w4-picklist.png') });
    await page.locator('[data-testid="auto-group-colour-menu"] [data-testid="auto-group-colour-cell"]').nth(5).click();
    await page.waitForTimeout(600);
    await shot(page, 'w5-recoloured.png');
    // Zoom to a wall: open a wall group again and click one of its rows.
    const g2 = page.locator('[data-testid="auto-list-cat-walls"]').locator('xpath=../..').locator('button.text-left').first();
    const row = page.locator('[data-testid="auto-list-cat-walls"]').locator('xpath=../..').locator('[data-testid="auto-list-row"]').nth(2);
    r.zoomRow = await row.innerText().catch(() => null);
    await row.click();
    await page.waitForTimeout(2500);
    await shot(page, 'w6-zoom.png');
    // Without the caption labels, to see bands, studs and header areas.
    await page.locator('button', { hasText: /^Names$/ }).first().click().catch(() => {});
    await page.locator('button', { hasText: /^Values$/ }).first().click().catch(() => {});
    await page.locator('input[type="checkbox"]').first().uncheck().catch(() => {});
    await page.waitForTimeout(1200);
    await shot(page, 'w7-studs.png');
  } catch (e) {
    r.error = String(e).slice(0, 500);
    await shot(page, 'w-error.png').catch(() => {});
  }
  r.pageErrors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
