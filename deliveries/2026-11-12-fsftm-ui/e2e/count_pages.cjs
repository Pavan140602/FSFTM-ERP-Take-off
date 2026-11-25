const path = require('path'); const fs = require('fs');
const { PDFDocument } = require(path.join(process.argv[2], 'node_modules', 'pdf-lib'));
(async () => { for (const f of process.argv.slice(3)) { try { const d = await PDFDocument.load(fs.readFileSync(f)); const p = d.getPage(0); console.log(path.basename(f), d.getPageCount(), 'pages', Math.round(p.getWidth()), 'x', Math.round(p.getHeight())); } catch (e) { console.log(f, 'ERR'); } } })();
