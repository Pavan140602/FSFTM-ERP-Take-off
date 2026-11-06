# OE-DELIVERY 2026-11-05-framing-rules: frontend - new member types, house rules switch,
# sheets/schedules read, schedule height -> wall height, Level column.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) / "frontend/src/modules/pdf-takeoff"
F = {
    "at": ROOT / "data/auto-takeoff.ts",
    "st": ROOT / "data/structural-tools.ts",
    "panel": ROOT / "AutoTakeoffPanel.tsx",
    "viewer": ROOT / "TakeoffViewerModule.tsx",
}
S = {k: p.read_text(encoding="utf-8") for k, p in F.items()}


def rep(k, old, new):
    if S[k].count(old) != 1:
        print("ANCHOR FAIL", k, S[k].count(old), old[:140])
        sys.exit(1)
    S[k] = S[k].replace(old, new)


# ── data/auto-takeoff.ts ──
rep("at", '''  /** Column mark (C1, C2 ...) and where it is printed. */
  mark?: string | null;
  mark_quad?: number[][] | null;
}''', '''  /** Column mark (C1, C2 ...) and where it is printed. */
  mark?: string | null;
  mark_quad?: number[][] | null;
  /** Floor / schedule level the member belongs to ('1ST TO 2ND', '2ND FLOOR',
   *  'ROOF') and the wall height from the schedule, feet
   *  (OE-DELIVERY 2026-11-05-framing-rules). */
  level?: string | null;
  height_ft?: number | null;
}''')
rep("at", '''  { key: 'deck', label: 'Deck areas (B / composite / form)', group: 'Structural steel', cats: ['areas'], roles: ['Deck'], color: '#65A30D' },''',
    '''  { key: 'deck', label: 'Deck areas (B / composite / form)', group: 'Structural steel', cats: ['areas'], roles: ['Deck'], color: '#65A30D' },
  { key: 'base-plate', label: 'Base plates', group: 'Structural steel', cats: ['other'], roles: ['Base Plate'], color: '#0F766E' },
  { key: 'steel-brace', label: 'Steel braces (BRACE-X)', group: 'Structural steel', cats: ['other'], roles: ['Steel Brace'], color: '#B45309' },''')
rep("at", '''  { key: 'shear-wall', label: 'Shear walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Shear Wall'], color: '#BE123C' },''',
    '''  { key: 'shear-wall', label: 'Shear walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Shear Wall'], color: '#BE123C' },
  { key: 'strap-wall', label: 'Strap braced walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Strap Braced Wall'], color: '#9F1239' },
  { key: 'holdown', label: 'Holdowns', group: 'Cold-formed steel', cats: ['other'], roles: ['Holdown'], color: '#7E22CE' },
  { key: 'cfs-beam', label: 'CFS beams (boxed / built-up)', group: 'Cold-formed steel', cats: ['beams'], roles: ['CFS Beam'], color: '#1E40AF' },''')
rep("at", '''export function memberScope(keys: string[]): { cats: AutoCategory[]; roles: Set<string> } {''',
    '''/** Member types added with the house framing rules; turned on for anyone
 *  whose saved choices predate them (OE-DELIVERY 2026-11-05-framing-rules). */
export const RULES_MEMBER_TYPES = ['base-plate', 'steel-brace', 'strap-wall', 'holdown', 'cfs-beam'];

export function memberScope(keys: string[]): { cats: AutoCategory[]; roles: Set<string> } {''')

# ── data/structural-tools.ts ──
rep("st", '''  'Framing Area': '#65A30D',
};''', '''  'Framing Area': '#65A30D',
  // House framing rules (OE-DELIVERY 2026-11-05-framing-rules).
  'Strap Braced Wall': '#9F1239',
  Holdown: '#7E22CE',
  'Base Plate': '#0F766E',
  'Steel Brace': '#B45309',
  'CFS Beam': '#1E40AF',
};''')

