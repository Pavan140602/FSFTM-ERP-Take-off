# OE-DELIVERY 2026-11-04-auto-labels: auto markups show profile + length centred on the line,
# turned with it (horizontal / vertical / inclined); what was read first is reported.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:140])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('AutoTakeoffPanel.tsx', [
    ("""  pages: AutoTakeoffPage[];
  specs?: Record<string, string>;""", """  pages: AutoTakeoffPage[];
  specs?: Record<string, string>;
  /** Schedules / marks read before drawing (OE-DELIVERY 2026-11-04-auto-takeoff-zoom). */
  read?: { schedule_rows: number; wall_types: number; header_jamb_types: number; column_marks: number; sheets_read: number };"""),
    ("""const STYLE_KEY = 'takeoff.autoTakeoff.v2';""", """// v3: auto markups show profile + length on the line (OE-DELIVERY 2026-11-04-auto-labels).
const STYLE_KEY = 'takeoff.autoTakeoff.v3';"""),
    ("""  style: { width: 1.5, alpha: 0.6, labelMode: 'none' },
};""", """  style: { width: 1.5, alpha: 0.6, labelMode: 'all' },
};"""),
    ("""function loadPrefs(): SavedPrefs {
  try {
    const raw = localStorage.getItem(STYLE_KEY);""", """function loadPrefs(): SavedPrefs {
  try {
    // Carry the v2 choices over, with the new on-line labels.
    const raw = localStorage.getItem(STYLE_KEY) ?? (() => {
      const old = localStorage.getItem('takeoff.autoTakeoff.v2');
      if (!old) return null;
      try {
        const o = JSON.parse(old) as Partial<SavedPrefs>;
        return JSON.stringify({ ...o, style: { ...(o.style ?? {}), labelMode: 'all' } });
      } catch {
        return null;
      }
    })();"""),
    ("""          {last.summary.calibrated.length > 0 && (""", """          {last.res.read && (
            <p className="text-content-secondary" data-testid="auto-read-first">
              Read first: {last.res.read.sheets_read} sheet{last.res.read.sheets_read === 1 ? '' : 's'} of schedules and notes
              {last.res.read.wall_types ? ` · ${last.res.read.wall_types} wall types` : ''}
              {last.res.read.header_jamb_types ? ` · ${last.res.read.header_jamb_types} header/jamb types` : ''}
              {last.res.read.column_marks ? ` · ${last.res.read.column_marks} column marks` : ''}
              {last.res.read.schedule_rows ? ` · ${last.res.read.schedule_rows} schedule rows` : ''}
            </p>
          )}
          {last.summary.calibrated.length > 0 && ("""),
])

patch('TakeoffViewerModule.tsx', [
    # AISC-style profile on the sheet
    ("""      const name = m.auto
        ? (m.annotation?.trim() || m.auto.des)
        : (m.customFields?.Subject?.trim() || m.annotation?.trim() || '');""", """      const name = m.auto
        ? displayDesignation(m.annotation?.trim() || m.auto.des)
        : (m.customFields?.Subject?.trim() || m.annotation?.trim() || '');"""),
    ("""  withStructuralSets,
  markStructuralSeeded,""", """  withStructuralSets,
  markStructuralSeeded,
  displayDesignation,"""),
    # one-time: existing auto markups switch from hidden labels to profile + length
    ("""  const ledgerDocKey = documentId || fileName || 'local';""", """  const ledgerDocKey = documentId || fileName || 'local';
  /** Auto markups placed before on-line labels existed show profile + length
   *  once per drawing (OE-DELIVERY 2026-11-04-auto-labels); a later choice of
   *  "None" in the panel sticks. */
  useEffect(() => {
    const key = `takeoff.autoLabels.v3.${ledgerDocKey}`;
    try { if (localStorage.getItem(key)) return; } catch { return; }
    const legacy = measurements.filter((m) => m.auto && m.labelMode === 'none' && (m.type === 'distance' || m.type === 'polyline' || m.type === 'area'));
    if (measurements.some((m) => m.auto)) {
      try { localStorage.setItem(key, '1'); } catch { /* ignore */ }
    }
    if (legacy.length === 0) return;
    const ids = new Set(legacy.map((m) => m.id));
    setMeasurements((prev) => prev.map((m) => (ids.has(m.id) ? { ...m, labelMode: 'all' } : m)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [measurements, ledgerDocKey]);"""),
])
print('ok')
