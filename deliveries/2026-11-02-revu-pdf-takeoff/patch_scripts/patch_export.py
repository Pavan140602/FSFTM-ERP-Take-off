"""PDF export parity: missing measure types + Revu properties (all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-export"""
import sys
from pathlib import Path

root = Path(sys.argv[1])  # frontend/src
TAG = 'OE-DELIVERY 2026-11-02-revu-export'
exp = root / 'features/takeoff/lib/takeoff-export.ts'
viewer = root / 'modules/pdf-takeoff/TakeoffViewerModule.tsx'
s = exp.read_text(encoding='utf-8')
v = viewer.read_text(encoding='utf-8')

pairs = [
("""import { drawRevuMarkup, isRevuMarkupType, revuLabelAnchor } from '../../../modules/pdf-takeoff/data/revu-markups';
""", """import { drawRevuMarkup, isRevuMarkupType, revuLabelAnchor } from '../../../modules/pdf-takeoff/data/revu-markups';
// Export parity with the canvas (""" + TAG + """).
import { labelParts, lineDashFor } from '../../../modules/pdf-takeoff/data/revu-style';
import { circleFrom3Points } from '../../../modules/pdf-takeoff/data/hit-test';
"""),
# label mode gates the annotation badge
("""  const drawLabel = (text: string, lx: number, ly: number, color: string): void => {
    const fontSize = 11 * dpr;""", """  /** Label mode of the measurement being exported (""" + TAG + """). */
  let curParts = labelParts(undefined);
  const drawLabel = (text: string, lx: number, ly: number, color: string): void => {
    if (!curParts.name || !text) return;
    const fontSize = 11 * dpr;"""),
# prologue: fill colour, line style, label mode
("""    ctx.lineWidth = (m.strokeWidth ?? 2) * dpr * zoom;

    if (m.type === 'distance' && m.points.length === 2) {""", """    ctx.lineWidth = (m.strokeWidth ?? 2) * dpr * zoom;
    // Revu properties (""" + TAG + """): fill colour, line
    // pattern and which label parts print, exactly as on screen.
    ctx.fillStyle = m.fillColor ?? color;
    ctx.setLineDash(lineDashFor(m.lineStyle, (m.strokeWidth ?? 2) * dpr * zoom));
    curParts = labelParts(m.labelMode);
    const valueText = (text: string, x: number, y: number): void => {
      if (!curParts.value) return;
      ctx.save();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.fillText(text, x, y);
      ctx.restore();
    };

    if (m.type === 'distance' && m.points.length === 2) {"""),
# route the value labels through valueText
("""      ctx.font = `${12 * dpr}px sans-serif`;
      ctx.fillText(measurementLabel(m, scale, system), mx, my);""", """      ctx.font = `${12 * dpr}px sans-serif`;
      valueText(measurementLabel(m, scale, system), mx, my);"""),
("""      ctx.font = `${12 * dpr}px sans-serif`;
      ctx.fillText(measurementLabel(m, scale, system), totalLx, totalLy);""", """      ctx.font = `${12 * dpr}px sans-serif`;
      valueText(measurementLabel(m, scale, system), totalLx, totalLy);"""),
("""      ctx.font = `${12 * dpr}px sans-serif`;
      ctx.fillText(measurementLabel(m, scale, system), cx, cy);
      drawLabel(m.annotation, cx, cy - 14 * dpr, color);
      continue;
    }

    if (m.type === 'count') {""", """      ctx.font = `${12 * dpr}px sans-serif`;
      valueText(measurementLabel(m, scale, system), cx, cy);
      drawLabel(m.annotation, cx, cy - 14 * dpr, color);
      continue;
    }

    /* Measure types the export used to skip (""" + TAG + """):
     * perimeter, polygon cutout, dynamic fill, diameter, radius (centre and
     * 3-point), ellipse cutout and angle. Drawn like the canvas. */
    {
      const k = dpr * zoom;
      const P = (p: { x: number; y: number }) => ({ x: p.x * k, y: p.y * k });
      const pts = m.points;
      let labelAt: { x: number; y: number } | null = null;
      const closedPoly = (fill: boolean, dashed = false) => {
        const a = P(pts[0]!);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        for (let i = 1; i < pts.length; i++) {
          const b = P(pts[i]!);
          ctx.lineTo(b.x, b.y);
        }
        ctx.closePath();
        if (fill) {
          ctx.globalAlpha = m.fillAlpha ?? 0.15;
          ctx.fill();
          ctx.globalAlpha = 1;
        }
        if (dashed && !m.lineStyle) ctx.setLineDash([6 * dpr, 4 * dpr]);
        ctx.stroke();
        labelAt = {
          x: (pts.reduce((sx, p) => sx + p.x, 0) / pts.length) * k,
          y: (pts.reduce((sy, p) => sy + p.y, 0) / pts.length) * k,
        };
      };
      const circle = (c: { x: number; y: number }, rPx: number, fill: boolean, dashed = false) => {
        ctx.beginPath();
        ctx.arc(c.x * k, c.y * k, rPx * k, 0, Math.PI * 2);
        if (fill) {
          ctx.globalAlpha = m.fillAlpha ?? 0.15;
          ctx.fill();
          ctx.globalAlpha = 1;
        }
        if (dashed && !m.lineStyle) ctx.setLineDash([6 * dpr, 4 * dpr]);
        ctx.stroke();
      };
      let handled = true;
      if ((m.type === 'perimeter' || m.type === 'dynamicFill') && pts.length >= 3) {
        closedPoly(m.type === 'dynamicFill');
      } else if (m.type === 'polygonCutout' && pts.length >= 3) {
        closedPoly(true, true);
      } else if (m.type === 'diameter' && pts.length >= 2) {
        const a = P(pts[0]!);
        const b = P(pts[1]!);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        circle({ x: (pts[0]!.x + pts[1]!.x) / 2, y: (pts[0]!.y + pts[1]!.y) / 2 }, Math.hypot(pts[1]!.x - pts[0]!.x, pts[1]!.y - pts[0]!.y) / 2, false);
        labelAt = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 8 * dpr };
      } else if (m.type === 'radiusCenter' && pts.length >= 2) {
        const r = Math.hypot(pts[1]!.x - pts[0]!.x, pts[1]!.y - pts[0]!.y);
        circle(pts[0]!, r, false);
        const a = P(pts[0]!);
        const b = P(pts[1]!);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        labelAt = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 8 * dpr };
      } else if (m.type === 'radius3Point' && pts.length >= 3) {
        const circ = circleFrom3Points(pts[0]!, pts[1]!, pts[2]!);
        if (circ) {
          circle(circ.c, circ.r, false);
          labelAt = { x: circ.c.x * k, y: (circ.c.y - circ.r) * k - 8 * dpr };
        }
      } else if (m.type === 'ellipseCutout' && pts.length >= 2) {
        const cp = pts[0]!;
        const ep = pts[1]!;
        const r = (Math.abs(ep.x - cp.x) + Math.abs(ep.y - cp.y)) / 2;
        circle(cp, r, true, true);
        labelAt = P(cp);
      } else if (m.type === 'angle' && pts.length >= 3) {
        const vtx = P(pts[0]!);
        const a = P(pts[1]!);
        const b = P(pts[2]!);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(vtx.x, vtx.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        const a1 = Math.atan2(a.y - vtx.y, a.x - vtx.x);
        const a2 = Math.atan2(b.y - vtx.y, b.x - vtx.x);
        let sweep = a2 - a1;
        while (sweep > Math.PI) sweep -= 2 * Math.PI;
        while (sweep < -Math.PI) sweep += 2 * Math.PI;
        const arcR = 18 * dpr;
        ctx.beginPath();
        ctx.arc(vtx.x, vtx.y, arcR, a1, a1 + sweep, sweep < 0);
        ctx.stroke();
        labelAt = { x: vtx.x + arcR + 6 * dpr, y: vtx.y };
      } else {
        handled = false;
      }
      if (handled) {
        ctx.setLineDash([]);
        const at = labelAt as { x: number; y: number } | null;
        if (at) {
          ctx.font = `${12 * dpr}px sans-serif`;
          valueText(m.type === 'angle' ? m.label || measurementLabel(m, scale, system) : measurementLabel(m, scale, system), at.x, at.y);
          drawLabel(m.annotation, at.x, at.y - 14 * dpr, color);
        }
        continue;
      }
    }

    if (m.type === 'count') {"""),
# reset the dash after the loop body for annotation branches that stroke
("""    if (isRevuMarkupType(m.type) || m.type === 'arc') {
      const drawn = drawRevuMarkup(ctx, m, {""", """    if (isRevuMarkupType(m.type) || m.type === 'arc') {
      ctx.setLineDash([]);
      const drawn = drawRevuMarkup(ctx, m, {"""),
("""      if (anchor) {
        ctx.font = `${12 * dpr}px sans-serif`;
        ctx.fillStyle = annoColor;
        ctx.fillText(measurementLabel(m, scale, system), anchor.x * dpr * zoom + 6 * dpr, anchor.y * dpr * zoom - 6 * dpr);
      }
      continue;
    }
  }
}""", """      if (anchor) {
        ctx.font = `${12 * dpr}px sans-serif`;
        valueText(measurementLabel(m, scale, system), anchor.x * dpr * zoom + 6 * dpr, anchor.y * dpr * zoom - 6 * dpr);
      }
      continue;
    }
  }
  ctx.setLineDash([]);
}"""),
]
OLD_CALL = """        hiddenMeasurements,
        scale,
        groupColorMap,
        projectName: exportProjectName,"""
NEW_CALL = """        // Show/Hide-by-type also applies to the export (""" + TAG + """).
        hiddenMeasurements: hiddenTypes.size > 0
          ? new Set([...hiddenMeasurements, ...measurements.filter((mm) => hiddenTypes.has(mm.type)).map((mm) => mm.id)])
          : hiddenMeasurements,
        scale,
        groupColorMap,
        projectName: exportProjectName,"""

bad = [(o[:80], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if v.count(OLD_CALL) != 2:
    bad.append(('viewer export call', v.count(OLD_CALL)))
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
exp.write_text(s, encoding='utf-8')
viewer.write_text(v.replace(OLD_CALL, NEW_CALL), encoding='utf-8')
print('ok')
