// CPU profile: open the drawing (phase A) and zoom in/out (phase B); top self-time functions.
const path = require('path');
const fs = require('fs');
const [frontendDir, outDir, DOC, EMAIL, PW] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const { chromium } = require(path.join(path.resolve(frontendDir), 'node_modules', 'playwright-core'));
const BASE = 'http://localhost:5173';
function top(profile, n = 22) {
  const self = new Map();
  const byId = new Map(profile.nodes.map((nd) => [nd.id, nd]));
  const dt = profile.timeDeltas;
  const counts = new Map();
  profile.samples.forEach((id, i) => counts.set(id, (counts.get(id) || 0) + (dt[i] || 0)));
  for (const [id, us] of counts) {
    const nd = byId.get(id);
    const cf = nd.callFrame;
    const key = `${cf.functionName || '(anon)'} ${cf.url.replace(/^.*\/(src|node_modules)\//, '$1/').replace(/\?.*$/, '')}:${cf.lineNumber + 1}`;
    self.set(key, (self.get(key) || 0) + us);
  }
  return [...self.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, us]) => `${Math.round(us / 1000)}ms  ${k}`);
}
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  const out = {};
  await page.goto(BASE + '/login');
  const body = await (await page.request.post(BASE + '/api/v1/users/auth/login/', { data: { email: EMAIL, password: PW } })).json();
  await page.evaluate(({ tok }) => {
    localStorage.clear();
    for (const st of [sessionStorage, localStorage]) st.setItem('oe_access_token', tok);
    localStorage.setItem('oe_onboarding_completed', 'true');
    localStorage.setItem('oe_active_project', JSON.stringify({ id: 'c36f0df4-3be0-4dee-a063-64212295c1c3', name: 'Auto Takeoff QA' }));
  }, { tok: body.access_token });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Profiler.enable');
  await cdp.send('Profiler.setSamplingInterval', { interval: 500 });
  await cdp.send('Profiler.start');
  await page.goto(`${BASE}/takeoff?tab=measurements&doc=${DOC}&name=x.pdf`);
  await page.waitForFunction(() => document.querySelector('canvas.block')?.width > 400, null, { timeout: 120000 });
  await page.waitForTimeout(12000);
  const a = await cdp.send('Profiler.stop');
  out.openTop = top(a.profile);
  await cdp.send('Profiler.start');
  await page.mouse.move(1000, 450);
  for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(60); }
  await page.waitForTimeout(3000);
  for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, 120); await page.waitForTimeout(60); }
  await page.waitForTimeout(3000);
  const b = await cdp.send('Profiler.stop');
  out.zoomTop = top(b.profile);
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})();
