# OE-DELIVERY 2026-11-02-revu-properties-bar: library half (types, units, captions, persistence)
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])
edits = []

def rep(rel, old, new, count=1):
    edits.append((rel, old, new, count))

TYPES_FIELDS = """  /** Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar):
   *  caption units, caption pick list and caption text style per markup. */
  dispUnit?: 'in' | 'ft' | 'ftin' | 'mm' | 'cm' | 'm' | 'km';
  dispAreaUnit?: 'sq in' | 'sq ft' | 'sq cm' | 'sq m' | 'sq mm';
  captions?: ('label' | 'length' | 'area' | 'perimeter' | 'wallArea' | 'depth' | 'volume' | 'count')[];
  labelFont?: string;
  labelBold?: boolean;
  labelItalic?: boolean;
  labelUnderline?: boolean;
"""

# lib type
rep('features/takeoff/lib/takeoff-types.ts',
    "  labelMode?: 'all' | 'value' | 'name' | 'none';\n",
    "  labelMode?: 'all' | 'value' | 'name' | 'none';\n" + TYPES_FIELDS + """  labelTextSize?: number;
  labelMaterialSize?: number;
  labelDimSize?: number;
  labelNameColor?: string;
  labelMaterialColor?: string;
  labelDimColor?: string;
""")

# viewer local type
rep('modules/pdf-takeoff/TakeoffViewerModule.tsx',
    "  labelMode?: 'all' | 'value' | 'name' | 'none';\n  /** Placed by Auto Takeoff",
    "  labelMode?: 'all' | 'value' | 'name' | 'none';\n" + TYPES_FIELDS + "  /** Placed by Auto Takeoff")

# persistence local type + round trip
P = 'modules/pdf-takeoff/useMeasurementPersistence.ts'
rep(P, "  labelMode?: 'all' | 'value' | 'name' | 'none';\n",
    "  labelMode?: 'all' | 'value' | 'name' | 'none';\n" + TYPES_FIELDS + """  labelTextSize?: number;
  labelMaterialSize?: number;
  labelDimSize?: number;
  labelNameColor?: string;
  labelMaterialColor?: string;
  labelDimColor?: string;
""")
rep(P, "      label_mode: m.labelMode,\n",
    "      label_mode: m.labelMode,\n      label_style: labelStyleOf(m) ?? undefined,\n")
rep(P, "    lm: m.labelMode ?? null,\n",
    "    lm: m.labelMode ?? null,\n    lst: labelStyleOf(m),\n")
rep(P, "    label_mode: m.labelMode ?? null,\n",
    "    label_mode: m.labelMode ?? null,\n    label_style: labelStyleOf(m),\n")
rep(P, "    labelMode: isLabelMode(meta.label_mode) ? meta.label_mode : undefined,\n",
    "    labelMode: isLabelMode(meta.label_mode) ? meta.label_mode : undefined,\n    ...cleanLabelStyle(meta.label_style),\n")

# display units: per-markup override + km + area units + captions
D = 'features/takeoff/lib/takeoff-display-units.ts'
rep(D, "import type { Measurement } from './takeoff-types';\n",
    "import type { Measurement } from './takeoff-types';\nimport { METRES_PER, SQM_PER, type AreaDispUnit, type CaptionKey, type DispUnit } from './takeoff-revu-props';\n")
rep(D, """function formatWithDisplayUnit(
  metricValue: number,
  metricUnit: string,
  scale: ScaleConfig,
  system: MeasurementSystem,
): string {
  const isArea = metricUnit.includes('²') || metricUnit === 'm2';
  const isVol = metricUnit.includes('³') || metricUnit === 'm3';
  const forced = globalDisplayUnit !== 'auto' ? globalDisplayUnit : null;
""", """function formatWithDisplayUnit(
  metricValue: number,
  metricUnit: string,
  scale: ScaleConfig,
  system: MeasurementSystem,
  markupUnit?: DispUnit,
  markupAreaUnit?: AreaDispUnit,
): string {
  const isArea = metricUnit.includes('²') || metricUnit === 'm2';
  const isVol = metricUnit.includes('³') || metricUnit === 'm3';
  // Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar): the
  // markup's own area / length unit wins over the global choice.
  if (isArea && markupAreaUnit) {
    return `${formatPlainQuantity(metricValue / SQM_PER[markupAreaUnit])} ${markupAreaUnit}`;
  }
  if (markupUnit) {
    if (markupUnit === 'ftin') {
      if (!isArea && !isVol) return formatFeetInches(metricValue);
      return formatQuantity(metricValue, metricUnit, 'imperial');
    }
    const per = METRES_PER[markupUnit];
    const exp = isArea ? 2 : isVol ? 3 : 1;
    const u = isArea ? `${markupUnit}²` : isVol ? `${markupUnit}³` : markupUnit;
    return formatMeasurement(metricValue / per ** exp, u);
  }
  const forced = globalDisplayUnit !== 'auto' ? globalDisplayUnit : null;
""")

# measurementLabel honours markup units
rep(D, """export function measurementLabel(
  m: Measurement,
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  switch (m.type) {""", """export function measurementLabel(
  m: Measurement,
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  if (m.captions && m.captions.length > 0) return captionValueText(m, scale, system, areaUnitOverride);
  const fmt = (v: number, u: string) => formatWithDisplayUnit(v, u, scale, system, m.dispUnit, m.dispAreaUnit);
  switch (m.type) {""")
