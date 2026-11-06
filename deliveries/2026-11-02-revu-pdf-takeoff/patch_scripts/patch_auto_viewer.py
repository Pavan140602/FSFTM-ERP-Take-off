"""Auto Takeoff wiring in the viewer (all-or-nothing). OE-DELIVERY: 2026-11-02-auto-takeoff"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-auto-takeoff'

HANDLERS = r'''  /* ── Auto Takeoff (TAGX) ──────────────────────────
   * The panel fetches detected framing items; these handlers turn them into
   * real measurements and merge them idempotently (data/auto-takeoff.ts):
   * re-runs update or skip, never duplicate, and never touch user edits. */
  const autoStats = useMemo(() => {
    const page: Record<string, number> = {};
    const total: Record<string, number> = {};
    let edited = 0;
    for (const m of measurements) {
      if (!m.auto) continue;
      total[m.auto.cat] = (total[m.auto.cat] ?? 0) + 1;
      if (m.page === currentPage) page[m.auto.cat] = (page[m.auto.cat] ?? 0) + 1;
      if (isAutoEdited(m)) edited++;
    }
    return { page, total, edited };
  }, [measurements, currentPage]);

  const applyAutoTakeoff = useCallback(
    (res: AutoTakeoffResponse, opts: AutoApplyOptions): AutoApplyResult => {
      let ps = pageScalesRef.current;
      const calibrated: number[] = [];
      if (opts.autoCalibrate) {
        for (const p of res.pages) {
          if (!p.paper_in_per_ft || p.items.length === 0 || pageIsCalibrated(ps, p.page)) continue;
          const sc = scaleFromPaperInches(p.paper_in_per_ft);
          if (!sc) continue;
          ps = setPageScaleIn(ps, p.page, sc);
          calibrated.push(p.page);
        }
        if (calibrated.length > 0) setPageScales(ps);
      }
      const author = useAuthStore.getState().userFullName || undefined;
      const stamp = Date.now();
      let seq = 0;
      const valueFor = (m: Measurement, pts: Point[]): Partial<Measurement> => {
        if (m.type === 'count') return { value: pts.length, unit: 'pcs', label: String(pts.length) };
        const patch = recomputeMeasurement(m, pts, scaleForMeasurement(ps, m.page, pts));
        return { value: patch.value, unit: patch.unit ?? m.unit, label: patch.label };
      };
      const notesFor = (item: AutoItem): string | undefined => {
        const parts = [
          item.spec,
          item.generated ? 'Generated at the callout spacing - check against the drawing.' : null,
          item.source === 'ai' ? 'Read with AI.' : null,
        ].filter(Boolean);
        return parts.length ? parts.join('\n') : undefined;
      };
      const build = (item: AutoItem): Measurement => {
        const meta = autoCategoryMeta(item.category);
        const pts = itemPoints(item);
        const type: Measurement['type'] = item.kind === 'line' ? 'distance' : item.kind === 'count' ? 'count' : 'area';
        const base: Measurement = {
          id: `auto_${stamp}_${seq++}`,
          type,
          points: pts,
          value: 0,
          unit: '',
          label: '',
          annotation: item.label,
          page: item.page,
          group: autoGroupName(item.category, item.designation),
          color: meta.color,
          strokeWidth: opts.style.width,
          strokeAlpha: opts.style.alpha,
          ...(type === 'area' ? { fillAlpha: 0.1 } : {}),
          labelMode: opts.style.labelMode,
          notes: notesFor(item),
          author,
          createdAt: new Date().toISOString(),
          auto: tagForItem(item, pts),
        };
        return { ...base, ...valueFor(base, pts) };
      };
      const update = (m: Measurement, item: AutoItem): Measurement => {
        const pts = itemPoints(item);
        const next: Measurement = {
          ...m,
          points: pts,
          annotation: item.label,
          group: autoGroupName(item.category, item.designation),
          notes: notesFor(item) ?? m.notes,
          auto: tagForItem(item, pts),
        };
        return { ...next, ...valueFor(next, pts) };
      };
      const before = measurementsRef.current;
      const result = mergeAutoItems(
        before,
        res.pages.flatMap((p) => p.items),
        build,
        update,
        { pages: new Set(opts.pages), categories: new Set<string>(opts.categories), removeStale: opts.removeStale },
      );
      const keptIds = new Set(result.next.map((m) => m.id));
      for (const m of before) if (!keptIds.has(m.id) && m.serverId) registerDeletion(m.serverId);
      const beforeIds = new Set(before.map((m) => m.id));
      const added = result.next.filter((m) => !beforeIds.has(m.id));
      setMeasurements(result.next);
      if (added.length > 0) pushUndo({ kind: 'bulk_add', measurements: added });
      return { ...result.summary, calibrated };
    },
    [pushUndo, registerDeletion],
  );

  const restyleAutoMarkups = useCallback((style: AutoStyle, cats: Set<string>): number => {
    let n = 0;
    const next = measurementsRef.current.map((m) => {
      if (!m.auto || !cats.has(m.auto.cat)) return m;
      n++;
      return { ...m, strokeWidth: style.width, strokeAlpha: style.alpha, labelMode: style.labelMode };
    });
    if (n > 0) setMeasurements(next);
    return n;
  }, []);

  const removeAutoMarkups = useCallback(
    (scope: 'page' | 'all', keepEdited: boolean, cats: Set<string>): number => {
      const page = currentPageRef.current;
      const gone = measurementsRef.current.filter(
        (m) =>
          m.auto &&
          cats.has(m.auto.cat) &&
          (scope === 'all' || m.page === page) &&
          !m.locked &&
          !m.flattened &&
          (!keepEdited || !isAutoEdited(m)),
      );
      if (gone.length === 0) return 0;
      const ids = new Set(gone.map((m) => m.id));
      for (const m of gone) if (m.serverId) registerDeletion(m.serverId);
      setMeasurements((prev) => prev.filter((m) => !ids.has(m.id)));
      setSelectedMeasurementId((cur) => (cur && ids.has(cur) ? null : cur));
      setSelectedLedgerIds(new Set());
      return gone.length;
    },
    [registerDeletion],
  );

  const selectAutoCategory = useCallback((cat: AutoCategory): number => {
    const page = currentPageRef.current;
    const ids = measurementsRef.current.filter((m) => m.auto?.cat === cat && m.page === page).map((m) => m.id);
    setSelectedLedgerIds(new Set(ids));
    setSelectedMeasurementId(ids.length === 1 ? ids[0]! : null);
    return ids.length;
  }, []);

'''.replace('TAGX', TAG)

KEYS = r'''      // Extend / shorten the selected straight markup(s) along their own
      // direction: Alt+Right/Up or ']' longer, Alt+Left/Down or '[' shorter;
      // Shift = 10 units. Works at the end handle the user clicked, else
      // both ends. Coalesced into one undo frame per burst like the nudge
      // (TAGX).
      {
        const isArrow = e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown';
        const isBracket = e.code === 'BracketLeft' || e.code === 'BracketRight';
        if (
          ((isArrow && e.altKey) || (isBracket && !e.altKey)) &&
          !e.ctrlKey &&
          !e.metaKey &&
          shouldHandleShortcut(e.target) &&
          !detectPickMode
        ) {
          const wanted = new Set<string>(selectedLedgerIds);
          if (selectedMeasurementId) wanted.add(selectedMeasurementId);
          const ids = new Set<string>();
          for (const m of measurements) {
            if (wanted.has(m.id) && m.page === currentPage && m.type === 'distance' && !m.locked && !m.flattened) ids.add(m.id);
          }
          if (ids.size > 0) {
            e.preventDefault();
            const longer = e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.code === 'BracketRight';
            const step = (e.shiftKey ? 10 : 1) * (longer ? 1 : -1);
            const av = activeVertexRef.current;
            const bag = nudgeUndoRef.current;
            setMeasurements((prev) =>
              prev.map((m) => {
                if (!ids.has(m.id)) return m;
                if (!bag.originals.has(m.id)) bag.originals.set(m.id, { ...m, points: [...m.points] });
                const end: 0 | 1 | 'both' = av && av.measurementId === m.id ? (av.index === 0 ? 0 : 1) : 'both';
                const pts = extendLine(m.points, step, end);
                const patch = recomputeMeasurement(m, pts, editScaleFor(m, pts));
                return { ...m, points: pts, value: patch.value, label: patch.label, unit: patch.unit ?? m.unit };
              }),
            );
            if (bag.timer) window.clearTimeout(bag.timer);
            bag.timer = window.setTimeout(flushNudgeUndo, 700);
            return;
          }
        }
      }

'''.replace('TAGX', TAG)

pairs = [
("""import DetectPanel from './DetectPanel';
""", """import DetectPanel from './DetectPanel';
// Auto Takeoff (""" + TAG + """).
import AutoTakeoffPanel, {
  type AutoApplyOptions,
  type AutoApplyResult,
  type AutoStyle,
  type AutoTakeoffResponse,
} from './AutoTakeoffPanel';
import {
  type AutoCategory,
  type AutoItem,
  type AutoTag,
  autoCategoryMeta,
  autoGroupName,
  extendLine,
  isAutoEdited,
  itemPoints,
  mergeAutoItems,
  scaleFromPaperInches,
  tagForItem,
} from './data/auto-takeoff';
"""),
("""  labelMode?: 'all' | 'value' | 'name' | 'none';
""", """  labelMode?: 'all' | 'value' | 'name' | 'none';
  /** Placed by Auto Takeoff (""" + TAG + """). */
  auto?: AutoTag;
