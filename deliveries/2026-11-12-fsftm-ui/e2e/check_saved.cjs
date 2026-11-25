const path = require('path');
const { PDFDocument, PDFName, PDFArray } = require(path.join(process.argv[2], 'node_modules', 'pdf-lib'));
const fs = require('fs');
(async () => {
  const d = await PDFDocument.load(fs.readFileSync(process.argv[3]));
  const out = { pages: d.getPageCount(), kw: (d.getKeywords() || '').slice(0, 20), annots: [] };
  d.getPages().forEach((p, i) => {
    const a = p.node.lookupMaybe(PDFName.of('Annots'), PDFArray);
    if (a) for (let k = 0; k < a.size(); k++) {
      const x = d.context.lookup(a.get(k));
      out.annots.push(`p${i + 1}:${x.get(PDFName.of('Subtype'))}`);
    }
  });
  console.log(JSON.stringify(out));
})();
