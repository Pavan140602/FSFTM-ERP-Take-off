from pathlib import Path

root = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:90])
    s = s.replace(a, b)


# ── Markups list (ledger) ──────────────────────────────────────────────
p = root / "features" / "takeoff" / "components" / "MeasurementLedger.tsx"
s = p.read_text(encoding="utf-8")
rep("""                selectedIds={selectedIds}
                onToggleSelect={onToggleSelect}
                onRowClick={onRowClick}
                onAddToBoq={onAddToBoq}""", """                selectedIds={selectedIds}
                onToggleSelect={onToggleSelect}
                onRowClick={onRowClick}
                onRowClickEvent={handleRowClickEvent}
                onAddToBoq={onAddToBoq}""")
rep("""  selectedIds,
  onToggleSelect,
  onRowClick,
  onAddToBoq,
  onCreateRfi,
  measurementSystem,
  customColumns,
  onCustomFieldChange,
  onFieldChange,
  hiddenColumns,
  pageLabels,
  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: {
  group: string;""", """  selectedIds,
  onToggleSelect,
  onRowClick,
  onRowClickEvent,
  onAddToBoq,
  onCreateRfi,
  measurementSystem,
  customColumns,
  onCustomFieldChange,
  onFieldChange,
  hiddenColumns,
  pageLabels,
  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: {
  group: string;""")
rep("""  onToggleSelect?: (id: string) => void;
  onRowClick?: (m: Measurement) => void;
  onAddToBoq?: (m: Measurement) => void;
  onCreateRfi?: (m: Measurement) => void;
  measurementSystem: import('@/stores/usePreferencesStore').MeasurementSystem;""", """  onToggleSelect?: (id: string) => void;
  onRowClick?: (m: Measurement) => void;
  /** Row click with its keys: Ctrl / Cmd toggles, Shift selects a run
   *  (OE-DELIVERY 2026-11-07-multi-select). */
  onRowClickEvent?: (e: React.MouseEvent, m: Measurement) => void;
  onAddToBoq?: (m: Measurement) => void;
  onCreateRfi?: (m: Measurement) => void;
  measurementSystem: import('@/stores/usePreferencesStore').MeasurementSystem;""")
rep("""      <tr
        key={measurement.id}
        onClick={() => onRowClick?.(measurement)}""", """      <tr
        key={measurement.id}
        onClick={(e) => (onRowClickEvent ? onRowClickEvent(e, measurement) : onRowClick?.(measurement))}""")
# the handler, defined in the main component right after multiSelect
rep("""  const multiSelect = Boolean(onToggleSelect);""", """  const multiSelect = Boolean(onToggleSelect);
  /** Last row clicked: the start of a Shift+click run. */
  const anchorRef = useRef<string | null>(null);
  /** Ctrl / Cmd + click adds or removes one row from the selection; Shift +
   *  click selects every row from the last one clicked to this one, as
   *  listed (OE-DELIVERY 2026-11-07-multi-select). A plain click opens the
   *  markup as before. */
  const handleRowClickEvent = (e: React.MouseEvent, m: Measurement) => {
    if (onToggleSelect && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault();
      onToggleSelect(m.id);
      anchorRef.current = m.id;
      return;
    }
    if (onToggleSelect && e.shiftKey && anchorRef.current) {
      e.preventDefault();
      window.getSelection?.()?.removeAllRanges();
      const order = rowsByGroup.flatMap(([, gr]) => gr.map((r) => r.measurement.id));
      const a = order.indexOf(anchorRef.current);
      const b = order.indexOf(m.id);
      if (a >= 0 && b >= 0) {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        for (const id of order.slice(lo, hi + 1)) {
          if (!selectedIds?.has(id)) onToggleSelect(id);
        }
        return;
      }
    }
    anchorRef.current = m.id;
    onRowClick?.(m);
  };""")
if "useRef" not in s.split("\n", 40)[0:40].__str__():
    pass
p.write_text(s, encoding="utf-8")

# ── Detected markups list ──────────────────────────────────────────────
p = root / "modules" / "pdf-takeoff" / "AutoTakeoffList.tsx"
s = p.read_text(encoding="utf-8")
rep("""  const visible = useMemo(() => (scope === 'page' ? rows.filter((r) => r.page === currentPage) : rows), [rows, scope, currentPage]);
  const tree = useMemo(() => groupAutoRows(visible), [visible]);""", """  const visible = useMemo(() => (scope === 'page' ? rows.filter((r) => r.page === currentPage) : rows), [rows, scope, currentPage]);
  const tree = useMemo(() => groupAutoRows(visible), [visible]);
  /** Last row clicked: the start of a Shift+click run (OE-DELIVERY 2026-11-07-multi-select). */
  const anchor = useRef<string | null>(null);
  /** Ctrl / Cmd + click adds or removes one markup; Shift + click selects the
   *  run of markups from the last one clicked, as listed; a plain click
   *  selects and zooms to one markup. */
  const rowClick = (e: React.MouseEvent, id: string) => {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault();
      const next = new Set(selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      anchor.current = id;
      onSelect([...next]);
      return;
    }
    if (e.shiftKey && anchor.current) {
      e.preventDefault();
      window.getSelection?.()?.removeAllRanges();
      // Rows in the order they show: open categories and groups only.
      const order: string[] = [];
      for (const c of tree) {
        if (!openCats.has(c.cat)) continue;
        for (const g of c.groups) {
          if (!openGroups.has(`${c.cat}|${g.des}`)) continue;
          for (const r of g.rows.slice(0, SHOW_ROWS)) order.push(r.id);
        }
      }
      const a = order.indexOf(anchor.current);
      const b = order.indexOf(id);
      if (a >= 0 && b >= 0) {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        onSelect([...new Set([...selectedIds, ...order.slice(lo, hi + 1)])]);
        return;
      }
    }
    anchor.current = id;
    onFocus(id);
  };""")
rep("""                              onClick={() => onFocus(r.id)}
                              title="Select and zoom to this markup\"""", """                              onClick={(e) => rowClick(e, r.id)}
                              title="Click: select and zoom to it. Ctrl+click: add or remove it. Shift+click: select every markup from the last one clicked\"""")
p.write_text(s, encoding="utf-8")
print("ok")
