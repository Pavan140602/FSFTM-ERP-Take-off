"""Revu workspace: menu bar + full-window mode (all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-workspace"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-workspace'

MENUBAR = r'''      {/* Revu-style menu bar (TAGX): File / Edit / View / Document /
          Measure / Markup / Tools / Window / Help, each calling the same
          commands as the toolbars. */}
      {pdfDoc && (
        <RevuMenuBar
          title={
            <span className="mr-1 flex items-center gap-1 rounded bg-oe-blue px-1.5 py-0.5 text-[11px] font-bold text-white">
              <Ruler size={12} /> Takeoff
            </span>
          }
          menus={[
            {
              label: 'File',
              items: [
                { label: 'Save', shortcut: 'Ctrl+S', onClick: () => { void saveNow(); } },
                { separator: true },
                { label: 'Export PDF with markups…', onClick: () => { void handleExportPdf(); } },
                { label: 'Export to Excel', onClick: () => { void handleExportExcel(); } },
                { label: 'Export CSV', onClick: () => handleExportCSV() },
                { label: 'Send to BOQ / Estimate…', onClick: () => { void openExportDialog(); } },
                { separator: true },
                { label: revuWorkspace ? 'Exit workspace (back to ERP)' : 'Open full-window workspace', onClick: () => setRevuWorkspace((w) => !w), testId: 'revu-file-workspace' },
              ],
            },
            {
              label: 'Edit',
              items: [
                { label: 'Undo', shortcut: 'Ctrl+Z', onClick: () => handleUndo() },
                { label: 'Redo', shortcut: 'Ctrl+Y', onClick: () => handleRedo() },
                { separator: true },
                {
                  label: 'Select all on this page',
                  shortcut: 'Ctrl+A',
                  onClick: () => setSelectedLedgerIds(new Set(measurements.filter((m) => m.page === currentPage).map((m) => m.id))),
                },
                { label: 'Deselect', shortcut: 'Esc', onClick: () => { setSelectedLedgerIds(new Set()); setSelectedMeasurementId(null); } },
                {
                  label: 'Duplicate',
                  shortcut: 'Ctrl+D',
                  disabled: !selectedMeasurementId,
                  onClick: () => { if (selectedMeasurementId) duplicateMeasurement(selectedMeasurementId); },
                },
                {
                  label: 'Delete',
                  shortcut: 'Del',
                  disabled: !selectedMeasurementId && selectedLedgerIds.size === 0,
                  onClick: () => {
                    if (selectedLedgerIds.size > 0) bulkDeleteSelected();
                    else if (selectedMeasurementId) deleteMeasurement(selectedMeasurementId);
                  },
                },
              ],
            },
            {
              label: 'View',
              items: [
                { label: 'Zoom In', shortcut: 'Ctrl++', onClick: () => zoomTo(zoom * 1.25) },
                { label: 'Zoom Out', shortcut: 'Ctrl+-', onClick: () => zoomTo(zoom / 1.25) },
                { label: 'Actual Size (100%)', onClick: () => zoomTo(1) },
                { label: 'Fit Width', shortcut: 'Shift+1', onClick: () => fitToViewport('width') },
                { label: 'Fit Page', shortcut: 'Ctrl+0', onClick: () => fitToViewport('page') },
                { label: 'Zoom to Selection', shortcut: 'Shift+3', onClick: () => zoomToSelection() },
                { label: 'Zoom Tool', shortcut: 'Z', checked: zoomAreaArmed, onClick: () => setZoomAreaArmed((a) => !a) },
                { separator: true },
                { label: 'Single Page', checked: pageMode === 'single', onClick: () => setPageMode('single') },
                { label: 'Continuous', checked: pageMode === 'continuous', onClick: () => setPageMode('continuous') },
                { label: 'Split Vertical', checked: splitMode === 'vertical', onClick: () => toggleSplit('vertical') },
                { label: 'Split Horizontal', checked: splitMode === 'horizontal', onClick: () => toggleSplit('horizontal') },
                { separator: true },
                { label: 'Show Labels', checked: showLabels, onClick: () => setShowLabels((x) => !x) },
                { label: 'Show Dimensions', checked: showDimensions, onClick: () => setShowDimensions((x) => !x) },
                { separator: true },
                { label: 'Full Screen', shortcut: 'F11', checked: isTakeoffFullscreen, onClick: () => toggleTakeoffFullscreen() },
                { label: 'Full-window Workspace', checked: revuWorkspace, onClick: () => setRevuWorkspace((w) => !w), testId: 'revu-view-workspace' },
              ],
            },
            {
              label: 'Document',
              items: [
                { label: 'First Page', shortcut: 'Home', disabled: currentPage <= 1, onClick: () => goToPage(1) },
                { label: 'Previous Page', shortcut: 'PgUp', disabled: currentPage <= 1, onClick: () => goToPage(currentPage - 1) },
                { label: 'Next Page', shortcut: 'PgDn', disabled: currentPage >= totalPages, onClick: () => goToPage(currentPage + 1) },
                { label: 'Last Page', shortcut: 'End', disabled: currentPage >= totalPages, onClick: () => goToPage(totalPages) },
                { separator: true },
                {
                  label: 'Set Scale…',
                  onClick: () => { setCalibrationMode(false); setSettingScale(true); setScalePoints([]); setLiveCursor(null); setSnapPoint(null); },
                },
                { label: 'Calibrate (two clicks)…', onClick: () => handleStartCalibration() },
                { label: 'Viewports…', checked: showViewportPanel, onClick: () => setShowViewportPanel((x) => !x) },
              ],
            },
            {
              label: 'Measure',
              items: ([
                ['Length', 'distance'], ['Polylength', 'polyline'], ['Area', 'area'], ['Rectangle Area', 'rectarea'],
                ['Perimeter', 'perimeter'], ['Count', 'count'], ['Volume', 'volume'], ['Diameter', 'diameter'],
                ['Radius (centre)', 'radiusCenter'], ['Radius (3 points)', 'radius3Point'], ['Angle', 'angle'], ['Arc', 'arc'],
                ['Polygon Cutout', 'polygonCutout'], ['Ellipse Cutout', 'ellipseCutout'], ['Dynamic Fill', 'dynamicFill'],
              ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, checked: activeTool === tool, onClick: () => selectTool(tool) })),
            },
            {
              label: 'Markup',
              items: [
                { label: 'Select', shortcut: 'V', checked: activeTool === 'select', onClick: () => selectTool('select') },
                { separator: true },
                ...([
                  ['Line', 'line'], ['Arrow', 'arrow'], ['Text Box', 'text'], ['Callout', 'callout'], ['Cloud', 'cloud'],
                  ['Rectangle', 'rectangle'], ['Ellipse', 'ellipse'], ['Polygon', 'polygon'], ['Pen', 'pen'],
                  ['Highlight', 'highlight'], ['Stamp', 'stamp'],
                ] as [string, MeasureTool][]).map(([label, tool]) => ({ label, checked: activeTool === tool, onClick: () => selectTool(tool) })),
              ],
            },
            {
              label: 'Tools',
              items: [
                { label: 'Auto Takeoff…', onClick: () => { setShowSidebar(true); setSidebarTab('auto'); }, testId: 'revu-tools-auto' },
                { label: 'Recognize this page', onClick: () => { void handleRecognize(); } },
                { label: 'AI Assistant', onClick: () => { setShowSidebar(true); setSidebarTab('ai'); } },
                { label: 'Tool Chest', onClick: () => { setShowSidebar(true); setSidebarTab('tools'); } },
                { separator: true },
                { label: 'Pan Lock', checked: panLock, onClick: () => setPanLock((x) => !x) },
              ],
            },
            {
              label: 'Window',
              items: [
                { label: 'Thumbnails', checked: showThumbnails, onClick: () => setShowThumbnails((x) => !x) },
                { label: 'Right Panel', checked: showSidebar, onClick: () => setShowSidebar((x) => !x) },
                { label: 'Markups List', checked: showLedger, onClick: () => setShowLedger((x) => !x) },
                { separator: true },
                { label: 'Properties', checked: showSidebar && sidebarTab === 'properties', onClick: () => { setShowSidebar(true); setSidebarTab('properties'); } },
                { label: 'Tool Chest', checked: showSidebar && sidebarTab === 'tools', onClick: () => { setShowSidebar(true); setSidebarTab('tools'); } },
                { label: 'Colours', checked: showSidebar && sidebarTab === 'colours', onClick: () => { setShowSidebar(true); setSidebarTab('colours'); } },
                { label: 'AI Assistant', checked: showSidebar && sidebarTab === 'ai', onClick: () => { setShowSidebar(true); setSidebarTab('ai'); } },
                { label: 'Auto Takeoff', checked: showSidebar && sidebarTab === 'auto', onClick: () => { setShowSidebar(true); setSidebarTab('auto'); } },
                { separator: true },
                {
                  label: 'Reset Panel Sizes',
                  onClick: () => {
                    setLeftStripWidth(LEFT_STRIP_DEFAULT);
                    setRightPanelWidth(RIGHT_PANEL_DEFAULT);
                    setLedgerHeight(LEDGER_DEFAULT);
                    persistPanelWidth('left', LEFT_STRIP_DEFAULT);
                    persistPanelWidth('right', RIGHT_PANEL_DEFAULT);
                    try { localStorage.setItem(LEDGER_HEIGHT_KEY, String(LEDGER_DEFAULT)); } catch { /* ignore */ }
                  },
                },
              ],
            },
            {
              label: 'Help',
              items: [
                {
                  label: 'Keyboard Shortcuts',
                  onClick: () =>
                    addToast({
                      type: 'info',
                      title: 'Keyboard shortcuts',
                      message:
                        'V select · Z zoom tool · Ctrl+0 fit · Ctrl +/- zoom · arrows move · Shift ×10 · Alt+arrows or [ ] lengthen/shorten · Del delete · Ctrl+Z/Y undo/redo · Ctrl+D duplicate',
                    }),
                },
              ],
            },
          ]}
          right={
            <button
              type="button"
              onClick={() => setRevuWorkspace((w) => !w)}
              className="rounded border border-border px-2 py-0.5 text-[11px] text-content-secondary hover:bg-surface-tertiary"
              title={revuWorkspace ? 'Back to the normal ERP page' : 'Fill the browser window like Revu'}
              data-testid="revu-workspace-toggle"
            >
              {revuWorkspace ? 'Exit workspace' : 'Workspace'}
            </button>
          }
        />
      )}
'''.replace('TAGX', TAG)

pairs = [
("""import { FullscreenToastStack } from './components/FullscreenToastStack';""",
 """import { FullscreenToastStack } from './components/FullscreenToastStack';