# ── AutoTakeoffPanel.tsx ──
rep("panel", '''  MEMBER_TYPES,
  memberScope,''', '''  MEMBER_TYPES,
  RULES_MEMBER_TYPES,
  memberScope,''')
rep("panel", '''  read?: { schedule_rows: number; wall_types: number; header_jamb_types: number; column_marks: number; sheets_read: number };''',
    '''  read?: {
    schedule_rows: number;
    wall_types: number;
    header_jamb_types: number;
    column_marks: number;
    sheets_read: number;
    /** House framing rules (OE-DELIVERY 2026-11-05-framing-rules). */
    framing_rules?: boolean;
    schedules?: Record<string, string[]>;
    sheets?: { page: number; kind: string; level: number | null }[];
  };''')
rep("panel", '''  details: boolean;
  calibrate: boolean;
  removeStale: boolean;
  style: AutoStyle;
}''', '''  details: boolean;
  calibrate: boolean;
  removeStale: boolean;
  style: AutoStyle;
  /** House framing rules: per sheet kind, only what that sheet is for. */
  rules: boolean;
  /** Saved choices already include the framing-rules member types. */
  rulesTypes?: boolean;
}''')
rep("panel", '''  removeStale: false,
  style: { width: 1.5, alpha: 0.6, labelMode: 'all' },
};''', '''  removeStale: false,
  style: { width: 1.5, alpha: 0.6, labelMode: 'all' },
  rules: true,
  rulesTypes: true,
};''')
rep("panel", '''      types: Array.isArray(p.types) ? p.types.filter((k) => MEMBER_TYPES.some((t) => t.key === k)) : DEFAULT_PREFS.types,
      style: { ...DEFAULT_PREFS.style, ...(p.style ?? {}) },''', '''      types: Array.isArray(p.types)
        ? [...new Set([...p.types, ...(p.rulesTypes ? [] : RULES_MEMBER_TYPES)])].filter((k) => MEMBER_TYPES.some((t) => t.key === k))
        : DEFAULT_PREFS.types,
      style: { ...DEFAULT_PREFS.style, ...(p.style ?? {}) },
      rules: p.rules !== false,
      rulesTypes: true,''')
rep("panel", '''          use_ai: prefs.useAi,
          include_details: prefs.details,
        },''', '''          use_ai: prefs.useAi,
          include_details: prefs.details,
          framing_rules: prefs.rules,
        },''')
rep("panel", '''      <div className="space-y-1">
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.useAi} onChange={(e) => setPrefs((p) => ({ ...p, useAi: e.target.checked }))} data-testid="auto-use-ai" />''', '''      <div className="space-y-1">
        <label className="flex items-start gap-1.5 cursor-pointer" title={RULES_HELP}>
          <input type="checkbox" checked={prefs.rules} onChange={(e) => setPrefs((p) => ({ ...p, rules: e.target.checked }))} data-testid="auto-framing-rules" />
          <span>
            <b>House framing rules</b>{' '}
            <span className="text-content-tertiary">
              — framing plans: floor framing only (every joist / truss at its spacing, beams, deck); shear wall plans: walls of that floor&apos;s
              level row (1ST TO 2ND on the 1st floor), headers, shear / strap walls, holdowns; foundation: columns + base plates, no footings
            </span>
          </span>
        </label>
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.useAi} onChange={(e) => setPrefs((p) => ({ ...p, useAi: e.target.checked }))} data-testid="auto-use-ai" />''')
rep("panel", '''              {last.res.read.schedule_rows ? ` · ${last.res.read.schedule_rows} schedule rows` : ''}
            </p>
          )}''', '''              {last.res.read.schedule_rows ? ` · ${last.res.read.schedule_rows} schedule rows` : ''}
            </p>
          )}
          {last.res.read?.framing_rules && (
            <div className="text-content-secondary space-y-0.5" data-testid="auto-rules-summary">
              <p>
                <b>Framing rules:</b>{' '}
                {(last.res.read.sheets ?? []).map((s) => `p.${s.page} ${sheetKindName(s.kind, s.level)}`).join(' · ') || 'no plan sheets in the pages read'}
              </p>
              {last.res.read.schedules && Object.keys(last.res.read.schedules).length > 0 && (
                <p className="text-content-tertiary">
                  Schedules:{' '}
                  {Object.entries(last.res.read.schedules)
                    .map(([k, tags]) => `${SCHEDULE_NAMES[k] ?? k} ${tags.join(', ')}`)
                    .join(' · ')}
                </p>
              )}
            </div>
          )}''')
