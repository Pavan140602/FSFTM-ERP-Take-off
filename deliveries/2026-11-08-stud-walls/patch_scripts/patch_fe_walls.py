from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


# ── data/auto-takeoff.ts ──────────────────────────────────────────────
p = base / "data" / "auto-takeoff.ts"
s = p.read_text(encoding="utf-8")
rep("""  /** Column symbol on the sheet: [long side, short side, angle deg] in
   *  drawing units (OE-DELIVERY 2026-11-07-column-shapes). */
  symbol?: number[] | null;
}""", """  /** Column symbol on the sheet: [long side, short side, angle deg] in
   *  drawing units (OE-DELIVERY 2026-11-07-column-shapes). */
  symbol?: number[] | null;
  /** Stud wall (OE-DELIVERY 2026-11-08-stud-walls): full width (drawing
   *  units and inches), stud spacing (drawing units and inches), studs in
   *  the run, and whether the piece is plain wall or a header area. */
  wall_width?: number | null;
  wall_width_in?: number | null;
  stud_spacing?: number | null;
  stud_spacing_in?: number | null;
  stud_count?: number | null;
  segment?: 'wall' | 'header' | null;
  header?: string | null;
}""")
rep("""  /** Column symbol [long side, short side, angle deg] (OE-DELIVERY 2026-11-07-column-shapes). */
  sy?: [number, number, number];
}""", """  /** Column symbol [long side, short side, angle deg] (OE-DELIVERY 2026-11-07-column-shapes). */
  sy?: [number, number, number];
  /** Stud wall: width (units), width in inches, stud spacing (units and
   *  inches), piece kind (OE-DELIVERY 2026-11-08-stud-walls). */
  ww?: number;
  wi?: number;
  sd?: number;
  ss?: number;
  seg?: 'wall' | 'header';
}""")
rep("""    ...(Array.isArray(item.symbol) && item.symbol.length === 3
      ? { sy: [item.symbol[0]!, item.symbol[1]!, item.symbol[2]!] as [number, number, number] }
      : {}),
  };
}""", """    ...(Array.isArray(item.symbol) && item.symbol.length === 3
      ? { sy: [item.symbol[0]!, item.symbol[1]!, item.symbol[2]!] as [number, number, number] }
      : {}),
    ...(item.wall_width ? { ww: item.wall_width } : {}),
    ...(item.wall_width_in ? { wi: item.wall_width_in } : {}),
    ...(item.stud_spacing ? { sd: item.stud_spacing } : {}),
    ...(item.stud_spacing_in ? { ss: item.stud_spacing_in } : {}),
    ...(item.segment ? { seg: item.segment } : {}),
  };
}""")
rep("""  /** Column height in feet, entered by the user. */
  heightFt?: number | null;
}""", """  /** Column height in feet, entered by the user. */
  heightFt?: number | null;
  /** Member role (Load Bearing Wall, Shear Wall ...), material / profile
   *  set on it, studs in a wall run and the markup colour
   *  (OE-DELIVERY 2026-11-08-stud-walls). */
  role?: string;
  material?: string;
  studs?: number;
  spacingIn?: number;
  widthIn?: number;
  segment?: 'wall' | 'header';
  colour?: string;
}""")
p.write_text(s, encoding="utf-8")

# ── AutoTakeoffList.tsx ───────────────────────────────────────────────
p = base / "AutoTakeoffList.tsx"
s = p.read_text(encoding="utf-8")
rep("""import AutoTakeoffList""", """import AutoTakeoffList""", 0) if False else None
rep("""  /** Profiles to suggest while typing (the ones on this drawing). */
  profileOptions: string[];
}""", """  /** Profiles to suggest while typing (the ones on this drawing). */
  profileOptions: string[];
  /** Recolour markups from the Revu colour picklist (OE-DELIVERY 2026-11-08-stud-walls). */
  onRecolor?: (ids: string[], colour: string) => void;
  /** Walls shown: one role only (Shear Wall ...) or all (null). The sheet
   *  shows the same walls as the list. */
  roleFilter?: string | null;
  onRoleFilter?: (role: string | null) => void;
}""")
rep("""  const { rows, currentPage, selectedIds, formatTotal, onFocus, onSelect, onDelete, onSetHeight, onSetProfile, profileOptions } = props;""",
    """  const { rows, currentPage, selectedIds, formatTotal, onFocus, onSelect, onDelete, onSetHeight, onSetProfile, profileOptions, onRecolor, roleFilter, onRoleFilter } = props;""")
