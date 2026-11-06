"""Legend ▸ side window always shows; navbar Legend button creates a
legend from the selection; legend properties in the top bar
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# State for the side window + a shared "create legend from these" action.
rep("""  /** Legend Properties panel shows for a selected legend (Revu). */
  const [legendPropsOpen, setLegendPropsOpen] = useState(true);""", """  /** Legend Properties panel shows for a selected legend (Revu). */
  const [legendPropsOpen, setLegendPropsOpen] = useState(true);
  /** Legend ▸ side window of the right-click menu (screen position). */
  const [legendSub, setLegendSub] = useState<{ x: number; y: number } | null>(null);
  /** Create New Legend from markups: this sheet only, placed with the next
   *  click on the PDF (Revu). Returns false when none qualify. */
  const startLegendFromRef = useRef<(ids: Iterable<string>) => boolean>(() => false);""")

# Legend button in the right-click menu: side window opens on hover / click,
# fixed on screen so the menu's scroll box never clips it.
rep("""            <div className="relative group/legend">
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors"
                role="menuitem"
                data-testid="context-legend"
              >""", """            <div className="relative" onMouseLeave={() => setLegendSub(null)}>
              <button
                type="button"
                className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors ${legendSub ? 'bg-surface-secondary' : ''}`}
                role="menuitem"
                aria-haspopup="menu"
                aria-expanded={legendSub !== null}
                data-testid="context-legend"
                onMouseEnter={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  setLegendSub({ x: r.right, y: r.top });
                }}
                onClick={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  setLegendSub((v) => (v ? null : { x: r.right, y: r.top }));
                }}
              >""")
rep("""              <div className="absolute left-full top-0 hidden min-w-[190px] rounded-lg border border-border bg-surface-elevated py-1 shadow-lg group-hover/legend:block" data-testid="context-legend-sub">""",
    """              {legendSub && (
              <div
                className="fixed z-[70] min-w-[200px] rounded-lg border border-border bg-surface-elevated py-1 shadow-lg"
                style={{ left: Math.min(legendSub.x - 2, window.innerWidth - 210), top: Math.min(legendSub.y - 4, window.innerHeight - 90) }}
                data-testid="context-legend-sub"
              >""")
rep("""                  <span className="flex-1">Create Legend <span className="text-content-tertiary">(this sheet)</span></span>
                </button>
              </div>""", """                  <span className="flex-1">Create New Legend <span className="text-content-tertiary">(this sheet)</span></span>
                </button>
              </div>
              )}""")

# Create New Legend in the menu uses the shared action.
rep("""                    setSelectedLedgerIds(new Set(pageIds));
                    setSelectedMeasurementId(pageIds[0] ?? null);
                    // Revu: Create Legend - for this sheet only - then click
                    // where it goes; its look is set in Legend Properties
                    // (OE-DELIVERY 2026-11-12-revu-ui).
                    pendingLegendSetupRef.current = { live: true, columns: [...LEGEND_DEFAULT_COLUMNS], title: 'Legend', showTitle: true, border: 'grid', ids: pageIds };
                    setLegendPlacing(true);
                    setLegendPropsOpen(true);
                    setContextMenu(null);
                    addToast({ type: 'info', title: 'Click the sheet to place the legend', message: 'For this sheet only. Select it afterwards to set its properties.' });""",
    """                    setLegendSub(null);
                    setContextMenu(null);
                    startLegendFromRef.current(pageIds);""")
rep("""                    setContextMenu(null);
                    addToast({ type: 'info', title: n > 0 ? 'Taken out of the legend' :""",
    """                    setContextMenu(null);
                    setLegendSub(null);
                    addToast({ type: 'info', title: n > 0 ? 'Taken out of the legend' :""")

# The shared action (needs measurements / page / toast) - define near selectedMeasurement.
rep("""  const selectedMeasurement = useMemo(() => {""", """  startLegendFromRef.current = (idsIn: Iterable<string>) => {
    const pageIds = [...new Set(idsIn)].filter((id) => {
      const mm = measurements.find((x) => x.id === id);
      return mm && mm.page === currentPage && mm.type !== 'legend' && !isAnnotationType(mm.type);
    });
    if (pageIds.length === 0) return false;
    setSelectedLedgerIds(new Set(pageIds));
    setSelectedMeasurementId(pageIds[0] ?? null);
    pendingLegendSetupRef.current = { live: true, columns: [...LEGEND_DEFAULT_COLUMNS], title: 'Legend', showTitle: true, border: 'grid', ids: pageIds };
    setLegendPlacing(true);
    setLegendPropsOpen(true);
    addToast({
      type: 'info',
      title: 'Click the PDF to place the legend',
      message: `${pageIds.length} markup${pageIds.length === 1 ? '' : 's'}, this sheet only. Click the legend afterwards for its properties.`,
    });
    return true;
  };
  const selectedMeasurement = useMemo(() => {""")

# Navbar Legend button: with markups selected, create a legend from them.
rep("""                      const isOpen =
                        legendDashboardVisible && showSidebar && sidebarTab === 'properties';""", """                      // Markups selected: Create New Legend from them, placed
                      // with the next click on the PDF (Revu)
                      // (OE-DELIVERY 2026-11-12-revu-ui).
                      {
                        const sel = new Set<string>(selectedLedgerIds);
                        if (selectedMeasurementId) sel.add(selectedMeasurementId);
                        if (sel.size > 0 && startLegendFromRef.current(sel)) return;
                      }
                      const isOpen =
                        legendDashboardVisible && showSidebar && sidebarTab === 'properties';""")

# Legend properties in the top Properties bar, horizontally.
rep("""            {propsBar.mode === 'selection' && (
            <div className="mb-1.5">
              <RevuPropertiesBar""", """            {selectedMeasurement?.type === 'legend' ? (
            <div className="mb-1.5" data-testid="legend-props-bar-host">
              <LegendPropertiesPanel
                layout="bar"
                setup={selectedMeasurement.legendSetup}
                defaults={{ text: legendTextColor, bg: legendBgColor, border: legendBorderStyle }}
                columnDefs={legendColumnDefs.map((c) => ({ key: c.key, label: c.key === 'count' ? 'Count' : c.key === 'subject' ? 'Description (Subject)' : c.label }))}
                onChange={(patch) => {
                  const id = selectedMeasurement.id;
                  setMeasurements((prev) => prev.map((x) => (x.id === id ? { ...x, legendSetup: { ...(x.legendSetup ?? {}), ...patch } } : x)));
                }}
                onClose={() => setSelectedMeasurementId(null)}
              />
            </div>
            ) : propsBar.mode === 'selection' && (
            <div className="mb-1.5">
              <RevuPropertiesBar""")

# No floating panel any more.
a = s.index("      {selectedMeasurement?.type === 'legend' && legendPropsOpen && (")
b = s.index("      <LegendSetupDialog", a)
s = s[:a] + s[b:]

p.write_text(s, encoding="utf-8")
print("ok")
