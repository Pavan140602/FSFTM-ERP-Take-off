// Colours, header filter, page keys and moving (OE-DELIVERY 2026-11-09-colours-keys).
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
    const pageText = () => page.evaluate(() => { for (const i of document.querySelectorAll('input')) { const t = i.parentElement?.innerText || i.nextElementSibling?.textContent || ''; if (/of\s*\d+/.test(t)) return i.value + ' ' + t.match(/of\s*\d+/)[0]; } return '?'; });
    const canvas = page.locator('canvas.block').first();
    const canvasShot = async (n) => { const b = await canvas.boundingBox(); await page.screenshot({ path: path.join(outDir, n), clip: b }); return page.screenshot({ clip: b }); };
    // Colours: swatch of every group.
    r.groupColours = await page.$$eval('[data-testid="auto-group-colour"]', (els) => els.slice(0, 16).map((e) => {
      const sw = e.querySelector('span,div') || e;
      const row = e.closest('li,div');
      return getComputedStyle(sw).backgroundColor + ' | ' + (row?.innerText || '').replace(/\s+/g, ' ').slice(0, 50);
    }));
    r.roleChips = await page.locator('[data-testid="auto-wall-role"]').allInnerTexts();
    await page.locator('[data-testid="auto-list"]').screenshot({ path: path.join(outDir, 'k1-colours.png') });
    await shot(page, 'k1b-sheet.png');
    // Header areas only, then Select all.
    await page.locator('[data-testid="auto-wall-role"]', { hasText: 'Header areas' }).first().click();
    await page.waitForTimeout(700);
    r.afterHeaders = (await page.locator('[data-testid="auto-list-cat-walls"]').innerText()).replace(/\s+/g, ' ');
    await shot(page, 'k2-headers-only.png');
    const selAll = page.locator('[data-testid="auto-list-cat-walls"]').locator('xpath=../..').locator('button', { hasText: 'Select all' }).first();
    await selAll.click({ timeout: 5000 }).catch((e) => { r.selAllErr = String(e).slice(0, 160); });
    await page.waitForTimeout(800);
    const before = await canvasShot('k3-headers-selected.png');
    // Arrow keys move the selection.
    for (let i = 0; i < 12; i++) await page.keyboard.press('Shift+ArrowRight');
    await page.waitForTimeout(800);
    const after = await canvasShot('k4-moved-keys.png');
    r.arrowKeysChangedSheet = !before.equals(after);
    await page.keyboard.press('Control+z').catch(() => {});
    await page.keyboard.press('Escape');
    await page.locator('[data-testid="auto-wall-role"]', { hasText: 'All walls' }).first().click();
    await page.waitForTimeout(500);
    // Pages: PageDown / PageUp / Up / Down (nothing selected).
    await page.keyboard.press('Escape');
    await page.locator('body').click({ position: { x: 2, y: 2 } }).catch(() => {});
    await page.locator('[aria-label="Clear selection"]').first().click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(400);
    r.selectionBarAfterClear = await page.locator('[aria-label="Clear selection"]').count();
    r.pageStart = await pageText();
    await page.keyboard.press('PageDown'); await page.waitForTimeout(1500); r.afterPageDown = await pageText();
    await page.keyboard.press('PageUp'); await page.waitForTimeout(1500); r.afterPageUp = await pageText();
    await page.keyboard.press('ArrowUp'); await page.waitForTimeout(1500); r.afterUp = await pageText();
    await page.keyboard.press('ArrowDown'); await page.waitForTimeout(1500); r.afterDown = await pageText();
    } catch (e) {
    r.error = String(e).slice(0, 500);
    await shot(page, 'w-error.png').catch(() => {});
  }
  r.pageErrors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
