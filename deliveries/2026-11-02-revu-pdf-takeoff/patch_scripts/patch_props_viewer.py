# OE-DELIVERY 2026-11-02-revu-properties-bar: viewer half
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')
NL = chr(10)


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d, want %d):%s%s' % (c, count, NL, old[:300]))
        sys.exit(1)
    s = s.replace(old, new)


# 1. imports
rep("import { RevuMenuBar } from './components/RevuMenuBar';" + NL,
    "import { RevuMenuBar } from './components/RevuMenuBar';" + NL +
    "// Revu Properties toolbar + Revu shortcuts (OE-DELIVERY 2026-11-02-revu-properties-bar)." + NL +
    "import { RevuPropertiesBar, type PropsBarPatch } from './components/RevuPropertiesBar';" + NL +
    "import { REVU_SHORTCUTS, REVU_EXTRA_HELP, matchRevuShortcut, revuKeyForTool } from './data/revu-shortcuts';" + NL +
    "import { fontPrefix, selectionTotals } from '../../features/takeoff/lib/takeoff-revu-props';" + NL +
    "import { formatInUnits } from '../../features/takeoff/lib/takeoff-display-units';" + NL +
    "import {" + NL +
    "  LayoutGrid as RvThumbsIcon," + NL +
    "  Bookmark as RvBookmarkIcon," + NL +
    "  Ruler as RvMeasureIcon," + NL +
    "  Briefcase as RvChestIcon," + NL +
    "  Scaling as RvScaleIcon," + NL +
    "  Settings as RvSettingsIcon," + NL +
    "  ListChecks as RvMarkupsIcon," + NL +
    "  Search as RvSearchIcon," + NL +
    "} from 'lucide-react';" + NL)

# 2. local tooltip letters -> Revu keys
start = s.index("const SHORTCUT_LETTER: Record<string, string> = {")
end = s.index("};", start) + 2
s = s[:start] + """const SHORTCUT_LETTER: Record<string, string> = {
  // Revu default keys (OE-DELIVERY 2026-11-02-revu-shortcuts).
  select: 'V', distance: 'Shift+Alt+L', polyline: 'Shift+Alt+Q', area: 'Shift+Alt+A',
  volume: 'Shift+Alt+V', count: 'Shift+Alt+C', perimeter: 'Shift+Alt+P', diameter: 'Shift+Alt+D',
  radiusCenter: 'Shift+Alt+U', angle: 'Shift+Alt+G', dynamicFill: 'J', arc: 'Shift+C',
  rectangle: 'R', text: 'T', highlight: 'H', cloud: 'C', arrow: 'A',
  line: 'L', polygon: 'Shift+P', ellipse: 'E', pen: 'P', callout: 'Q', stamp: 'S',
};""" + s[end:]

# 3. leftTab gains Measurements + Scale
rep("""  const [leftTab, setLeftTab] = useState<'thumbs' | 'index' | 'layers' | 'side'>(() => {
    try {
      const v = localStorage.getItem('takeoff.leftTab');
      return v === 'index' || v === 'layers' || v === 'side' ? v : 'thumbs';""",
    """  const [leftTab, setLeftTab] = useState<'thumbs' | 'index' | 'layers' | 'side' | 'measure' | 'scale'>(() => {
    try {
      const v = localStorage.getItem('takeoff.leftTab');
      return v === 'index' || v === 'layers' || v === 'side' || v === 'measure' || v === 'scale' ? v : 'thumbs';""")

# 4. openRevuPanel keys
rep("""    (key: 'thumbs' | 'index' | 'layers' | 'properties' | 'tools' | 'colours' | 'ai' | 'auto') => {
      const isSide = key !== 'thumbs' && key !== 'index' && key !== 'layers';""",
    """    (key: 'thumbs' | 'index' | 'layers' | 'measure' | 'scale' | 'properties' | 'tools' | 'colours' | 'ai' | 'auto') => {
      const isSide = key !== 'thumbs' && key !== 'index' && key !== 'layers' && key !== 'measure' && key !== 'scale';""")

