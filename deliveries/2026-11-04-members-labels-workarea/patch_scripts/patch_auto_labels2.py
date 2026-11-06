# OE-DELIVERY 2026-11-04-auto-labels (layout): auto lines read like a dimension - profile above
# the line, length below, centred, turned with the line, sized like the drawing's own callout.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:140])
        sys.exit(1)
    s = s.replace(old, new)


rep("""      if (!showName && !showMaterial && !showValue) return;""", """      if (!showName && !showMaterial && !showValue) return;
      // Auto Takeoff lines (beams, joists, walls ...): profile above the line,
      // length below, both centred on it and turned with it - horizontal,
      // vertical or inclined - like a dimension, so the callout on the sheet
      // stays readable (OE-DELIVERY 2026-11-04-auto-labels).
      if (m.auto && (m.type === 'distance' || m.type === 'polyline') && m.points.length >= 2) {
        const k0 = dpr * zoom;
        const fsA = (m.labelTextSize ?? 6) * k0;
        const fsB = (m.labelDimSize ?? m.labelTextSize ?? 6) * k0;
        const fam = m.labelFont ? `"${m.labelFont}", Arial, Helvetica, sans-serif` : labelFontCss;
        const wt = fontPrefix(m, labelBold, labelItalic);
        const col = m.labelNameColor ?? resolveMeasurementColor(m, groupColorMap);
        const half = ((m.strokeWidth ?? 2) * dpr * zoom) / 2;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(labelAngle);
        ctx.textAlign = 'center';
        ctx.fillStyle = col;
        if (showName) {
          ctx.font = `${wt}${fsA}px ${fam}`;
          ctx.textBaseline = 'bottom';
          ctx.fillText(name, 0, -half - fsA * 0.15);
        }
        if (showValue) {
          ctx.font = `${wt}${fsB}px ${fam}`;
          ctx.textBaseline = 'top';
          ctx.fillText(value, 0, half + fsB * 0.15);
        }
        ctx.restore();
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        return;
      }""")

# new auto markups: caption size taken from the callout they were read from
rep("""          labelMode: opts.style.labelMode,""", """          labelMode: opts.style.labelMode,
          // Caption as tall as the callout on the sheet (drawing units).
          ...(item.label_rect && item.label_rect.length === 4
            ? (() => {
                const h = Math.max(3, Math.min(14, Math.min(Math.abs(item.label_rect![3]! - item.label_rect![1]!), Math.abs(item.label_rect![2]! - item.label_rect![0]!)) * 0.85));
                return { labelTextSize: h, labelDimSize: h };
              })()
            : { labelTextSize: 6, labelDimSize: 6 }),""")

# existing auto markups get the same size once
rep("""    const legacy = measurements.filter((m) => m.auto && m.labelMode === 'none' && (m.type === 'distance' || m.type === 'polyline' || m.type === 'area'));""",
    """    const legacy = measurements.filter((m) => m.auto && (m.labelMode === 'none' || m.labelTextSize == null) && (m.type === 'distance' || m.type === 'polyline' || m.type === 'area'));""")
rep("""    setMeasurements((prev) => prev.map((m) => (ids.has(m.id) ? { ...m, labelMode: 'all' } : m)));""",
    """    setMeasurements((prev) =>
      prev.map((m) => {
        if (!ids.has(m.id)) return m;
        const lr = m.auto?.lr;
        const h = lr ? Math.max(3, Math.min(14, Math.min(Math.abs(lr[3] - lr[1]), Math.abs(lr[2] - lr[0])) * 0.85)) : 6;
        return { ...m, labelMode: m.labelMode === 'none' ? 'all' : m.labelMode, labelTextSize: m.labelTextSize ?? h, labelDimSize: m.labelDimSize ?? h };
      }),
    );""")
P.write_text(s, encoding='utf-8')
print('ok')
