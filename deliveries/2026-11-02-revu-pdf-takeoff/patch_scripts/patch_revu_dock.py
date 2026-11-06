"""Revu dock: one left icon rail for every panel (panels moved left),
click-to-close / edge rail, bottom panel cap, two-way Sync.
OE-DELIVERY: 2026-11-02-revu-dock"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-dock'


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:100], s.count(old))
    s = s.replace(old, new)


# icons
rep("""  Eye,
  EyeOff,
  Images,
  ListOrdered,""", """  Eye,
  EyeOff,
  Images,
  ListOrdered,
  Palette,
  SlidersHorizontal,
  Wrench,
  WandSparkles,""")

# bottom panel never pushes past the window: leave the toolbars, status bar
# and a strip of drawing.
rep("""const ledgerMax = (): number => Math.max(LEDGER_MIN + 40, (typeof window !== 'undefined' ? window.innerHeight : 1000) - 160);""",
    """const ledgerMax = (): number => Math.max(LEDGER_MIN + 40, (typeof window !== 'undefined' ? window.innerHeight : 1000) - 420);""")

# resize drag can be mirrored (the panel docked on the other side)
rep("""  const beginPanelResize = useCallback((side: 'left' | 'right', startWidthOverride?: number) =>""",
    """  const beginPanelResize = useCallback((side: 'left' | 'right', startWidthOverride?: number, mirrored = false) =>""")
rep("""        rtl: typeof document !== 'undefined' && document.documentElement.dir === 'rtl',
        latest: startWidth,""", """        // A panel docked on the other side (""" + TAG + """) drags mirrored.
        rtl: (typeof document !== 'undefined' && document.documentElement.dir === 'rtl') !== mirrored,
        latest: startWidth,""")

# leftTab gains 'side' = the Properties / Tool Chest / ... panel docked left
rep("""  const [leftTab, setLeftTab] = useState<'thumbs' | 'index' | 'layers'>(() => {
    try {
      const v = localStorage.getItem('takeoff.leftTab');
      return v === 'index' || v === 'layers' ? v : 'thumbs';""", """  const [leftTab, setLeftTab] = useState<'thumbs' | 'index' | 'layers' | 'side'>(() => {
    try {
      const v = localStorage.getItem('takeoff.leftTab');
      return v === 'index' || v === 'layers' || v === 'side' ? v : 'thumbs';""")

STATE = r'''
  /* ── Revu dock (TAGX): every panel docks on the LEFT behind one vertical
   * icon rail, like Revu. Clicking the open panel's icon closes it (the rail
   * stays at the edge); clicking any icon opens that panel. */
  const [panelSide, setPanelSide] = useState<'left' | 'right'>(() => {
    try { return localStorage.getItem('takeoff.panelSide') === 'right' ? 'right' : 'left'; } catch { return 'left'; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.panelSide', panelSide); } catch { /* ignore */ }
  }, [panelSide]);
  /** Opening a sidebar tab from code (selection, menus, deep link) brings
   *  the docked panel forward on the left. */
  const sidebarTabFirstRef = useRef(true);
  useEffect(() => {
    if (sidebarTabFirstRef.current) {
      sidebarTabFirstRef.current = false;
      return;
    }
    if (panelSide !== 'left') return;
    setLeftTab('side');
    setShowThumbnails(true);
    setShowSidebar(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sidebarTab]);
  const sideLeftOpen = panelSide === 'left' && showThumbnails && leftTab === 'side' && showSidebar;
  const sideVisible = panelSide === 'left' ? sideLeftOpen : showSidebar;
  const openRevuPanel = useCallback(
    (key: 'thumbs' | 'index' | 'layers' | 'properties' | 'tools' | 'colours' | 'ai' | 'auto') => {
      const isSide = key !== 'thumbs' && key !== 'index' && key !== 'layers';
      const isActive = isSide
        ? (panelSide === 'left' ? leftTab === 'side' && showThumbnails && showSidebar : showSidebar) && sidebarTab === key
        : leftTab === key && showThumbnails;
      if (isActive) {
        // Revu: clicking the open panel's tab closes the panel.
        if (isSide && panelSide === 'right') setShowSidebar(false);
        else setShowThumbnails(false);
        return;
      }
      if (isSide) {
        sidebarTabFirstRef.current = false;
        setSidebarTab(key);
        setShowSidebar(true);
        if (panelSide === 'left') {
          setLeftTab('side');
          setShowThumbnails(true);
        }
      } else {
        setLeftTab(key);
        setShowThumbnails(true);
      }
    },
    [panelSide, leftTab, showThumbnails, showSidebar, sidebarTab],
  );
'''.replace('TAGX', TAG)
rep("""  /** Thumbnail whose sheet number is being typed""", STATE + """  /** Thumbnail whose sheet number is being typed""")

RAIL = r'''          {/* Revu icon rail (TAGX): one vertical strip at the left edge
              for every panel; stays when the panel is closed. */}
          <div
            className="flex w-9 shrink-0 flex-col items-center gap-1 rounded-lg border border-border bg-surface-secondary/70 py-1.5"
            role="tablist"
            aria-orientation="vertical"
            data-testid="revu-rail"
            style={{ order: 0 }}
          >
            {([
              ['thumbs', 'Thumbnails', Images],
              ['index', 'Page Index', ListOrdered],
              ['layers', 'Layers', Layers],
              ['sep', '', null],
              ['properties', 'Properties', SlidersHorizontal],
              ['tools', 'Tool Chest', Wrench],
              ['colours', 'Colours & Labels', Palette],
              ['ai', 'AI Assistant', Sparkles],
              ['auto', 'Auto Takeoff', WandSparkles],
            ] as const).map(([key, label, Icon]) => {
              if (key === 'sep' || !Icon) return <span key="sep" className="my-0.5 h-px w-5 bg-border" aria-hidden="true" />;
              const isSide = key !== 'thumbs' && key !== 'index' && key !== 'layers';
              const active = isSide
                ? sideVisible && sidebarTab === key
                : showThumbnails && leftTab === key;
              return (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  aria-label={label}
                  title={label}
                  onClick={() => openRevuPanel(key)}
                  data-testid={`rail-${key}`}
                  className={clsx(
                    'flex h-8 w-8 items-center justify-center rounded transition-colors',
                    active ? 'bg-oe-blue text-white shadow-sm' : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
                  )}
                >
                  <Icon size={16} />
                </button>
              );
            })}
          </div>
'''.replace('TAGX', TAG)
rep("""      {pdfDoc && (
        <div
          className="flex flex-1 min-h-0 min-w-0"
        >""", """      {pdfDoc && (
        <div
          className="flex flex-1 min-h-0 min-w-0"
        >
""" + RAIL)

# left content panel: no inner rail any more; hidden while the docked side
# panel is open; no collapsed edge tab when the rail is there
start = s.index("""              {/* Revu left panel tabs (OE-DELIVERY 2026-11-02-revu-left-panel) */}""")
end = s.index("""              <div className="flex min-h-0 min-w-0 flex-1 flex-col">""", start)
s = s[:start] + s[end:]
rep("""          {totalPages >= 1 && (
            showThumbnails ? (""", """          {totalPages >= 1 && (
            showThumbnails && leftTab !== 'side' ? (""")
rep("""            ) : (
            <CollapsedEdgeTab
              side="left\"""", """            ) : panelSide === 'left' ? null : (
            <CollapsedEdgeTab
              side="left\"""")

# canvas column after any left-docked panel
rep("""          <div className="flex flex-1 min-w-0 min-h-0 flex-col space-y-2">""",
    """          <div className="flex flex-1 min-w-0 min-h-0 flex-col space-y-2" style={{ order: 3 }}>""")

# right sidebar: docked left when panelSide is left
rep("""          {showSidebar ? (
            <>
            <TakeoffResizeHandle
              testId="takeoff-resize-handle-right"
              label={t('takeoff_viewer.resize_panel', { defaultValue: 'Drag to resize the measurements panel · click to collapse · drag to the right edge to hide · double-click to reset' })}
              onPointerDown={beginPanelResize('right')}
              onDoubleClick={() => resetPanelWidth('right')}
              onKeyDown={onResizeHandleKeyDown('right')}
            />
            <div
              className="shrink-0 space-y-2 overflow-y-auto min-h-0"
              style={{ width: rightPanelWidth }}
              data-testid="measurements-panel"
            >""", """          {sideVisible ? (
            <>
            <div className="flex shrink-0" style={{ order: panelSide === 'left' ? 2 : 4 }}>
            <TakeoffResizeHandle
              testId="takeoff-resize-handle-right"
              label={t('takeoff_viewer.resize_panel', { defaultValue: 'Drag to resize the panel · click to close it · double-click to reset' })}
              onPointerDown={beginPanelResize('right', undefined, panelSide === 'left')}
              onDoubleClick={() => resetPanelWidth('right')}
              onKeyDown={onResizeHandleKeyDown('right')}
            />
            </div>
            <div
              className="shrink-0 space-y-2 overflow-y-auto min-h-0"
              style={{ width: rightPanelWidth, order: panelSide === 'left' ? 1 : 5 }}
              data-testid="measurements-panel"
            >""")
rep("""          ) : (
            <CollapsedEdgeTab
              side="right\"""", """          ) : panelSide === 'left' ? null : (
            <CollapsedEdgeTab
              side="right\"""")

# the text tab row is replaced by the rail when docked left
rep("""            <div
              className="flex rounded-md border border-border/80 bg-surface-primary/80 backdrop-blur-sm p-1 shadow-sm"
              role="tablist"
              data-testid="sidebar-tab-toggle"
            >""", """            <div
              className={clsx('flex rounded-md border border-border/80 bg-surface-primary/80 backdrop-blur-sm p-1 shadow-sm', panelSide === 'left' && 'hidden')}
              role="tablist"
              data-testid="sidebar-tab-toggle"
            >""")

# Window menu: dock side
rep("""                { label: 'Left Panel', checked: showThumbnails, onClick: () => setShowThumbnails((x) => !x) },""",
    """                { label: 'Left Panel', checked: showThumbnails, onClick: () => setShowThumbnails((x) => !x) },
                { label: 'Dock Panels Left (Revu)', checked: panelSide === 'left', onClick: () => setPanelSide((p) => (p === 'left' ? 'right' : 'left')) },""")

# ── Two-way Sync ──
# same page in both panes when sync turns on
rep("""                    if (splitMode === 'off') {
                      const other = currentPage < totalPages ? currentPage + 1 : Math.max(1, currentPage - 1);
                      toggleSplit('vertical');
                      setSplitPage(other);
                      syncDeltaRef.current = other - currentPage;
                      setSyncViews(true);
                    } else {
                      setSyncViews((x) => {
                        if (!x) syncDeltaRef.current = splitPage - currentPage;
                        return !x;
                      });
                    }""", """                    // Revu Sync (""" + TAG + """): both panes on the same
                    // page number, zoom and position, driven from either one.
                    if (splitMode === 'off') toggleSplit('vertical');
                    setSyncViews((x) => {
                      if (!x || splitMode === 'off') {
                        syncDeltaRef.current = 0;
                        setSplitPage(currentPage);
                        setSplitZoom(zoom);
                        return true;
                      }
                      return false;
                    });""")
rep("""                  title={splitMode === 'off' ? 'Sync & compare: open the next sheet beside this one, in step' : syncViews ? 'Sync on: the second pane follows this view' : 'Sync off'}""",
    """                  title={syncViews ? 'Sync on: both panes show the same page, zoom and position' : 'Sync: split the view and keep both panes on the same page, zoom and position'}""")
rep("""                { label: 'Sync Split Views', checked: syncViews, disabled: splitMode === 'off', onClick: () => setSyncViews((x) => { if (!x) syncDeltaRef.current = splitPage - currentPage; return !x; }) },""",
    """                { label: 'Sync Split Views', checked: syncViews, onClick: () => { if (splitMode === 'off') toggleSplit('vertical'); setSyncViews((x) => { if (!x) { syncDeltaRef.current = 0; setSplitPage(currentPage); setSplitZoom(zoom); } return !x; }); } },""")

# split pane drives the main view too
rep("""                  onPageChange={(p) => { setSplitPage(p); if (syncViews) syncDeltaRef.current = p - currentPage; }}
                  onZoomChange={(z) => setSplitZoom(z)}
                  onClose={() => { setSplitMode('off'); setSyncViews(false); }}
                  syncTo={syncViews ? syncTo : null}
                />""", """                  onPageChange={(p) => { setSplitPage(p); if (syncViews) goToPage(p - syncDeltaRef.current); }}
                  onZoomChange={(z) => {
                    setSplitZoom(z);
                    if (syncViews && Math.abs(z - zoomRef.current) > 1e-4) {
                      mainSyncIgnoreUntilRef.current = Date.now() + 400;
                      zoomTo(z);
                    }
                  }}
                  onClose={() => { setSplitMode('off'); setSyncViews(false); }}
                  syncTo={syncViews ? syncTo : null}
                  onViewChange={syncViews ? applySplitView : undefined}
                />""")

# main side: ignore its own scroll emission while following the split pane
rep("""  const syncDeltaRef = useRef(0);""", """  const syncDeltaRef = useRef(0);
  /** While the main view follows the split pane, its own scroll must not
   *  echo back (""" + TAG + """). */
  const mainSyncIgnoreUntilRef = useRef(0);""")
rep("""    const onScroll = () => {
      if (!timer) timer = window.setTimeout(emit, 60);
    };
    c.addEventListener('scroll', onScroll, { passive: true });
    emit();""", """    const onScroll = () => {
      if (Date.now() < mainSyncIgnoreUntilRef.current) return;
      if (!timer) timer = window.setTimeout(emit, 60);
    };
    c.addEventListener('scroll', onScroll, { passive: true });
    if (Date.now() >= mainSyncIgnoreUntilRef.current) emit();""")
SPLIT_APPLY = r'''
  /** Sync from the split pane: centre the main view on the same spot. */
  const applySplitView = useCallback((fx: number, fy: number) => {
    const c = containerRef.current;
    const canvas = canvasRef.current;
    if (!c || !canvas) return;
    mainSyncIgnoreUntilRef.current = Date.now() + 300;
    const cr = canvas.getBoundingClientRect();
    const vr = c.getBoundingClientRect();
    c.scrollLeft += cr.left + fx * cr.width - (vr.left + vr.width / 2);
    c.scrollTop += cr.top + fy * cr.height - (vr.top + vr.height / 2);
  }, []);
'''
rep("""  /* Revu Sync effects (OE-DELIVERY 2026-11-02-revu-left-panel). */""", SPLIT_APPLY + """  /* Revu Sync effects (OE-DELIVERY 2026-11-02-revu-left-panel). */""")

# SplitPane: report its own scroll; never echo a position it was given
rep("""  onClose,
  syncTo,
}: {""", """  onClose,
  syncTo,
  onViewChange,
}: {""")
rep("""  syncTo?: { fx: number; fy: number; seq: number } | null;
}) {""", """  syncTo?: { fx: number; fy: number; seq: number } | null;
  /** Revu Sync, the other way: this pane's centre as a fraction of the sheet. */
  onViewChange?: (fx: number, fy: number) => void;
}) {""")
rep("""  // Revu Sync: follow the main view's position (OE-DELIVERY 2026-11-02-revu-left-panel).
  useEffect(() => {
    if (!syncTo) return;
    const id = window.setTimeout(() => {
      const sc = scrollRef.current;
      const sheet = sheetRef.current;
      if (!sc || !sheet) return;""", """  // Revu Sync: follow the main view's position (OE-DELIVERY 2026-11-02-revu-left-panel).
  const syncIgnoreUntilRef = useRef(0);
  const onViewChangeRef = useRef(onViewChange);
  onViewChangeRef.current = onViewChange;
  useEffect(() => {
    const sc = scrollRef.current;
    if (!sc) return;
    let timer = 0;
    const emit = () => {
      timer = 0;
      const sheet = sheetRef.current;
      const cb = onViewChangeRef.current;
      if (!sheet || !cb) return;
      const sr = sheet.getBoundingClientRect();
      const vr = sc.getBoundingClientRect();
      if (sr.width <= 0 || sr.height <= 0) return;
      cb((vr.left + vr.width / 2 - sr.left) / sr.width, (vr.top + vr.height / 2 - sr.top) / sr.height);
    };
    const onScroll = () => {
      if (Date.now() < syncIgnoreUntilRef.current) return;
      if (!timer) timer = window.setTimeout(emit, 60);
    };
    sc.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      sc.removeEventListener('scroll', onScroll);
      if (timer) window.clearTimeout(timer);
    };
  }, []);
  useEffect(() => {
    if (!syncTo) return;
    const id = window.setTimeout(() => {
      const sc = scrollRef.current;
      const sheet = sheetRef.current;
      if (!sc || !sheet) return;
      syncIgnoreUntilRef.current = Date.now() + 300;""")

v.write_text(s, encoding='utf-8')
print('ok')