rep("""  const visible = useMemo(() => (scope === 'page' ? rows.filter((r) => r.page === currentPage) : rows), [rows, scope, currentPage]);""",
    """  const onScope = useMemo(() => (scope === 'page' ? rows.filter((r) => r.page === currentPage) : rows), [rows, scope, currentPage]);
  /** Wall roles on the sheet, for the "show only" chips. */
  const wallRoles = useMemo(
    () => [...new Set(onScope.filter((r) => r.cat === 'walls' && r.role).map((r) => r.role!))].sort(),
    [onScope],
  );
  const visible = useMemo(
    () => (roleFilter ? onScope.filter((r) => r.cat !== 'walls' || r.role === roleFilter) : onScope),
    [onScope, roleFilter],
  );""")
# role chips under the header row
rep("""      {tree.length === 0 && (""", """      {onRoleFilter && wallRoles.length > 1 && (
        <div className="flex flex-wrap items-center gap-1" data-testid="auto-wall-role-filter">
          <span className="text-content-tertiary">Walls:</span>
          {[null, ...wallRoles].map((role) => (
            <button
              key={role ?? 'all'}
              type="button"
              onClick={() => onRoleFilter(role)}
              className={`rounded-full border px-1.5 py-0.5 text-[10px] ${roleFilter === role ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
              title={role ? `Show only ${role.toLowerCase()}s, in this list and on the sheet` : 'Show every wall'}
              data-testid="auto-wall-role"
            >
              {role ?? 'All walls'}
            </button>
          ))}
        </div>
      )}
      {tree.length === 0 && (""")
# group header: material + studs + colour picklist
rep("""                        <span className="font-medium text-content-primary shrink-0 max-w-[120px] truncate" title={g.des}>{g.des}</span>
                        <span className="text-content-tertiary shrink-0">×{g.rows.length}</span>
                        {cat.cat !== 'columns' && <span className="ml-auto min-w-0 truncate text-content-secondary">{formatTotal(ids)}</span>}""", """                        <span className="font-medium text-content-primary shrink-0 max-w-[120px] truncate" title={g.des}>{g.des}</span>
                        <span className="text-content-tertiary shrink-0">×{g.rows.length}</span>
                        {/* Material from the plan (stud / joist / beam size), when it is not the name already. */}
                        {(() => {
                          const mat = g.rows.find((r) => r.material && r.material.replace(/\\s+/g, '').toUpperCase() !== g.des.replace(/\\s+/g, '').toUpperCase())?.material;
                          return mat ? (
                            <span className="min-w-0 truncate rounded bg-surface-secondary px-1 text-[10px] text-content-secondary" title={`Material: ${mat}`} data-testid="auto-group-material">
                              {mat}
                            </span>
                          ) : null;
                        })()}
                        {cat.cat !== 'columns' && (
                          <span className="ml-auto min-w-0 truncate text-content-secondary">
                            {formatTotal(ids)}
                            {cat.cat === 'walls' && (() => {
                              const studs = g.rows.reduce((acc, r) => acc + (r.studs ?? 0), 0);
                              return studs > 0 ? <b className="ml-1 text-content-primary" data-testid="auto-group-studs">· {studs} studs</b> : null;
                            })()}
                          </span>
                        )}""")
rep("""                      {cat.cat === 'columns' && (
                        <HeightInput
                          valueFt={g.rows.every((r) => r.heightFt === g.rows[0]!.heightFt) ? g.rows[0]!.heightFt : null}""", """                      {onRecolor && (
                        <ColorPicklist
                          value={g.rows[0]?.colour ?? null}
                          onChange={(c) => c && onRecolor(ids, c)}
                          title={`Colour of all ${g.rows.length}`}
                          testId="auto-group-colour"
                          size={14}
                        />
                      )}
                      {cat.cat === 'columns' && (
                        <HeightInput
                          valueFt={g.rows.every((r) => r.heightFt === g.rows[0]!.heightFt) ? g.rows[0]!.heightFt : null}""")