# within measurementLabel, route the formatWithDisplayUnit calls through fmt
body_old_new = [
    ("      const lengthStr = formatWithDisplayUnit(m.value, m.unit || 'm', scale, system);",
     "      const lengthStr = fmt(m.value, m.unit || 'm');"),
    ("      const heightStr = formatWithDisplayUnit(m.wallHeight ?? 0, m.unit || 'm', scale, system);",
     "      const heightStr = fmt(m.wallHeight ?? 0, m.unit || 'm');"),
    ("      const head = `${lengthStr} × ${heightStr} = ${formatWithDisplayUnit(gross, areaUnit, scale, system)}`;",
     "      const head = `${lengthStr} × ${heightStr} = ${fmt(gross, areaUnit)}`;"),
    ("        ? `${head} → ${formatWithDisplayUnit(reported, areaUnit, scale, system)}`",
     "        ? `${head} → ${fmt(reported, areaUnit)}`"),
    ("      const areaStr = areaUnitOverride\n        ? formatAreaWithUnit(trueArea, m.unit || 'm²', areaUnitOverride)\n        : formatWithDisplayUnit(trueArea, m.unit || 'm²', scale, system);",
     "      const areaStr = areaUnitOverride && !m.dispAreaUnit\n        ? formatAreaWithUnit(trueArea, m.unit || 'm²', areaUnitOverride)\n        : fmt(trueArea, m.unit || 'm²');"),
    ("      const perimStr = formatWithDisplayUnit(perimMetres, 'm', scale, system);",
     "      const perimStr = fmt(perimMetres, 'm');"),
    ("      const volStr = formatWithDisplayUnit(m.value, m.unit || 'm³', scale, system);",
     "      const volStr = fmt(m.value, m.unit || 'm³');"),
    ("      const baseStr = formatWithDisplayUnit(baseArea, 'm²', scale, system);",
     "      const baseStr = fmt(baseArea, 'm²');"),
    ("      const depthStr = formatWithDisplayUnit(m.depth ?? 0, 'm', scale, system);",
     "      const depthStr = fmt(m.depth ?? 0, 'm');"),
]
for o, n in body_old_new:
    rep(D, o, n)

CAPTION_FN = """

/**
 * Caption text built from the markup's caption pick list (Revu Properties
 * toolbar, OE-DELIVERY 2026-11-02-revu-properties-bar). 'label' is the name
 * line and is drawn by the viewer, so it is skipped here; every other pick
 * adds one figure in the markup's own units.
 */
export function captionValueText(
  m: Measurement,
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  const fmt = (v: number, u: string) => formatWithDisplayUnit(v, u, scale, system, m.dispUnit, m.dispAreaUnit);
  const fmtArea = (v: number) =>
    areaUnitOverride && !m.dispAreaUnit ? formatAreaWithUnit(v, 'm²', areaUnitOverride) : fmt(v, 'm²');
  const caps = (m.captions ?? []) as CaptionKey[];
  const out: string[] = [];
  const linear = m.type !== 'area' && m.type !== 'volume' && m.type !== 'count';
  const trueArea = m.type === 'area' ? (m.value || 0) * quantityFactor(m) : m.type === 'volume' ? m.area ?? 0 : 0;
  for (const c of caps) {
    switch (c) {
      case 'length':
        if (linear) out.push(fmt(m.value || 0, 'm'));
        break;
      case 'area':
        if (m.type === 'area' || m.type === 'volume') out.push(`A: ${fmtArea(trueArea)}`);
        break;
      case 'perimeter':
        if ((m.type === 'area' || m.type === 'volume') && m.points.length > 2) {
          out.push(`P: ${fmt(toRealDistance(polygonPerimeterPixels(m.points), scale), 'm')}`);
        }
        break;
      case 'wallArea':
        if (isWallMeasurement(m)) out.push(`WA: ${fmtArea(Math.abs(effectiveQuantity(m)))}`);
        break;
      case 'depth': {
        const d = m.type === 'volume' || m.type === 'area' ? m.depth : m.wallHeight;
        if (d && d > 0) out.push(`D: ${fmt(d, 'm')}`);
        break;
      }
      case 'volume': {
        const vol = m.type === 'volume' ? m.value : m.type === 'area' && m.depth ? trueArea * m.depth : 0;
        if (vol) out.push(`V: ${fmt(vol, 'm³')}`);
        break;
      }
      case 'count':
        if (m.type === 'count') out.push(String(m.points.length));
        break;
      default:
        break;
    }
  }
  return out.join('  ');
}
"""

def main():
    files = {}
    for rel, old, new, count in edits:
        p = ROOT / rel
        if rel not in files:
            files[rel] = p.read_text(encoding='utf-8')
        s = files[rel]
        c = s.count(old)
        if c != count:
            print(f'ANCHOR FAIL {rel}: found {c}, want {count}:\n{old[:160]}')
            sys.exit(1)
        files[rel] = s.replace(old, new)
    # caption fn appended to display units
    files[D] = files[D].rstrip('\n') + CAPTION_FN
    # persistence imports
    s = files[P]
    imp = "import { cleanLabelStyle, labelStyleOf } from '../../features/takeoff/lib/takeoff-revu-props';\n"
    first = s.index('\nimport ')
    files[P] = s[: first + 1] + imp + s[first + 1:]
    for rel, s in files.items():
        (ROOT / rel).write_text(s, encoding='utf-8')
    print('ok', len(edits), 'edits')

main()
