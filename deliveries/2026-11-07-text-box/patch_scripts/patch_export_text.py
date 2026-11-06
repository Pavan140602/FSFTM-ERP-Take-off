from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\features\takeoff\lib\takeoff-export.ts")
s = p.read_text(encoding="utf-8")
a = """    if (m.type === 'text' && m.points.length >= 1) {
      const p = m.points[0]!;
      const tx = p.x * dpr * zoom;
      const ty = p.y * dpr * zoom;
      const textContent = m.text || m.annotation;
      const fontSize = 14 * dpr;
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = annoColor;
      ctx.fillText(textContent, tx, ty);
      continue;
    }"""
b = """    if (m.type === 'text' && m.points.length >= 1) {
      const p = m.points[0]!;
      const textContent = m.text || m.annotation;
      // Text boxes export exactly as drawn on screen: wrapped, with their
      // font, fill and border (OE-DELIVERY 2026-11-07-text-box).
      if (m.width && m.width > 0) {
        const st = resolveTextStyle(m.textStyle);
        const lay = layoutTextBox(textContent, m.width, st);
        const bh = Math.max(m.height && m.height > 0 ? m.height : 0, lay.contentHeight);
        drawTextBox(ctx, p.x, p.y, m.width, bh, lay.lines, st, dpr * zoom, annoColor);
        continue;
      }
      const tx = p.x * dpr * zoom;
      const ty = p.y * dpr * zoom;
      const fontSize = 14 * dpr;
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = annoColor;
      ctx.fillText(textContent, tx, ty);
      continue;
    }"""
assert s.count(a) == 1
s = s.replace(a, b)
a = "import { circleFrom3Points } from '../../../modules/pdf-takeoff/data/hit-test';\n"
assert s.count(a) == 1
s = s.replace(a, a + "import { drawTextBox, layoutTextBox, resolveTextStyle } from '../../../modules/pdf-takeoff/data/text-box';\n")
p.write_text(s, encoding="utf-8")
print("ok")
