// Revu-style Text Box in the real viewer (OE-DELIVERY 2026-11-07-text-box).
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const shot = (page, n) => page.screenshot({ path: path.join(outDir, n) });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    if (!body.access_token) throw new Error('login failed: ' + JSON.stringify(body).slice(0, 200));
    await page.evaluate(({ tok }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${qa.doc}&name=x.pdf`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
    await page.waitForTimeout(2500);
    const canvas = page.locator('canvas.block').first();
    const box = await canvas.boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.keyboard.press('KeyT');
    await page.waitForTimeout(300);
    r.toolBar = await page.locator('[data-testid="text-format-bar"]').count();
    await shot(page, 't1-tool.png');

    // Drag out a box.
    const x0 = 620, y0 = 300;
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    await page.mouse.move(x0 + 150, y0 + 40, { steps: 6 });
    r.dragRect = await page.locator('[data-testid="text-drag-rect"]').count();
    await page.mouse.move(x0 + 300, y0 + 80, { steps: 6 });
    await page.mouse.up();
    await page.waitForTimeout(400);
    const ed = page.locator('[data-testid="text-box-editor"]');
    r.editorOpen = await ed.count();
    r.editorWidth = await ed.evaluate((el) => el.getBoundingClientRect().width).catch(() => null);
    await ed.type('Revu text box test');
    await page.keyboard.press('Enter');
    await ed.type('Second line, centred and bold');
    // Style from the bar while typing.
    await page.locator('[data-testid="text-format-bar"] [data-testid="text-bold"]').click();
    await page.locator('[data-testid="text-format-bar"] [data-testid="text-align-center"]').click();
    await page.locator('[data-testid="text-format-bar"] [data-testid="text-fill"] input').fill('#fff176');
    r.stillEditing = await ed.count();
    r.editorFont = await ed.evaluate((el) => getComputedStyle(el).fontWeight + ' ' + getComputedStyle(el).textAlign).catch(() => null);
    await shot(page, 't2-editing.png');
    await ed.focus();
    await page.keyboard.press('Control+Enter');
    await page.waitForTimeout(500);
    r.editorClosed = (await ed.count()) === 0;
    await shot(page, 't3-placed.png');

    // Select it with the select tool and restyle from the floating bar.
    await page.keyboard.press('KeyV');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
    await page.mouse.click(x0 + 60, y0 + 15);
    await page.waitForTimeout(400);
    r.selBar = await page.locator('[data-testid="text-format-bar"]').count();
    await page.locator('[data-testid="text-format-bar"] [data-testid="text-border-style"]').selectOption('cloud').catch((e) => (r.cloudErr = String(e).slice(0, 120)));
    await page.waitForTimeout(400);
    await shot(page, 't4-selected-cloud.png');
    await page.waitForTimeout(9000); // let the auto-save reach the server
    r.saved = await page.evaluate(() => {
      const out = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        const v = localStorage.getItem(k) || '';
        if (v.includes('Revu text box test')) out.push(k + ' ' + (v.includes('"textStyle"') ? 'has textStyle' : 'NO textStyle'));
      }
      return out;
    });
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 't-error.png').catch(() => {});
  }
  r.pageErrors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