import { RevuMenuBar } from './components/RevuMenuBar';"""),
("""  const [isTakeoffFullscreen, setIsTakeoffFullscreen] = useState(false);""",
 """  const [isTakeoffFullscreen, setIsTakeoffFullscreen] = useState(false);
  /** Revu-style full-window workspace (""" + TAG + """): the takeoff
   *  fills the browser window (ERP header, banners and tabs covered) with
   *  its own menu bar, panels and status bar - Revu's window layout. */
  const [revuWorkspace, setRevuWorkspace] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.revuWorkspace') !== '0'; } catch { return true; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.revuWorkspace', revuWorkspace ? '1' : '0'); } catch { /* ignore */ }
  }, [revuWorkspace]);"""),
("""        className={clsx(
          'flex flex-1 min-h-0 min-w-0 flex-col',
          isTakeoffFullscreen && 'bg-surface-primary p-3 overflow-auto',
        )}
      >""", """        className={clsx(
          'flex flex-1 min-h-0 min-w-0 flex-col',
          isTakeoffFullscreen && 'bg-surface-primary p-3 overflow-auto',
          revuWorkspace && !isTakeoffFullscreen && 'fixed inset-0 z-50 bg-surface-primary p-1 gap-1 overflow-hidden',
        )}
        data-revu-workspace={revuWorkspace ? '1' : '0'}
      >"""),
("""      {isTakeoffFullscreen && <FullscreenToastStack />}
""", """      {isTakeoffFullscreen && <FullscreenToastStack />}
""" + MENUBAR),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
v.write_text(s, encoding='utf-8')
print('ok', len(pairs))
