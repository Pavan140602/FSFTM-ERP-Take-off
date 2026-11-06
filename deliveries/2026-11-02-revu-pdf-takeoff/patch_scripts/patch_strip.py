# OE-DELIVERY 2026-11-02-revu-tool-strip
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d, want %d):\n%s' % (c, count, old[:300]))
        sys.exit(1)
    s = s.replace(old, new)


rep("import { RevuPropertiesBar, type PropsBarPatch } from './components/RevuPropertiesBar';\n",
    "import { RevuPropertiesBar, type PropsBarPatch } from './components/RevuPropertiesBar';\n"
    "import { RevuToolStrip, type StripTool } from './components/RevuToolStrip';\n")

# rail: drop Layers, Settings, Colours
rep("""              ['scale', 'Scale & Calibration', RvScaleIcon],
              ['layers', 'Layers (Alt+Y)', Layers],
              ['sep', '', null],
              ['properties', 'Settings (Alt+P)', RvSettingsIcon],
              ['colours', 'Colours & Labels', Palette],
              ['ai', 'AI Assistant', Sparkles],""",
    """              ['scale', 'Scale & Calibration', RvScaleIcon],
              ['sep', '', null],
              ['ai', 'AI Assistant', Sparkles],""")
rep("""  Settings as RvSettingsIcon,
""", "")

# Window menu: drop Layers, Settings, Colours
rep("""                { label: 'Layers', checked: showThumbnails && leftTab === 'layers', onClick: () => { setShowThumbnails(true); setLeftTab('layers'); } },
""", "")
rep("""                { label: 'Settings', shortcut: 'Alt+P', checked: showSidebar && sidebarTab === 'properties', onClick: () => { setShowSidebar(true); setSidebarTab('properties'); } },
""", "")
rep("""                { label: 'Colours', checked: showSidebar && sidebarTab === 'colours', onClick: () => { setShowSidebar(true); setSidebarTab('colours'); } },
""", "")

# selecting markups no longer opens the old Settings panel
rep("""    // Open the Properties panel on any ledger (un)check so the selection's
    // editable fields are immediately visible.
    setSidebarTab('properties');
""", """    // The selection's fields show in the top Properties bar (OE-DELIVERY 2026-11-02-revu-tool-strip).
""")
rep("""      setSelectedMeasurementId(next.size > 0 ? [...next][0] : null);
      return next;
    });
    setSidebarTab('properties');
""", """      setSelectedMeasurementId(next.size > 0 ? [...next][0] : null);
      return next;
    });
""")
rep("""  useEffect(() => {
    if (sidebarTabPrevRef.current === sidebarTab) return;
    sidebarTabPrevRef.current = sidebarTab;
    if (panelSide !== 'left') return;""",
    """  useEffect(() => {
    if (sidebarTabPrevRef.current === sidebarTab) return;
    sidebarTabPrevRef.current = sidebarTab;
    if (panelSide !== 'left') return;
    // Settings / Colours / Layers left the Revu rail; never pop them open.
    if (sidebarTab === 'properties' || sidebarTab === 'colours') return;""")
# a saved Layers / Settings / Colours panel falls back to Thumbnails
rep("""  useEffect(() => {
    try { localStorage.setItem('takeoff.leftTab', leftTab); } catch { /* ignore */ }
  }, [leftTab]);
""", """  useEffect(() => {
    try { localStorage.setItem('takeoff.leftTab', leftTab); } catch { /* ignore */ }
  }, [leftTab]);
  useEffect(() => {
    if (leftTab === 'layers' || (leftTab === 'side' && (sidebarTab === 'properties' || sidebarTab === 'colours'))) setLeftTab('thumbs');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
""")

# remove the top Markup group (tools now on the right strip)
a = s.index("              {/* Markup tools - second segmented track; orange accent marks")
b = s.index("              {/* Stamp preset (OE-DELIVERY 2026-10-30-revu-markup-tools):")
s = s[:a] + s[b:]

