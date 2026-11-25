const path = require('path');
const fs = require('fs');
const [frontendDir, qaFile, docId] = process.argv.slice(2);
const qa = JSON.parse(fs.readFileSync(qaFile, 'utf8'));
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  await page.goto(BASE + '/login', { timeout: 120000 });
  const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: qa.email, password: qa.pw } })).json();
  const out = await page.evaluate(async ({ tok, docId }) => {
    const pdfjs = await import('/node_modules/.vite/deps/pdfjs-dist_legacy_build_pdf__mjs.js').catch(() => import('/@id/pdfjs-dist/legacy/build/pdf.mjs'));
    const lib = pdfjs.default ?? pdfjs;
    lib.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/legacy/build/pdf.worker.min.mjs';
    const buf = await (await fetch(`/api/v1/takeoff/documents/${docId}/download/`, { headers: { Authorization: `Bearer ${tok}` } })).arrayBuffer();
    const res = {}; window.__W = 600; window.__P = [18,19,20,21];
    for (const [name, opts] of [['default', {}], ['noOffscreen', { isOffscreenCanvasSupported: false }]]) {
      const doc = await lib.getDocument({ data: buf.slice(0), ...opts }).promise;
      const times = [];
      for (const n of (window.__P || [3, 4, 5])) {
        const pg = await doc.getPage(n);
        const vp = pg.getViewport({ scale: (window.__W || 600) / pg.getViewport({ scale: 1 }).width });
        const c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height;
        const t = performance.now();
        await pg.render({ canvas: c, viewport: vp }).promise;
        times.push(Math.round(performance.now() - t));
      }
      res[name] = times;
      await doc.loadingTask.destroy();
    }
    return res;
  }, { tok: body.access_token, docId });
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.log('ERR', String(e).slice(0, 400)); process.exit(1); });