# 5. rail: Revu tab order + icons, Markups list toggle
rep("""            {([
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
                : showThumbnails && leftTab === key;""",
    """            {([
              // Revu tab order and icons (OE-DELIVERY 2026-11-02-revu-properties-bar).
              ['thumbs', 'Thumbnails (Alt+T)', RvThumbsIcon],
              ['index', 'Bookmarks / Page Index (Alt+B)', RvBookmarkIcon],
              ['measure', 'Measurements (Alt+U)', RvMeasureIcon],
              ['tools', 'Tool Chest (Alt+X)', RvChestIcon],
              ['scale', 'Scale & Calibration', RvScaleIcon],
              ['layers', 'Layers (Alt+Y)', Layers],
              ['sep', '', null],
              ['properties', 'Settings (Alt+P)', RvSettingsIcon],
              ['colours', 'Colours & Labels', Palette],
              ['ai', 'AI Assistant', Sparkles],
              ['auto', 'Auto Takeoff', WandSparkles],
              ['sep2', '', null],
              ['markups', 'Markups List (Alt+L)', RvMarkupsIcon],
              ['search', 'Search (Ctrl+F)', RvSearchIcon],
            ] as const).map(([key, label, Icon]) => {
              if (key === 'sep' || key === 'sep2' || !Icon) return <span key={key} className="my-0.5 h-px w-5 bg-border" aria-hidden="true" />;
              if (key === 'markups' || key === 'search') {
                const on = key === 'markups' ? showLedger : searchOpen;
                return (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={on}
                    aria-label={label}
                    title={label}
                    onClick={() => {
                      if (key === 'markups') setShowLedger((x) => !x);
                      else setSearchOpen((v) => { if (!v) requestAnimationFrame(() => searchInputRef.current?.focus()); return !v; });
                    }}
                    data-testid={`rail-${key}`}
                    className={clsx(
                      'flex h-8 w-8 items-center justify-center rounded transition-colors',
                      on ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
                    )}
                  >
                    <Icon size={16} />
                  </button>
                );
              }
              const isSide = key !== 'thumbs' && key !== 'index' && key !== 'layers' && key !== 'measure' && key !== 'scale';
              const active = isSide
                ? sideVisible && sidebarTab === key
                : showThumbnails && leftTab === key;""")

# 6. menu labels
rep("""                { label: 'Properties', checked: showSidebar && sidebarTab === 'properties', onClick: () => { setShowSidebar(true); setSidebarTab('properties'); } },""",
    """                { label: 'Measurements', shortcut: 'Alt+U', checked: showThumbnails && leftTab === 'measure', onClick: () => openRevuPanel('measure') },
                { label: 'Scale & Calibration', checked: showThumbnails && leftTab === 'scale', onClick: () => openRevuPanel('scale') },
                { label: 'Settings', shortcut: 'Alt+P', checked: showSidebar && sidebarTab === 'properties', onClick: () => { setShowSidebar(true); setSidebarTab('properties'); } },""")
rep("""                {
                  label: 'Keyboard Shortcuts',
                  onClick: () =>
                    addToast({
                      type: 'info',
                      title: 'Keyboard shortcuts',
                      message:
                        'V select · Z zoom tool · Ctrl+0 fit · Ctrl +/- zoom · arrows move · Shift ×10 · Alt+arrows or [ ] lengthen/shorten · Del delete · Ctrl+Z/Y undo/redo · Ctrl+D duplicate',
                    }),
                },""",
    """                { label: 'Keyboard Shortcuts (Revu)', onClick: () => setShowShortcutSheet(true), testId: 'revu-help-shortcuts' },""")
rep("""                ['Polygon Cutout', 'polygonCutout'], ['Ellipse Cutout', 'ellipseCutout'], ['Dynamic Fill', 'dynamicFill'],
              ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, checked: activeTool === tool, onClick: () => selectTool(tool) })),""",
    """                ['Polygon Cutout', 'polygonCutout'], ['Ellipse Cutout', 'ellipseCutout'], ['Dynamic Fill', 'dynamicFill'],
              ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, shortcut: revuKeyForTool(tool), checked: activeTool === tool, onClick: () => selectTool(tool) })),""")
rep("""                  ['Highlight', 'highlight'], ['Stamp', 'stamp'],
                ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, checked: activeTool === tool, onClick: () => selectTool(tool) })),""",
    """                  ['Highlight', 'highlight'], ['Stamp', 'stamp'],
                ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, shortcut: revuKeyForTool(tool), checked: activeTool === tool, onClick: () => selectTool(tool) })),""")