# the area popup anchors to the strip's Area button
rep("""                        ref={tool === 'area' ? areaToolBtnRef : undefined}
                        onClick={() => {
                          if (tool === 'area' && activeTool === 'area') {""",
    """                        onClick={() => {
                          if (tool === 'area' && activeTool === 'area') {""")
rep("""      setAreaPopupPos({ left: Math.max(8, rect.left), top: rect.bottom + 8 });""",
    """      setAreaPopupPos({ left: Math.max(8, Math.min(rect.left, window.innerWidth - 380)), top: Math.min(rect.bottom + 8, window.innerHeight - 320) });""")

# right strip between the canvas column and a right-docked panel
rep("""          <div className="flex flex-1 min-w-0 min-h-0 flex-col space-y-2" style={{ order: 3 }}>""",
    """          {/* Revu vertical tool strip (OE-DELIVERY 2026-11-02-revu-tool-strip). */}
          <div className="flex shrink-0 min-h-0" style={{ order: 4 }}>
            <RevuToolStrip
              tools={stripTools}
              active={activeTool}
              areaRef={areaToolBtnRef}
              onSelect={(tool) => {
                if (tool === 'area' && activeTool === 'area') {
                  setAreaPopupDismissed((d) => !d);
                  return;
                }
                setAreaPopupDismissed(false);
                selectTool(tool as MeasureTool);
              }}
            />
          </div>
          <div className="flex flex-1 min-w-0 min-h-0 flex-col space-y-2" style={{ order: 3 }}>""")
rep("""            <div className="flex shrink-0" style={{ order: panelSide === 'left' ? 2 : 4 }}>""",
    """            <div className="flex shrink-0" style={{ order: panelSide === 'left' ? 2 : 5 }}>""")
rep("""              style={{ width: rightPanelWidth, order: panelSide === 'left' ? 1 : 5 }}""",
    """              style={{ width: rightPanelWidth, order: panelSide === 'left' ? 1 : 6 }}""")

# Properties bar only for a selection; Subject + Label + Height
rep("""            {/* Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar). */}
            <div className="mb-1.5">
              <RevuPropertiesBar
                mode={propsBar.mode}
                type={propsBar.type}
                title={propsBar.title}
                value={propsBar.value}
                label={propsBar.label}
                onLabel={setPropsLabel}""",
    """            {/* Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar):
                only while markups are selected. */}
            {propsBar.mode === 'selection' && (
            <div className="mb-1.5">
              <RevuPropertiesBar
                mode={propsBar.mode}
                type={propsBar.type}
                title={propsBar.title}
                value={propsBar.value}
                subject={propsBar.subject}
                onSubject={setPropsSubject}
                label={propsBar.label}
                onLabel={setPropsLabel}
                onWallHeight={setPropsWallHeight}""")
rep("""                totals={propsBar.totals}
                defaults={propsBar.defaults}
              />
            </div>
""", """                totals={propsBar.totals}
                defaults={propsBar.defaults}
              />
            </div>
            )}
""")
rep("""        // Label = the Markups list Label column (Subject), as in Revu.
        label: first.customFields?.Subject ?? first.annotation ?? '',""",
    """        // Revu: Subject = category (Markups list Label column), Label = sheet text.
        subject: first.customFields?.Subject ?? '',
        label: first.auto ? (first.annotation?.trim() || first.auto.des) : (first.annotation ?? ''),""")
rep("""        value: toolStyles[activeTool] ?? {},
        label: undefined,""", """        value: toolStyles[activeTool] ?? {},
        subject: undefined,
        label: undefined,""")
rep("""    return { mode: 'none' as const, type: 'select', title: 'Properties', value: {}, label: undefined, totals: undefined, defaults };""",
    """    return { mode: 'none' as const, type: 'select', title: 'Properties', value: {}, subject: undefined, label: undefined, totals: undefined, defaults };""")
# title tab: type + subject
rep("""        title: propsSelected.length > 1 ? `${propsSelected.length} markups` : (TYPE_LABELS[first.type] ?? first.type),""",
    """        title: propsSelected.length > 1 ? `${TYPE_LABELS[first.type] ?? first.type} · ${propsSelected.length} markups` : (TYPE_LABELS[first.type] ?? first.type),""")