# row: value + studs + material
rep("""                                  <span className="flex-1 truncate text-content-primary" title={r.label}>
                                    {cat.cat === 'columns' ? (r.label ?? r.des) : r.valueText}
                                  </span>""", """                                  <span className="flex-1 truncate text-content-primary" title={[r.label, r.material].filter(Boolean).join(' · ')}>
                                    {cat.cat === 'columns' ? (r.label ?? r.des) : r.valueText}
                                    {cat.cat === 'walls' && r.segment === 'header' && (
                                      <span className="ml-1 rounded bg-amber-100 px-1 text-[9px] text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">header area</span>
                                    )}
                                    {cat.cat === 'walls' && r.segment !== 'header' && (r.studs ?? 0) > 0 && (
                                      <span className="ml-1 text-content-secondary" data-testid="auto-row-studs">
                                        · {r.studs} studs{r.spacingIn ? ` @ ${r.spacingIn}" o.c.` : ''}
                                      </span>
                                    )}
                                    {cat.cat !== 'columns' && r.material && r.material.replace(/\\s+/g, '').toUpperCase() !== r.des.replace(/\\s+/g, '').toUpperCase() && (
                                      <span className="ml-1 text-content-tertiary">· {r.material}</span>
                                    )}
                                  </span>""")
first_import_end = s.index("\n", s.index("import { Check"))
s = s[: first_import_end + 1] + "import ColorPicklist from './components/ColorPicklist';\n" + s[first_import_end + 1 :]
p.write_text(s, encoding="utf-8")

# ── TakeoffViewerModule.tsx ───────────────────────────────────────────
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")
rep("import TextFormatBar from './components/TextFormatBar';\n",
    "import TextFormatBar from './components/TextFormatBar';\nimport { drawStudWall, studCount } from './data/stud-wall';\n")
# state
rep("""  const [toolTextStyle, setToolTextStyle] = useState<Partial<TextStyle>>(() => loadToolTextStyle());""",
    """  const [toolTextStyle, setToolTextStyle] = useState<Partial<TextStyle>>(() => loadToolTextStyle());
  /** Walls shown: one role (Shear Wall ...) or every wall (OE-DELIVERY 2026-11-08-stud-walls). */
  const [autoRoleFilter, setAutoRoleFilter] = useState<string | null>(null);""")
# main render filter
rep("""!(m.auto?.cat === 'columns' && !autoShowColumns))) {""",
    """!(m.auto?.cat === 'columns' && !autoShowColumns) && !(autoRoleFilter && m.auto?.cat === 'walls' && (m.auto.role ?? '') !== autoRoleFilter))) {""")
# wall bands drawn before the column marks
rep("""    // Column marks (OE-DELIVERY 2026-11-03-auto-takeoff-roles): every auto""", """    // Stud walls (OE-DELIVERY 2026-11-08-stud-walls): each wall at its full
    // width as a see-through band, a stud at every spacing, header areas
    // hatched with no studs.
    {
      const k = dpr * zoom;
      for (const m of measurements) {
        if (m.page !== currentPage || m.auto?.cat !== 'walls' || !m.auto.ww) continue;
        if (hiddenGroups.has(m.group) || hiddenMeasurements.has(m.id) || hiddenTypes.has(m.type)) continue;
        if (autoRoleFilter && (m.auto.role ?? '') !== autoRoleFilter) continue;
        const colour = resolveMeasurementColor(m, groupColorMap);
        drawStudWall(ctx, m.points, m.auto, k, colour, 0.28, zoom >= 0.35);
      }
    }
    // Column marks (OE-DELIVERY 2026-11-03-auto-takeoff-roles): every auto""")
# draw deps
rep("""labelFontCss, labelFontStyle, displayUnitPref]);""", """labelFontCss, labelFontStyle, displayUnitPref, autoRoleFilter]);""")
# autoRows fields
rep("""            label: m.annotation || m.auto.des,
            heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
          };
        }),""", """            label: m.annotation || m.auto.des,
            heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
            // What the plan says it is made of, and the studs in a wall run
            // (OE-DELIVERY 2026-11-08-stud-walls).
            role: m.auto.role,
            material: typeof m.customFields?.Material === 'string' && m.customFields.Material ? m.customFields.Material : undefined,
            studs: m.auto.cat === 'walls' ? studCount(m.points, m.auto) : undefined,
            spacingIn: m.auto.ss,
            widthIn: m.auto.wi,
            segment: m.auto.seg,
            colour: resolveMeasurementColor(m, groupColorMap),
          };
        }),""")
