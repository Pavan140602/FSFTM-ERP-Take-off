"""Markups list right-click = Revu markup menu for the selection
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    n = s.count(a)
    assert n == 1, (n, a[:90])
    s = s.replace(a, b)


rep('''  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    measurementId: string;
  } | null>(null);''', '''  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    measurementId: string;
    /** Opened from the Markups list (OE-DELIVERY 2026-11-12-revu-ui). */
    fromList?: boolean;
  } | null>(null);
  /** Which sub-list of the markup menu is open (Status / Colour). */
  const [contextSub, setContextSub] = useState<'status' | 'colour' | null>(null);''')

rep('''  const handleLedgerRowClick = useCallback((m: Measurement) => {''', '''  /** Right-click in the Markups list: like Revu, a row outside the
   *  selection becomes the selection; a row inside keeps the whole
   *  selection, and the markup menu acts on all of it
   *  (OE-DELIVERY 2026-11-12-revu-ui). */
  const openListContextMenu = useCallback((e: React.MouseEvent, m: Measurement) => {
    if (!selectedLedgerIdsRef.current.has(m.id)) setSelectedLedgerIds(new Set([m.id]));
    setSelectedMeasurementId(m.id);
    setContextSub(null);
    setContextMenu({ x: e.clientX, y: e.clientY, measurementId: m.id, fromList: true });
  }, []);

  const handleLedgerRowClick = useCallback((m: Measurement) => {''')

rep('''                    onRowClick={handleLedgerRowClick}
                    selectedMeasurementId={selectedMeasurementId}''', '''                    onRowClick={handleLedgerRowClick}
                    onRowContextMenu={openListContextMenu}
                    selectedMeasurementId={selectedMeasurementId}''')

rep('''            role="menu"
            data-testid="measurement-context-menu"
          >''', '''            role="menu"
            data-testid="measurement-context-menu"
          >
            {(() => {
              // Revu markup menu for the selection (OE-DELIVERY 2026-11-12-revu-ui).
              const cm = contextMenu;
              const ids: ReadonlySet<string> =
                selectedLedgerIds.size > 1 && selectedLedgerIds.has(cm.measurementId) ? selectedLedgerIds : new Set([cm.measurementId]);
              const n = ids.size;
              const first = measurements.find((x) => x.id === cm.measurementId);
              const picked = measurements.filter((x) => ids.has(x.id));
              const anyLocked = picked.some((x) => x.locked);
              const allHidden = picked.length > 0 && picked.every((x) => hiddenMeasurements.has(x.id));
              const item = 'flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors';
              const close = () => { setContextMenu(null); setContextSub(null); };
              const STATUSES = ['None', 'Accepted', 'Rejected', 'Cancelled', 'Completed'];
              return (
                <>
                  <div className="px-3 pb-1 pt-0.5 text-[10px] uppercase tracking-wide text-content-tertiary" data-testid="context-count">
                    {n} markup{n === 1 ? '' : 's'} selected
                  </div>
                  {cm.fromList && first && (
                    <button type="button" className={item} role="menuitem" data-testid="context-goto" onClick={() => { handleLedgerRowClick(first); close(); }}>
                      <Copy size={13} className="opacity-0" /><span className="flex-1">Go to markup</span>
                    </button>
                  )}
                  <button
                    type="button"
                    className={item}
                    role="menuitem"
                    data-testid="context-properties"
                    onClick={() => {
                      setRightPanelWidth((w) => (w !== 0 ? w : lastOpenRightWidthRef.current > 0 ? lastOpenRightWidthRef.current : RIGHT_PANEL_DEFAULT));
                      setShowSidebar(true);
                      setSidebarTab('properties');
                      close();
                    }}
                  >
                    <Copy size={13} className="opacity-0" /><span className="flex-1">Properties</span>
                  </button>
                  <button type="button" className={item} role="menuitem" data-testid="context-status" onClick={() => setContextSub((v) => (v === 'status' ? null : 'status'))}>
                    <Copy size={13} className="opacity-0" /><span className="flex-1">Set Status</span><span className="text-content-tertiary">{contextSub === 'status' ? '▾' : '▸'}</span>
                  </button>
                  {contextSub === 'status' && (
                    <div className="ml-7 border-l border-border pl-1" data-testid="context-status-list">
                      {STATUSES.map((st) => (
                        <button
                          key={st}
                          type="button"
                          className={item}
                          role="menuitem"
                          data-testid={`context-status-${st.toLowerCase()}`}
                          onClick={() => { handleLedgerFlagsChange(cm.measurementId, { status: st === 'None' ? '' : st }); close(); }}
                        >
                          <span className="flex-1">{st}</span>
                          {first && (first.status || 'None') === st ? <span className="text-oe-blue">✓</span> : null}
                        </button>
                      ))}
                    </div>
                  )}
                  <button type="button" className={item} role="menuitem" data-testid="context-colour" onClick={() => setContextSub((v) => (v === 'colour' ? null : 'colour'))}>
                    <span className="inline-block h-3 w-3 rounded-sm border border-black/20" style={{ background: first ? resolveMeasurementColor(first, groupColorMap) : '#888' }} />
                    <span className="flex-1">Colour</span><span className="text-content-tertiary">{contextSub === 'colour' ? '▾' : '▸'}</span>
                  </button>
                  {contextSub === 'colour' && (
                    <div className="px-3 py-1.5" data-testid="context-colour-list">
                      <ColorPicklist
                        value={first ? resolveMeasurementColor(first, groupColorMap) : null}
                        onChange={(c) => {
                          if (!c) return;
                          setMeasurements((prev) => prev.map((x) => (ids.has(x.id) && !x.locked && !x.flattened ? { ...x, color: c } : x)));
                          close();
                        }}
                        title="Colour"
                        testId="context-colour-pick"
                        size={22}
                      />
                    </div>
                  )}
                  <button
                    type="button"
                    className={item}
                    role="menuitem"
                    data-testid="context-lock"
                    onClick={() => { handleLedgerFlagsChange(cm.measurementId, { locked: !anyLocked }); close(); }}
                  >
                    <Copy size={13} className="opacity-0" /><span className="flex-1">{anyLocked ? 'Unlock' : 'Lock'}</span>
                  </button>
                  <button
                    type="button"
                    className={item}
                    role="menuitem"
                    data-testid="context-hide"
                    onClick={() => {
                      setHiddenMeasurements((prev) => {
                        const next = new Set(prev);
                        for (const id of ids) {
                          if (allHidden) next.delete(id);
                          else next.add(id);
                        }
                        return next;
                      });
                      close();
                    }}
                  >
                    <Copy size={13} className="opacity-0" /><span className="flex-1">{allHidden ? 'Show' : 'Hide'}</span>
                  </button>
                  <button
                    type="button"
                    className={item}
                    role="menuitem"
                    data-testid="context-select-all"
                    onClick={() => {
                      const all = measurements.filter((x) => x.page === (first?.page ?? currentPage)).map((x) => x.id);
                      setSelectedLedgerIds(new Set(all));
                      close();
                    }}
                  >
                    <Copy size={13} className="opacity-0" /><span className="flex-1">Select All (this page)</span>
                  </button>
                  <div className="my-1 border-t border-border" />
                </>
              );
            })()}''')

rep('''              onClick={() => { deleteMeasurement(contextMenu.measurementId); setContextMenu(null); }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-semantic-error hover:bg-semantic-error-bg transition-colors"
              role="menuitem"
              data-testid="context-delete"''', '''              onClick={() => {
                // Several selected: delete them all, like Revu (OE-DELIVERY 2026-11-12-revu-ui).
                if (selectedLedgerIds.size > 1 && selectedLedgerIds.has(contextMenu.measurementId)) bulkDeleteSelected();
                else deleteMeasurement(contextMenu.measurementId);
                setContextMenu(null);
              }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-semantic-error hover:bg-semantic-error-bg transition-colors"
              role="menuitem"
              data-testid="context-delete"''')

p.write_text(s, encoding="utf-8")
print("ok")