rep("panel", '''const LABEL_MODES: { key: AutoStyle['labelMode']; label: string }[] = [''', '''const RULES_HELP =
  'House framing rules (same for every project): the sheet title decides what is taken off. ' +
  'Floor / roof framing plan: joists and trusses framed one by one at the schedule spacing, beams, deck. ' +
  'Shear wall plan of floor N: walls with the schedule row N TO N+1 (framing, spacing, height), headers, ' +
  'shear and strap-braced walls, holdowns, steel braces. Foundation plan: columns and base plates (no footings). ' +
  'Details, sections and notes sheets are read for schedules only.';

const SCHEDULE_NAMES: Record<string, string> = {
  wall: 'Walls',
  shear_wall: 'Shear walls',
  brace_wall: 'Strap walls',
  header: 'Headers',
  truss: 'Trusses',
  joist: 'Joists',
  cfs_beam: 'CFS beams',
  base_plate: 'Base plates',
  diaphragm: 'Diaphragm',
};

function ordinal(n: number): string {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th';
  return `${n}${s}`;
}

/** "walls", 1 -> "1st floor shear walls". */
export function sheetKindName(kind: string, level: number | null): string {
  if (kind === 'foundation') return 'foundation';
  if (kind === 'roof') return 'roof framing';
  if (kind === 'walls') return `${level ? `${ordinal(level)} floor ` : ''}shear walls`;
  if (kind === 'framing') return `${level ? `${ordinal(level)} floor ` : ''}framing`;
  return kind;
}

const LABEL_MODES: { key: AutoStyle['labelMode']; label: string }[] = [''')

# ── TakeoffViewerModule.tsx ──
rep("viewer", '''          // Markups list (Revu Subject / profile columns).
          customFields: { Subject: subjectFor(item), Material: item.profile || item.designation },
          auto: tagForItem(item, pts),
        };
        return { ...base, ...valueFor(base, pts) };''', '''          // Markups list (Revu Subject / profile columns).
          customFields: { Subject: subjectFor(item), Material: item.profile || item.designation, ...(item.level ? { Level: item.level } : {}) },
          // Wall height from the schedule row (feet -> metres) drives Wall Area
          // (OE-DELIVERY 2026-11-05-framing-rules).
          ...(type === 'distance' && item.height_ft && item.height_ft > 0 ? { wallHeight: +(item.height_ft * 0.3048).toFixed(4) } : {}),
          auto: tagForItem(item, pts),
        };
        return { ...base, ...valueFor(base, pts) };''')
rep("viewer", '''            Subject: genericSubjects.has(m.customFields?.Subject ?? '') ? subjectFor(item) : m.customFields!.Subject!,
            Material: m.auto?.ud ? (m.customFields?.Material ?? item.designation) : item.profile || item.designation,
          },''', '''            Subject: genericSubjects.has(m.customFields?.Subject ?? '') ? subjectFor(item) : m.customFields!.Subject!,
            Material: m.auto?.ud ? (m.customFields?.Material ?? item.designation) : item.profile || item.designation,
            ...(item.level && !m.customFields?.Level ? { Level: item.level } : {}),
          },
          ...(m.wallHeight === undefined && item.kind === 'line' && item.height_ft && item.height_ft > 0
            ? { wallHeight: +(item.height_ft * 0.3048).toFixed(4) }
            : {}),''')

for k, p in F.items():
    p.write_text(S[k], encoding="utf-8")
print("ok")