"""),
("""  const [sidebarTab, setSidebarTab] = useState<'properties' | 'tools' | 'colours' | 'ai' | 'detect'>(() => {
    try {
      const saved = localStorage.getItem('takeoff.sidebarTab');
      return saved === 'tools' || saved === 'colours' ? saved : 'properties';""",
 """  const [sidebarTab, setSidebarTab] = useState<'properties' | 'tools' | 'colours' | 'ai' | 'detect' | 'auto'>(() => {
    try {
      const saved = localStorage.getItem('takeoff.sidebarTab');
      return saved === 'tools' || saved === 'colours' || saved === 'auto' ? saved : 'properties';"""),
("""                {t('takeoff_viewer.tab_detect', { defaultValue: 'Detect' })}
              </button>
""", """                {t('takeoff_viewer.tab_detect', { defaultValue: 'Detect' })}
              </button>
              {/* Auto Takeoff (""" + TAG + """) */}
              <button
                type="button"
                role="tab"
                aria-selected={sidebarTab === 'auto'}
                onClick={() => setSidebarTab('auto')}
                className={clsx(
                  'flex-1 px-2 py-1 rounded text-[11px] font-semibold transition-colors',
                  sidebarTab === 'auto'
                    ? 'bg-oe-blue text-white shadow-sm'
                    : 'text-content-secondary hover:bg-surface-secondary',
                )}
                data-testid="sidebar-tab-auto"
              >
                {t('takeoff_viewer.tab_auto', { defaultValue: 'Auto Takeoff' })}
              </button>
"""),
("""                onShowMarks={setDetectMarks}
              />
            )}
""", """                onShowMarks={setDetectMarks}
              />
            )}

            {/* Auto Takeoff — placed, editable framing markups (""" + TAG + """). */}
            {sidebarTab === 'auto' && (
              <AutoTakeoffPanel
                documentId={documentId}
                currentPage={currentPage}
                pageCount={totalPages}
                stats={autoStats}
                onApply={applyAutoTakeoff}
                onRestyle={restyleAutoMarkups}
                onRemove={removeAutoMarkups}
                onSelectCategory={selectAutoCategory}
                onJumpToPage={goToPage}
              />
            )}
"""),
("""  /** Scan the current page's vector layer and drop suggested measurements.""",
 HANDLERS + """  /** Scan the current page's vector layer and drop suggested measurements."""),
("""      // Arrow keys nudge the selected markup(s) on the current
      // page: 1 unit per press, Shift for a bigger step; a burst of""",
 KEYS + """      // Arrow keys nudge the selected markup(s) on the current
      // page: 1 unit per press, Shift for a bigger step; a burst of"""),
("""handleCanvasDblClick, currentPage, detectPickMode, nudgeMeasurements]);""",
 """handleCanvasDblClick, currentPage, detectPickMode, nudgeMeasurements, flushNudgeUndo]);"""),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
v.write_text(s, encoding='utf-8')
print('ok', len(pairs))
