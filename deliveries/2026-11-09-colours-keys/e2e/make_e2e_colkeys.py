p = r"C:/Users/ishat/AppData/Local/Temp/claude/421772d99a25f2fb/732e120e-2b91-4dfc-bda2-2925a51afa1e/scratchpad/"
s = open(p + "e2e_walls.cjs", encoding="utf-8").read()
start = s.index("    // Walls in the list")
end = s.index("  } catch (e) {")
body = r"""    const pageText = async () => (await page.locator('span', { hasText: /^\s*\d+\s*\/\s*\d+\s*$/ }).first().innerText().catch(() => '?')).trim();
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
    r.pageStart = await pageText();
    await page.keyboard.press('PageDown'); await page.waitForTimeout(1500); r.afterPageDown = await pageText();
    await page.keyboard.press('PageUp'); await page.waitForTimeout(1500); r.afterPageUp = await pageText();
    await page.keyboard.press('ArrowUp'); await page.waitForTimeout(1500); r.afterUp = await pageText();
    await page.keyboard.press('ArrowDown'); await page.waitForTimeout(1500); r.afterDown = await pageText();
  """
s = s[:start] + body + s[end:]
s = s.replace("Stud walls in the real viewer (OE-DELIVERY 2026-11-08-stud-walls)",
              "Colours, header filter, page keys and moving (OE-DELIVERY 2026-11-09-colours-keys)")
open(p + "e2e_colkeys.cjs", "w", encoding="utf-8").write(s)
print("ok")
