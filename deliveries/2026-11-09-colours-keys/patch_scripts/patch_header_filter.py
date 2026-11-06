from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


p = base / "AutoTakeoffList.tsx"
s = p.read_text(encoding="utf-8")
rep("""  const visible = useMemo(
    () => (roleFilter ? onScope.filter((r) => r.cat !== 'walls' || r.role === roleFilter) : onScope),
    [onScope, roleFilter],
  );""", """  const hasHeaderAreas = useMemo(() => onScope.some((r) => r.cat === 'walls' && r.segment === 'header'), [onScope]);
  const visible = useMemo(
    () =>
      roleFilter === HEADER_FILTER
        ? onScope.filter((r) => r.cat !== 'walls' || r.segment === 'header')
        : roleFilter
          ? onScope.filter((r) => r.cat !== 'walls' || r.role === roleFilter)
          : onScope,
    [onScope, roleFilter],
  );""")
rep("""      {onRoleFilter && wallRoles.length > 1 && (""", """      {onRoleFilter && (wallRoles.length > 1 || hasHeaderAreas) && (""")
rep("""          {[null, ...wallRoles].map((role) => (""", """          {[null, ...wallRoles, ...(hasHeaderAreas ? [HEADER_FILTER] : [])].map((role) => (""")
rep("""              title={role ? `Show only ${role.toLowerCase()}s, in this list and on the sheet` : 'Show every wall'}
              data-testid="auto-wall-role"
            >
              {role ?? 'All walls'}
            </button>""", """              title={
                role === HEADER_FILTER
                  ? 'Show only the header areas (openings) of the walls - then "Select all" picks every one'
                  : role
                    ? `Show only ${role.toLowerCase()}s, in this list and on the sheet`
                    : 'Show every wall'
              }
              data-testid="auto-wall-role"
            >
              {role === HEADER_FILTER ? 'Header areas' : (role ?? 'All walls')}
            </button>""")
rep("""const SHOW_ROWS = 60;""", """const SHOW_ROWS = 60;
/** Walls filter value for the header areas of every wall (OE-DELIVERY 2026-11-09-colours-keys). */
export const HEADER_FILTER = '__header__';""")
p.write_text(s, encoding="utf-8")

p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")
# helper used by both the main render filter and the band loop
rep("""!(autoRoleFilter && m.auto?.cat === 'walls' && (m.auto.role ?? '') !== autoRoleFilter))) {""",
    """!(autoRoleFilter && m.auto?.cat === 'walls' && !wallPassesFilter(m.auto, autoRoleFilter)))) {""")
rep("""        if (autoRoleFilter && (m.auto.role ?? '') !== autoRoleFilter) continue;""",
    """        if (autoRoleFilter && !wallPassesFilter(m.auto, autoRoleFilter)) continue;""")
rep("import { AutoColours } from './data/auto-colours';\n", """import { AutoColours } from './data/auto-colours';
/** A wall shown under the Walls filter: one role, or the header areas only
 *  (OE-DELIVERY 2026-11-09-colours-keys). */
const wallPassesFilter = (tag: { role?: string; seg?: string }, filter: string): boolean =>
  filter === '__header__' ? tag.seg === 'header' : (tag.role ?? '') === filter;
""")
p.write_text(s, encoding="utf-8")
print("ok")