rep("""                {t('takeoff_viewer.tab_properties', { defaultValue: 'Properties' })}""",
    """                {t('takeoff_viewer.tab_settings', { defaultValue: 'Settings' })}""")

# 7. cut the scale controls and measure tools out of the top toolbar
a = s.index("              {/* Scale + calibration controls, grouped in one segmented track. */}")
b = s.index("              {/* Measure tools - one segmented track, icon-only with tooltips")
c = s.index("              {/* Markup tools - second segmented track; orange accent marks")
scale_chunk = s[a:b]
s = s[:a] + s[c:]
# viewport list drops inline inside the narrow panel instead of floating
old_vp = 'className="absolute left-0 top-full z-40 mt-1 w-72 rounded-lg border border-border bg-surface-elevated p-2 shadow-lg" data-testid="viewport-panel"'
assert scale_chunk.count(old_vp) == 1, 'viewport panel class'
scale_chunk = scale_chunk.replace(old_vp, 'className="mt-1 w-full rounded-lg border border-border bg-surface-elevated p-2 shadow-sm" data-testid="viewport-panel"')
scale_chunk = scale_chunk.replace('<div className="relative inline-flex items-center gap-0.5">', '<div className="relative flex w-full flex-wrap items-center gap-0.5">', 1)

MEASURE_PANEL = """              {/* Revu Measurements tab (OE-DELIVERY 2026-11-02-revu-properties-bar): the
                  measure tools, moved from the top toolbar, with their Revu keys
                  and the totals of this page. */}
              {leftTab === 'measure' && (
                <div className="min-h-0 flex-1 overflow-y-auto p-2" data-testid="revu-measure-panel" data-guide="takeoff-tools">
                  <p className="mb-1 px-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">Measurements</p>
                  <div className="flex flex-col gap-0.5" role="group" aria-label={t('takeoff_viewer.measure_tools', { defaultValue: 'Measure tools' })}>
                    {([
                      { tool: 'select' as MeasureTool, icon: MousePointer2, label: t('takeoff_viewer.tool_select', { defaultValue: 'Select' }) },
                      { tool: 'distance' as MeasureTool, icon: Minus, label: t('takeoff_viewer.tool_length', { defaultValue: 'Length' }) },
                      { tool: 'polyline' as MeasureTool, icon: Route, label: t('takeoff_viewer.tool_polylength', { defaultValue: 'Polylength' }) },
                      { tool: 'area' as MeasureTool, icon: Pentagon, label: t('takeoff_viewer.tool_area', { defaultValue: 'Area' }) },
                      { tool: 'rectarea' as MeasureTool, icon: RectangleHorizontal, label: t('takeoff_viewer.tool_rectarea', { defaultValue: 'Rectangle Area' }) },
                      { tool: 'perimeter' as MeasureTool, icon: Hexagon, label: t('takeoff_viewer.tool_perimeter', { defaultValue: 'Perimeter' }) },
                      { tool: 'volume' as MeasureTool, icon: Box, label: t('takeoff_viewer.tool_volume', { defaultValue: 'Volume' }) },
                      { tool: 'count' as MeasureTool, icon: Hash, label: t('takeoff_viewer.tool_count', { defaultValue: 'Count' }) },
                      { tool: 'diameter' as MeasureTool, icon: Circle, label: t('takeoff_viewer.tool_diameter', { defaultValue: 'Diameter' }) },
                      { tool: 'radiusCenter' as MeasureTool, icon: DraftingCompass, label: t('takeoff_viewer.tool_radius_center', { defaultValue: 'Radius' }) },
                      { tool: 'radius3Point' as MeasureTool, icon: Waypoints, label: t('takeoff_viewer.tool_radius_3point', { defaultValue: 'Radius (3-Point)' }) },
                      { tool: 'angle' as MeasureTool, icon: Triangle, label: t('takeoff_viewer.tool_angle', { defaultValue: 'Angle' }) },
                      { tool: 'arc' as MeasureTool, icon: Spline, label: t('takeoff_viewer.tool_arc', { defaultValue: 'Arc' }) },
                      { tool: 'polygonCutout' as MeasureTool, icon: Scissors, label: t('takeoff_viewer.tool_polygon_cutout', { defaultValue: 'Polygon Cutout' }) },
                      { tool: 'ellipseCutout' as MeasureTool, icon: CircleDashed, label: t('takeoff_viewer.tool_ellipse_cutout', { defaultValue: 'Ellipse Cutout' }) },
                      { tool: 'dynamicFill' as MeasureTool, icon: PaintBucket, label: t('takeoff_viewer.tool_dynamic_fill', { defaultValue: 'Dynamic Fill' }) },
                    ] as const).map(({ tool, icon: Icon, label }) => (
                      <button
                        key={tool}
                        type="button"
                        ref={tool === 'area' ? areaToolBtnRef : undefined}
                        onClick={() => {
                          if (tool === 'area' && activeTool === 'area') {
                            setAreaPopupDismissed((d) => !d);
                            return;
                          }
                          setAreaPopupDismissed(false);
                          selectTool(tool);
                        }}
                        className={clsx(
                          'flex w-full items-center gap-2 rounded px-2 py-1 text-left text-[12px] transition-colors',
                          activeTool === tool ? 'bg-oe-blue text-white' : 'text-content-primary hover:bg-surface-secondary',
                        )}
                        title={labelWithShortcut(label, tool)}
                        aria-label={labelWithShortcut(label, tool)}
                        aria-pressed={activeTool === tool}
                        data-tool={tool}
                        data-shortcut={SHORTCUT_LETTER[tool]}
                      >
                        <Icon size={15} className="shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{label}</span>
                        {SHORTCUT_LETTER[tool] && (
                          <span className={clsx('shrink-0 font-mono text-[9px]', activeTool === tool ? 'text-white/80' : 'text-content-tertiary')}>{SHORTCUT_LETTER[tool]}</span>
                        )}
                      </button>
                    ))}
                  </div>
                  {(() => {
                    const onPage = measurements.filter((m) => m.page === currentPage && !ANNOTATION_TYPES.has(m.type as never));
                    if (onPage.length === 0) return null;
                    const tot = selectionTotals(onPage);
                    const first = onPage[0]!;
                    const sc = scaleForMeasurement(pageScales, first.page, first.points);
                    const rows: [string, string][] = [];
                    if (tot.length) rows.push(['Length', formatInUnits(tot.length, 'm', sc, measurementSystem)]);
                    if (tot.area) rows.push(['Area', formatInUnits(tot.area, 'm²', sc, measurementSystem)]);
                    if (tot.volume) rows.push(['Volume', formatInUnits(tot.volume, 'm³', sc, measurementSystem)]);
                    if (tot.count) rows.push(['Count', String(tot.count)]);
                    return (
                      <div className="mt-3 border-t border-border pt-2" data-testid="revu-measure-totals">
                        <p className="mb-1 px-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">This page · {onPage.length}</p>
                        {rows.map(([k, v]) => (
                          <div key={k} className="flex justify-between px-1 text-[11px]"><span className="text-content-secondary">{k}</span><span className="font-semibold tabular-nums">{v}</span></div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              )}
              {/* Revu Scale tab: scale, calibration and viewports, moved from the top toolbar. */}
              {leftTab === 'scale' && (
                <div className="min-h-0 flex-1 overflow-y-auto p-2" data-testid="revu-scale-panel">
                  <p className="mb-2 px-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">Scale &amp; Calibration</p>
                  <div className="flex flex-col items-start gap-2">
""" + scale_chunk + """                  </div>
                  <p className="mt-3 px-1 text-[11px] leading-snug text-content-tertiary">Pick a preset scale in the status bar, or Calibrate by clicking two points of a known length. Viewports give one region of the sheet its own scale.</p>
                </div>
              )}
"""
rep("              {leftTab === 'index' && (", MEASURE_PANEL + "              {leftTab === 'index' && (")

