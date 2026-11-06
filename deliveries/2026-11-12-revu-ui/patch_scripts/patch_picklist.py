"""Every colour choice in PDF Measurements uses the Revu colour picklist
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")


def patch(rel, pairs):
    p = base / rel
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        n = s.count(a)
        assert n == 1, (rel, n, a[:80])
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


patch("TakeoffViewerModule.tsx", [
    ("import TextFormatBar from './components/TextFormatBar';",
     "import TextFormatBar from './components/TextFormatBar';\nimport ColorPicklist from './components/ColorPicklist'; // OE-DELIVERY 2026-11-12-revu-ui"),
    ('''                    <input
                      type="color"
                      value={annotationColor}
                      onChange={(e) => setAnnotationColor(e.target.value)}
                      className="h-8 w-10 cursor-pointer rounded border border-border bg-transparent p-0.5"
                      aria-label={t('takeoff_viewer.markup_colour', { defaultValue: 'Markup colour' })}
                    />''',
     '''                    <ColorPicklist value={annotationColor} onChange={(c) => c && setAnnotationColor(c)} title={t('takeoff_viewer.markup_colour', { defaultValue: 'Markup colour' })} testId="markup-colour" size={26} />'''),
    ('''                    <input
                      type="color"
                      value={labelTextColor}
                      onChange={(e) => setLabelTextColor(e.target.value)}
                      className="h-8 w-10 cursor-pointer rounded border border-border bg-transparent p-0.5"
                      aria-label={t('takeoff_viewer.label_text_colour', { defaultValue: 'Label text colour' })}
                    />''',
     '''                    <ColorPicklist value={labelTextColor} onChange={(c) => c && setLabelTextColor(c)} title={t('takeoff_viewer.label_text_colour', { defaultValue: 'Label text colour' })} testId="label-text-colour" size={26} />'''),
    ('''                    <input
                      type="color"
                      value={labelBgColor}
                      onChange={(e) => setLabelBgColor(e.target.value)}
                      className="h-8 w-10 cursor-pointer rounded border border-border bg-transparent p-0.5"
                      aria-label={t('takeoff_viewer.label_bg_colour', { defaultValue: 'Label background colour' })}
                    />''',
     '''                    <ColorPicklist value={labelBgColor} onChange={(c) => c && setLabelBgColor(c)} title={t('takeoff_viewer.label_bg_colour', { defaultValue: 'Label background colour' })} testId="label-bg-colour" size={26} />'''),
    ('''                        <input
                          type="color"
                          value={row.color}
                          onChange={(e) => row.setColor(e.target.value)}
                          className="h-6 w-7 shrink-0 cursor-pointer rounded border border-border bg-transparent p-0.5"
                          aria-label={`${row.label} text colour`}
                          title={`${row.label} text colour — applies to all markups`}
                        />''',
     '''                        <ColorPicklist value={row.color} onChange={(c) => c && row.setColor(c)} title={`${row.label} text colour — applies to all markups`} testId={`label-row-colour-${row.label}`} size={22} />'''),
    ('''                              <input
                                type="color"
                                value={legendTextColor}
                                onChange={(e) => setLegendTextColor(e.target.value)}
                                className="h-6 w-8 cursor-pointer rounded border border-border"
                                title={t('takeoff_viewer.legend_text_color', { defaultValue: 'Text color' })}
                              />''',
     '''                              <ColorPicklist value={legendTextColor} onChange={(c) => c && setLegendTextColor(c)} title={t('takeoff_viewer.legend_text_color', { defaultValue: 'Text color' })} testId="legend-text-colour" size={22} />'''),
    ('''                              <input
                                type="color"
                                value={legendBgColor}
                                onChange={(e) => setLegendBgColor(e.target.value)}
                                className="h-6 w-8 cursor-pointer rounded border border-border"
                                title={t('takeoff_viewer.legend_bg_color', { defaultValue: 'Background color' })}
                              />''',
     '''                              <ColorPicklist value={legendBgColor} onChange={(c) => c && setLegendBgColor(c)} title={t('takeoff_viewer.legend_bg_color', { defaultValue: 'Background color' })} testId="legend-bg-colour" size={22} />'''),
    ('''                    <input
                      type="color"
                      value={resolveMeasurementColor(selectedMeasurement, groupColorMap)}
                      onChange={(e) => updateSelectedMeasurement({ color: e.target.value })}
                      className="h-5 w-6 cursor-pointer rounded border border-border bg-transparent p-0"
                      title={t('takeoff_viewer.prop_color_custom', { defaultValue: 'Custom color' })}
                      aria-label={t('takeoff_viewer.prop_color_custom', { defaultValue: 'Custom color' })}
                      data-testid="prop-color-custom"
                    />''',
     '''                    <ColorPicklist value={resolveMeasurementColor(selectedMeasurement, groupColorMap)} onChange={(c) => c && updateSelectedMeasurement({ color: c })} title={t('takeoff_viewer.prop_color_custom', { defaultValue: 'Custom color' })} testId="prop-color-custom" size={20} />'''),
])

patch("components/RevuToolChest.tsx", [
    ("import clsx from 'clsx';", "import clsx from 'clsx';\nimport ColorPicklist from './ColorPicklist';"),
    ('<input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-6 w-7 rounded border border-border p-0" />',
     '<ColorPicklist value={color} onChange={(c) => c && setColor(c)} title="Colour" testId="chest-tool-colour" size={22} />'),
])

patch("RevuStyleFields.tsx", [
    ('''        <input
          type="color"
          value={value[key] ?? '#3b82f6'}
          onChange={(e) => onChange({ [key]: e.target.value })}
          className="h-5 w-7 cursor-pointer rounded border border-border bg-transparent p-0"
          data-testid={`${testIdPrefix}-${key}`}
        />''',
     '''        <ColorPicklist value={value[key] ?? '#3b82f6'} onChange={(c) => c && onChange({ [key]: c })} title="Colour" testId={`${testIdPrefix}-${key}`} size={20} />'''),
])

patch("components/RevuPropertiesBar.tsx", [
    ('''      <input
        type="color"
        disabled={off}
        value={value.labelNameColor ?? value.color ?? defaults.textColor}
        onChange={(e) => onPatch({ labelNameColor: e.target.value, labelMaterialColor: e.target.value, labelDimColor: e.target.value })}
        className="h-6 w-7 shrink-0 cursor-pointer rounded border border-border bg-transparent p-0 disabled:opacity-40"
        title="Text colour"
        aria-label="Text colour"
        data-testid="props-text-color"
      />''',
     '''      {off ? (
        <span className="h-6 w-7 shrink-0 rounded border border-border opacity-40" style={{ background: value.labelNameColor ?? value.color ?? defaults.textColor }} data-testid="props-text-color" />
      ) : (
        <ColorPicklist value={value.labelNameColor ?? value.color ?? defaults.textColor} onChange={(c) => c && onPatch({ labelNameColor: c, labelMaterialColor: c, labelDimColor: c })} title="Text colour" testId="props-text-color" size={22} />
      )}'''),
])
print("ok")
