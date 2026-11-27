#!/usr/bin/env node
// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * PDF Measurements smoke test - run after every change.
 *
 * Opens the real viewer workspace in Chrome (pdf-workspace-harness.html on
 * the dev server), with a mocked API serving three generated PDFs of
 * different sizes and page counts, and walks through the everyday actions:
 * draw, label move cursor and rotation, delete, split / nested split / "too
 * small", one-click pane switching, Split H inside a pane, Sync (never
 * splits), a different PDF in a pane drawn on with the one tool strip,
 * copy / paste across PDFs, dragging a tab between panes, and overlay of a
 * different-size PDF page for page. Every check prints PASS or FAIL; the exit
 * code is the number of failures.
 *
 *   npm run dev            (in another terminal: http://localhost:5173)
 *   npm run test:pdf-smoke [-- --headed] [-- --shots <folder>]
 */
const path = require('path');
const { chromium } = require('playwright-core');
const { PDFDocument, rgb, StandardFonts } = require('pdf-lib');

const BASE = process.env.PDF_SMOKE_URL || 'http://localhost:5173';
const HEADED = process.argv.includes('--headed');
const shotsAt = process.argv.indexOf('--shots');
const SHOTS = shotsAt > 0 ? process.argv[shotsAt + 1] : null;
const ID = (n) => `aaaaaaaa-0000-0000-0000-00000000000${n}`;

/** A drawing-like PDF: a frame, a title, grid lines, per-page number. */
async function makePdf(pages, w, h, title) {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  for (let i = 1; i <= pages; i++) {
    const p = doc.addPage([w, h]);
    p.drawRectangle({ x: 20, y: 20, width: w - 40, height: h - 40, borderColor: rgb(0, 0, 0), borderWidth: 2 });
    p.drawText(`${title} - page ${i}`, { x: 40, y: h - 60, size: 24, font });
    for (let x = 60; x < w - 60; x += 72) p.drawLine({ start: { x, y: 60 }, end: { x, y: h - 90 }, thickness: 0.8 });
    p.drawLine({ start: { x: 60, y: h / 2 }, end: { x: w - 60, y: h / 2 }, thickness: 1.5 });
  }
  return Buffer.from(await doc.save());
}

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
};