rep("""    [measurements, pageScales, measurementSystem],
  );

  const formatAutoTotal = useCallback(""", """    [measurements, pageScales, measurementSystem, groupColorMap],
  );

  /** Recolour markups from the colour picklist (OE-DELIVERY 2026-11-08-stud-walls). */
  const recolorAutoIds = useCallback((ids: string[], colour: string) => {
    const set = new Set(ids);
    setMeasurements((prev) => prev.map((m) => (set.has(m.id) ? { ...m, color: colour } : m)));
  }, []);

  const formatAutoTotal = useCallback(""")
rep("""                  onSetProfile: setAutoProfile,
                  profileOptions: autoProfileOptions,
                }}""", """                  onSetProfile: setAutoProfile,
                  profileOptions: autoProfileOptions,
                  onRecolor: recolorAutoIds,
                  roleFilter: autoRoleFilter,
                  onRoleFilter: setAutoRoleFilter,
                }}""")
p.write_text(s, encoding="utf-8")

# ── TextFormatBar: Revu colour picklist ───────────────────────────────
p = base / "components" / "TextFormatBar.tsx"
s = p.read_text(encoding="utf-8")
rep("""function Swatch({ value, title, onPick, testId, none }: { value: string | null; title: string; onPick: (v: string | null) => void; testId: string; none?: boolean }) {
  return (
    <span className="flex items-center gap-0.5" title={title}>""", """function Swatch({ value, title, onPick, testId, none }: { value: string | null; title: string; onPick: (v: string | null) => void; testId: string; none?: boolean }) {
  // Revu-style colour picklist (OE-DELIVERY 2026-11-08-stud-walls).
  return <ColorPicklist value={value} onChange={onPick} allowNone={none} title={title} testId={testId} />;
}

export function NativeSwatch({ value, title, onPick, testId, none }: { value: string | null; title: string; onPick: (v: string | null) => void; testId: string; none?: boolean }) {
  return (
    <span className="flex items-center gap-0.5" title={title}>""")
rep("""import { TEXT_FONTS, TEXT_SIZES } from '../data/text-box';""", """import { TEXT_FONTS, TEXT_SIZES } from '../data/text-box';
import ColorPicklist from './ColorPicklist';""")
p.write_text(s, encoding="utf-8")

# ── RevuPropertiesBar: colour + fill picklists ────────────────────────
p = base / "components" / "RevuPropertiesBar.tsx"
s = p.read_text(encoding="utf-8")
rep("""      <Field label="Colour">
        <input
          type="color"
          disabled={off}
          value={value.color ?? defaults.color}
          onChange={(e) => onPatch({ color: e.target.value })}
          className="h-6 w-7 cursor-pointer rounded border border-border bg-transparent p-0 disabled:opacity-40"
          data-testid="props-color"
        />
      </Field>""", """      <Field label="Colour">
        {off ? (
          <input type="color" disabled value={value.color ?? defaults.color} readOnly className="h-6 w-7 rounded border border-border bg-transparent p-0 opacity-40" data-testid="props-color" />
        ) : (
          // Revu-style colour picklist (OE-DELIVERY 2026-11-08-stud-walls).
          <ColorPicklist value={value.color ?? defaults.color} onChange={(c) => c && onPatch({ color: c })} title="Colour" testId="props-color" size={22} />
        )}
      </Field>""")
rep("""        <Field label="Fill">
          <input
            type="color"
            disabled={off}
            value={value.fillColor ?? value.color ?? defaults.color}
            onChange={(e) => onPatch({ fillColor: e.target.value })}
            className="h-6 w-7 cursor-pointer rounded border border-border bg-transparent p-0 disabled:opacity-40"
            data-testid="props-fill"
          />
        </Field>""", """        <Field label="Fill">
          {off ? (
            <input type="color" disabled value={value.fillColor ?? value.color ?? defaults.color} readOnly className="h-6 w-7 rounded border border-border bg-transparent p-0 opacity-40" data-testid="props-fill" />
          ) : (
            <ColorPicklist value={value.fillColor ?? value.color ?? defaults.color} onChange={(c) => c && onPatch({ fillColor: c })} title="Fill" testId="props-fill" size={22} />
          )}
        </Field>""")
first_import_end = s.index("\n", s.index("\nimport ") + 1)
s = s[: first_import_end + 1] + "import ColorPicklist from './ColorPicklist';\n" + s[first_import_end + 1 :]
p.write_text(s, encoding="utf-8")
print("ok")
