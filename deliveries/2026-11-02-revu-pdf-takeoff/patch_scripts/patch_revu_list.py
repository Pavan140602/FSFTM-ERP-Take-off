"""Auto markups in the Markups list, no profile text on the sheet, column
markers optional (all-or-nothing). OE-DELIVERY: 2026-11-02-revu-markups-list"""
import sys
from pathlib import Path

root = Path(sys.argv[1])  # frontend/src/modules/pdf-takeoff
TAG = 'OE-DELIVERY 2026-11-02-revu-markups-list'


def apply(path: Path, pairs):
    s = path.read_text(encoding='utf-8')
    bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
    if bad:
        print('NOT WRITTEN', path.name, *bad, sep='\n  ')
        sys.exit(1)
    for o, n in pairs:
        s = s.replace(o, n)
    return s


# ── data/auto-takeoff.ts ──
d = root / 'data' / 'auto-takeoff.ts'
ds = apply(d, [
("""/** Group name for an item: category + designation, so the ledger totals""",
 """/** Revu "Subject" of an auto markup, shown in the Markups list Label
 *  column (""" + TAG + """). */
export function autoSubject(cat: string): string {
  return (
    {
      beams: 'Beam',
      columns: 'Column',
      joists: 'Joist',
      trusses: 'Truss',
      walls: 'CFS Wall',
      areas: 'Framing Area',
      other: 'Member',
    } as Record<string, string>
  )[cat] ?? 'Member';
}

/** Group name for an item: category + designation, so the ledger totals"""),
])

# ── useMeasurementPersistence.ts: custom fields sync on edit too ──
pm = root / 'useMeasurementPersistence.ts'
ps = apply(pm, [
("""    at: m.auto ?? null,""", """    at: m.auto ?? null,
    // Markups-list Label / Material (custom fields) edits must re-sync; they
    // were only written on create before (""" + TAG + """).
    cf: m.customFields ?? null,"""),
("""    auto_takeoff: m.auto ?? null,
    column_height: m.columnHeight ?? null,""", """    auto_takeoff: m.auto ?? null,
    column_height: m.columnHeight ?? null,
    custom_fields: m.customFields ?? null,"""),
])

# ── AutoTakeoffPanel.tsx ──
ap = root / 'AutoTakeoffPanel.tsx'
aps = apply(ap, [
("""const STYLE_KEY = 'takeoff.autoTakeoff.v1';""", """// v2: no profile text on the sheet by default - the highlight shows it (""" + TAG + """).
const STYLE_KEY = 'takeoff.autoTakeoff.v2';"""),
("""  style: { width: 1.5, alpha: 0.6, labelMode: 'name' },""", """  style: { width: 1.5, alpha: 0.6, labelMode: 'none' },"""),
("""  highlightAll: boolean;
  onToggleHighlight: (on: boolean) => void;
}""", """  highlightAll: boolean;
  onToggleHighlight: (on: boolean) => void;
  /** Draw the auto column markers on the sheet (off: the highlighted
   *  profile text marks them, like Revu). */
  showColumns: boolean;
  onToggleColumns: (on: boolean) => void;
}"""),
("""list, rejectedCount, onForgetRejected, highlightAll, onToggleHighlight } = props;""",
 """list, rejectedCount, onForgetRejected, highlightAll, onToggleHighlight, showColumns, onToggleColumns } = props;"""),
("""      {anyAuto && <AutoTakeoffList {...list} currentPage={currentPage} />}""", """      {anyAuto && (
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showColumns} onChange={(e) => onToggleColumns(e.target.checked)} data-testid="auto-show-columns" />
          <span>
            Show column markers on the sheet <span className="text-content-tertiary">(off: only the profile highlight, like Revu)</span>
          </span>
        </label>
      )}
      {anyAuto && <AutoTakeoffList {...list} currentPage={currentPage} />}"""),
])

