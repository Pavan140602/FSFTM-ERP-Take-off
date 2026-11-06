const path = require('path');
const { PDFDocument, PDFName, PDFString, StandardFonts, rgb } = require(path.join(process.argv[2], 'node_modules', 'pdf-lib'));
const fs = require('fs');
(async () => {
  const d = await PDFDocument.create();
  const f = await d.embedFont(StandardFonts.Helvetica);
  for (let i = 0; i < 3; i++) {
    const p = d.addPage([1224, 792]);
    p.drawText(`ARCHITECTURAL SHEET ${i}`, { x: 80, y: 700, size: 20, font: f, color: rgb(0, 0, 0) });
    p.drawRectangle({ x: 200, y: 200, width: 500, height: 300, borderColor: rgb(0, 0, 0), borderWidth: 2 });
  }
  const nums = [];
  for (let i = 0; i < 3; i++) nums.push(i, d.context.obj({ P: PDFString.of(`A00${i}`) }));
  d.catalog.set(PDFName.of('PageLabels'), d.context.obj({ Nums: nums }));
  fs.writeFileSync(process.argv[3], await d.save());
})();