# 8. Properties toolbar row under the top toolbar
rep("""            {/* Scale auto-detect suggestion - kept on its own slim strip""",
    """            {/* Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar). */}
            <div className="mb-1.5">
              <RevuPropertiesBar
                mode={propsBar.mode}
                type={propsBar.type}
                title={propsBar.title}
                value={propsBar.value}
                label={propsBar.label}
                onLabel={setPropsLabel}
                onPatch={applyPropsPatch}
                totals={propsBar.totals}
                defaults={propsBar.defaults}
              />
            </div>

            {/* Scale auto-detect suggestion - kept on its own slim strip""")

# 9. caption rendering: pick list, font, style, underline
rep("""      const parts = labelParts(m.labelMode);
      const showName = labelShowName && parts.name && name.length > 0;""",
    """      const parts = labelParts(m.labelMode);
      // Caption pick list (Revu Properties toolbar): 'label' shows the name line.
      const showName = labelShowName && (m.captions ? m.captions.includes('label') : parts.name) && name.length > 0;""")
rep("""      const fontFamily = revu ? labelFontCss : 'sans-serif';
      const weight = revu ? labelFontStyle : 'bold ';""",
    """      const fontFamily = m.labelFont ? `"${m.labelFont}", Arial, Helvetica, sans-serif` : revu ? labelFontCss : 'sans-serif';
      const weight = revu ? fontPrefix(m, labelBold, labelItalic) : fontPrefix(m, true, false);
      const matStyle = m.labelItalic ? 'italic ' : '';
      const underline = (text: string, x: number, y: number, fs: number) => {
        if (!m.labelUnderline) return;
        const w = ctx.measureText(text).width;
        ctx.fillRect(Math.round(x - w / 2), Math.round(y + fs * 0.12), Math.round(w), Math.max(1, Math.round(fs * 0.07)));
      };""")
