# OE-DELIVERY 2026-11-03-auto-takeoff-members (frontend): pick member types, not raw categories.
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


patch('data/auto-takeoff.ts', [
    ("""export function autoCategoryMeta(cat: string) {""", """/** What Auto Takeoff can take off, the way an estimator thinks of it:
 *  structural steel and cold-formed steel member types. Each maps to the
 *  backend categories it needs and the roles it keeps
 *  (OE-DELIVERY 2026-11-03-auto-takeoff-members). */
export interface MemberType {
  key: string;
  label: string;
  group: 'Structural steel' | 'Cold-formed steel' | 'Other';
  cats: AutoCategory[];
  roles: string[];
  color: string;
}
export const MEMBER_TYPES: MemberType[] = [
  { key: 'column', label: 'Columns', group: 'Structural steel', cats: ['columns'], roles: ['Column'], color: '#7C3AED' },
  { key: 'beam', label: 'Beams', group: 'Structural steel', cats: ['beams'], roles: ['Beam'], color: '#1D4ED8' },
  { key: 'steel-joist', label: 'Joists (SJI K / LH / DLH)', group: 'Structural steel', cats: ['joists'], roles: ['Steel Joist'], color: '#4F46E5' },
  { key: 'deck', label: 'Deck areas (B / composite / form)', group: 'Structural steel', cats: ['areas'], roles: ['Deck'], color: '#65A30D' },
  { key: 'lb-wall', label: 'Load bearing walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Load Bearing Wall', 'CFS Wall'], color: '#DC2626' },
  { key: 'lb-header', label: 'Load bearing headers', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Load Bearing Header'], color: '#EA580C' },
  { key: 'lb-jamb', label: 'Load bearing jambs', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Load Bearing Jamb'], color: '#9333EA' },
  { key: 'shear-wall', label: 'Shear walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Shear Wall'], color: '#BE123C' },
  { key: 'nlb-wall', label: 'Non-load bearing walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Non-Load Bearing Wall'], color: '#16A34A' },
  { key: 'nlb-header', label: 'Non-load bearing headers', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Non-Load Bearing Header'], color: '#F59E0B' },
  { key: 'nlb-jamb', label: 'Non-load bearing jambs', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Non-Load Bearing Jamb'], color: '#C084FC' },
  { key: 'truss', label: 'Trusses (roof / floor)', group: 'Cold-formed steel', cats: ['trusses'], roles: ['Roof Truss', 'Floor Truss'], color: '#92400E' },
  { key: 'cfs-joist', label: 'Joists (CFS)', group: 'Cold-formed steel', cats: ['joists'], roles: ['CFS Joist', 'Floor Joist', 'Roof Joist', 'Ceiling Joist'], color: '#2563EB' },
  { key: 'hat', label: 'Hat channels', group: 'Cold-formed steel', cats: ['joists', 'other'], roles: ['Hat Channel'], color: '#0D9488' },
  { key: 'other', label: 'Other (angles, track, bays)', group: 'Other', cats: ['other', 'areas'], roles: ['Angle', 'Track', 'Stud', 'Other', 'Header', 'Jamb', 'Framing Area'], color: '#A16207' },
];
/** Categories + roles for a set of picked member types. */
export function memberScope(keys: string[]): { cats: AutoCategory[]; roles: Set<string> } {
  const picked = MEMBER_TYPES.filter((t) => keys.includes(t.key));
  return {
    cats: [...new Set(picked.flatMap((t) => t.cats))],
    roles: new Set(picked.flatMap((t) => t.roles)),
  };
}

export function autoCategoryMeta(cat: string) {"""),
    ("""  /** Remove unedited auto markups the run no longer finds. */
  removeStale: boolean;""", """  /** Remove unedited auto markups the run no longer finds. */
  removeStale: boolean;
  /** Member roles the run covered: stale clean-up only touches these
   *  (markups without a role fall back to the category). */
  roles?: Set<string>;"""),
    ("""        opts.categories.has(m.auto.cat) &&
        !isAutoEdited(m);""", """        opts.categories.has(m.auto.cat) &&
        (!opts.roles || !m.auto.role || opts.roles.has(m.auto.role)) &&
        !isAutoEdited(m);"""),
])

