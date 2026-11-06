# OE-DELIVERY 2026-11-02-revu-markups-units: Markups list = sheet units; Subject + Label columns
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])
L = ROOT / 'features/takeoff/components/MeasurementLedger.tsx'
s = L.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d want %d)\n%s' % (c, count, old[:200]))
        sys.exit(1)
    s = s.replace(old, new)


FIELD_OLD = "(id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material', value: string) => void;"
FIELD_NEW = "(id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material' | 'subject', value: string) => void;"
rep(FIELD_OLD, FIELD_NEW, 2)

rep("""  { key: 'label', i18nKey: 'takeoff_viewer.col_label', fallback: 'Label', align: 'left' },""",
    """  // Revu Markups list: Subject (category) and Label (text on the sheet).
  { key: 'subject', i18nKey: 'takeoff_viewer.col_subject', fallback: 'Subject', align: 'left' },
  { key: 'label', i18nKey: 'takeoff_viewer.col_label', fallback: 'Label', align: 'left' },""")

TAIL = """}

/** Measurement types that carry a pushable quantity."""
FMT_PROP = """  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
""" + TAIL
FMT_NEW = """  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
""" + """  /** Formats a quantity exactly as the sheet caption does (the markup's own
   *  units, else the chosen display unit, else the page calibration). Returns
   *  the number and the unit separately. (OE-DELIVERY 2026-11-02-revu-markups-units) */
  formatQuantityCell?: (m: Measurement, kind: 'length' | 'area' | 'volume', metricValue: number) => { num: string; unit: string };
""" + TAIL
# GroupRows prop type
rep("""  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
}) {""", """  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
  formatQuantityCell?: (m: Measurement, kind: 'length' | 'area' | 'volume', metricValue: number) => { num: string; unit: string };
}) {""")
rep(FMT_PROP, FMT_NEW, 1)  # props interface (first occurrence is in MeasurementLedgerProps)
rep("""  areaUnit = 'sf',
  lengthUnit,
}: MeasurementLedgerProps) {""", """  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: MeasurementLedgerProps) {""")
rep("""  areaUnit = 'sf',
  lengthUnit,
}: {""", """  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: {""")
rep("""                areaUnit={areaUnit}
                lengthUnit={lengthUnit}
              />""", """                areaUnit={areaUnit}
                lengthUnit={lengthUnit}
                formatQuantityCell={formatQuantityCell}
              />""")

# per-row: the figures as the sheet shows them
rep("""    const isWall = isWallMeasurement(measurement);
    const openingCount = isWall ? wallOpeningsCount(measurement) : 0;
    return (""", """    const isWall = isWallMeasurement(measurement);
    const openingCount = isWall ? wallOpeningsCount(measurement) : 0;
    // Same figures and units as the sheet caption (OE-DELIVERY 2026-11-02-revu-markups-units).
    const sheet = (() => {
      if (!formatQuantityCell || measurement.type === 'count' || ANNOTATION_KINDS.has(measurement.type)) return null;
      const sign = signed < 0 ? '-' : '';
      const fmt = (kind: 'length' | 'area' | 'volume', v: number) => {
        const r = formatQuantityCell(measurement, kind, Math.abs(v));
        return { num: sign && Math.abs(v) > 0 ? `${sign}${r.num}` : r.num, unit: r.unit };
      };
      const trueArea = (measurement.value || 0) * quantityFactor(measurement);
      if (measurement.type === 'area' || measurement.type === 'rectangle') {
        const a = fmt('area', signed < 0 ? -trueArea : trueArea);
        return { primary: a, area: a };
      }
      if (measurement.type === 'volume') return { primary: fmt('volume', signed), area: null };
      if (isWall) {
        // A wall: Length column is its run, Area column its (net) wall area.
        return { primary: fmt('length', measurement.value || 0), area: fmt('area', signed) };
      }
      return { primary: fmt('length', signed), area: null };
    })();
    return (""")

# Subject + Label cells
rep("""        {isColVisible('label') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.customFields?.Subject || ''}
        >
          {onFieldChange ? (
            <EditableCell
              value={measurement.customFields?.Subject || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'label', v)}
              placeholder="Add label…"
              testId={`ledger-label-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.customFields?.Subject || '—'
          )}
        </td>
        )}""", """        {isColVisible('subject') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.customFields?.Subject || ''}
        >
          {onFieldChange ? (
            <EditableCell
              value={measurement.customFields?.Subject || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'subject', v)}
              placeholder="Add subject…"
              testId={`ledger-subject-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.customFields?.Subject || '—'
          )}
        </td>
        )}
        {isColVisible('label') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.annotation || ''}
        >
          {/* Label = the text on the sheet, as in Revu. */}
          {onFieldChange ? (
            <EditableCell
              value={measurement.annotation || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'label', v)}
              placeholder="Add label…"
              testId={`ledger-label-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.annotation || '—'
          )}
        </td>
        )}""")

# Length cell
rep("""          {measurement.type === 'count'
            ? formatCountQuantity(disp.value)
            : lengthUnit && measurement.type !== 'count'""", """          {sheet
            ? sheet.primary.num
            : measurement.type === 'count'
            ? formatCountQuantity(disp.value)
            : lengthUnit && measurement.type !== 'count'""")
# Area cell
rep("""        <td className="px-1.5 py-1 text-right font-mono text-content-secondary">
          {measurement.type === 'area' || measurement.type === 'rectangle'
            ? (() => {""", """        <td className="px-1.5 py-1 text-right font-mono text-content-secondary">
          {sheet
            ? sheet.area
              ? `${sheet.area.num}${sheet.area.unit === 'ft-in' ? '' : ` ${sheet.area.unit}`}`
              : '—'
            : measurement.type === 'area' || measurement.type === 'rectangle'
            ? (() => {""")
# Unit cell
rep("""          {localizedUnitCode(
            lengthUnit && LINEAR_KINDS.has(measurement.type) ? lengthUnit : disp.unit,
            i18n.language,
          )}""", """          {sheet
            ? sheet.primary.unit
            : localizedUnitCode(
                lengthUnit && LINEAR_KINDS.has(measurement.type) ? lengthUnit : disp.unit,
                i18n.language,
              )}""")
# annotation kinds set
rep("""const LINEAR_KINDS = new Set(['distance', 'polyline', 'perimeter', 'arc']);""",
    """const LINEAR_KINDS = new Set(['distance', 'polyline', 'perimeter', 'arc']);
/** Markup-only kinds: no measured figure to format. */
const ANNOTATION_KINDS = new Set(['cloud', 'arrow', 'text', 'highlight', 'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp', 'legend', 'angle']);""")
L.write_text(s, encoding='utf-8')

# sort: Label by sheet text, Subject by Subject
T = ROOT / 'features/takeoff/lib/takeoff-ledger.ts'
t = T.read_text(encoding='utf-8')
old = """    case 'label':
      return ((a.customFields?.Subject || '') as string).localeCompare((b.customFields?.Subject || '') as string);"""
assert t.count(old) == 1
t = t.replace(old, """    case 'subject':
      return ((a.customFields?.Subject || '') as string).localeCompare((b.customFields?.Subject || '') as string);
    case 'label':
      return (a.annotation || '').localeCompare(b.annotation || '');""")
T.write_text(t, encoding='utf-8')
print('ok')
