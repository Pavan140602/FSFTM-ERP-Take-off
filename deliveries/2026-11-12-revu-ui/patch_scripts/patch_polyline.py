"""Polyline markup tool (Revu: Markup > Polyline, no measurement) next to the
Polylength measure tool (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("""  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp' | 'arc';

/** Annotation-specific tool types */
type AnnotationToolType = 'cloud' | 'arrow' | 'text' | 'rectangle' | 'highlight'
  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp';

const ANNOTATION_TOOLS: AnnotationToolType[] = [
  'cloud', 'arrow', 'text', 'rectangle', 'highlight',
  'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp',
];""", """  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp' | 'arc'
  // Revu Polyline markup: a line through any number of points, no measure.
  | 'polylineMarkup';

/** Annotation-specific tool types */
type AnnotationToolType = 'cloud' | 'arrow' | 'text' | 'rectangle' | 'highlight'
  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp' | 'polylineMarkup';

const ANNOTATION_TOOLS: AnnotationToolType[] = [
  'cloud', 'arrow', 'text', 'rectangle', 'highlight',
  'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp', 'polylineMarkup',
];""")
rep("""  line: '#EF4444',""", """  line: '#EF4444',
  polylineMarkup: '#EF4444',""")

# Click: add a point.
rep("""      if (activeTool === 'polygon') {
        pushUndo({ kind: 'add_point', tool: 'polygon', point });
        setActivePoints((prev) => [...prev, point]);
        return;
      }""", """      if (activeTool === 'polygon' || activeTool === 'polylineMarkup') {
        pushUndo({ kind: 'add_point', tool: activeTool, point });
        setActivePoints((prev) => [...prev, point]);
        return;
      }""")

# Finish (double-click / right-click): a multi-point Line markup.
rep("""    if (activeTool === 'polygon' && pts.length >= 3) {""", """    if (activeTool === 'polylineMarkup' && pts.length >= 2) {
      // The double-click's own clicks may repeat the last point.
      const clean = pts.filter((q, i) => i === 0 || Math.hypot(q.x - pts[i - 1]!.x, q.y - pts[i - 1]!.y) > 0.5);
      if (clean.length >= 2) {
        const newMeasurement: Measurement = {
          id: `m_${Date.now()}`,
          type: 'line',
          points: clean,
          value: 0,
          unit: '',
          label: '',
          annotation: t('takeoff.polyline_n', { defaultValue: 'Polyline {{n}}', n: measurements.filter((x) => x.type === 'line' && x.points.length > 2).length + 1 }),
          ...toolFieldSpread(),
          page: currentPage,
          group: activeGroup,
          color: annotationColor,
        };
        pushUndo({ kind: 'complete_measurement', measurement: newMeasurement, previousActivePoints: [...pts] });
        setMeasurements((prev) => [...prev, newMeasurement]);
      }
      setActivePoints([]);
      return;
    }

    if (activeTool === 'polygon' && pts.length >= 3) {""")
rep("""      } else if ((activeTool === 'cloud' || activeTool === 'polygon') && activePoints.length >= 3) {""",
    """      } else if (
        ((activeTool === 'cloud' || activeTool === 'polygon') && activePoints.length >= 3) ||
        (activeTool === 'polylineMarkup' && activePoints.length >= 2)
      ) {""")

# Preview while drawing.
rep("""      if (activeTool === 'line' || activeTool === 'polygon' || activeTool === 'callout' || activeTool === 'arc' || activeTool === 'pen') {
        drawRevuPreview(ctx, activeTool, activePoints,""", """      if (activeTool === 'line' || activeTool === 'polygon' || activeTool === 'callout' || activeTool === 'arc' || activeTool === 'pen' || activeTool === 'polylineMarkup') {
        drawRevuPreview(ctx, activeTool === 'polylineMarkup' ? 'line' : activeTool, activePoints,""")

# Tool strip + menu.
rep("""      T('line', 'Line', RevuLine, 'markup'),""", """      T('line', 'Line', RevuLine, 'markup'),
      T('polylineMarkup', 'Polyline', RevuPolylineMarkup, 'markup'),""")
rep("""                  ['Line', 'line'], ['Arrow', 'arrow'],""", """                  ['Line', 'line'], ['Polyline', 'polylineMarkup'], ['Arrow', 'arrow'],""")
rep("""  RevuAngle, RevuArc, RevuArea,""", """  RevuPolylineMarkup, RevuAngle, RevuArc, RevuArea,""")
p.write_text(s, encoding="utf-8")

# A Line markup draws through every point (Polyline).
q = base / "data" / "revu-markups.ts"
t = q.read_text(encoding="utf-8")
a = """    case 'line': {
      const [a, b] = pts;
      if (!a || !b) { ok = false; break; }
      const A = P(a); const B = P(b);
      ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.stroke();
      break;
    }"""
b = """    case 'line': {
      // Two points = Line; more = Polyline (OE-DELIVERY 2026-11-12-revu-ui).
      if (pts.length < 2) { ok = false; break; }
      ctx.beginPath();
      pts.forEach((pt, i) => { const q = P(pt); if (i === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y); });
      ctx.stroke();
      break;
    }"""
assert t.count(a) == 1
t = t.replace(a, b)
q.write_text(t, encoding="utf-8")

# Icon.
r = base / "components" / "revu-icons.tsx"
u = r.read_text(encoding="utf-8")
u += """
export const RevuPolylineMarkup = make('polylinemarkup', <path d="M3 18l6-9 5 6 7-10" stroke={RED} strokeWidth={1.9} />);
"""
r.write_text(u, encoding="utf-8")
print("ok")
