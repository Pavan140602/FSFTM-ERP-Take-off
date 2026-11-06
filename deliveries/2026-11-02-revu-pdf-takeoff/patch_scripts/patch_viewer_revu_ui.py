"""Toolbar, hints and text dialog for the Revu markup + arc tools (anchored, all-or-nothing)."""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
pairs = [
# icons
("""  Spline,
  Magnet,
""", """  Spline,
  Magnet,
  // Revu markup tools (OE-DELIVERY 2026-10-30-revu-markup-tools).
  Slash,
  Octagon,
  Egg,
  PenLine,
  MessageSquareText,
  Stamp,
"""),
# measure toolbar: Arc after Angle
("""                  { tool: 'angle' as MeasureTool, icon: Triangle, label: t('takeoff_viewer.tool_angle', { defaultValue: 'Angle' }) },
""", """                  { tool: 'angle' as MeasureTool, icon: Triangle, label: t('takeoff_viewer.tool_angle', { defaultValue: 'Angle' }) },
                  { tool: 'arc' as MeasureTool, icon: Spline, label: t('takeoff_viewer.tool_arc', { defaultValue: 'Arc length' }) },
"""),
# markup toolbar
("""                  { tool: 'highlight' as MeasureTool, icon: Highlighter, label: t('takeoff_viewer.tool_highlight', { defaultValue: 'Highlight' }) },
                ] as const).map(({ tool, icon: Icon, label }) => (""", """                  { tool: 'highlight' as MeasureTool, icon: Highlighter, label: t('takeoff_viewer.tool_highlight', { defaultValue: 'Highlight' }) },
                  { tool: 'line' as MeasureTool, icon: Slash, label: t('takeoff_viewer.tool_line', { defaultValue: 'Line' }) },
                  { tool: 'polygon' as MeasureTool, icon: Octagon, label: t('takeoff_viewer.tool_polygon', { defaultValue: 'Polygon' }) },
                  { tool: 'ellipse' as MeasureTool, icon: Egg, label: t('takeoff_viewer.tool_ellipse', { defaultValue: 'Ellipse' }) },
                  { tool: 'pen' as MeasureTool, icon: PenLine, label: t('takeoff_viewer.tool_pen', { defaultValue: 'Pen' }) },
                  { tool: 'callout' as MeasureTool, icon: MessageSquareText, label: t('takeoff_viewer.tool_callout', { defaultValue: 'Callout' }) },
                  { tool: 'stamp' as MeasureTool, icon: Stamp, label: t('takeoff_viewer.tool_stamp', { defaultValue: 'Stamp' }) },
                ] as const).map(({ tool, icon: Icon, label }) => ("""),
# stamp preset picker, right after the markup group, before AI assist
("""              {/* AI assist - offline Recognize (issue #194) + optional vision
                  Read-with-AI. Pushed right as the two hero actions of the row. */}""", """              {/* Stamp preset (OE-DELIVERY 2026-10-30-revu-markup-tools):
                  which Revu review stamp the next click drops. */}
              {activeTool === 'stamp' && (
                <select
                  value={stampPresetId}
                  onChange={(e) => setStampPresetId(e.target.value)}
                  className="h-7 rounded-md border border-border bg-surface-primary px-2 text-xs text-content-primary"
                  aria-label={t('takeoff_viewer.stamp_preset', { defaultValue: 'Stamp' })}
                  data-testid="stamp-preset"
                >
                  {STAMP_PRESETS.map((sp) => (
                    <option key={sp.id} value={sp.id}>{sp.text}</option>
                  ))}
                  <option value="custom">{t('takeoff_viewer.stamp_custom', { defaultValue: 'Custom text…' })}</option>
                </select>
              )}

              {/* AI assist - offline Recognize (issue #194) + optional vision
                  Read-with-AI. Pushed right as the two hero actions of the row. */}"""),
# hints
("""                    {activeTool === 'highlight' && t('takeoff_viewer.hint_highlight', { defaultValue: 'Drag to highlight a region.' })}
""", """                    {activeTool === 'highlight' && t('takeoff_viewer.hint_highlight', { defaultValue: 'Drag to highlight a region.' })}
                    {activeTool === 'line' && t('takeoff_viewer.hint_line', { defaultValue: 'Click start, then end.' })}
                    {activeTool === 'polygon' && t('takeoff_viewer.hint_polygon', { defaultValue: 'Click vertices; double-click or right-click to close.' })}
                    {activeTool === 'ellipse' && t('takeoff_viewer.hint_ellipse', { defaultValue: 'Click two opposite corners of the ellipse box.' })}
                    {activeTool === 'pen' && t('takeoff_viewer.hint_pen', { defaultValue: 'Hold and drag to draw freehand.' })}
                    {activeTool === 'callout' && t('takeoff_viewer.hint_callout', { defaultValue: 'Click the point to call out, then where the text goes.' })}
                    {activeTool === 'stamp' && t('takeoff_viewer.hint_stamp', { defaultValue: 'Pick a stamp, then click to place it.' })}
                    {activeTool === 'arc' && t('takeoff_viewer.hint_arc', { defaultValue: 'Click arc start, a point on the arc, then the end.' })}
"""),
# text dialog, before the volume depth dialog
("""      {/* Volume depth input dialog */}
      {showVolumeDepthInput && (""", """      {/* Callout / custom stamp text (OE-DELIVERY 2026-10-30-revu-markup-tools) */}
      {markupTextPrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-80 rounded-xl border border-border bg-surface-elevated p-5 shadow-lg">
            <h3 className="text-sm font-semibold text-content-primary mb-3">
              {markupTextPrompt.kind === 'callout'
                ? t('takeoff_viewer.callout_text_title', { defaultValue: 'Callout text' })
                : t('takeoff_viewer.stamp_text_title', { defaultValue: 'Stamp text' })}
            </h3>
            <textarea
              value={markupTextPrompt.value}
              onChange={(e) => {
                const value = e.target.value;
                setMarkupTextPrompt((cur) => (cur ? { ...cur, value } : cur));
              }}
              rows={markupTextPrompt.kind === 'callout' ? 3 : 1}
              className="mb-4 w-full rounded border border-border bg-surface-secondary px-2 py-1.5 text-sm text-content-primary"
              placeholder={markupTextPrompt.kind === 'callout'
                ? t('takeoff_viewer.callout_text_placeholder', { defaultValue: 'Enter = place, Shift+Enter = new line' })
                : t('takeoff_viewer.stamp_text_placeholder', { defaultValue: 'e.g. CHECKED' })}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  confirmMarkupText();
                }
                if (e.key === 'Escape') setMarkupTextPrompt(null);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setMarkupTextPrompt(null)}
                className="px-3 py-1.5 rounded-lg text-xs text-content-secondary hover:bg-surface-secondary transition-colors"
              >
                {t('common.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                onClick={confirmMarkupText}
                className="px-3 py-1.5 rounded-lg bg-oe-blue text-white text-xs font-medium hover:bg-oe-blue-hover transition-colors"
              >
                {t('takeoff_viewer.place', { defaultValue: 'Place' })}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Volume depth input dialog */}
      {showVolumeDepthInput && ("""),
]
bad = [(old[:100], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if bad:
    print('NOT WRITTEN, anchors:', bad)
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs))
