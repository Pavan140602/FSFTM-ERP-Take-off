const { chromium } = require(process.argv[2]);
const url = 'file:///' + process.argv[3].split('\\').join('/');
(async () => {
  const b = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const p = await b.newPage({ viewport: { width: 900, height: 260 } });
  await p.goto(url);
  await p.waitForTimeout(300);
  await p.screenshot({ path: process.argv[4] });
  await b.close();
})();