(async () => {
  const PDF = {
    1: await makePdf(1, 1224, 792, 'Set A'), // 17 x 11 in, 1 page
    2: await makePdf(3, 2592, 1728, 'Set B'), // 36 x 24 in, 3 pages
    3: await makePdf(2, 1224, 792, 'Set C'), // 17 x 11 in, 2 pages
  };
  const browser = await chromium.launch({ channel: 'chrome', headless: !HEADED });
  const page = await browser.newPage({ viewport: { width: 1900, height: 1000 } });
  await page.route('**/api/**', (r) => {
    const m = r.request().url().match(/documents\/aaaaaaaa-0000-0000-0000-00000000000(\d)\/download/);
    if (m) return r.fulfill({ status: 200, contentType: 'application/pdf', body: PDF[m[1]] });
    return r.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"smoke"}' });
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  const shot = async (name) => { if (SHOTS) await page.screenshot({ path: path.join(SHOTS, `smoke_${name}.png`) }); };
  const S = (key) => page.evaluate((k) => window.__getShared(k), key);
  const marks = async (n) => ((await S(`doc.meas.${ID(n)}`)) || []);
  const focus = async () => ((await S('ws.focus')) || '').replace(/^aaaaaaaa-0000-0000-0000-00000000000/, '');
  const cursorAt = (x, y) => page.evaluate(([x, y]) => getComputedStyle(document.elementFromPoint(x, y)).cursor, [x, y]);
  const box = async (sel) => page.locator(sel).first().boundingBox();
  /** The part of a drawing's canvas you can actually see (a zoomed sheet
   *  is bigger than its pane). */
  const visibleCanvas = async (hostSel) => {
    const c = await box(`${hostSel} canvas.absolute.left-0`);
    const h = await box(`${hostSel} [data-viewer-root] .overflow-auto`) || await box(hostSel);
    const x = Math.max(c.x, h.x), y = Math.max(c.y, h.y);
    return { x, y, width: Math.min(c.x + c.width, h.x + h.width) - x, height: Math.min(c.y + c.height, h.y + h.height) - y };
  };
  const drawLength = async (hostSel, fy) => {
    const bb = await visibleCanvas(hostSel);
    await page.locator('[data-strip-tool="distance"]').first().click();
    await page.mouse.click(bb.x + bb.width * 0.3, bb.y + bb.height * fy);
    await page.waitForTimeout(250);
    await page.mouse.click(bb.x + bb.width * 0.6, bb.y + bb.height * fy);
    await page.waitForTimeout(700);
    const apply = page.locator('button', { hasText: 'Apply Scale' }).first();
    if (process.env.PDF_SMOKE_DEBUG) console.log('   debug hit', await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return e ? `${e.tagName}.${(e.className || '').toString().slice(0, 60)} host=${e.closest('[data-viewer-host]')?.getAttribute('data-viewer-host')?.slice(-4)}` : 'none'; }, [bb.x + bb.width * 0.6, bb.y + bb.height * fy]));
    if (process.env.PDF_SMOKE_DEBUG) console.log('   debug draw', hostSel.slice(-12), 'applyBtns', await page.locator('button', { hasText: 'Apply Scale' }).count(), 'B', (await marks(2)).length, 'tool', await page.locator('[data-strip-tool="distance"]').first().getAttribute('aria-pressed'));
    if (await apply.count()) { await apply.click(); await page.waitForTimeout(600); }
    await page.keyboard.press('Escape');
    await page.locator('[data-strip-tool="select"]').first().click();
    await page.waitForTimeout(300);
    return bb;
  };

  try {
    await page.goto(`${BASE}/pdf-workspace-harness.html`, { waitUntil: 'load', timeout: 120000 });
    await page.waitForSelector('[data-viewer-host] canvas', { timeout: 120000 });
    await page.waitForTimeout(2500);
    check('opens a drawing', (await page.locator('[data-testid="viewer-active"] canvas').count()) > 0);
    const toolbarNames = await page.evaluate(() => ['Width', 'Page', 'Ortho', 'Snap', 'Multiply'].every((t) => [...document.querySelectorAll('button span')].some((s) => s.textContent === t)));
    check('toolbar icons have names', toolbarNames);

    // ── Draw, label cursor, label rotation, delete ──
    const bb = await drawLength('[data-testid="viewer-active"]', 0.5);
    check('draws a Length markup', (await marks(1)).length === 1);
    let lab = null;
    for (let dy = 4; dy < 90 && !lab; dy += 3) {
      const x = bb.x + bb.width * 0.45, y = bb.y + bb.height * 0.5 - dy;
      await page.mouse.move(x, y);
      await page.waitForTimeout(30);
      if ((await cursorAt(x, y)) === 'move') lab = { x, y };
    }
    check('label shows the move cursor', !!lab);
    let knob = null;
    if (lab) for (let dy = -36; dy < 24 && !knob; dy += 4) for (let dx = 10; dx < 220 && !knob; dx += 4) {
      await page.mouse.move(lab.x, lab.y);
      await page.mouse.move(lab.x + dx, lab.y + dy);
      await page.waitForTimeout(15);
      if ((await cursorAt(lab.x + dx, lab.y + dy)) === 'grab') knob = { x: lab.x + dx, y: lab.y + dy };
    }
    if (knob) {
      const before = (await marks(1))[0].points;
      await page.mouse.move(knob.x, knob.y);
      await page.mouse.down();
      await page.mouse.move(knob.x - 10, knob.y - 40, { steps: 8 });
      await page.mouse.up();
      const m = (await marks(1))[0];
      check('label rotates, markup stays', typeof m.labelRotation === 'number' && m.labelRotation !== 0 && JSON.stringify(m.points) === JSON.stringify(before), `angle ${m.labelRotation}`);
    } else check('label rotates, markup stays', false, 'rotate knob not found');
    await page.mouse.move(bb.x + bb.width * 0.2, bb.y + bb.height * 0.35);
    await page.mouse.down();
    await page.mouse.move(bb.x + bb.width * 0.7, bb.y + bb.height * 0.65, { steps: 6 });
    await page.mouse.up();
    await page.keyboard.press('Control+c');
    await page.keyboard.press('Delete');
    await page.waitForTimeout(400);
    check('Delete removes the selected markup', (await marks(1)).length === 0);
    await page.keyboard.press('Control+z');
    await page.waitForTimeout(400);
    check('Undo brings it back', (await marks(1)).length === 1);

    // ── Sync never splits ──
    await page.locator('[data-testid="status-sync"]').first().click();
    await page.waitForTimeout(500);
    check('Sync on a single view does not split', (await S('split.mode')) === 'off' && (await page.locator('[data-testid="split-pane"]').count()) === 0);
    await page.locator('[data-testid="status-sync"]').first().click();

    // ── Split, the new pane shows the same drawing, one-click focus ──
    await page.locator('[data-testid="viewmode-split-vertical"]').first().click();
    await page.waitForTimeout(2500);
    check('Split V opens the same drawing in the new pane (no picker)', (await page.locator('[data-testid="viewer-pane"]').count()) === 1 && (await page.locator('[data-testid="split-chooser"]').count()) === 0);
    check('no SPLIT badge / + Pane button', (await page.locator('text="SPLIT"').count()) === 0 && (await page.locator('[data-testid="split-add-pane"]').count()) === 0);
    const pane = await box('[data-testid="viewer-pane"]');
    await page.mouse.click(pane.x + pane.width * 0.5, pane.y + pane.height * 0.3);
    await page.waitForTimeout(250);
    check('one click hands the controls to the pane', (await focus()) === '1@p2', `focus ${await focus()}`);
    await page.locator('[data-testid="viewmode-split-horizontal"]').first().click();
    await page.waitForTimeout(1500);
    const tree = JSON.stringify(await S('split.tree'));
    check('Split H inside the pane splits that pane (one click)', /"dir":"col"[^\]]*"pane":"p2"/.test(tree));
    await page.locator('[data-testid="status-sync"]').first().click();
    await page.waitForTimeout(400);
    check('Sync with panes open does not add a pane', (await page.locator('[data-testid="split-pane"]').count()) === 2);
    await page.locator('[data-testid="status-sync"]').first().click();
    let refused = false;
    for (let i = 0; i < 6 && !refused; i++) {
      await page.locator('[data-testid="viewmode-split-vertical"]').first().click();
      await page.waitForTimeout(500);
      refused = (await page.locator('[data-testid="split-error"]').count()) > 0;
    }
    check('"too small to split" message', refused);
    if (refused) await page.locator('[data-testid="split-error-ok"]').click();
    await shot('split');
    await page.mouse.click(bb.x + 15, bb.y + 15);
    await page.waitForTimeout(250);
    check('one click back hands the controls to the main pane', (await focus()) === '1');

    // ── A different PDF in a pane: the one tool strip draws there ──
    await page.locator('[data-testid="split-tabs"] select').first().selectOption(ID(2));
    await page.waitForTimeout(4000);
    const bHost = `[data-viewer-host="${ID(2)}"]`;
    const pb = await visibleCanvas(bHost);
    await page.mouse.click(pb.x + pb.width * 0.5, pb.y + pb.height * 0.3);
    await page.waitForTimeout(250);
    await drawLength(bHost, 0.45);
    if (process.env.PDF_SMOKE_DEBUG) {
      console.log('   debug: pane box', JSON.stringify(pb), 'focus', await focus(), 'B', (await marks(2)).length, 'hosts', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[data-viewer-host]')].map((h) => h.dataset.viewerHost.slice(-3) + ':' + h.getAttribute('data-testid')))));
      await shot('bdraw');
    }
    check('the shared tool strip draws in the pane\'s PDF', (await marks(2)).length === 1 && (await marks(1)).length === 1);
    // ── Copy in A, paste in B ──
    await page.mouse.click(pb.x + pb.width * 0.5, pb.y + pb.height * 0.6);
    await page.mouse.move(pb.x + pb.width * 0.4, pb.y + pb.height * 0.6);
    await page.keyboard.press('Control+v');
    await page.waitForTimeout(600);
    check('markups copied in one PDF paste into another', (await marks(2)).length === 2);

    // ── Drag a main tab into a pane: it moves ──
    const cTab = page.locator('[data-testid="doc-tab"]', { hasText: 'Set C' }).first();
    await cTab.dragTo(page.locator('[data-testid="split-tabs"]').first());
    await page.waitForTimeout(3500);
    const tabs = await page.evaluate(() => window.__tabs);
    check('dragging a tab into a pane moves it', !tabs.includes('Set C.pdf'), `main tabs ${tabs.join(', ')}`);

    // ── Overlay a different-size PDF, page for page ──
    await page.mouse.click(bb.x + 15, bb.y + 15);
    await page.locator('text=Document').first().click();
    await page.locator('[data-testid="fsftm-doc-overlay"]').first().click();
    await page.locator('[data-testid="overlay-source-select"]').selectOption(ID(2));
    await page.waitForTimeout(2500);
    check('overlay of another PDF shows', (await page.locator('[data-testid="overlay-page-img"]').count()) === 1);
    check('overlay explains different sheet sizes', (await page.locator('[data-testid="overlay-size-note"]').count()) === 1);
    await shot('overlay');
  } catch (e) {
    check('smoke run finished', false, e.message.slice(0, 200));
  }
  check('no browser errors', errors.length === 0, errors.slice(0, 2).join(' | '));
  await browser.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed);
})();
