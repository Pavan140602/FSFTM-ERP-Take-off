"""Auto Takeoff list, single-column delete, remembered deletions (all-or-nothing).
OE-DELIVERY: 2026-11-02-auto-takeoff-list"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-auto-takeoff-list'

LIST_HANDLERS = r'''  /* ── Auto Takeoff list + single delete (TAGX) ─────────────────
   * Columns used to be ONE count markup per sheet, so clicking one column
   * selected them all and a single wrong one could not be removed. They are
   * now one markup each; an earlier combined count is split here once. */
  useEffect(() => {
    if (!hasCombinedAutoCounts(measurements)) return;
    const stamp = Date.now();
    const { next } = splitAutoCounts(measurements, (m, p, i, tag) => ({
      ...m,
      id: i === 0 ? m.id : `${m.id}_c${i}_${stamp}`,
      serverId: i === 0 ? m.serverId : undefined,
      points: [p],
      value: 1,
      label: '1',
      auto: tag,
    }));
    setMeasurements(next);
  }, [measurements]);

  /** Deleted auto markups, remembered per drawing so a re-run never places
   *  them again. Clearing (the Clear buttons) is not remembered. */
  const rejectedKey = documentId ? `takeoff.autoRejected.${documentId}` : '';
  const [autoRejected, setAutoRejected] = useState<RejectedTag[]>([]);
  useEffect(() => {
    if (!rejectedKey) {
      setAutoRejected([]);
      return;
    }
    try {
      const raw = localStorage.getItem(rejectedKey);
      const parsed = raw ? (JSON.parse(raw) as RejectedTag[]) : [];
      setAutoRejected(Array.isArray(parsed) ? parsed : []);
    } catch {
      setAutoRejected([]);
    }
  }, [rejectedKey]);
  const autoRejectedRef = useRef(autoRejected);
  autoRejectedRef.current = autoRejected;
  const rememberRejected = useCallback(
    (ms: Measurement[]) => {
      const tags = ms.map((m) => rejectedFrom(m)).filter((t): t is RejectedTag => t !== null);
      if (tags.length === 0) return;
      setAutoRejected((prev) => {
        const next = [...prev, ...tags].slice(-5000);
        try {
          if (rejectedKey) localStorage.setItem(rejectedKey, JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    },
    [rejectedKey],
  );
  const forgetRejected = useCallback(() => {
    setAutoRejected([]);
    try {
      if (rejectedKey) localStorage.removeItem(rejectedKey);
    } catch {
      /* ignore */
    }
  }, [rejectedKey]);

  const autoRows = useMemo<AutoListRow[]>(
    () =>
      measurements
        .filter((m) => m.auto)
        .map((m) => ({
          id: m.id,
          cat: m.auto!.cat,
          des: m.auto!.des,
          page: m.page,
          valueText:
            m.type === 'count'
              ? String(m.points.length)
              : measurementLabel(m, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnitRef.current, imperialDenominator),
          value: m.type === 'count' ? m.points.length : m.value || 0,
          edited: isAutoEdited(m),
          generated: Boolean(m.auto!.gen),
        })),
    [measurements, pageScales, measurementSystem, imperialDenominator],
  );

  const formatAutoTotal = useCallback(
    (ids: string[]): string => {
      const set = new Set(ids);
      const ms = measurementsRef.current.filter((m) => set.has(m.id));
      const first = ms[0];
      if (!first) return '';
      if (first.type === 'count') return String(ms.length);
      const sum = ms.reduce((acc, m) => acc + (m.value || 0), 0);
      return measurementLabel(
        { ...first, value: sum },
        scaleForMeasurement(pageScalesRef.current, first.page, first.points),
        measurementSystem,
        areaAreaUnitRef.current,
        imperialDenominator,
      );
    },
    [measurementSystem, imperialDenominator],
  );

  /** Zoom so one markup fills the view, never closer than ~200 units. */
  const zoomToAutoMarkup = useCallback(
    (id: string) => {
      const m = measurementsRef.current.find((x) => x.id === id);
      if (!m) return;
      const b = boundingBoxOfPoints(m.points);
      if (!b) return;
      const cx = (b.minX + b.maxX) / 2;
      const cy = (b.minY + b.maxY) / 2;
      const hw = Math.max((b.maxX - b.minX) / 2 + 30, 100);
      const hh = Math.max((b.maxY - b.minY) / 2 + 30, 100);
      const vp = viewportSize();
      const res = computeZoomToBox({ minX: cx - hw, minY: cy - hh, maxX: cx + hw, maxY: cy + hh }, vp.width, vp.height, {
        fallbackZoom: zoomRef.current || 1,
      });
      zoomTo(res.zoom);
      if (pageModeRef.current === 'continuous') {
        pendingScrollRef.current = { kind: 'box', left: res.scrollLeft, top: res.scrollTop };
        return;
      }
      requestAnimationFrame(() => {
        const c = containerRef.current;
        if (!c) return;
        c.scrollLeft = res.scrollLeft;
        c.scrollTop = res.scrollTop;
      });
    },
    [viewportSize, zoomTo],
  );

  const pendingAutoFocusRef = useRef<string | null>(null);
  const focusAutoMarkup = useCallback(
    (id: string) => {
      const m = measurementsRef.current.find((x) => x.id === id);
      if (!m) return;
      setSelectedMeasurementId(id);
      setSelectedLedgerIds(new Set([id]));
      if (m.page !== currentPageRef.current) {
        pendingAutoFocusRef.current = id;
        goToPage(m.page);
        return;
      }
      zoomToAutoMarkup(id);
    },
    [goToPage, zoomToAutoMarkup],
  );
  useEffect(() => {
    const id = pendingAutoFocusRef.current;
    if (!id) return;
    const m = measurementsRef.current.find((x) => x.id === id);
    if (!m || m.page !== currentPage) return;
    pendingAutoFocusRef.current = null;
    const timer = window.setTimeout(() => {
      setSelectedMeasurementId(id);
      setSelectedLedgerIds(new Set([id]));
      zoomToAutoMarkup(id);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [currentPage, zoomToAutoMarkup]);

  const selectAutoIds = useCallback((ids: string[]) => {
    const page = currentPageRef.current;
    const onPage = ids.filter((id) => measurementsRef.current.some((m) => m.id === id && m.page === page));
    const chosen = onPage.length > 0 ? onPage : ids;
    setSelectedLedgerIds(new Set(chosen));
    setSelectedMeasurementId(chosen.length === 1 ? chosen[0]! : null);
  }, []);

  const deleteAutoMarkups = useCallback(
    (ids: string[]) => {
      const set = new Set(ids);
      const gone = measurementsRef.current.filter((m) => set.has(m.id) && !m.locked && !m.flattened);
      if (gone.length === 0) return;
      for (const m of gone) {
        pushUndo({ kind: 'delete_measurement', measurement: { ...m, points: [...m.points] } });
        if (m.serverId) registerDeletion(m.serverId);
      }
      rememberRejected(gone);
      const goneIds = new Set(gone.map((m) => m.id));
      setMeasurements((prev) => prev.filter((m) => !goneIds.has(m.id)));
      setSelectedMeasurementId((cur) => (cur && goneIds.has(cur) ? null : cur));
      setSelectedLedgerIds((prev) => {
        const next = new Set(prev);
        for (const id of goneIds) next.delete(id);
        return next;
      });
      addToast({
        type: 'info',
        title: `${gone.length} markup${gone.length === 1 ? '' : 's'} deleted`,
        message: 'Re-running Auto Takeoff will not place them again. Ctrl+Z brings them back.',
      });
    },
    [pushUndo, registerDeletion, rememberRejected, addToast],
  );

'''.replace('TAGX', TAG)

pairs = [
("""  mergeAutoItems,
  scaleFromPaperInches,
  tagForItem,
} from './data/auto-takeoff';""", """  mergeAutoItems,
  scaleFromPaperInches,
  tagForItem,
  // """ + TAG + """
  type AutoListRow,
  type RejectedTag,
  hasCombinedAutoCounts,
  rejectedFrom,
  splitAutoCounts,
} from './data/auto-takeoff';"""),
# merge honours rejected
("""        { pages: new Set(opts.pages), categories: new Set<string>(opts.categories), removeStale: opts.removeStale },""",
 """        {
          pages: new Set(opts.pages),
          categories: new Set<string>(opts.categories),
          removeStale: opts.removeStale,
          rejected: autoRejectedRef.current,
        },"""),
# handlers go right before applyAutoTakeoff (needs autoRejectedRef)
("""  const applyAutoTakeoff = useCallback(""", LIST_HANDLERS + """  const applyAutoTakeoff = useCallback("""),
# canvas Delete of an auto markup is remembered too
("""    if (target && (target.locked || target.flattened)) return;
    if (target) {
      pushUndo({ kind: 'delete_measurement', measurement: { ...target, points: [...target.points] } });""",
 """    if (target && (target.locked || target.flattened)) return;
    if (target) {
      // A deleted auto markup stays deleted on re-runs (""" + TAG + """).
      if (target.auto) rememberRejectedRef.current([target]);
      pushUndo({ kind: 'delete_measurement', measurement: { ...target, points: [...target.points] } });"""),
# panel props
("""                onSelectCategory={selectAutoCategory}
                onJumpToPage={goToPage}
              />""", """                onSelectCategory={selectAutoCategory}
                onJumpToPage={goToPage}
                rejectedCount={autoRejected.length}
                onForgetRejected={forgetRejected}
                list={{
                  rows: autoRows,
                  selectedIds: selectedMeasurementId ? new Set([...selectedLedgerIds, selectedMeasurementId]) : selectedLedgerIds,
                  formatTotal: formatAutoTotal,
                  onFocus: focusAutoMarkup,
                  onSelect: selectAutoIds,
                  onDelete: deleteAutoMarkups,
                }}
              />"""),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)

# deleteMeasurement is defined BEFORE the auto handlers, so it reaches
# rememberRejected through a ref declared near the top of the component.
anchor = """  const nudgeUndoRef = useRef<"""
assert s.count(anchor) == 1
s = s.replace(anchor, """  /** Set once the Auto Takeoff handlers exist (""" + TAG + """). */
  const rememberRejectedRef = useRef<(ms: Measurement[]) => void>(() => {});
""" + anchor)
anchor2 = """  const autoRejectedRef = useRef(autoRejected);
  autoRejectedRef.current = autoRejected;"""
s = s.replace(anchor2, anchor2)  # no-op, kept for clarity
anchor3 = """  const forgetRejected = useCallback(() => {"""
s = s.replace(anchor3, """  rememberRejectedRef.current = rememberRejected;
""" + anchor3)
v.write_text(s, encoding='utf-8')
print('ok', len(pairs))
