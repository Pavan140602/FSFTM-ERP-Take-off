"""Update 9: Recent Tools bar removed; live tracing for every click tool;
Area / Volume / Perimeter / Polygon Cutout drawn by dragging a rectangle
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


POLY = "(activeTool === 'area' || activeTool === 'volume' || activeTool === 'perimeter' || activeTool === 'polygonCutout')"

# 1. Recent Tools bar off (user, update 9).
rep("""            {(() => {
              const recentItems = chestSets.find((x) => x.recent)?.items ?? [];
              if (recentItems.length === 0) return null;""", """            {/* Removed at the user's request (update 9). */}
            {false && (() => {
              const recentItems = chestSets.find((x) => x.recent)?.items ?? [];
              if (recentItems.length === 0) return null;""")

# 2. Track the cursor for every click-placed tool.
rep("""          activeTool === 'cloud' ||
          activeTool === 'cloudPlus' ||
          activeTool === 'polylineMarkup')
      ) {""", """          activeTool === 'cloud' ||
          activeTool === 'cloudPlus' ||
          activeTool === 'polylineMarkup' ||
          // Live tracing for every click tool (update 9).
          activeTool === 'perimeter' ||
          activeTool === 'polygonCutout' ||
          activeTool === 'ellipseCutout' ||
          activeTool === 'diameter' ||
          activeTool === 'radiusCenter' ||
          activeTool === 'radius3Point' ||
          activeTool === 'angle' ||
          activeTool === 'arrow' ||
          activeTool === 'rectarea')
      ) {""")

# 3. Previews.
rep("""    // In-progress rectangle/highlight drag preview""", """    // Live tracing (update 9): the shape follows the mouse as in Revu.
    if (!settingScale && liveCursor && !panning && activePoints.length > 0) {
      const k = dpr * zoom;
      const P = (q: Point) => ({ x: q.x * k, y: q.y * k });
      const c = P(liveCursor);
      const a0 = P(activePoints[0]!);
      ctx.save();
      ctx.strokeStyle = '#2563EB';
      ctx.fillStyle = '#2563EB';
      ctx.lineWidth = 1.5 * dpr;
      ctx.setLineDash([5 * dpr, 4 * dpr]);
      // Area-type tools: the live shape, shaded.
      if (""" + POLY + """ && activePoints.length >= 2) {
        const ring = [...activePoints.map(P), c];
        ctx.globalAlpha = activeTool === 'perimeter' ? 0 : 0.12;
        if (activeTool === 'polygonCutout') ctx.fillStyle = '#DC2626';
        ctx.beginPath();
        ring.forEach((q, i) => (i === 0 ? ctx.moveTo(q.x, q.y) : ctx.lineTo(q.x, q.y)));
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      if (activeTool === 'perimeter' || activeTool === 'polygonCutout') {
        const first = activePoints[0]!;
        ctx.globalAlpha = 0.4;
        ctx.beginPath();
        ctx.moveTo(c.x, c.y);
        ctx.lineTo(first.x * k, first.y * k);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
      if (activeTool === 'diameter' && activePoints.length === 1) {
        const r = Math.hypot(c.x - a0.x, c.y - a0.y) / 2;
        ctx.beginPath();
        ctx.moveTo(a0.x, a0.y);
        ctx.lineTo(c.x, c.y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc((a0.x + c.x) / 2, (a0.y + c.y) / 2, r, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (activeTool === 'radiusCenter' && activePoints.length === 1) {
        ctx.beginPath();
        ctx.moveTo(a0.x, a0.y);
        ctx.lineTo(c.x, c.y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(a0.x, a0.y, Math.hypot(c.x - a0.x, c.y - a0.y), 0, Math.PI * 2);
        ctx.stroke();
      }
      if (activeTool === 'ellipseCutout' && activePoints.length === 1) {
        ctx.strokeStyle = '#DC2626';
        ctx.beginPath();
        ctx.ellipse(a0.x, a0.y, Math.max(1, Math.abs(c.x - a0.x)), Math.max(1, Math.abs(c.y - a0.y)), 0, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (activeTool === 'radius3Point') {
        const pts = [...activePoints.map(P), c];
        if (pts.length === 2) {
          ctx.beginPath();
          ctx.moveTo(pts[0]!.x, pts[0]!.y);
          ctx.lineTo(pts[1]!.x, pts[1]!.y);
          ctx.stroke();
        } else if (pts.length >= 3) {
          const [A, B, C] = pts as [Point, Point, Point];
          const d = 2 * (A.x * (B.y - C.y) + B.x * (C.y - A.y) + C.x * (A.y - B.y));
          if (Math.abs(d) > 1e-6) {
            const ux = ((A.x ** 2 + A.y ** 2) * (B.y - C.y) + (B.x ** 2 + B.y ** 2) * (C.y - A.y) + (C.x ** 2 + C.y ** 2) * (A.y - B.y)) / d;
            const uy = ((A.x ** 2 + A.y ** 2) * (C.x - B.x) + (B.x ** 2 + B.y ** 2) * (A.x - C.x) + (C.x ** 2 + C.y ** 2) * (B.x - A.x)) / d;
            ctx.beginPath();
            ctx.arc(ux, uy, Math.hypot(A.x - ux, A.y - uy), 0, Math.PI * 2);
            ctx.stroke();
          }
        }
      }
      if (activeTool === 'angle') {
        // Vertex first, then the two arms.
        ctx.beginPath();
        ctx.moveTo(a0.x, a0.y);
        ctx.lineTo(c.x, c.y);
        if (activePoints.length >= 2) {
          const p1 = P(activePoints[1]!);
          ctx.moveTo(a0.x, a0.y);
          ctx.lineTo(p1.x, p1.y);
        }
        ctx.stroke();
      }
      if (activeTool === 'arrow' && activePoints.length === 1) {
        ctx.strokeStyle = annotationColor || '#EF4444';
        ctx.fillStyle = annotationColor || '#EF4444';
        ctx.setLineDash([]);
        ctx.lineWidth = 2 * dpr;
        ctx.beginPath();
        ctx.moveTo(a0.x, a0.y);
        ctx.lineTo(c.x, c.y);
        ctx.stroke();
        const ang = Math.atan2(c.y - a0.y, c.x - a0.x);
        const h = 11 * dpr;
        ctx.beginPath();
        ctx.moveTo(c.x, c.y);
        ctx.lineTo(c.x - h * Math.cos(ang - 0.45), c.y - h * Math.sin(ang - 0.45));
        ctx.lineTo(c.x - h * Math.cos(ang + 0.45), c.y - h * Math.sin(ang + 0.45));
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    }

    // In-progress rectangle/highlight drag preview""")

# 4. Area-type tools: press and drag draws a rectangle.
rep("""        (activeTool === 'cloud' || activeTool === 'cloudPlus' || activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse')
      ) {
        const bp = pointerToPdf(e);""", """        ((activeTool === 'cloud' || activeTool === 'cloudPlus' || activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse') ||
          (""" + POLY + """ && activePointsLenRef.current === 0))
      ) {
        const bp = pointerToPdf(e);""")
rep("""        if (bd && ep && Math.abs(ep.x - bd.start.x) > 1 && Math.abs(ep.y - bd.start.y) > 1) {
          const a = bd.start;""", """        if (bd && ep && Math.abs(ep.x - bd.start.x) > 1 && Math.abs(ep.y - bd.start.y) > 1) {
          const a = bd.start;
          // Rectangle area / volume / perimeter / cutout (update 9): the
          // four corners go through the normal double-click finish.
          if (""" + POLY + """ && activePoints.length === 0) {
            dblOverridePtsRef.current = [a, { x: ep.x, y: a.y }, ep, { x: a.x, y: ep.y }];
            handleCanvasDblClickRef.current?.();
            return;
          }""")
rep("""    const pts = dropTrailingDuplicateVertex(activePoints, zoom);
""", """    const pts = dblOverridePtsRef.current ?? dropTrailingDuplicateVertex(activePoints, zoom);
    dblOverridePtsRef.current = null;
""")
rep("""  const handleCanvasDblClickRef = useRef<(() => void) | null>(null);""", """  const handleCanvasDblClickRef = useRef<(() => void) | null>(null);
  /** Corners of a dragged rectangle for the area-type finish (update 9). */
  const dblOverridePtsRef = useRef<Point[] | null>(null);
  const activePointsLenRef = useRef(0);
  activePointsLenRef.current = activePoints.length;""")

# Drag preview: shaded box for the area-type tools.
rep("""      } else if (activeTool === 'highlight') {
        ctx.globalAlpha = 0.35;""", """      } else if (""" + POLY + """) {
          ctx.strokeStyle = activeTool === 'polygonCutout' ? '#DC2626' : '#2563EB';
          ctx.setLineDash([5 * dpr, 4 * dpr]);
          ctx.strokeRect(bx, by, bw, bh);
          if (activeTool !== 'perimeter') {
            ctx.globalAlpha = 0.12;
            ctx.fillStyle = ctx.strokeStyle;
            ctx.fillRect(bx, by, bw, bh);
          }
      } else if (activeTool === 'highlight') {
        ctx.globalAlpha = 0.35;""")
p.write_text(s, encoding="utf-8")
print("ok")
