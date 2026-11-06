"""Revu-style plain-text labels (anchored, all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-labels"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-labels'
REVU_FONT = 'Arial, Helvetica, sans-serif'
pairs = [
# state
("""  const [labelBgColor, setLabelBgColor] = useState<string>(() => {""",
 """  /** Label look (""" + TAG + """): 'revu' = plain text in the
   *  markup's colour, no box, sized in drawing space so it scales with zoom
   *  like Revu captions (default); 'badge' = the previous filled pills. */
  const [labelStyle, setLabelStyle] = useState<'revu' | 'badge'>(() => {
    try { return localStorage.getItem('takeoff.labelStyle') === 'badge' ? 'badge' : 'revu'; }
    catch { return 'revu'; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.labelStyle', labelStyle); } catch { /* ignore */ }
  }, [labelStyle]);
  const [labelBgColor, setLabelBgColor] = useState<string>(() => {"""),
("""showTextInput, editingTextId, viewportDraft, hiddenTypes]);""",
 """showTextInput, editingTextId, viewportDraft, hiddenTypes, labelStyle]);"""),

# name / annotation badge
("""      if (!showLabels || curLabelMode === 'none' || curLabelMode === 'value') return;
      const fontSize = 11 * dpr;""", """      if (!showLabels || curLabelMode === 'none' || curLabelMode === 'value') return;
      if (labelStyle === 'revu') {
        // Revu caption: plain text in the markup colour, drawing-space size.
        const fsRevu = 11 * dpr * zoom;
        ctx.save();
        ctx.font = `${fsRevu}px """ + REVU_FONT + """`;
        ctx.textAlign = alignRight ? 'right' : 'left';
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = color;
        ctx.fillText(text, lx, ly);
        ctx.restore();
        return;
      }
      const fontSize = 11 * dpr;"""),

# three-line stack: sizes, no pill, markup-coloured text
("""      const fsName = (m.labelTextSize ?? labelTextSize) * dpr;
      const fsMat = (m.labelMaterialSize ?? labelMaterialSize) * dpr;
      const fsDim = (m.labelDimSize ?? labelDimSize) * dpr;
      const gap = 4 * dpr;
      const lift = 2 * dpr; // stack bottom sits tight above the line (no floating gap)
      const padX = 6 * dpr;
      const padY = 4 * dpr;""", """      // Revu captions live in drawing space, so every size scales with zoom
      // (""" + TAG + """); badges keep their fixed screen size.
      const revu = labelStyle === 'revu';
      const zs = revu ? zoom : 1;
      const fsName = (m.labelTextSize ?? labelTextSize) * dpr * zs;
      const fsMat = (m.labelMaterialSize ?? labelMaterialSize) * dpr * zs;
      const fsDim = (m.labelDimSize ?? labelDimSize) * dpr * zs;
      const gap = (revu ? 1 : 4) * dpr * zs;
      const lift = 2 * dpr * zs; // stack bottom sits tight above the line (no floating gap)
      const padX = (revu ? 0 : 6) * dpr * zs;
      const padY = (revu ? 0 : 4) * dpr * zs;
      const fontFamily = revu ? '""" + REVU_FONT + """' : 'sans-serif';
      const weight = revu ? '' : 'bold ';"""),
("""      ctx.font = `bold ${fsName}px sans-serif`;
      const nameW = showName ? ctx.measureText(name).width : 0;
      ctx.font = `${fsMat}px sans-serif`;
      const matW = showMaterial ? ctx.measureText(material).width : 0;
      ctx.font = `bold ${fsDim}px sans-serif`;
      const valueW = showValue ? ctx.measureText(value).width : 0;""",
 """      ctx.font = `${weight}${fsName}px ${fontFamily}`;
      const nameW = showName ? ctx.measureText(name).width : 0;
      ctx.font = `${fsMat}px ${fontFamily}`;
      const matW = showMaterial ? ctx.measureText(material).width : 0;
      ctx.font = `${weight}${fsDim}px ${fontFamily}`;
      const valueW = showValue ? ctx.measureText(value).width : 0;"""),
("""      // Pill background in the user's label colour.
      ctx.fillStyle = labelBgColor;
      const r = Math.min(6 * dpr, boxH / 2);
      ctx.beginPath();
      if (typeof ctx.roundRect === 'function') ctx.roundRect(bx, by, Math.round(boxW), Math.round(boxH), r);
      else ctx.rect(bx, by, Math.round(boxW), Math.round(boxH));
      ctx.fill();
      // Text lines, top to bottom: name, material, dimension — each with its
      // own size and colour (per-markup overrides win).
      const colName = m.labelNameColor ?? labelNameColor;
      const colMat = m.labelMaterialColor ?? labelMaterialColor;
      const colDim = m.labelDimColor ?? labelDimColor;""",
 """      // Pill background in the user's label colour (badge style only).
      if (!revu) {
        ctx.fillStyle = labelBgColor;
        const r = Math.min(6 * dpr, boxH / 2);
        ctx.beginPath();
        if (typeof ctx.roundRect === 'function') ctx.roundRect(bx, by, Math.round(boxW), Math.round(boxH), r);
        else ctx.rect(bx, by, Math.round(boxW), Math.round(boxH));
        ctx.fill();
      }
      // Text lines, top to bottom: name, material, dimension — each with its
      // own size and colour (per-markup overrides win). Revu captions default
      // to the markup's own colour.
      const markupColor = resolveMeasurementColor(m, groupColorMap);
      const colName = m.labelNameColor ?? (revu ? markupColor : labelNameColor);
      const colMat = m.labelMaterialColor ?? (revu ? markupColor : labelMaterialColor);
      const colDim = m.labelDimColor ?? (revu ? markupColor : labelDimColor);"""),
("""      if (showName) {
        ctx.font = `bold ${fsName}px sans-serif`;""", """      if (showName) {
        ctx.font = `${weight}${fsName}px ${fontFamily}`;"""),
("""      if (showMaterial) {
        ctx.font = `${fsMat}px sans-serif`;""", """      if (showMaterial) {
        ctx.font = `${fsMat}px ${fontFamily}`;"""),
("""      if (showValue) {
        ctx.font = `bold ${fsDim}px sans-serif`;""", """      if (showValue) {
        ctx.font = `${weight}${fsDim}px ${fontFamily}`;"""),

# area centroid value text
("""        ctx.font = `${12 * dpr}px sans-serif`;
        // Prefix a minus so the on-canvas number reads as a subtraction.""",
 """        ctx.font = labelStyle === 'revu' ? `${12 * dpr * zoom}px """ + REVU_FONT + """` : `${12 * dpr}px sans-serif`;
        // The fill pass left fillStyle on the fill colour; the text reads in
        // the markup colour (""" + TAG + """).
        ctx.fillStyle = isVoid ? '#ef4444' : color;
        // Prefix a minus so the on-canvas number reads as a subtraction."""),
("""        drawAnnotationLabel(m.annotation, cx, cy - 14 * dpr, color);
      }
""", """        drawAnnotationLabel(m.annotation, cx, cy - 14 * dpr * (labelStyle === 'revu' ? zoom : 1), color);
      }
"""),

# Colours tab control
("""                <div className="space-y-2">
                  <p className="text-[11px] font-semibold text-content-secondary">
                    {t('takeoff_viewer.label_show_lines', { defaultValue: 'Show in label' })}
                  </p>""", """                {/* Label style (""" + TAG + """) */}
                <div className="space-y-1">
                  <p className="text-[11px] font-semibold text-content-secondary">
                    {t('takeoff_viewer.label_style', { defaultValue: 'Label style' })}
                  </p>
                  <div className="grid grid-cols-2 gap-1">
                    {(['revu', 'badge'] as const).map((ls) => (
                      <button
                        key={ls}
                        type="button"
                        onClick={() => setLabelStyle(ls)}
                        className={`rounded border px-2 py-1 text-[11px] ${labelStyle === ls ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
                        data-testid={`label-style-${ls}`}
                      >
                        {ls === 'revu'
                          ? t('takeoff_viewer.label_style_revu', { defaultValue: 'Revu (plain text)' })
                          : t('takeoff_viewer.label_style_badge', { defaultValue: 'Badge' })}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-[11px] font-semibold text-content-secondary">
                    {t('takeoff_viewer.label_show_lines', { defaultValue: 'Show in label' })}
                  </p>"""),
]
bad = [(old[:90], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if bad:
    print('NOT WRITTEN, anchors:', *bad, sep='\n  ')
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs))
