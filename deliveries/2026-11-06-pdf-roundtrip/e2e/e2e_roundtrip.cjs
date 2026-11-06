// Round trip: upload rotated PDF to a temp project, draw markups, Download PDF,
// re-upload the download, check markups come back editable and persist.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, qaFile, pdfPath, keepProject] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
const shot = (page, n) => page.screenshot({ path: path.join(outDir, n) });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1700, height: 1000 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const r = { steps: [] };
  const errors = [];
  const toasts = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 160)); });
  const net = []; const t0 = Date.now(); let phase = 'p1';
  page.on('request', (q) => {
    const u = q.url();
    if (!u.includes('/takeoff/measurements') || q.method() === 'GET') return;
    let n = ''; try { const b = q.postDataJSON(); n = Array.isArray(b) ? b.length : Array.isArray(b?.measurements) ? b.measurements.length : (b?.items?.length ?? ''); } catch { /* */ }
    net.push(`${phase} ${((Date.now() - t0) / 1000).toFixed(1)}s ${q.method()} ${u.replace(/.*\/takeoff/, '')} n=${n}`);
  });
  let tok; let projectId;
  const api = async (method, url, data) => {
    const res = await page.request.fetch(BASE + '/api' + url, { method, data, headers: { Authorization: `Bearer ${tok}` } });
    let body = null; try { body = await res.json(); } catch { /* none */ }
    return { status: res.status(), body };
  };
  const listMs = async () => {
    const { body } = await api('GET', `/v1/takeoff/measurements/?project_id=${projectId}&limit=500`);
    const items = Array.isArray(body) ? body : body?.items ?? [];
    const byDoc = {};
    for (const m of items) byDoc[m.document_id] = (byDoc[m.document_id] || 0) + 1;
    return { n: items.length, byDoc, items };
  };
  const rows = () => page.locator('[data-testid="ledger-row"]').count();
  const grabToasts = async () => {
    const t = await page.locator('[role="status"], [role="alert"], .toast, [data-sonner-toast]').allInnerTexts().catch(() => []);
    for (const x of t) if (x.trim() && !toasts.includes(x.trim())) toasts.push(x.trim().slice(0, 160));
  };
  try {
    await page.goto(BASE + '/login', { timeout: 120000 });
    const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
    tok = body.access_token;
    const pr = await api('POST', '/v1/projects/', { name: 'ZZ temp round-trip test (safe to delete)' });
    projectId = pr.body?.id;
    r.project = pr.status;
    await page.evaluate(({ tok, projectId }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: projectId, name: 'ZZ temp round-trip test (safe to delete)' }));
    }, { tok, projectId });
    await page.goto(`${BASE}/takeoff?tab=measurements`);
    await page.waitForTimeout(4000);
    await page.locator('input[type="file"][accept="application/pdf,.pdf"]').first().setInputFiles(pdfPath);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    await page.waitForTimeout(3000);
    r.url1 = page.url().replace(BASE, '');
    await page.locator('[data-testid="status-scale"]').click();
    await page.locator('[data-testid="set-scale-preset"]').selectOption({ index: 5 });
    await page.locator('[data-testid="set-scale-apply"]').click();
    await page.waitForTimeout(500);
    await page.locator('[data-strip-tool="distance"]').click();
    await page.mouse.click(600, 600); await page.mouse.click(900, 600);
    await page.waitForTimeout(400);
    await page.locator('[data-strip-tool="polyline"]').click();
    await page.mouse.click(600, 450); await page.mouse.click(900, 450);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    await page.locator('[data-strip-tool="polyline"]').click();
    await page.mouse.click(1000, 300); await page.mouse.click(1000, 600);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(600);
    await page.keyboard.press('Escape');
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(5000);
    r.rows1 = await rows();
    r.server1 = (await listMs()).byDoc;
    await shot(page, 'r1-drawn.png');
    phase = 'p1-edit'; await page.locator('[data-strip-tool="select"]').click().catch(() => {});
    await page.mouse.move(750, 600); await page.mouse.down(); await page.mouse.move(760, 640, { steps: 8 }); await page.mouse.move(770, 680, { steps: 8 }); await page.mouse.up();
    await page.waitForTimeout(500);
    await page.waitForTimeout(4000); phase = 'p1';
    const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('[data-testid="toolbar-export-pdf-button"]').click()]);
    const saved = path.join(outDir, 'downloaded.pdf');
    await dl.saveAs(saved);
    r.downloadedName = dl.suggestedFilename();
    await page.locator('[data-testid="toolbar-close-pdf"]').click();
    await page.waitForTimeout(2500);
    phase = 'p2-upload'; await page.locator('input[type="file"][accept="application/pdf,.pdf"]').first().setInputFiles(saved);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    for (let i = 0; i < 6; i++) { await grabToasts(); await page.waitForTimeout(400); if (i < 5) await page.keyboard.press('Control+s'); }
    r.url2 = page.url().replace(BASE, '');
    r.rows2 = await rows();
    await shot(page, 'r2-reuploaded.png');
    await page.waitForTimeout(8000);
    r.rows2b = await rows();
    r.server2 = (await listMs()).byDoc;
    // Edit: select the first ledger row, nudge it, save.
    if (r.rows2b > 0) {
      const docId2 = new URL(page.url()).searchParams.get('doc');
      const before = (await listMs()).items.filter((m) => m.document_id === docId2).map((m) => JSON.stringify(m.points?.[0] ?? m.geometry ?? null));
      phase = 'p3-edit'; await page.locator('[data-strip-tool="select"]').click().catch(() => {});
    await page.mouse.move(770, 680); await page.mouse.down(); await page.mouse.move(780, 700, { steps: 8 }); await page.mouse.move(790, 720, { steps: 8 }); await page.mouse.up(); // await page.mouse.move(760, 640, { steps: 8 }); await page.mouse.move(770, 680, { steps: 8 }); await page.mouse.up();
    await page.waitForTimeout(500);
      await shot(page, 'r2c-dragged.png');
      r.ls = await page.evaluate(() => { const out = {}; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (!k.includes('takeoff') || !k.includes('oe_')) continue; try { const v = JSON.parse(localStorage.getItem(k)); if (v && Array.isArray(v.measurements)) out[k.slice(-60)] = v.measurements.map((m) => `${m.id.slice(-10)} sid=${(m.serverId || '-').slice(0, 8)} x=${Math.round(m.points[0].x)},${Math.round(m.points[0].y)}`); } catch { /* */ } } return out; });
      await page.keyboard.press('Control+s');
      await page.waitForTimeout(5000);
      const after = (await listMs()).items.filter((m) => m.document_id === docId2).map((m) => JSON.stringify(m.points?.[0] ?? m.geometry ?? null));
      r.editPersisted = JSON.stringify(before.sort()) !== JSON.stringify(after.sort());
      r.editSample = { before: before.slice(0, 2), after: after.slice(0, 2) };
    }
    phase = 'p4-reload'; await page.reload();
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(6000);
    r.rowsAfterReload = await rows();
    r.serverFinal = (await listMs()).byDoc;
    await shot(page, 'r3-reloaded.png');
  } catch (e) { r.fail = String(e).slice(0, 400); await shot(page, 'fail.png').catch(() => {}); }
  r.toasts = toasts; r.net = net;
  r.errors = errors.slice(0, 15);
  if (projectId && keepProject !== 'keep') {
    const del = await api('DELETE', `/v1/projects/${projectId}`).catch(() => ({ status: 'x' }));
    r.projectDeleted = del.status;
  } else r.projectId = projectId;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
