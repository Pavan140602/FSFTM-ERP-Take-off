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
const fs = require('fs');
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
  const posted = [];
  const studio = { s: null, msgs: [], created: null };
  const json = (r, body) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  await page.route('**/api/**', (r) => {
    const url = r.request().url();
    const m = url.match(/documents\/aaaaaaaa-0000-0000-0000-00000000000(\d)\/download/);
    if (m) return r.fulfill({ status: 200, contentType: 'application/pdf', body: PDF[m[1]] });
    // Team panel: someone else at work, the people list, comments.
    if (/\/takeoff\/presence\//.test(url)) {
      return json(r, { active: [{ user_id: 'u-ana', name: 'Ana Lead', email: 'ana@example.com', document_id: ID(2), document_name: 'Set B.pdf', project_id: '', page: 2, seconds_ago: 5 }, { user_id: 'u-ben', name: 'Ben Field', email: 'ben@example.com', document_id: ID(1), document_name: 'Set A.pdf', project_id: '', page: 1, seconds_ago: 3 }, { user_id: 'u-me', name: 'Me', email: 'me@example.com', document_id: ID(1), document_name: 'Set A.pdf', project_id: '', page: 1, seconds_ago: 0 }], me: 'u-me' });
    }
    // Studio sessions (a tiny in-memory server).
    const st = url.match(/\/takeoff\/studio\/sessions\/(.*)$/);
    if (st) {
      const rest = st[1].split('?')[0];
      const method = r.request().method();
      if (rest === '' && method === 'GET') return json(r, { sessions: studio.s ? [{ id: 's1', name: studio.s.name, code: studio.s.code, status: studio.s.status, role: 'host', my_status: 'joined', created_at: new Date().toISOString() }] : [] });
      if (rest === '' && method === 'POST') {
        const b = r.request().postDataJSON();
        studio.created = b;
        studio.s = {
          id: 's1', name: b.name, code: '123-456-789', status: 'active', open_join: !!b.open_join, created_at: new Date().toISOString(), finished_at: null,
          me: { attendee_id: 'a1', role: 'host', status: 'joined' },
          documents: b.document_ids.map((id) => ({ id, name: `Set ${'?ABC'[Number(id.slice(-1))]}.pdf`, project_id: 'p1', project_name: 'QA project', folder: '' })),
          project_id: 'p1', project_name: 'QA project', folders: [],
          attendees: [
            { id: 'a1', user_id: 'u-me', name: 'Me', email: 'me@example.com', role: 'host', status: 'joined', online: true, document_id: ID(1), page: 1 },
            ...b.invite.map((e, i) => ({ id: `a${i + 2}`, user_id: 'u-ben', name: 'Ben Field', email: e, role: 'attendee', status: 'joined', online: true, document_id: ID(1), page: 3 })),
          ],
        };
        return json(r, { ...studio.s, invites: b.invite.map((e) => ({ email: e, status: 'invited' })) });
      }
      if (rest === 's1/' && method === 'GET') return json(r, studio.s);
      if (rest === 's1/folders/' && method === 'POST') {
        studio.s = { ...studio.s, folders: [...(studio.s.folders || []), r.request().postDataJSON().path] };
        return json(r, studio.s);
      }
      if (rest === 's1/documents/' && method === 'POST') {
        const b = r.request().postDataJSON();
        studio.addedTo = b.folder;
        studio.s = { ...studio.s, documents: [...studio.s.documents, ...b.document_ids.map((id) => ({ id, name: 'Upload me.pdf', pages: 1, project_id: 'p1', project_name: 'QA project', folder: b.folder }))] };
        return json(r, studio.s);
      }
      if (rest === 's1/messages/') {
        if (method === 'POST') studio.msgs.push({ id: `m${studio.msgs.length}`, user_id: 'u-me', name: 'Me', text: r.request().postDataJSON().text, at: new Date().toISOString() });
        return json(r, { messages: studio.msgs });
      }
      if (rest === 's1/report/') return json(r, { total: 2, people: [{ user_id: 'u-ben', name: 'Ben Field', email: 'ben@example.com', count: 2, by_type: { distance: 2 } }], documents: [] });
      if (rest === 's1/finish/') {
        studio.s = { ...studio.s, status: 'finished', finished_at: new Date().toISOString() };
        return json(r, { ...studio.s, report: { total: 2, people: [], documents: [] } });
      }
    }
    if (/\/takeoff\/documents\/upload\//.test(url)) {
      studio.uploaded = (studio.uploaded || 0) + 1;
      return json(r, { id: 'up-1', filename: 'Upload me.pdf', pages: 1, size_bytes: 1 });
    }
    if (/\/takeoff\/people\//.test(url)) {
      return json(r, { people: [{ id: 'u-ana', name: 'Ana Lead', email: 'ana@example.com' }, { id: 'u-ben', name: 'Ben Field', email: 'ben@example.com' }] });
    }
    if (/\/collaboration\/comments\//.test(url)) {
      if (r.request().method() === 'POST') {
        const body = r.request().postDataJSON();
        posted.push(body);
        return json(r, { id: 'c1', author_id: 'u-me', text: body.text, created_at: new Date().toISOString(), mentions: [] });
      }
      return json(r, { items: posted.map((b, i) => ({ id: `c${i}`, author_id: 'u-me', text: b.text, created_at: new Date().toISOString(), replies: [] })), total: posted.length });
    }
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
    await page.addInitScript(() => { try { if (!sessionStorage.getItem('smoke.init')) { localStorage.setItem('takeoff.viewMode', 'normal'); sessionStorage.setItem('smoke.init', '1'); } } catch { /* ignore */ } });
    await page.goto(`${BASE}/pdf-workspace-harness.html`, { waitUntil: 'load', timeout: 120000 });
    await page.waitForSelector('[data-viewer-host] canvas', { timeout: 120000 });
    await page.waitForTimeout(2500);
    check('opens a drawing', (await page.locator('[data-testid="viewer-active"] canvas').count()) > 0);
    const toolbarNames = await page.evaluate(() => ['Width', 'Page', 'Ortho', 'Snap', 'Multiply'].every((t) => [...document.querySelectorAll('button span')].some((s) => s.textContent === t)));
    check('toolbar icons have names', toolbarNames);
    // Top-right Workspace button: one click normal page <-> full screen.
    const wsBtn = () => page.locator('[data-testid="fsftm-workspace-toggle"]:visible').first();
    const wsLabel = (await wsBtn().innerText().catch(() => '')).trim();
    if ((await wsBtn().getAttribute('aria-pressed')) === 'true') { await wsBtn().click(); await page.waitForTimeout(600); }
    const startNormal = await page.evaluate(() => !document.fullscreenElement);
    await wsBtn().click();
    await page.waitForTimeout(700);
    const fsOn = await page.evaluate(() => !!document.fullscreenElement);
    const fsLabel = (await wsBtn().innerText().catch(() => '')).trim();
    const noPopup = (await page.locator('[data-testid="workspace-menu"]').count()) === 0;
    await wsBtn().click();
    await page.waitForTimeout(700);
    const backNormal = await page.evaluate(() => !document.fullscreenElement && localStorage.getItem('takeoff.viewMode') === 'normal');
    check('Workspace: one click to full screen (shows Exit full screen), one click back (no pop-up)', wsLabel === 'Workspace' && fsLabel === 'Exit full screen' && startNormal && fsOn && noPopup && backNormal, `labels "${wsLabel}"/"${fsLabel}" fs ${fsOn} popup ${!noPopup} back ${backNormal}`);

    // ── Draw, label cursor, label rotation, delete ──
    const bb = await drawLength('[data-testid="viewer-active"]', 0.5);
    check('draws a Length markup', (await marks(1)).length === 1);
    let lab = null;
    for (let dy = 4; dy < 90 && !lab; dy += 3) {
      const x = bb.x + bb.width * 0.45, y = bb.y + bb.height * 0.5 - dy;
      await page.mouse.move(x, y);
      await page.waitForTimeout(30);
      if ((await cursorAt(x, y)) === 'grab') lab = { x, y };
    }
    check('label shows the hand cursor', !!lab);
    let knob = null;
    if (lab) for (let dy = -36; dy < 24 && !knob; dy += 4) for (let dx = 10; dx < 220 && !knob; dx += 4) {
      await page.mouse.move(lab.x, lab.y);
      await page.mouse.move(lab.x + dx, lab.y + dy);
      await page.waitForTimeout(15);
      if ((await cursorAt(lab.x + dx, lab.y + dy)).includes('alias')) knob = { x: lab.x + dx, y: lab.y + dy };
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
    // With the Length tool still on (right after drawing), the caption can be dragged.
    if (lab) {
      await page.locator('[data-strip-tool="distance"]').first().click();
      await page.mouse.move(lab.x + 1, lab.y);
      await page.waitForTimeout(60);
      const curDraw = await cursorAt(lab.x + 1, lab.y);
      const off0 = JSON.stringify((await marks(1))[0].labelOffset || {});
      await page.mouse.down();
      await page.mouse.move(lab.x + 40, lab.y - 30, { steps: 6 });
      await page.mouse.up();
      await page.waitForTimeout(300);
      const after = await marks(1);
      check('caption drags with a drawing tool on (hand cursor, no new point)', curDraw === 'grab' && after.length === 1 && JSON.stringify(after[0].labelOffset || {}) !== off0, `cursor ${curDraw}, markups ${after.length}`);
      await page.keyboard.press('Escape');
      await page.locator('[data-strip-tool="select"]').first().click();
      await page.waitForTimeout(200);
    }
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

    // ── A caption turned along an angled line: the hand shows all along it ──
    {
      const vb = await visibleCanvas('[data-testid="viewer-active"]');
      const p0 = { x: vb.x + vb.width * 0.3, y: vb.y + vb.height * 0.8 };
      const p1 = { x: vb.x + vb.width * 0.62, y: vb.y + vb.height * 0.45 };
      await page.locator('[data-strip-tool="distance"]').first().click();
      await page.mouse.click(p0.x, p0.y);
      await page.waitForTimeout(200);
      await page.mouse.click(p1.x, p1.y);
      await page.waitForTimeout(600);
      await page.keyboard.press('Escape');
      await page.locator('[data-strip-tool="select"]').first().click();
      await page.waitForTimeout(300);
      // Use the line as saved (Ortho may have snapped it to 45 degrees).
      const saved = (await marks(1)).slice(-1)[0];
      const ovr = await page.evaluate(() => { const c = document.querySelector('[data-testid="viewer-active"] canvas.absolute.left-0'); const r = c.getBoundingClientRect(); return { x: r.x, y: r.y, k: r.width / 1224 }; });
      const q0 = { x: ovr.x + saved.points[0].x * ovr.k, y: ovr.y + saved.points[0].y * ovr.k };
      const q1 = { x: ovr.x + saved.points[1].x * ovr.k, y: ovr.y + saved.points[1].y * ovr.k };
      const L = Math.hypot(q1.x - q0.x, q1.y - q0.y);
      const ux = (q1.x - q0.x) / L, uy = (q1.y - q0.y) / L;
      const mx = (q0.x + q1.x) / 2, my = (q0.y + q1.y) / 2;
      const along = [];
      for (const side of [1, -1]) for (let dn = 3; dn <= 30; dn += 3) for (let t = -60; t <= 60; t += 6) {
        const x = mx + ux * t + side * uy * dn, y = my + uy * t - side * ux * dn;
        await page.mouse.move(x, y);
        await page.waitForTimeout(25);
        if ((await cursorAt(x, y)) === 'grab') along.push(t);
      }
      const spread = along.length ? Math.max(...along) - Math.min(...along) : 0;
      check('angled caption: the hand cursor shows along the whole caption', (await marks(1)).length === 2 && spread >= 40, `hand at ${along.length} points, spread ${spread}px`);
      await page.keyboard.press('Control+z');
      await page.waitForTimeout(400);
      await page.mouse.move(vb.x + 5, vb.y + 5);
    }

    // ── Sync never splits ──
    await page.locator('[data-testid="status-sync"]').first().click();
    await page.waitForTimeout(500);
    check('Sync on a single view does not split', (await S('split.mode')) === 'off' && (await page.locator('[data-testid="split-pane"]').count()) === 0);
    await page.locator('[data-testid="status-sync"]').first().click();

    // ── Closing a pane's only drawing closes the pane (no copy left behind) ──
    await page.locator('[data-testid="viewmode-split-vertical"]').first().click();
    await page.waitForTimeout(2000);
    await page.locator('[data-testid="split-tab-close"]').first().click();
    await page.waitForTimeout(800);
    check("closing the pane's only drawing closes the pane", (await page.locator('[data-testid="split-pane"]').count()) === 0 && (await S('split.mode')) === 'off');

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

    // ── Overlay Pages: layers in colour -> a new Overlay document ──
    await page.mouse.click(bb.x + 15, bb.y + 15);
    await page.locator('text=Document').first().click();
    await page.locator('[data-testid="fsftm-doc-overlay"]').first().click();
    await page.waitForTimeout(800);
    check('overlay asks for at least 2 layers', (await page.locator('[data-testid="overlay-warn-layers"]').count()) === 1 && (await page.locator('[data-testid="overlay-ok"]').isDisabled()));
    await page.locator('[data-testid="overlay-add"]').click();
    await page.locator('[data-testid="overlay-add-menu"] button', { hasText: 'Set B' }).first().click();
    await page.waitForTimeout(2500);
    check('overlay adds a second PDF as a layer', (await page.locator('[data-testid="overlay-layer"]').count()) === 2);
    check('overlay warns when page counts differ', (await page.locator('[data-testid="overlay-warn-pages"]').count()) === 1);
    const pv = await page.locator('[data-testid="overlay-preview"]').evaluate((c) => c.width);
    check('overlay preview is drawn', pv > 100, `width ${pv}`);
    await page.locator('[data-testid="overlay-ok"]').click();
    await page.waitForFunction(() => window.__generated && window.__generated.pages > 0, null, { timeout: 120000 }).catch(() => {});
    const gen = await page.evaluate(() => window.__generated);
    check('OK creates a new Overlay PDF (one page per page of the longest layer)', !!gen && gen.name === 'Overlay.pdf' && gen.pages === 3, gen ? `${gen.pages} pages, ${Math.round(gen.size / 1024)} KB` : 'nothing created');
    await page.waitForTimeout(3000);
    check('the Overlay document opens as a new tab', (await page.locator('[data-testid="doc-tab"]:visible', { hasText: 'Overlay.pdf (unsaved)' }).count()) >= 1);
    await shot('overlay');

    // ── Combine opens the combined PDF as a new document, like Overlay ──
    await page.locator('[data-testid="toolbar-combine"]:visible').first().click();
    await page.locator('[data-testid="combine-file-input"]').setInputFiles({ name: 'Extra.pdf', mimeType: 'application/pdf', buffer: Buffer.from(PDF['3']) });
    await page.waitForTimeout(400);
    await page.locator('[data-testid="combine-name"]').fill('Combined set');
    await page.locator('[data-testid="combine-ok"]').click();
    await page.waitForTimeout(2500);
    const comb = await page.evaluate(() => window.__generated);
    check('Combine opens the combined PDF as a new document', !!comb && comb.name === 'Combined set.pdf' && (await page.locator('[data-testid="doc-tab"]:visible', { hasText: 'Combined set.pdf (unsaved)' }).count()) >= 1, comb ? `${comb.name} ${comb.pages} pages` : 'nothing opened');

    // ── Team: who is working where, comments with @mentions ──
    // (comments need a saved drawing: back to Set A first)
    await page.locator('[data-testid="doc-tab"]:visible', { hasText: 'Set A' }).first().locator('button').first().click();
    await page.waitForTimeout(2500);
    await page.keyboard.press('Escape');
    if (process.env.PDF_SMOKE_DEBUG) {
      console.log('   debug rail-team', await page.locator('[data-testid="rail-team"]').count(), 'visible', await page.locator('[data-testid="rail-team"]:visible').count(), 'focus', await focus());
      await shot('before_team');
    }
    await page.locator('[data-testid="rail-team"]:visible').first().click();
    await page.waitForTimeout(1200);
    const tabA = page.locator('[data-testid="doc-tab"]:visible', { hasText: 'Set A' }).first();
    const badge = tabA.locator('[data-testid="doc-tab-people"]');
    check('file tab shows who else has it open (not me)', (await badge.count()) === 1 && (await badge.innerText()).trim() === 'BF', (await badge.count()) ? await badge.innerText() : 'no badge');
    check('Team panel lists every account as a member', (await page.locator('[data-testid="team-member"]').count()) >= 2);
    check('Team panel shows who is working where', (await page.locator('[data-testid="team-presence"]', { hasText: 'Ana Lead' }).count()) === 1);
    const box2 = page.locator('[data-testid="team-comment-input"]');
    await box2.click();
    await box2.type('Please check the beams @Ben');
    await page.waitForTimeout(300);
    const sugg = page.locator('[data-testid="team-mention-list"] button', { hasText: 'Ben Field' });
    check('@ suggests people', (await sugg.count()) === 1);
    // A last name finds the person too.
    await box2.press('End');
    await box2.type(' and @fiel');
    await page.waitForTimeout(250);
    check('@ finds a person by last name', (await page.locator('[data-testid="team-mention-list"] button', { hasText: 'Ben Field' }).count()) === 1);
    for (let i = 0; i < ' and @fiel'.length; i++) await box2.press('Backspace');
    await page.waitForTimeout(150);
    check('@names are highlighted while typing', (await page.locator('[data-testid="team-comment-highlight"] mark').count()) >= 1);
    if (await sugg.count()) await sugg.first().dispatchEvent('mousedown');
    await page.locator('[data-testid="team-comment-send"]').click();
    await page.waitForTimeout(800);
    const sent = posted[0];
    check('comment is sent with the @mention', !!sent && sent.entity_type === 'takeoff_document' && (sent.mentions || []).some((x) => x.mentioned_user_id === 'u-ben'), sent ? JSON.stringify(sent.mentions) : 'nothing posted');
    check('the comment shows in the thread', (await page.locator('[data-testid="team-comments"]', { hasText: 'Please check the beams' }).count()) === 1);
    await shot('team');

    // ── Studio: start a session, people, chat, report, finish ──
    await page.locator('[data-testid="rail-studio"]:visible').first().click();
    await page.waitForTimeout(600);
    check('Studio: New session and Join buttons are in view', (await page.locator('[data-testid="studio-new-btn"]:visible').count()) === 1 && (await page.locator('[data-testid="studio-join-btn"]:visible').count()) === 1);
    await page.locator('[data-testid="studio-new-btn"]').click();
    const pickBen = page.locator('[data-testid="studio-people-picker"] label', { hasText: 'Ben Field' });
    check('Studio: the new-session dialog lists every account', (await page.locator('[data-testid="studio-people-picker"] label').count()) >= 2 && (await pickBen.count()) === 1);
    await pickBen.locator('input').check();
    await page.locator('[data-testid="studio-start"]').click();
    await page.waitForTimeout(1200);
    check('Studio: a session starts with the open PDF and the invite', !!studio.created && studio.created.document_ids.includes(ID(1)) && studio.created.invite[0] === 'ben@example.com', JSON.stringify(studio.created));
    check('Studio: the session ID is shown', (await page.locator('[data-testid="studio-code-shown"]').innerText().catch(() => '')) === '123-456-789');
    check('Studio: the session ID and how to join are shown in the session', (await page.locator('[data-testid="studio-id-card"]', { hasText: '123-456-789' }).count()) === 1);
    check('Studio: a big Add PDF button is in the open session', (await page.locator('[data-testid="studio-add-pdf-big"]:visible').count()) === 1);
    check('Studio: says who can see the session', (await page.locator('[data-testid="studio-visibility-note"]', { hasText: 'Only the people added here' }).count()) === 1);
    check('Studio: people in the session are listed', (await page.locator('[data-testid="studio-person"]', { hasText: 'Ben Field' }).count()) === 1);
    check('Studio: the viewer knows which PDFs are in the session (faster live sync)', (await S('studio.active'))?.docIds?.includes(ID(1)) === true);
    await shot('studio_live');
    await page.locator('[data-testid="studio-chat-input"]').click();
    await page.locator('[data-testid="studio-chat-input"]').type('Hi @Be');
    await page.waitForTimeout(250);
    check('Studio chat: @ suggests people', (await page.locator('[data-testid="studio-mention-list"] button', { hasText: 'Ben Field' }).count()) === 1);
    await page.locator('[data-testid="studio-chat-input"]').fill('Grid B is mine');
    await page.locator('[data-testid="studio-chat-send"]').click();
    await page.waitForTimeout(700);
    check('Studio: chat message shows', (await page.locator('[data-testid="studio-chat"]', { hasText: 'Grid B is mine' }).count()) === 1);
    const benRow = page.locator('[data-testid="studio-person"]', { hasText: 'Ben Field' });
    check('Studio: markups per person show beside each name', (await benRow.locator('span[title="Markups made in this session"]').innerText().catch(() => '')) === '2');
    await page.locator('[data-testid="studio-actions"]').click();
    const [dl] = await Promise.all([
      page.waitForEvent('download', { timeout: 8000 }).catch(() => null),
      page.locator('[data-testid="studio-report-pdf"]').click(),
    ]);
    let pdfHead = '';
    if (dl) { const fp = await dl.path(); pdfHead = fs.readFileSync(fp).subarray(0, 5).toString(); }
    check('Studio: report downloads as a PDF', pdfHead === '%PDF-', dl ? `${dl.suggestedFilename()} ${pdfHead}` : 'no download');
    // Folders: make one, upload a PDF into the session from the computer.
    await page.locator('[data-testid="studio-add"]').click();
    await page.locator('[data-testid="studio-new-folder"]').click();
    await page.locator('[data-testid="studio-folder-name"]').fill('Level 2');
    await page.locator('[data-testid="studio-folder-ok"]').click();
    await page.waitForTimeout(600);
    check('Studio: a folder is created in the session', (await page.locator('[data-testid="studio-folder"]', { hasText: 'Level 2' }).count()) === 1);
    await page.locator('[data-testid="studio-add"]').click();
    await page.locator('[data-testid="studio-upload-open"]').click();
    await page.locator('[data-testid="studio-file-input"]').setInputFiles({ name: 'Upload me.pdf', mimeType: 'application/pdf', buffer: Buffer.from(PDF['2']) });
    await page.locator('[data-testid="studio-upload-form"] select').selectOption('Level 2');
    await page.locator('[data-testid="studio-upload-ok"]').click();
    await page.waitForTimeout(1200);
    check('Studio: a PDF uploads into the chosen folder', studio.uploaded === 1 && studio.addedTo === 'Level 2' && (await page.locator('[data-testid="studio-doc"]', { hasText: 'Upload me.pdf' }).count()) === 1, `uploaded ${studio.uploaded} folder ${studio.addedTo}`);
    await page.locator('[data-testid="studio-actions"]').click();
    page.once('dialog', (dlg) => dlg.accept());
    await page.locator('[data-testid="studio-finish"]').click();
    await page.waitForTimeout(1000);
    check('Studio: the host can finish the session', studio.s.status === 'finished' && (await page.locator('[data-testid="studio-chat-input"]').count()) === 0);
    await shot('studio');
  } catch (e) {
    check('smoke run finished', false, e.message.slice(0, process.env.PDF_SMOKE_DEBUG ? 1500 : 200));
  }
  check('no browser errors', errors.length === 0, errors.slice(0, 2).join(' | '));
  await browser.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed);
})();
