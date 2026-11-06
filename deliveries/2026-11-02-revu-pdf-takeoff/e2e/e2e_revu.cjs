// Browser check of the Revu workspace: menu bar, full window, panel drag, live style, highlight.
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
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  const r = {};
  try {
    await page.goto(BASE + '/login');
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
    await page.evaluate(({ tok }) => {
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('takeoff.sidebarTab', 'auto');
      localStorage.removeItem('takeoff.revuWorkspace');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
    }, { tok: body.access_token });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=autotest2.pdf`);
    await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(5000);
    const mb = page.locator('[data-testid="revu-menubar"]');
    await page.evaluate(() => localStorage.setItem('takeoff.rightPanelWidth', '420'));
    r.menubar = await mb.count();
    const box = await mb.boundingBox();
    r.menubarTop = box && Math.round(box.y);
    r.workspaceAttr = await page.locator('[data-revu-workspace]').first().getAttribute('data-revu-workspace');
    await shot(page, 'r1-workspace.png');

    // Menus: View > Fit Page, then View menu screenshot
    await page.locator('[data-testid="revu-menu-view"]').click();
    await page.waitForTimeout(300);
    await shot(page, 'r2-view-menu.png');
    await page.getByRole('menuitem', { name: /Fit Page/ }).click();
    await page.waitForTimeout(1200);
    await page.locator('[data-testid="revu-menu-measure"]').click();
    await page.getByRole('menuitem', { name: /^Length/ }).click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid="revu-menu-measure"]').click();
    r.lengthCheckedInMenu = await page.getByRole('menuitem', { name: /^Length/ }).locator('svg').count();
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');
    await page.keyboard.press('v');

    // Drag the right panel far left (beyond the old 760px cap).
    const grips = page.locator('[role="separator"][aria-orientation="vertical"]');
    r.grips = await grips.count();
    const rightPanel = page.locator('[data-testid="sidebar-tab-auto"]').locator('xpath=ancestor::*[contains(@style,"width")][1]');
    r.rightWidthBefore = Math.round((await rightPanel.boundingBox())?.width ?? 0);
    if (r.grips >= 1) {
      const g = grips.last();
      const gb = await g.boundingBox();
      await page.mouse.move(gb.x + gb.width / 2, gb.y + gb.height / 2);
      await page.mouse.down();
      await page.mouse.move(gb.x - 600, gb.y + gb.height / 2, { steps: 12 });
      await page.mouse.up();
      await page.waitForTimeout(600);
    }
    r.rightWidthAfter = Math.round((await rightPanel.boundingBox())?.width ?? 0);
    await shot(page, 'r3-wide-panel.png');

    // Live style: drag the opacity slider in the Auto Takeoff panel, read the canvas.
    const ranges = page.locator('[data-testid="auto-takeoff-panel"] input[type="range"]');
    r.sliders = await ranges.count();
    const overlayAlpha = async () => page.evaluate(() => {
      const c = [...document.querySelectorAll('canvas')].find((x) => x.className.includes('absolute left-0'));
      if (!c) return -1;
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let sum = 0; let n = 0;
      for (let i = 3; i < d.length; i += 4 * 13) if (d[i] > 0) { sum += d[i]; n++; }
      return n ? Math.round(sum / n) : 0;
    });
    r.alphaBefore = await overlayAlpha();
    await ranges.nth(1).evaluate((el) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, '1');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.waitForTimeout(700);
    r.alphaAfterOpacity100 = await overlayAlpha();
    await ranges.nth(0).evaluate((el) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, '5');
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForTimeout(700);
    await shot(page, 'r4-live-style.png');

    // Highlight close-up: focus a beam from the Detected markups list.
    const beams = page.locator('[data-testid="auto-list-cat-beams"]').locator('xpath=..');
    await beams.locator(':scope > div > div > button.flex-1').first().click();
    await beams.locator('[data-testid="auto-list-row"]').nth(2).click();
    await page.waitForTimeout(2500);
    await shot(page, 'r5-highlight.png');
    const cb = await page.locator('canvas.block').first().boundingBox();
    r.menubarY = Math.round((await page.locator('[data-testid="revu-menubar"]').boundingBox()).y);

    // Exit workspace from the menu bar button.
    await page.locator('[data-testid="revu-workspace-toggle"]').click();
    await page.waitForTimeout(800);
    r.afterExit = await page.locator('[data-revu-workspace]').first().getAttribute('data-revu-workspace');
    await shot(page, 'r6-exit.png');
  } catch (e) {
    r.error = String(e).slice(0, 400);
    await shot(page, 'rz-error.png').catch(() => {});
  }
  console.log(JSON.stringify(r, null, 1));
  console.log('page errors:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