a = s.index("  const setPropsLabel = useCallback(")
b = s.index("  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts).")
s = s[:a] + """  const setPropsSubject = useCallback(
    (v: string) => {
      const text = v.trim();
      setMeasurements((prev) =>
        prev.map((m) =>
          propsSelectedIds.has(m.id) && !m.locked && !m.flattened
            ? { ...m, customFields: { ...(m.customFields ?? {}), Subject: text } }
            : m,
        ),
      );
    },
    [propsSelectedIds],
  );
  const setPropsLabel = useCallback(
    (v: string) => {
      const text = v.trim();
      const ids = [...propsSelectedIds];
      // An Auto Takeoff label is its profile: rename it the same way the
      // list does, so re-runs keep it.
      const autoIds = propsSelected.filter((m) => m.auto && !m.locked && !m.flattened).map((m) => m.id);
      if (autoIds.length && text) setAutoProfile(autoIds, text);
      setMeasurements((prev) =>
        prev.map((m) => (ids.includes(m.id) && !m.auto && !m.locked && !m.flattened ? { ...m, annotation: text } : m)),
      );
    },
    [propsSelectedIds, propsSelected, setAutoProfile],
  );
  const setPropsWallHeight = useCallback(
    (h: number | undefined) => {
      setMeasurements((prev) =>
        prev.map((m) =>
          propsSelectedIds.has(m.id) && !m.locked && !m.flattened && (m.type === 'distance' || m.type === 'polyline')
            ? { ...m, wallHeight: h }
            : m,
        ),
      );
    },
    [propsSelectedIds],
  );
  /** Every tool for the right-hand vertical strip, Revu order. */
  const stripTools = useMemo<StripTool[]>(() => {
    const T = (tool: string, label: string, icon: StripTool['icon'], kind: StripTool['kind']): StripTool => ({ tool, label, icon, kind, shortcut: SHORTCUT_LETTER[tool] });
    return [
      T('select', 'Select', MousePointer2, 'select'),
      T('distance', 'Length', Minus, 'measure'),
      T('polyline', 'Polylength', Route, 'measure'),
      T('area', 'Area', Pentagon, 'measure'),
      T('rectarea', 'Rectangle Area', RectangleHorizontal, 'measure'),
      T('perimeter', 'Perimeter', Hexagon, 'measure'),
      T('volume', 'Volume', Box, 'measure'),
      T('count', 'Count', Hash, 'measure'),
      T('diameter', 'Diameter', Circle, 'measure'),
      T('radiusCenter', 'Radius', DraftingCompass, 'measure'),
      T('radius3Point', 'Radius (3-Point)', Waypoints, 'measure'),
      T('angle', 'Angle', Triangle, 'measure'),
      T('arc', 'Arc', Spline, 'measure'),
      T('polygonCutout', 'Polygon Cutout', Scissors, 'measure'),
      T('ellipseCutout', 'Ellipse Cutout', CircleDashed, 'measure'),
      T('dynamicFill', 'Dynamic Fill', PaintBucket, 'measure'),
      T('line', 'Line', Slash, 'markup'),
      T('arrow', 'Arrow', ArrowUpRight, 'markup'),
      T('text', 'Text Box', Type, 'markup'),
      T('callout', 'Callout', MessageSquareText, 'markup'),
      T('cloud', 'Cloud', Cloud, 'markup'),
      T('rectangle', 'Rectangle', Square, 'markup'),
      T('ellipse', 'Ellipse', Egg, 'markup'),
      T('polygon', 'Polygon', Octagon, 'markup'),
      T('pen', 'Pen', PenLine, 'markup'),
      T('highlight', 'Highlight', Highlighter, 'markup'),
      T('stamp', 'Stamp', Stamp, 'markup'),
    ];
  }, []);

""" + s[b:]

P.write_text(s, encoding='utf-8')
print('ok')
