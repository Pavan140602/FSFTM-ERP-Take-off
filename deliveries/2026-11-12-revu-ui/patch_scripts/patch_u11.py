"""Update 11: Enter closes Cloud+/Polygon/Perimeter/cutout/Polyline; dashed
ghost closing line; snap to drawing lines for calibration and every measure
tool; properties bar (colour, line, width, opacity %) for every tool;
grey scrolling tool strip; Polylength icon (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# 1. Enter finishes every multi-point tool.
rep("""        if (
          (activeTool === 'polyline' && activePoints.length >= 2) ||
          ((activeTool === 'area' || activeTool === 'volume' || activeTool === 'cloud') &&
            activePoints.length >= 3)
        ) {""", """        if (
          ((activeTool === 'polyline' || activeTool === 'polylineMarkup') && activePoints.length >= 2) ||
          ((activeTool === 'area' || activeTool === 'volume' || activeTool === 'cloud' || activeTool === 'cloudPlus' ||
            activeTool === 'polygon' || activeTool === 'perimeter' || activeTool === 'polygonCutout') &&
            activePoints.length >= 3)
        ) {""")

# 2. Cloud preview: scallops through the points + mouse, dashed ghost back to the start.
rep("""        const pts = [...activePoints, ...(liveCursor && !panning ? [liveCursor] : [])].map((q) => ({ x: q.x * dpr * zoom, y: q.y * dpr * zoom }));
        if (pts.length >= 2) {
          const ring = pts.length >= 3 ? [...pts, pts[0]!] : pts;""", """        const pts = [...activePoints, ...(liveCursor && !panning ? [liveCursor] : [])].map((q) => ({ x: q.x * dpr * zoom, y: q.y * dpr * zoom }));
        if (pts.length >= 2) {
          // Open scallops; the closing edge is a dashed ghost line (update 11)
          // so it is clear where Enter / double-click will close it.
          const ring = pts;""")
rep("""          ctx.stroke();
          if (pts.length >= 3) {
            ctx.globalAlpha = 0.08;""", """          ctx.stroke();
          if (pts.length >= 3) {
            ctx.save();
            ctx.setLineDash([5 * dpr, 4 * dpr]);
            ctx.globalAlpha = 0.7;
            ctx.beginPath();
            ctx.moveTo(pts[pts.length - 1]!.x, pts[pts.length - 1]!.y);
            ctx.lineTo(pts[0]!.x, pts[0]!.y);
            ctx.stroke();
            ctx.restore();
          }
          if (pts.length >= 3) {
            ctx.globalAlpha = 0.08;""")

# 3. Snap to the drawing for calibration and every measure / markup click tool.
rep("""      const canVertexSnap =
        activeTool === 'distance' ||""", """      const canVertexSnap =
        settingScale ||
        activeTool === 'perimeter' ||
        activeTool === 'polygonCutout' ||
        activeTool === 'ellipseCutout' ||
        activeTool === 'diameter' ||
        activeTool === 'radiusCenter' ||
        activeTool === 'radius3Point' ||
        activeTool === 'angle' ||
        activeTool === 'rectarea' ||
        activeTool === 'cloud' ||
        activeTool === 'cloudPlus' ||
        activeTool === 'polylineMarkup' ||
        activeTool === 'arrow' ||
        activeTool === 'distance' ||""")
# Calibration hover: show / use the snap ring too.
rep("""      if (settingScale) {
        if (pt && scalePoints.length === 1) {
          const a = scalePoints[0]!;
          setLiveCursor(orthoLock || shiftHeldRef.current ? orthoSnap(a, pt) : pt);
        } else if (liveCursor) {
          setLiveCursor(null);
        }
        return;
      }""", """      if (settingScale) {
        // Snap to the drawing's lines / ends while calibrating (Revu, update 11).
        const csnapCal = pt && contentSnapRef.current ? (() => {
          const idx = contentSnapCache.current.get(currentPage);
          return idx ? snapToContent(pt, idx, zoomRef.current || 1, VERTEX_SNAP_SCREEN_PX) : null;
        })() : null;
        if (csnapCal) {
          setSnapPoint(csnapCal.point);
          setSnapIsContent(true);
          setSnapKind(csnapCal.kind);
        } else {
          setSnapPoint((cur) => (cur ? null : cur));
        }
        if (pt && scalePoints.length === 1) {
          const a = scalePoints[0]!;
          setLiveCursor(csnapCal ? csnapCal.point : orthoLock || shiftHeldRef.current ? orthoSnap(a, pt) : pt);
        } else if (liveCursor) {
          setLiveCursor(null);
        }
        return;
      }""")

# 4. Properties bar (colour picklist, line, width, opacity %) for every tool.
rep("""            ) : (propsBar.mode === 'selection' || (propsBar.mode === 'tool' && (activeTool === 'area' || activeTool === 'volume'))) && (""",
    """            ) : (propsBar.mode === 'selection' || propsBar.mode === 'tool') && (""")
p.write_text(s, encoding="utf-8")

# 5. Tool strip: grey like the left rail, scrolls, no names.
q = base / "components/RevuToolStrip.tsx"
t = q.read_text(encoding="utf-8")


def trep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)


trep("""          on
            ? t.kind === 'markup'
              ? 'bg-orange-500 text-white'
              : 'bg-oe-blue text-white'
            : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',""",
     """          // Same look as the left rail: grey icons, blue when on (update 11).
          on ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-secondary hover:text-content-primary',""")
trep("""        <Icon size={inMenu ? 15 : 22} className="shrink-0" />""",
     """        <span className="flex shrink-0" style={{ filter: on && !inMenu ? 'brightness(0) invert(1)' : 'grayscale(1) contrast(1.4)', opacity: on ? 1 : 0.85 }}>
          <Icon size={inMenu ? 15 : 20} />
        </span>""")
i = t.index("  // One column; what does not fit opens from the arrow at the bottom (Revu).")
t = t[:i] + """  // One column that scrolls (update 11); the arrows at the ends scroll it.
  const listRef = useRef<HTMLDivElement>(null);
  const [canUp, setCanUp] = useState(false);
  const [canDown, setCanDown] = useState(false);
  const syncArrows = () => {
    const el = listRef.current;
    if (!el) return;
    setCanUp(el.scrollTop > 2);
    setCanDown(el.scrollTop + el.clientHeight < el.scrollHeight - 2);
  };
  useEffect(() => {
    syncArrows();
  });
  const scrollBy = (dy: number) => listRef.current?.scrollBy({ top: dy, behavior: 'smooth' });
  void rows;
  void moreOpen;
  return (
    <div
      ref={boxRef}
      className="relative flex h-full shrink-0 flex-col items-center rounded-lg border border-border bg-surface-primary p-[3px] pb-[76px]"
      role="toolbar"
      aria-orientation="vertical"
      aria-label="Tools"
      data-testid="revu-tool-strip"
      data-cols={1}
    >
      {canUp && (
        <button type="button" onClick={() => scrollBy(-200)} aria-label="Scroll tools up" className="flex h-5 w-[34px] shrink-0 items-center justify-center rounded text-content-secondary hover:bg-surface-secondary" data-testid="revu-tool-strip-up">
          <ChevronDown size={15} className="rotate-180" />
        </button>
      )}
      <div
        ref={listRef}
        onScroll={syncArrows}
        className="flex min-h-0 flex-1 flex-col items-center gap-[2px] overflow-y-auto [scrollbar-width:thin]"
        data-testid="revu-tool-strip-list"
      >
        {tools.map((t, i) => (
          <div key={t.tool} className="flex flex-col items-center">
            {i > 0 && (tools[i - 1]!.kind !== t.kind || t.sepBefore) && <span className="my-1 w-7 border-t border-dotted border-content-tertiary/60" aria-hidden="true" />}
            {btn(t)}
          </div>
        ))}
      </div>
      {canDown && (
        <button type="button" onClick={() => scrollBy(200)} aria-label="Scroll tools down" title="More tools" className="flex h-6 w-[34px] shrink-0 items-center justify-center rounded text-content-secondary hover:bg-surface-secondary" data-testid="revu-tool-strip-more">
          <ChevronDown size={16} />
        </button>
      )}
    </div>
  );
}
"""
q.write_text(t, encoding="utf-8")

# 6. Polylength icon after the user's Revu picture: a polyline with square
#    vertex grips inside violet corner brackets.
r = base / "components/revu-icons.tsx"
u = r.read_text(encoding="utf-8")
a = u.index("export const RevuPolylength = make('polylength', (")
b = u.index("export const RevuArea = make('area', (")
u = u[:a] + """export const RevuPolylength = make('polylength', (
  <>
    {/* Revu Polylength (update 11): a polyline with square grips at its
        vertices, in violet corner brackets. */}
    <path d="M3 7V3h4M17 3h4v4M21 17v4h-4M7 21H3v-4" stroke="#7C5CFF" strokeWidth={1.4} />
    <path d="M7 17V9l5-3 5 4" strokeWidth={1.5} />
    <rect x="5.6" y="15.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="5.6" y="7.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="10.6" y="4.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="15.6" y="8.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
  </>
));
""" + u[b:]
r.write_text(u, encoding="utf-8")
print("ok")
