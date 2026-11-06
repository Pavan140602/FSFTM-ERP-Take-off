"""Revu Properties UI: selected-markup rows, Tool Properties card, Show/Hide by type.
OE-DELIVERY: 2026-11-02-revu-properties"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-properties'
FILL_TYPES = "['area', 'volume', 'count', 'rectangle', 'highlight', 'polygon', 'ellipse', 'cloud', 'dynamicFill', 'polygonCutout', 'ellipseCutout', 'rectarea']"
LINEAR_TYPES = "['distance', 'polyline']"
pairs = [
# selected markup(s): line style, fill colour, label mode
("""                {/* Line opacity (issue #332): distance + polyline runs draw fully""",
 """                {/* Revu-style properties (""" + TAG + """): line
                    style, fill colour and label mode; bulk-apply to the
                    whole selection like every other row here. */}
                <div className="space-y-2 border-t border-border-light pt-2" data-testid="prop-revu-style">
                  {selectedLedgerIds.size > 1 && (
                    <p className="text-[10px] text-content-tertiary">
                      {t('takeoff_viewer.prop_applies_to', { defaultValue: 'Applies to {{n}} selected markups', n: selectedLedgerIds.size })}
                    </p>
                  )}
                  <RevuStyleFields
                    testIdPrefix="prop-style"
                    value={{
                      lineStyle: selectedMeasurement.lineStyle,
                      fillColor: selectedMeasurement.fillColor,
                      labelMode: selectedMeasurement.labelMode,
                    }}
                    fields={
                      (" + FILL_TYPES + " as string[]).includes(selectedMeasurement.type)
                        ? (['lineStyle', 'fillColor', 'labelMode'] as StyleField[])
                        : (['lineStyle', 'labelMode'] as StyleField[])
                    }
                    onChange={(patch) => updateSelectedMeasurement(patch as Partial<Measurement>)}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const m = selectedMeasurement;
                      setToolStyles((prev) =>
                        patchToolStyle(prev, m.type, {
                          color: m.color,
                          fillColor: m.fillColor,
                          strokeWidth: m.strokeWidth,
                          lineStyle: m.lineStyle,
                          fillAlpha: m.fillAlpha,
                          strokeAlpha: m.strokeAlpha,
                          labelMode: m.labelMode,
                        }),
                      );
                      addToast({
                        type: 'success',
                        title: t('takeoff_viewer.style_saved_title', { defaultValue: 'Set as tool default' }),
                        message: t('takeoff_viewer.style_saved_msg', { defaultValue: 'New {{tool}} markups will use this style.', tool: TYPE_LABELS[m.type] ?? m.type }),
                      });
                    }}
                    className="w-full rounded border border-border px-2 py-1 text-[11px] text-content-secondary hover:bg-surface-secondary hover:text-content-primary"
                    data-testid="prop-set-tool-default"
                  >
                    {t('takeoff_viewer.set_tool_default', { defaultValue: 'Set as tool default' })}
                  </button>
                </div>
                {/* Line opacity (issue #332): distance + polyline runs draw fully"""),

# armed tool, nothing selected: Tool Properties card
("""            {sidebarTab === 'properties' && selectedMeasurement && (""",
 """            {/* Revu Tool Properties (""" + TAG + """): the
                style the NEXT markup of the armed tool is drawn with. */}
            {sidebarTab === 'properties' && !selectedMeasurement && activeTool !== 'select' && (
              <div className="space-y-2.5 rounded-md border border-border bg-surface-primary p-3 shadow-sm" data-testid="tool-properties">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-content-tertiary">
                    {t('takeoff_viewer.tool_properties', { defaultValue: 'Tool properties' })} · {TYPE_LABELS[activeTool] ?? activeTool}
                  </p>
                  {toolStyles[activeTool] && (
                    <button
                      type="button"
                      onClick={() => {
                        setToolStyles((prev) => {
                          const next = { ...prev };
                          delete next[activeTool];
                          return next;
                        });
                        if (isAnnotationTool(activeTool)) setAnnotationColor(DEFAULT_ANNOTATION_COLORS[activeTool]);
                      }}
                      className="text-[10px] text-content-tertiary underline hover:text-content-primary"
                    >
                      {t('takeoff_viewer.reset_all', { defaultValue: 'Reset all' })}
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-content-tertiary">
                  {t('takeoff_viewer.tool_properties_hint', { defaultValue: 'Applies to the next markups you draw with this tool. Select a markup to change it instead.' })}
                </p>
                <RevuStyleFields
                  testIdPrefix="tool-style"
                  value={toolStyles[activeTool] ?? {}}
                  fields={[
                    'color',
                    ...((" + FILL_TYPES + " as string[]).includes(activeTool) ? (['fillColor'] as StyleField[]) : []),
                    'strokeWidth',
                    'lineStyle',
                    ...((" + FILL_TYPES + " as string[]).includes(activeTool) ? (['fillAlpha'] as StyleField[]) : []),
                    ...((" + LINEAR_TYPES + " as string[]).includes(activeTool) ? (['strokeAlpha'] as StyleField[]) : []),
                    'labelMode',
                  ]}
                  onChange={(patch: Partial<ToolStyle>) => {
                    setToolStyles((prev) => patchToolStyle(prev, activeTool, patch));
                    if ('color' in patch && isAnnotationTool(activeTool)) {
                      setAnnotationColor(patch.color ?? DEFAULT_ANNOTATION_COLORS[activeTool]);
                    }
                  }}
                />
              </div>
            )}
            {sidebarTab === 'properties' && selectedMeasurement && ("""),

# toolbar: show / hide by type
("""                  {/* Declutter toggles: hide the on-canvas name badges and the""",
 """                  {/* Show / hide by markup type, Revu markup-list filter
                      (""" + TAG + """). "Only" solos one type. */}
                  <div className="relative">
                    <button
                      onClick={() => setShowTypeFilter((v) => !v)}
                      className={tbBtn(hiddenTypes.size > 0)}
                      title={t('takeoff_viewer.type_filter', { defaultValue: 'Show or hide markups by type' })}
                      aria-expanded={showTypeFilter}
                      data-testid="type-filter-button"
                    >
                      {hiddenTypes.size > 0 ? <EyeOff size={15} /> : <Eye size={15} />}
                      <span className="takeoff-toolbar-label">
                        {t('takeoff_viewer.show_hide', { defaultValue: 'Show/Hide' })}
                        {hiddenTypes.size > 0 ? ` (${hiddenTypes.size})` : ''}
                      </span>
                    </button>
                    {showTypeFilter && (() => {
                      const counts = new Map<string, number>();
                      for (const m of measurements) counts.set(m.type, (counts.get(m.type) ?? 0) + 1);
                      const types = [...counts.keys()].sort((a, b) => (TYPE_LABELS[a] ?? a).localeCompare(TYPE_LABELS[b] ?? b));
                      return (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setShowTypeFilter(false)} aria-hidden="true" />
                          <div className="absolute left-0 top-full z-50 mt-1 w-64 rounded-lg border border-border bg-surface-elevated p-2 shadow-lg" data-testid="type-filter-panel">
                            <div className="mb-1 flex items-center justify-between px-1">
                              <span className="text-[11px] font-semibold uppercase tracking-wide text-content-tertiary">
                                {t('takeoff_viewer.markup_types', { defaultValue: 'Markup types' })}
                              </span>
                              <button
                                type="button"
                                onClick={() => setHiddenTypes(new Set())}
                                className="text-[11px] text-oe-blue hover:underline"
                              >
                                {t('takeoff_viewer.show_all', { defaultValue: 'Show all' })}
                              </button>
                            </div>
                            {types.length === 0 && (
                              <p className="px-1 py-2 text-xs text-content-tertiary">{t('takeoff_viewer.no_markups', { defaultValue: 'No markups yet.' })}</p>
                            )}
                            {types.map((ty) => (
                              <div key={ty} className="flex items-center gap-2 rounded px-1 py-1 text-xs hover:bg-surface-secondary">
                                <input
                                  type="checkbox"
                                  checked={!hiddenTypes.has(ty)}
                                  onChange={() =>
                                    setHiddenTypes((prev) => {
                                      const next = new Set(prev);
                                      if (next.has(ty)) next.delete(ty);
                                      else next.add(ty);
                                      return next;
                                    })
                                  }
                                  data-testid={`type-filter-${ty}`}
                                />
                                <span className="flex-1 text-content-primary">{TYPE_LABELS[ty] ?? ty}</span>
                                <span className="tabular-nums text-content-tertiary">{counts.get(ty)}</span>
                                <button
                                  type="button"
                                  onClick={() => setHiddenTypes(new Set(types.filter((x) => x !== ty)))}
                                  className="text-[10px] text-oe-blue hover:underline"
                                  title={t('takeoff_viewer.show_only', { defaultValue: 'Show only this type' })}
                                >
                                  {t('takeoff_viewer.only', { defaultValue: 'Only' })}
                                </button>
                              </div>
                            ))}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                  {/* Declutter toggles: hide the on-canvas name badges and the"""),
]
pairs = [(o, n.replace('" + FILL_TYPES + "', FILL_TYPES).replace('" + LINEAR_TYPES + "', LINEAR_TYPES)) for o, n in pairs]
bad = [(old[:90], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if bad:
    print('NOT WRITTEN, anchors:', bad)
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs))