rep("""      ctx.font = `${fsMat}px ${fontFamily}`;
      const matW = showMaterial ? ctx.measureText(material).width : 0;""",
    """      ctx.font = `${matStyle}${fsMat}px ${fontFamily}`;
      const matW = showMaterial ? ctx.measureText(material).width : 0;""")
rep("""        ctx.fillText(name, tx, Math.round(ty));
        ty += lineHName - fsName + gap;""",
    """        ctx.fillText(name, tx, Math.round(ty));
        underline(name, tx, ty, fsName);
        ty += lineHName - fsName + gap;""")
rep("""        ctx.font = `${fsMat}px ${fontFamily}`;
        ctx.fillStyle = colMat;
        ty += fsMat;
        ctx.fillText(material, tx, Math.round(ty));""",
    """        ctx.font = `${matStyle}${fsMat}px ${fontFamily}`;
        ctx.fillStyle = colMat;
        ty += fsMat;
        ctx.fillText(material, tx, Math.round(ty));
        underline(material, tx, ty, fsMat);""")
rep("""        ty += fsDim;
        ctx.fillText(value, tx, Math.round(ty));
      }""",
    """        ty += fsDim;
        ctx.fillText(value, tx, Math.round(ty));
        underline(value, tx, ty, fsDim);
      }""")

