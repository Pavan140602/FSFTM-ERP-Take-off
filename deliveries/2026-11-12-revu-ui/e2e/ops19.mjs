import fs from 'fs';
const FE = process.argv[2];
const pdfjs = await import('file:///' + FE + '/node_modules/pdfjs-dist/legacy/build/pdf.mjs');
const doc = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(process.argv[3])), isEvalSupported: false }).promise;
for (const n of [18, 19, 20]) {
  const pg = await doc.getPage(n);
  const t = Date.now();
  const ops = await pg.getOperatorList();
  const counts = {};
  ops.fnArray.forEach((f) => { counts[f] = (counts[f] || 0) + 1; });
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 7).map(([k, v]) => `${Object.keys(pdfjs.OPS).find((x) => pdfjs.OPS[x] == k)}:${v}`);
  let big = [];
  ops.fnArray.forEach((f, i) => { if (f === pdfjs.OPS.paintImageXObject) { const a = ops.argsArray[i]; if (a[1] * a[2] > 200000) big.push(`${a[1]}x${a[2]}`); } });
  let pathPts = 0;
  ops.fnArray.forEach((f, i) => { if (f === pdfjs.OPS.constructPath) { const d = ops.argsArray[i]?.[1]?.[0]; if (d) pathPts += d.length; } });
  console.log(`p${n} ${Date.now() - t}ms ops=${ops.fnArray.length} pathData=${pathPts}`, top.join(' '), 'big:', big.slice(0, 5).join(','));
}
{
  const pg = await doc.getPage(19);
  const ops = await pg.getOperatorList();
  const u = new Map();
  ops.fnArray.forEach((f, i) => { if (f === pdfjs.OPS.paintImageXObject) { const a = ops.argsArray[i]; if (a[1] * a[2] > 200000) u.set(a[0], (u.get(a[0]) || 0) + 1); } });
  console.log('big images p19: draws', [...u.values()].reduce((a, b) => a + b, 0), 'unique', u.size);
}