# ── TakeoffViewerModule.tsx ──
v = root / 'TakeoffViewerModule.tsx'
vs = apply(v, [
("""  hasCombinedAutoCounts,
  normalizeProfile,""", """  hasCombinedAutoCounts,
  autoSubject,
  normalizeProfile,"""),
# state
("""  const [autoHighlightAll, setAutoHighlightAll] = useState<boolean>(() => {""",
 """  /** Auto column markers on the sheet (""" + TAG + """): off by default -
   *  the highlighted profile text marks each column, like Revu. A click on
   *  the spot still selects the column. */
  const [autoShowColumns, setAutoShowColumns] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.autoShowColumns') === '1'; } catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.autoShowColumns', autoShowColumns ? '1' : '0'); } catch { /* ignore */ }
  }, [autoShowColumns]);
  const [autoHighlightAll, setAutoHighlightAll] = useState<boolean>(() => {"""),
# draw filter
("""    for (const rawM of orderedMeasurements.filter((m) => m.page === currentPage && !hiddenGroups.has(m.group) && !hiddenMeasurements.has(m.id) && !hiddenTypes.has(m.type) && !(isAnnotationType(m.type) && hiddenGroups.has('__annotations__')))) {""",
 """    for (const rawM of orderedMeasurements.filter((m) => m.page === currentPage && !hiddenGroups.has(m.group) && !hiddenMeasurements.has(m.id) && !hiddenTypes.has(m.type) && !(isAnnotationType(m.type) && hiddenGroups.has('__annotations__')) && !(m.auto?.cat === 'columns' && !autoShowColumns))) {"""),
("""hiddenTypes, labelStyle, autoHighlightAll]);""", """hiddenTypes, labelStyle, autoHighlightAll, autoShowColumns]);"""),
# build: list fields
("""          notes: notesFor(item),
          author,
          createdAt: new Date().toISOString(),
          auto: tagForItem(item, pts),
        };""", """          notes: notesFor(item),
          author,
          createdAt: new Date().toISOString(),
          // Markups list (Revu Subject / profile columns).
          customFields: { Subject: autoSubject(item.category), Material: item.designation },
          auto: tagForItem(item, pts),
        };"""),
("""          group: autoGroupName(item.category, item.designation),
          notes: notesFor(item) ?? m.notes,
          auto: tagForItem(item, pts),""", """          group: autoGroupName(item.category, item.designation),
          notes: notesFor(item) ?? m.notes,
          customFields: { ...m.customFields, Subject: m.customFields?.Subject || autoSubject(item.category), Material: item.designation },
          auto: tagForItem(item, pts),"""),
# profile edit from the Auto list keeps the Markups list in step
("""          ? { ...m, annotation: des, group: autoGroupName(m.auto.cat, des), auto: { ...m.auto, des, ud: true } }""",
 """          ? {
              ...m,
              annotation: des,
              group: autoGroupName(m.auto.cat, des),
              customFields: { ...m.customFields, Subject: m.customFields?.Subject || autoSubject(m.auto.cat), Material: des },
              auto: { ...m.auto, des, ud: true },
            }"""),
# profile edit from the Markups list Material/Profile column = same as the Auto list
("""          if (field === 'material') {
            return { ...m, customFields: { ...m.customFields, Material: value } };
          }""", """          if (field === 'material') {
            // An auto markup's profile edited in the Markups list moves it to
            // that size, exactly like the Auto Takeoff list edit (""" + TAG + """).
            const prof = normalizeProfile(value);
            if (m.auto && prof) {
              return {
                ...m,
                annotation: prof,
                group: autoGroupName(m.auto.cat, prof),
                customFields: { ...m.customFields, Material: prof },
                auto: { ...m.auto, des: prof, ud: true },
              };
            }
            return { ...m, customFields: { ...m.customFields, Material: value } };
          }"""),
# migrate earlier auto markups once
("""  /** Deleted auto markups, remembered per drawing so a re-run never places""",
 """  /** Earlier auto markups: fill the Markups list columns and drop the
   *  profile text from the sheet (""" + TAG + """). Runs once per markup. */
  useEffect(() => {
    if (!measurements.some((m) => m.auto && !m.customFields?.Material)) return;
    setMeasurements((prev) =>
      prev.map((m) =>
        m.auto && !m.customFields?.Material
          ? {
              ...m,
              labelMode: 'none',
              customFields: { ...m.customFields, Subject: m.customFields?.Subject || autoSubject(m.auto.cat), Material: m.auto.des },
            }
          : m,
      ),
    );
  }, [measurements]);

  /** Deleted auto markups, remembered per drawing so a re-run never places"""),
# panel props
("""                highlightAll={autoHighlightAll}
                onToggleHighlight={setAutoHighlightAll}""", """                highlightAll={autoHighlightAll}
                onToggleHighlight={setAutoHighlightAll}
                showColumns={autoShowColumns}
                onToggleColumns={setAutoShowColumns}"""),
])

d.write_text(ds, encoding='utf-8')
pm.write_text(ps, encoding='utf-8')
ap.write_text(aps, encoding='utf-8')
v.write_text(vs, encoding='utf-8')
print('ok')
