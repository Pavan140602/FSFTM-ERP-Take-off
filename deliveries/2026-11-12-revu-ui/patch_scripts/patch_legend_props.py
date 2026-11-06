"""Legend Properties panel (Revu), Legend ▸ None / Create Legend
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

SP = Path(r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad")
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# Imports.
rep("import type { LegendSetup } from './data/legend-setup';",
    "import type { LegendSetup } from './data/legend-setup';\n"
    "import { legendFont, legendLook, legendMetrics, legendTotalHeight, LEGEND_DEFAULT_COLUMNS } from './data/legend-setup';\n"
    "import { LegendPropertiesPanel } from './components/LegendPropertiesPanel';")

# New drawing block.
a = s.index("      if (m.type === 'legend' && m.points.length >= 1) {\n        const p = m.points[0]!;\n        const rows = getPlacedLegendRowsRef.current(m);")
b = s.index("      if (m.type === 'rectangle' && m.points.length === 2) {", a)
s = s[:a] + (SP / "legend_draw_block.tsx").read_text(encoding="utf-8") + s[b:]

# Size used by clicks / drags = size drawn.
rep("""    const titleH = m.legendSetup?.showTitle === false ? LEGEND_HEADER_H + legendPadTop + legendPadBottom : 0;
    const h = (legendBoxHeight(getPlacedLegendRowsRef.current(m).length, legendPadTop + legendPadBottom) - titleH) * cs;""",
    """    const met = legendMetrics(m.legendSetup, legendPadTop + legendPadBottom);
    const h = legendTotalHeight(getPlacedLegendRowsRef.current(m).length, met, m.legendSetup?.showTitle !== false) * cs;""")

# Legend ▸ None takes markups out; rows skip them.
rep("""        let selected = measurements.filter((m) => idSet.has(m.id));""",
    """        const excluded = new Set(legend.legendSetup?.excludeIds ?? []);
        let selected = measurements.filter((m) => idSet.has(m.id) && !excluded.has(m.id));""")
rep("""            (m) => m.page === legend.page && m.type !== 'legend' && !isAnnotationType(m.type) && (idSet.has(m.id) || keys.has(lookKey(m))),""",
    """            (m) => m.page === legend.page && m.type !== 'legend' && !isAnnotationType(m.type) && !excluded.has(m.id) && (idSet.has(m.id) || keys.has(lookKey(m))),""")

# Legend submenu: None + Create Legend (this sheet), placed straight away.
rep("""              <div className="absolute left-full top-0 hidden min-w-[160px] rounded-lg border border-border bg-surface-elevated py-1 shadow-lg group-hover/legend:block">
                <button
                  type="button"
                  onClick={() => {
                    // Collect selected IDs (or the right-clicked one), filtered""",
    """              <div className="absolute left-full top-0 hidden min-w-[190px] rounded-lg border border-border bg-surface-elevated py-1 shadow-lg group-hover/legend:block" data-testid="context-legend-sub">
                <button
                  type="button"
                  onClick={() => {
                    // Legend ▸ None (Revu): the selected markups leave every
                    // legend on this sheet (OE-DELIVERY 2026-11-12-revu-ui).
                    const ids = new Set<string>(selectedLedgerIds);
                    ids.add(contextMenu.measurementId);
                    let n = 0;
                    setMeasurements((prev) =>
                      prev.map((x) => {
                        if (x.type !== 'legend' || x.page !== currentPage) return x;
                        n += 1;
                        const keepIds = (x.legendMeasurementIds ?? x.legendSetup?.ids ?? []).filter((id) => !ids.has(id));
                        const excl = [...new Set([...(x.legendSetup?.excludeIds ?? []), ...ids])];
                        return { ...x, legendMeasurementIds: keepIds, legendSetup: { ...(x.legendSetup ?? {}), ids: keepIds, excludeIds: excl } };
                      }),
                    );
                    setContextMenu(null);
                    addToast({ type: 'info', title: n > 0 ? 'Taken out of the legend' : 'No legend on this sheet', message: n > 0 ? `${ids.size} markup${ids.size === 1 ? '' : 's'} no longer listed in this sheet's legend.` : undefined });
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors"
                  role="menuitem"
                  data-testid="context-legend-none"
                >
                  <X size={13} />
                  <span className="flex-1">None</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    // Collect selected IDs (or the right-clicked one), filtered""")
rep("""                    // Revu: the Legend Setup comes first, then place it
                    // (OE-DELIVERY 2026-11-12-revu-ui).
                    setLegendSetupDlg({ mode: 'create', ids: pageIds });
                    setContextMenu(null);""", """                    // Revu: Create Legend - for this sheet only - then click
                    // where it goes; its look is set in Legend Properties
                    // (OE-DELIVERY 2026-11-12-revu-ui).
                    pendingLegendSetupRef.current = { live: true, columns: [...LEGEND_DEFAULT_COLUMNS], title: 'Legend', showTitle: true, border: 'grid' };
                    setLegendPlacing(true);
                    setLegendPropsOpen(true);
                    setContextMenu(null);
                    addToast({ type: 'info', title: 'Click the sheet to place the legend', message: 'For this sheet only. Select it afterwards to set its properties.' });""")
rep("""                  <span className="flex-1">{t('takeoff_viewer.create_new_legend', { defaultValue: 'Create New Legend' })}</span>""",
    """                  <span className="flex-1">Create Legend <span className="text-content-tertiary">(this sheet)</span></span>""")

# Context item on a legend: Legend Properties.
rep("""                    <button type="button" className={item} role="menuitem" data-testid="context-legend-setup" onClick={() => { setLegendSetupDlg({ mode: 'edit', id: first.id }); close(); }}>
                      <BookOpen size={13} /><span className="flex-1">Legend Setup…</span>
                    </button>""", """                    <button type="button" className={item} role="menuitem" data-testid="context-legend-setup" onClick={() => { setSelectedMeasurementId(first.id); setLegendPropsOpen(true); close(); }}>
                      <BookOpen size={13} /><span className="flex-1">Legend Properties…</span>
                    </button>""")

# State: panel open flag.
rep("""  const pendingLegendSetupRef = useRef<LegendSetup | null>(null);""", """  const pendingLegendSetupRef = useRef<LegendSetup | null>(null);
  /** Legend Properties panel shows for a selected legend (Revu). */
  const [legendPropsOpen, setLegendPropsOpen] = useState(true);""")

# The panel, next to the setup window.
rep("""      <LegendSetupDialog
        open={legendSetupDlg !== null}""", """      {selectedMeasurement?.type === 'legend' && legendPropsOpen && (
        <div className="fixed right-14 top-44 z-40" data-testid="legend-props-host">
          <LegendPropertiesPanel
            setup={selectedMeasurement.legendSetup}
            defaults={{ text: legendTextColor, bg: legendBgColor, border: legendBorderStyle }}
            columnDefs={legendColumnDefs.map((c) => ({ key: c.key, label: c.key === 'count' ? 'Count' : c.key === 'subject' ? 'Description (Subject)' : c.label }))}
            onChange={(patch) => {
              const id = selectedMeasurement.id;
              setMeasurements((prev) => prev.map((x) => (x.id === id ? { ...x, legendSetup: { ...(x.legendSetup ?? {}), ...patch } } : x)));
            }}
            onClose={() => setLegendPropsOpen(false)}
          />
        </div>
      )}
      <LegendSetupDialog
        open={legendSetupDlg !== null}""")

p.write_text(s, encoding="utf-8")
print("ok")