# 10. properties bar state + Revu key dispatcher (after applyTool)
rep("""  /** Keyboard shortcuts: per-tool letters, Ctrl+Z/Y redo/undo, Esc cancel,""",
    """  /* ── Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar) ──
   * Edits every selected markup at once; with nothing selected it edits the
   * armed tool's defaults for the next markup, as in Revu. */
  const propsSelectedIds = useMemo(() => {
    const ids = new Set<string>(selectedLedgerIds);
    if (ids.size === 0 && selectedMeasurementId) ids.add(selectedMeasurementId);
    return ids;
  }, [selectedLedgerIds, selectedMeasurementId]);
  const propsSelected = useMemo(
    () => measurements.filter((m) => propsSelectedIds.has(m.id)),
    [measurements, propsSelectedIds],
  );
  const propsBar = useMemo(() => {
    const first = propsSelected[0];
    const defaults = {
      color: first ? resolveMeasurementColor(first, groupColorMap) : toolStyles[activeTool]?.color ?? annotationColor ?? '#3B82F6',
      font: labelFont,
      size: labelTextSize,
      textColor: first ? resolveMeasurementColor(first, groupColorMap) : '#1F2937',
      bold: labelBold,
      italic: labelItalic,
    };
    if (first) {
      const tot = selectionTotals(propsSelected);
      const sc = scaleForMeasurement(pageScales, first.page, first.points);
      const parts: string[] = [`${tot.n} markup${tot.n === 1 ? '' : 's'}`];
      if (tot.length) parts.push(formatInUnits(tot.length, 'm', sc, measurementSystem, first.dispUnit));
      if (tot.area) parts.push(formatInUnits(tot.area, 'm²', sc, measurementSystem, first.dispUnit, first.dispAreaUnit));
      if (tot.volume) parts.push(formatInUnits(tot.volume, 'm³', sc, measurementSystem, first.dispUnit));
      if (tot.count) parts.push(`${tot.count} ea`);
      return {
        mode: 'selection' as const,
        type: first.type as string,
        title: propsSelected.length > 1 ? `${propsSelected.length} markups` : (TYPE_LABELS[first.type] ?? first.type),
        value: first,
        label: first.auto ? (first.annotation?.trim() || first.auto.des) : (first.customFields?.Subject ?? first.annotation ?? ''),
        totals: parts.join(' · '),
        defaults,
      };
    }
    if (activeTool !== 'select') {
      return {
        mode: 'tool' as const,
        type: activeTool as string,
        title: `${TYPE_LABELS[activeTool] ?? activeTool} tool`,
        value: toolStyles[activeTool] ?? {},
        label: undefined,
        totals: undefined,
        defaults,
      };
    }
    return { mode: 'none' as const, type: 'select', title: 'Properties', value: {}, label: undefined, totals: undefined, defaults };
  }, [propsSelected, activeTool, toolStyles, groupColorMap, annotationColor, labelFont, labelTextSize, labelBold, labelItalic, pageScales, measurementSystem]);
  const applyPropsPatch = useCallback(
    (patch: PropsBarPatch) => {
      if (propsSelectedIds.size > 0) {
        setMeasurements((prev) =>
          prev.map((m) => (propsSelectedIds.has(m.id) && !m.locked && !m.flattened ? { ...m, ...(patch as Partial<Measurement>) } : m)),
        );
        return;
      }
      if (activeTool === 'select') return;
      setToolStyles((prev) => patchToolStyle(prev, activeTool, patch as Partial<ToolStyle>));
      if ('color' in patch && isAnnotationTool(activeTool)) {
        setAnnotationColor(patch.color ?? DEFAULT_ANNOTATION_COLORS[activeTool]);
      }
    },
    [propsSelectedIds, activeTool],
  );
  const setPropsLabel = useCallback(
    (v: string) => {
      const text = v.trim();
      setMeasurements((prev) =>
        prev.map((m) => {
          if (!propsSelectedIds.has(m.id) || m.locked || m.flattened) return m;
          if (m.auto) return { ...m, annotation: text };
          return { ...m, annotation: text, customFields: { ...(m.customFields ?? {}), Subject: text } };
        }),
      );
    },
    [propsSelectedIds],
  );

  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts).
   *  Refreshed every render so the key handler always sees current state. */
  const [showShortcutSheet, setShowShortcutSheet] = useState(false);
  const revuKeyRef = useRef<(e: KeyboardEvent) => boolean>(() => false);
  revuKeyRef.current = (e: KeyboardEvent): boolean => {
    if (!shouldHandleShortcut(e.target)) return false;
    const sc = matchRevuShortcut(e);
    if (!sc) return false;
    if (sc.action.kind === 'tool') {
      e.preventDefault();
      setAreaPopupDismissed(false);
      selectTool(sc.action.tool as MeasureTool);
      return true;
    }
    const ids = [...propsSelectedIds];
    const cp = currentPageRef.current || 1;
    switch (sc.action.cmd) {
      case 'fullScreen':
      case 'selectAll':
        return false; // handled by the existing listeners
      case 'pan': setPanLock((x) => !x); break;
      case 'zoomTool': setZoomAreaArmed((v) => !v); break;
      case 'zoomIn': zoomIn(); break;
      case 'zoomOut': zoomOut(); break;
      case 'fitPage': fitToViewport('page'); break;
      case 'fitWidth': fitToViewport('width'); break;
      case 'actualSize': zoomTo(1); break;
      case 'nextPage': goToPage(cp + 1); break;
      case 'prevPage': goToPage(cp - 1); break;
      case 'firstPage': goToPage(1); break;
      case 'lastPage': goToPage(totalPagesRef.current || 1); break;
      case 'splitVertical': if (splitMode !== 'vertical') toggleSplit('vertical'); break;
      case 'splitHorizontal': if (splitMode !== 'horizontal') toggleSplit('horizontal'); break;
      case 'toggleSplit': if (splitMode === 'off') toggleSplit('vertical'); else { setSplitMode('off'); setSyncViews(false); } break;
      case 'unsplit': setSplitMode('off'); setSyncViews(false); break;
      case 'singlePage': setPageMode('single'); break;
      case 'continuous': setPageMode('continuous'); break;
      case 'panelThumbnails': openRevuPanel('thumbs'); break;
      case 'panelBookmarks': openRevuPanel('index'); break;
      case 'panelMarkups': setShowLedger((x) => !x); break;
      case 'panelProperties': openRevuPanel('properties'); break;
      case 'panelToolChest': openRevuPanel('tools'); break;
      case 'panelMeasurements': openRevuPanel('measure'); break;
      case 'panelLayers': openRevuPanel('layers'); break;
      case 'panelSearch':
      case 'find':
        setSearchOpen(true);
        requestAnimationFrame(() => searchInputRef.current?.focus());
        break;
      case 'lock': {
        if (ids.length === 0) return false;
        const allLocked = propsSelected.every((m) => m.locked);
        setMeasurements((prev) => prev.map((m) => (propsSelectedIds.has(m.id) ? { ...m, locked: !allLocked } : m)));
        addToast({ type: 'info', title: allLocked ? 'Unlocked' : 'Locked' });
        break;
      }
      case 'flatten':
        if (ids.length === 0) return false;
        setMeasurements((prev) => prev.map((m) => (propsSelectedIds.has(m.id) ? { ...m, flattened: true } : m)));
        break;
      case 'bringToFront': ids.forEach((id) => reorderMeasurement(id, 'front')); break;
      case 'sendToBack': ids.forEach((id) => reorderMeasurement(id, 'back')); break;
      case 'group': if (ids[0]) groupSelection(ids[0]); break;
      case 'ungroup': if (ids[0]) ungroupSelection(ids[0]); break;
      case 'snapContent':
        setContentSnap((v) => { const next = !v; try { localStorage.setItem('oe-content-snap', next ? '1' : '0'); } catch { /* ignore */ } return next; });
        setSnapPoint(null);
        break;
      default:
        return false;
    }
    e.preventDefault();
    return true;
  };

  /** Keyboard shortcuts: per-tool letters, Ctrl+Z/Y redo/undo, Esc cancel,""")

