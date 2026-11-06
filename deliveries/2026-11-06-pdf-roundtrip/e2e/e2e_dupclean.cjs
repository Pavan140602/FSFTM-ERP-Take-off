// Seed a stale duplicate (same frontend id, older) on a document, open it,
// and check the viewer keeps one copy and deletes the stale one on the server.
const path = require('path');
const fs = require('fs');
const [frontendDir, qaFile, projectId, docId] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const r = {};
  let tok;
  const api = async (method, url, data) => {
    const res = await page.request.fetch(BASE + '/api' + url, { method, data, headers: { Authorization: `Bearer ${tok}` } });
    let body = null; try { body = await res.json(); } catch { /* none */ }
    return { status: res.status(), body };
  };
  const list = async () => {
    const { body } = await api('GET', `/v1/takeoff/measurements/?project_id=${projectId}&limit=500`);
    return (Array.isArray(body) ? body : body?.items ?? []).filter((m) => m.document_id === docId);
  };
  try {
    await page.goto(BASE + '/login', { timeout: 120000 });
    tok = (await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json()).access_token;
    const rows = await list();
    const src = rows[0];
    // A copy with the same frontend id: what the old double-create left behind.
    const keys = ['project_id', 'document_id', 'page', 'type', 'group_name', 'group_color', 'annotation', 'points', 'measurement_value', 'measurement_unit', 'depth', 'volume', 'perimeter', 'count_value', 'scale_pixels_per_unit', 'scale_source', 'linked_boq_position_id', 'is_deduction', 'metadata'];
    const copy = {};
    for (const k of keys) if (src[k] !== undefined && src[k] !== null) copy[k] = src[k];
    copy.points = (src.points || []).map((q) => ({ x: q.x - 40, y: q.y }));
    const made = await api('POST', '/v1/takeoff/measurements/bulk/', { measurements: [copy] });
    if (made.status >= 300) r.seedErr = JSON.stringify(made.body).slice(0, 300);
    r.seeded = made.status;
    const seeded = await list();
    r.before = seeded.length;
    r.sameFrontendId = seeded.filter((m) => m.metadata?.frontend_id === src.metadata?.frontend_id).length;
    await page.evaluate(({ tok, projectId }) => {
      localStorage.clear();
      for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
      localStorage.setItem('oe_onboarding_completed', 'true');
      localStorage.setItem('oe_active_project', JSON.stringify({ id: projectId, name: 'ZZ temp' }));
    }, { tok, projectId });
    await page.goto(`${BASE}/takeoff?tab=measurements&doc=${docId}`);
    await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 300, null, { timeout: 120000 });
    await page.waitForTimeout(9000);
    r.ledgerRows = await page.locator('[data-testid="ledger-row"]').count();
    const after = await list();
    r.after = after.length;
    r.sameFrontendIdAfter = after.filter((m) => m.metadata?.frontend_id === src.metadata?.frontend_id).length;
  } catch (e) { r.fail = String(e).slice(0, 300); }
  r.projectDeleted = (await api('DELETE', `/v1/projects/${projectId}`)).status;
  console.log(JSON.stringify(r));
  await browser.close();
})();