patch('AutoTakeoffPanel.tsx', [
    ("""export interface AutoApplyOptions {
  pages: number[];
  categories: AutoCategory[];""", """export interface AutoApplyOptions {
  pages: number[];
  categories: AutoCategory[];
  /** Member roles picked (OE-DELIVERY 2026-11-03-auto-takeoff-members). */
  roles?: string[];"""),
    ("""interface SavedPrefs {
  cats: AutoCategory[];""", """interface SavedPrefs {
  cats: AutoCategory[];
  /** Picked member types (MEMBER_TYPES keys). */
  types: string[];"""),
    ("""const DEFAULT_PREFS: SavedPrefs = {
  cats: AUTO_CATEGORIES.map((c) => c.key),""", """const DEFAULT_PREFS: SavedPrefs = {
  cats: AUTO_CATEGORIES.map((c) => c.key),
  types: MEMBER_TYPES.map((t) => t.key),"""),
    ("""      cats: Array.isArray(p.cats) ? (p.cats.filter((c) => AUTO_CATEGORIES.some((a) => a.key === c)) as AutoCategory[]) : DEFAULT_PREFS.cats,""",
     """      cats: Array.isArray(p.cats) ? (p.cats.filter((c) => AUTO_CATEGORIES.some((a) => a.key === c)) as AutoCategory[]) : DEFAULT_PREFS.cats,
      types: Array.isArray(p.types) ? p.types.filter((k) => MEMBER_TYPES.some((t) => t.key === k)) : DEFAULT_PREFS.types,"""),
    ("""    if (prefs.cats.length === 0) {
      setError('Tick at least one thing to take off.');
      return;
    }""", """    const scope = memberScope(prefs.types);
    if (scope.cats.length === 0) {
      setError('Tick at least one thing to take off.');
      return;
    }"""),
    ("""          pages: prefs.scope === 'all' ? null : pages,
          categories: prefs.cats,""", """          pages: prefs.scope === 'all' ? null : pages,
          categories: scope.cats,"""),
    ("""      const summary = onApply(res, {
        pages: res.pages.map((p) => p.page),
        categories: prefs.cats,""", """      // Keep only the member types picked (e.g. load bearing headers without
      // the walls that were read to tell bearing from non-bearing).
      const kept: AutoTakeoffResponse = {
        ...res,
        pages: res.pages.map((pg) => ({
          ...pg,
          items: pg.items.filter((it) => (it.role ? scope.roles.has(it.role) : scope.cats.includes(it.category))),
        })),
      };
      const summary = onApply(kept, {
        pages: res.pages.map((p) => p.page),
        categories: scope.cats,
        roles: [...scope.roles],"""),
    ("""      setLast({ res, summary, pages: res.pages.map((p) => p.page) });""", """      setLast({ res: kept, summary, pages: res.pages.map((p) => p.page) });"""),
    ("""  const toggleCat = (cat: AutoCategory) =>
    setPrefs((p) => ({ ...p, cats: p.cats.includes(cat) ? p.cats.filter((c) => c !== cat) : [...p.cats, cat] }));""",
     """  const toggleType = (key: string) =>
    setPrefs((p) => {
      const types = p.types.includes(key) ? p.types.filter((k) => k !== key) : [...p.types, key];
      return { ...p, types, cats: memberScope(types).cats };
    });
  const setGroup = (group: MemberType['group'], on: boolean) =>
    setPrefs((p) => {
      const keys = MEMBER_TYPES.filter((t) => t.group === group).map((t) => t.key);
      const types = on ? [...new Set([...p.types, ...keys])] : p.types.filter((k) => !keys.includes(k));
      return { ...p, types, cats: memberScope(types).cats };
    });"""),
    ("""        <p className="font-semibold text-content-secondary">What to take off</p>
        <div className="grid grid-cols-2 gap-1">
          {AUTO_CATEGORIES.map((c) => (
            <label key={c.key} className="flex items-center gap-1.5 rounded border border-border px-1.5 py-1 cursor-pointer hover:bg-surface-secondary">
              <input type="checkbox" checked={prefs.cats.includes(c.key)} onChange={() => toggleCat(c.key)} data-testid={`auto-cat-${c.key}`} />
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: c.color }} />
              <span className="flex-1 text-content-primary">{c.label}</span>
              {(stats.page[c.key] ?? 0) > 0 && <span className="text-content-tertiary">{stats.page[c.key]}</span>}
            </label>
          ))}
        </div>""", """        <p className="font-semibold text-content-secondary">What to take off</p>
        {(['Structural steel', 'Cold-formed steel', 'Other'] as const).map((group) => {
          const list = MEMBER_TYPES.filter((t) => t.group === group);
          const all = list.every((t) => prefs.types.includes(t.key));
          return (
            <div key={group} className="space-y-0.5" data-testid={`auto-group-${group.split(' ')[0]!.toLowerCase()}`}>
              {group !== 'Other' && (
                <label className="flex items-center gap-1.5 pt-1 text-[10px] font-bold uppercase tracking-wider text-content-tertiary">
                  <input type="checkbox" checked={all} onChange={() => setGroup(group, !all)} />
                  {group}
                </label>
              )}
              <div className="grid grid-cols-2 gap-1">
                {list.map((mt) => (
                  <label key={mt.key} className="flex cursor-pointer items-center gap-1.5 rounded border border-border px-1.5 py-1 hover:bg-surface-secondary">
                    <input type="checkbox" checked={prefs.types.includes(mt.key)} onChange={() => toggleType(mt.key)} data-testid={`auto-type-${mt.key}`} />
                    <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: mt.color }} />
                    <span className="flex-1 leading-tight text-content-primary">{mt.label}</span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}"""),
])

p = ROOT / 'AutoTakeoffPanel.tsx'
s = p.read_text(encoding='utf-8')
anchor = 'AUTO_CATEGORIES'
i = s.index('import {')
# add MEMBER_TYPES / memberScope / MemberType to the auto-takeoff import
j = s.index("from './data/auto-takeoff'")
k = s.rfind('import', 0, j)
block = s[k:j]
if 'MEMBER_TYPES' not in block:
    new_block = block.replace('import {', 'import {\n  MEMBER_TYPES,\n  memberScope,\n  type MemberType,', 1)
    s = s[:k] + new_block + s[j:]
p.write_text(s, encoding='utf-8')

V = ROOT / 'TakeoffViewerModule.tsx'
v = V.read_text(encoding='utf-8')
old = """          removeStale: opts.removeStale,
          rejected: autoRejectedRef.current,
        },"""
if v.count(old) != 1:
    print('ANCHOR FAIL viewer merge opts', v.count(old))
    sys.exit(1)
v = v.replace(old, """          removeStale: opts.removeStale,
          rejected: autoRejectedRef.current,
          roles: opts.roles ? new Set(opts.roles) : undefined,
        },""")
V.write_text(v, encoding='utf-8')
print('ok')