# 11. dispatcher call in the key handler, before the Ctrl zoom keys
rep("""      // Revu / Acrobat zoom keys (OE-DELIVERY 2026-11-02-revu-zoom): Ctrl+= in,""",
    """      // Revu default shortcuts first (OE-DELIVERY 2026-11-02-revu-shortcuts).
      if (revuKeyRef.current(e)) return;

      // Revu / Acrobat zoom keys (OE-DELIVERY 2026-11-02-revu-zoom): Ctrl+= in,""")

# 12. shortcut sheet modal next to the menu bar
rep("""      {/* Viewer + Sidebar (PDF on the left, Measurements panel on the right).""",
    """      {showShortcutSheet && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-4" onClick={() => setShowShortcutSheet(false)} data-testid="revu-shortcut-sheet">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-border bg-surface-elevated p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold text-content-primary">Keyboard Shortcuts (Bluebeam Revu defaults)</h2>
              <button type="button" onClick={() => setShowShortcutSheet(false)} className="text-content-tertiary hover:text-content-primary" aria-label="Close"><X size={14} /></button>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {(['Markup', 'Measure', 'View', 'Panels', 'Edit'] as const).map((sec) => (
                <div key={sec}>
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">{sec}</p>
                  {REVU_SHORTCUTS.filter((x) => x.section === sec).map((x) => (
                    <div key={x.keys} className="flex justify-between gap-2 py-0.5 text-[11px]">
                      <span className="text-content-primary">{x.label}</span>
                      <kbd className="rounded border border-border bg-surface-secondary px-1 font-mono text-[10px]">{x.keys}</kbd>
                    </div>
                  ))}
                </div>
              ))}
              <div>
                <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">Also</p>
                {REVU_EXTRA_HELP.map((x) => (
                  <div key={x.keys} className="flex justify-between gap-2 py-0.5 text-[11px]">
                    <span className="text-content-primary">{x.label}</span>
                    <kbd className="rounded border border-border bg-surface-secondary px-1 font-mono text-[10px]">{x.keys}</kbd>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Viewer + Sidebar (PDF on the left, Measurements panel on the right).""")

P.write_text(s, encoding='utf-8')
print('ok')
