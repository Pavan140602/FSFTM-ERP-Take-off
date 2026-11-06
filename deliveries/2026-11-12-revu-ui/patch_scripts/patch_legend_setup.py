"""Legend Setup (columns, table lines, title, live), whole-legend scaling,
right-click entries (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# Imports.
rep("import ColorPicklist from './components/ColorPicklist'; // OE-DELIVERY 2026-11-12-revu-ui",
    "import ColorPicklist from './components/ColorPicklist'; // OE-DELIVERY 2026-11-12-revu-ui\n"
    "import { LegendSetupDialog } from './components/LegendSetupDialog';\n"
    "import type { LegendSetup } from './data/legend-setup';")

# Measurement field.
rep("  legendMeasurementIds?: string[];", "  legendMeasurementIds?: string[];\n  /** Revu legend setup (OE-DELIVERY 2026-11-12-revu-ui). */\n  legendSetup?: LegendSetup;")

# State for the dialog + pending setup.
rep("  const [legendColsOpen, setLegendColsOpen] = useState(false);", """  const [legendColsOpen, setLegendColsOpen] = useState(false);
  /** Legend Setup window: create (from picked markups) or edit a placed legend. */
  const [legendSetupDlg, setLegendSetupDlg] = useState<{ mode: 'create'; ids: string[] } | { mode: 'edit'; id: string } | null>(null);
  /** Setup chosen in the window, used by the next legend placed. */
  const pendingLegendSetupRef = useRef<LegendSetup | null>(null);""")

# Placement: carry the setup.
rep("""          ...(legendIds ? { legendMeasurementIds: legendIds } : {}),
        };""", """          ...(legendIds ? { legendMeasurementIds: legendIds } : {}),
          ...(pendingLegendSetupRef.current
            ? { legendSetup: { ...pendingLegendSetupRef.current, ...(legendIds ? { ids: legendIds } : {}) } }
            : {}),
        };
        pendingLegendSetupRef.current = null;""")

# Live rows for a selection legend + per-legend size helper.
rep("""  const getPlacedLegendRows = useCallback(
    (legend: Measurement) => {
      if (legend.legendMeasurementIds && legend.legendMeasurementIds.length > 0) {
        const idSet = new Set(legend.legendMeasurementIds);
        const selected = measurements.filter((m) => idSet.has(m.id));""", """  const getPlacedLegendRows = useCallback(
    (legend: Measurement) => {
      const pickedIds = legend.legendMeasurementIds ?? legend.legendSetup?.ids;
      if (pickedIds && pickedIds.length > 0) {
        const idSet = new Set(pickedIds);
        let selected = measurements.filter((m) => idSet.has(m.id));
        // Live legend (Revu): every markup on the page with the same Subject
        // and look as a picked one counts, so new ones join it.
        if (legend.legendSetup?.live) {
          const lookKey = (m: Measurement) =>
            `${m.type}||${(m.customFields?.Subject?.trim() || m.annotation?.trim() || '').toLowerCase()}||${resolveMeasurementColor(m, groupColorMap).toLowerCase()}`;
          const keys = new Set(selected.map(lookKey));
          selected = measurements.filter(
            (m) => m.page === legend.page && m.type !== 'legend' && !isAnnotationType(m.type) && (idSet.has(m.id) || keys.has(lookKey(m))),
          );
        }""")

rep("""  const getPlacedLegendRowsRef = useRef(getPlacedLegendRows);""", """  const getPlacedLegendRowsRef = useRef(getPlacedLegendRows);
  /** Columns a placed legend shows: its own setup, else the panel's. */
  const legendColumnDefsRef = useRef(legendColumnDefs);
  legendColumnDefsRef.current = legendColumnDefs;
  const legendColsFor = (m: Measurement) => {
    const keys = m.legendSetup?.columns;
    if (!keys || keys.length === 0) return legendVisibleColumnsRef.current;
    const defs = legendColumnDefsRef.current;
    return keys
      .map((k) => defs.find((c) => c.key === k))
      .filter((c): c is (typeof defs)[number] => Boolean(c))
      .map((c) => (c.key === 'count' ? { ...c, label: 'Qty' } : c.key === 'subject' ? { ...c, label: 'Description' } : c));
  };
  const legendColsForRef = useRef(legendColsFor);
  legendColsForRef.current = legendColsFor;
  /** On-sheet size of a placed legend (PDF units). The box scales as a
   *  whole with its stored width - smaller or bigger - like Revu. */
  const legendSizeRef = useRef<(m: Measurement) => { w: number; h: number; cs: number }>(() => ({ w: 0, h: 0, cs: 1 }));
  legendSizeRef.current = (m: Measurement) => {
    const cols = legendColsFor(m);
    const autoW = legendAutoWidthRef.current.get(m.id) ?? legendContentWidth(cols.length);
    const cs = m.width && m.width > 0 ? Math.min(4, Math.max(0.25, m.width / Math.max(autoW, 1))) : 1;
    const titleH = m.legendSetup?.showTitle === false ? LEGEND_HEADER_H + legendPadTop + legendPadBottom : 0;
    const h = (legendBoxHeight(getPlacedLegendRowsRef.current(m).length, legendPadTop + legendPadBottom) - titleH) * cs;
    return { w: autoW * cs, h, cs };
  };""")

# Drawing: per-legend columns, scale, title, border.
rep("""        const rows = getPlacedLegendRowsRef.current(m);
        const cols = legendVisibleColumnsRef.current;
        const lx = p.x * dpr * zoom;""", """        const rows = getPlacedLegendRowsRef.current(m);
        const cols = legendColsForRef.current(m);
        const lSetup = m.legendSetup;
        const showTitle = lSetup?.showTitle !== false;
        const lx = p.x * dpr * zoom;""")
rep("""        // Never shrink below what the content needs (prevents overlap);
        // the user can only enlarge, and content scales up with the box.
        const effW = userW > 0 ? Math.max(userW, autoW) : autoW;
        const lw = effW * dpr * zoom;
        const lh = legendHeightOf(m, rows.length, legendPadTop + legendPadBottom) * dpr * zoom;
        // Content scale: only when the user manually enlarged beyond auto —
        // then content scales up. Auto-width itself always renders at cs=1.
        const cs = userW > 0 ? Math.min(3, Math.max(1, userW / Math.max(autoW, 1))) : 1;""", """        // The whole legend scales with its box, smaller or bigger, like Revu
        // (OE-DELIVERY 2026-11-12-revu-ui): text, rows and symbols together.
        const cs = userW > 0 ? Math.min(4, Math.max(0.25, userW / Math.max(autoW, 1))) : 1;
        const lw = autoW * cs * dpr * zoom;
        const lh =
          (legendBoxHeight(rows.length, legendPadTop + legendPadBottom) - (showTitle ? 0 : LEGEND_HEADER_H + legendPadTop + legendPadBottom)) *
          cs * dpr * zoom;""")
rep("""        const headerH = (LEGEND_HEADER_H + legendPadTop + legendPadBottom) * cs * dpr * zoom;""",
    """        const headerH = showTitle ? (LEGEND_HEADER_H + legendPadTop + legendPadBottom) * cs * dpr * zoom : 0;""")
rep("""        ctx.fillText('Legend', lx + lw / 2, ly + headerH / 2);
        ctx.textAlign = 'left';
        // Separator between the title field and the grid: "Legend" stays a
        // visually separate field, the column grid starts below it.
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath();
        ctx.moveTo(lx, ly + headerH);
        ctx.lineTo(lx + lw, ly + headerH);
        ctx.stroke();""", """        if (showTitle) {
          ctx.fillText(lSetup?.title || 'Legend', lx + lw / 2, ly + headerH / 2);
        }
        ctx.textAlign = 'left';
        // Separator between the title field and the grid: "Legend" stays a
        // visually separate field, the column grid starts below it.
        if (showTitle) {
          ctx.strokeStyle = '#9ca3af';
          ctx.lineWidth = 1 * dpr;
          ctx.beginPath();
          ctx.moveTo(lx, ly + headerH);
          ctx.lineTo(lx + lw, ly + headerH);
          ctx.stroke();
        }""")
rep("""        const borderStyle = legendBorderStyleRef.current;""", """        const borderStyle = lSetup?.border ?? legendBorderStyleRef.current;""")
rep("""          ctx.strokeStyle = '#9ca3af';
          ctx.lineWidth = 1 * dpr;
          ctx.beginPath();
          if (borderStyle === 'outline' || borderStyle === 'grid') {""", """          ctx.strokeStyle = lSetup?.border ? '#374151' : '#9ca3af';
          ctx.lineWidth = 1 * dpr;
          ctx.beginPath();
          if (borderStyle === 'outline' || borderStyle === 'grid') {""")

# Hit test / resize start / hover: same size as drawn.
rep("""          const lh = legendHeightOf(m, getPlacedLegendRowsRef.current(m).length, legendPadTop + legendPadBottom);
          const lw = legendHitWidth(m, legendAutoWidthRef.current, legendVisibleColumnsRef.current.length);""",
    """          const { w: lw, h: lh } = legendSizeRef.current(m);""")
rep("""          const lw = legendHitWidth(m, legendAutoWidthRef.current, legendVisibleColumnsRef.current.length);
          const lh = legendHeightOf(m, getPlacedLegendRowsRef.current(m).length, legendPadTop + legendPadBottom);""",
    """          const { w: lw, h: lh } = legendSizeRef.current(m);""", 2)

# Resize: keep the proportions (the whole legend scales).
rep("""      let nw = rs.origW + (isLeft ? -dx : isRight ? dx : 0);
      let nh = rs.origH + (isTop ? -dy : isBottom ? dy : 0);""", """      let nw = rs.origW + (isLeft ? -dx : isRight ? dx : 0);
      let nh = rs.origH + (isTop ? -dy : isBottom ? dy : 0);
      // Revu: a legend scales as a whole - one factor for width and height
      // (OE-DELIVERY 2026-11-12-revu-ui).
      {
        const sw = (isLeft || isRight) ? nw / Math.max(rs.origW, 1) : nh / Math.max(rs.origH, 1);
        const sh = (isTop || isBottom) ? nh / Math.max(rs.origH, 1) : sw;
        const f = Math.max(0.2, (isLeft || isRight) && (isTop || isBottom) ? Math.max(sw, sh) : sw);
        nw = rs.origW * f;
        nh = rs.origH * f;
        if (isLeft) dxFix = rs.origW - nw;
        if (isTop) dyFix = rs.origH - nh;
      }""")
rep("""      if (leftMoves) nx = rs.origAnchor.x + dx;
      if (topMoves) ny = rs.origAnchor.y + dy;
      // Clamp to the minimum box; push the anchor back so the fixed
      // opposite corner stays put.
      if (nw < LEGEND_MIN_W) {
        if (leftMoves) nx -= LEGEND_MIN_W - nw;
        nw = LEGEND_MIN_W;
      }
      if (nh < LEGEND_MIN_H) {
        if (topMoves) ny -= LEGEND_MIN_H - nh;
        nh = LEGEND_MIN_H;
      }""", """      if (leftMoves) nx = rs.origAnchor.x + dxFix;
      if (topMoves) ny = rs.origAnchor.y + dyFix;""")
rep("""      const leftMoves = isLeft;
      const topMoves = isTop;""", """      const leftMoves = isLeft;
      const topMoves = isTop;
      let dxFix = 0;
      let dyFix = 0;""")

# Context menu: Create New Legend opens the setup window.
rep("""                    setSelectedLedgerIds(new Set(pageIds));
                    setSelectedMeasurementId(pageIds[0] ?? null);
                    setLegendPlacing(true);
                    setContextMenu(null);""", """                    setSelectedLedgerIds(new Set(pageIds));
                    setSelectedMeasurementId(pageIds[0] ?? null);
                    // Revu: the Legend Setup comes first, then place it
                    // (OE-DELIVERY 2026-11-12-revu-ui).
                    setLegendSetupDlg({ mode: 'create', ids: pageIds });
                    setContextMenu(null);""")

# Context menu: Legend Setup on a placed legend (top of the Revu section).
rep("""                  {cm.fromList && first && (
                    <button type="button" className={item} role="menuitem" data-testid="context-goto\"""", """                  {first?.type === 'legend' && (
                    <button type="button" className={item} role="menuitem" data-testid="context-legend-setup" onClick={() => { setLegendSetupDlg({ mode: 'edit', id: first.id }); close(); }}>
                      <BookOpen size={13} /><span className="flex-1">Legend Setup…</span>
                    </button>
                  )}
                  {cm.fromList && first && (
                    <button type="button" className={item} role="menuitem" data-testid="context-goto\"""")

# The window itself, next to the context menu.
rep("""      {/* Measurement context menu (issue #302): right-click a measurement with""", """      <LegendSetupDialog
        open={legendSetupDlg !== null}
        mode={legendSetupDlg?.mode ?? 'create'}
        initial={legendSetupDlg?.mode === 'edit' ? measurements.find((x) => x.id === legendSetupDlg.id)?.legendSetup : undefined}
        columnDefs={legendColumnDefs.map((c) => ({ key: c.key, label: c.key === 'count' ? 'Qty (count)' : c.key === 'subject' ? 'Description (Subject)' : c.label }))}
        markupCount={legendSetupDlg?.mode === 'create' ? legendSetupDlg.ids.length : undefined}
        onCancel={() => setLegendSetupDlg(null)}
        onSave={(setup) => {
          const dlg = legendSetupDlg;
          setLegendSetupDlg(null);
          if (!dlg) return;
          if (dlg.mode === 'edit') {
            setMeasurements((prev) => prev.map((x) => (x.id === dlg.id ? { ...x, legendSetup: { ...(x.legendSetup ?? {}), ...setup } } : x)));
            return;
          }
          pendingLegendSetupRef.current = setup;
          setLegendPlacing(true);
          addToast({ type: 'info', title: 'Click the sheet to place the legend' });
        }}
      />
      {/* Measurement context menu (issue #302): right-click a measurement with""")

p.write_text(s, encoding="utf-8")

# Persistence of the setup.
q = base / "useMeasurementPersistence.ts"
t = q.read_text(encoding="utf-8")


def rep2(a, b, n=1):
    global t
    c = t.count(a)
    assert c == n, (c, a[:100])
    t = t.replace(a, b)


rep2("""  textStyle?: Partial<import("./data/text-box").TextStyle>;""", """  textStyle?: Partial<import("./data/text-box").TextStyle>;
  /** Revu legend setup (OE-DELIVERY 2026-11-12-revu-ui). */
  legendSetup?: import("./data/legend-setup").LegendSetup;""")
rep2("""      text_style: m.textStyle,
""", """      text_style: m.textStyle,
      legend_setup: m.legendSetup,
""")
rep2("""    ts: m.textStyle ?? null,
""", """    ts: m.textStyle ?? null,
    ls: m.legendSetup ?? null,
""")
rep2("""    text_style: m.textStyle ?? null,
""", """    text_style: m.textStyle ?? null,
    legend_setup: m.legendSetup ?? null,
""")
rep2("""    textStyle: cleanTextStyle(meta.text_style),
""", """    textStyle: cleanTextStyle(meta.text_style),
    legendSetup: cleanLegendSetup(meta.legend_setup),
""")
i = t.index("import")
t = t[:i] + "import { cleanLegendSetup } from './data/legend-setup';\n" + t[i:]
q.write_text(t, encoding="utf-8")
print("ok")
