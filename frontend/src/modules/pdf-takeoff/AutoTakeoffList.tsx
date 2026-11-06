// OE-DELIVERY: 2026-11-02-auto-takeoff-list
import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronRight, Crosshair, MousePointer2, Pencil, Trash2, X } from 'lucide-react';
import ColorPicklist from './components/ColorPicklist';
import { type AutoCategory, type AutoListRow, autoCategoryMeta, formatFeetInches, groupAutoRows, parseFeetInches } from './data/auto-takeoff';

/** Inline profile editor (OE-DELIVERY 2026-11-02-auto-takeoff-profile-edit): type a size or pick one of the
 *  profiles already on the drawing; Enter / tick saves, Esc / cross
 *  cancels. */
function ProfileInput(props: { initial: string; onSave: (v: string) => void; onCancel: () => void }) {
  const { initial, onSave, onCancel } = props;
  const [v, setV] = useState(initial === 'COLUMN' ? '' : initial);
  const done = useRef(false);
  const save = () => {
    if (done.current) return;
    done.current = true;
    if (v.trim()) onSave(v);
    else onCancel();
  };
  return (
    <span className="flex flex-1 items-center gap-0.5 min-w-0" onClick={(e) => e.stopPropagation()}>
      <input
        autoFocus
        type="text"
        value={v}
        list="auto-profile-options"
        placeholder="e.g. W12X26, HSS6X6X1/4"
        onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => {
          e.stopPropagation();
          if (e.key === 'Enter') save();
          if (e.key === 'Escape') {
            done.current = true;
            onCancel();
          }
        }}
        className="min-w-0 flex-1 rounded border border-oe-blue bg-surface-primary px-1 py-0 text-[10px] uppercase"
        data-testid="auto-profile-input"
      />
      <button
        type="button"
        title="Save profile"
        className="rounded p-0.5 text-emerald-600 hover:bg-surface-secondary"
        onMouseDown={(e) => e.preventDefault()}
        onClick={save}
        data-testid="auto-profile-save"
      >
        <Check size={11} />
      </button>
      <button
        type="button"
        title="Cancel"
        className="rounded p-0.5 text-content-tertiary hover:bg-surface-secondary"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          done.current = true;
          onCancel();
        }}
      >
        <X size={11} />
      </button>
    </span>
  );
}

/** Column height box: type 12'-6", 12.5 or 150"; saved on Enter / leaving
 *  the box (OE-DELIVERY 2026-11-02-auto-takeoff-columns). */
function HeightInput(props: { valueFt: number | null | undefined; placeholder?: string; onSave: (ft: number | null) => void; testId?: string }) {
  const { valueFt, placeholder, onSave, testId } = props;
  const [text, setText] = useState(formatFeetInches(valueFt));
  const [bad, setBad] = useState(false);
  useEffect(() => {
    setText(formatFeetInches(valueFt));
    setBad(false);
  }, [valueFt]);
  const commit = () => {
    if (!text.trim()) {
      setBad(false);
      if (valueFt) onSave(null);
      return;
    }
    const ft = parseFeetInches(text);
    if (ft == null) {
      setBad(true);
      return;
    }
    setBad(false);
    setText(formatFeetInches(ft));
    if (Math.abs((valueFt ?? 0) - ft) > 1e-6) onSave(ft);
  };
  return (
    <input
      type="text"
      value={text}
      placeholder={placeholder ?? "Height"}
      title="Column height, e.g. 12'-6&quot; or 12.5"
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') {
          setText(formatFeetInches(valueFt));
          setBad(false);
        }
      }}
      className={`w-[64px] shrink-0 rounded border bg-surface-primary px-1 py-0 text-[10px] ${bad ? 'border-red-500' : 'border-border'}`}
      data-testid={testId}
    />
  );
}

/** Detected-markups list of the Auto Takeoff tab.
 *
 * Category -> size / tag -> every single markup. A row click selects the
 * markup and zooms the sheet to it; the bin deletes just that markup (a
 * wrong column, a beam on the wrong line). Group buttons select or delete
 * every markup of one size. Deleting asks for a second click.
 */

export interface AutoTakeoffListProps {
  rows: AutoListRow[];
  currentPage: number;
  selectedIds: ReadonlySet<string>;
  formatTotal: (ids: string[]) => string;
  onFocus: (id: string) => void;
  onSelect: (ids: string[]) => void;
  onDelete: (ids: string[]) => void;
  /** Save a column height (feet; null clears) on the given markups. */
  onSetHeight: (ids: string[], ft: number | null) => void;
  /** Set the profile of the given markups by hand (OE-DELIVERY 2026-11-02-auto-takeoff-profile-edit). */
  onSetProfile: (ids: string[], profile: string) => void;
  /** Profiles to suggest while typing (the ones on this drawing). */
  profileOptions: string[];
  /** Recolour markups from the Revu colour picklist (OE-DELIVERY 2026-11-08-stud-walls). */
  onRecolor?: (ids: string[], colour: string) => void;
  /** Walls shown: one role only (Shear Wall ...) or all (null). The sheet
   *  shows the same walls as the list. */
  roleFilter?: string | null;
  onRoleFilter?: (role: string | null) => void;
}

const SHOW_ROWS = 60;
/** Walls filter value for the header areas of every wall (OE-DELIVERY 2026-11-09-colours-keys). */
export const HEADER_FILTER = '__header__';

export default function AutoTakeoffList(props: AutoTakeoffListProps) {
  const { rows, currentPage, selectedIds, formatTotal, onFocus, onSelect, onDelete, onSetHeight, onSetProfile, profileOptions, onRecolor, roleFilter, onRoleFilter } = props;
  /** What is being renamed: `g:<cat>|<des>` (a whole size group) or `r:<id>`. */
  const [editing, setEditing] = useState<string>('');
  const [scope, setScope] = useState<'page' | 'all'>('page');
  const [openCats, setOpenCats] = useState<Set<string>>(() => new Set(['beams', 'columns', 'joists', 'trusses', 'walls', 'areas', 'other']));
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [armed, setArmed] = useState<string>('');
  const armTimer = useRef<number | null>(null);

  const onScope = useMemo(() => (scope === 'page' ? rows.filter((r) => r.page === currentPage) : rows), [rows, scope, currentPage]);
  /** Wall roles on the sheet, for the "show only" chips. */
  const wallRoles = useMemo(
    () => [...new Set(onScope.filter((r) => r.cat === 'walls' && r.role).map((r) => r.role!))].sort(),
    [onScope],
  );
  const hasHeaderAreas = useMemo(() => onScope.some((r) => r.cat === 'walls' && r.segment === 'header'), [onScope]);
  const visible = useMemo(
    () =>
      roleFilter === HEADER_FILTER
        ? onScope.filter((r) => r.cat !== 'walls' || r.segment === 'header')
        : roleFilter
          ? onScope.filter((r) => r.cat !== 'walls' || r.role === roleFilter)
          : onScope,
    [onScope, roleFilter],
  );
  const tree = useMemo(() => groupAutoRows(visible), [visible]);
  /** Last row clicked: the start of a Shift+click run (OE-DELIVERY 2026-11-07-multi-select). */
  const anchor = useRef<string | null>(null);
  /** Ctrl / Cmd + click adds or removes one markup; Shift + click selects the
   *  run of markups from the last one clicked, as listed; a plain click
   *  selects and zooms to one markup. */
  const rowClick = (e: React.MouseEvent, id: string) => {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault();
      const next = new Set(selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      anchor.current = id;
      onSelect([...next]);
      return;
    }
    if (e.shiftKey && anchor.current) {
      e.preventDefault();
      window.getSelection?.()?.removeAllRanges();
      // Rows in the order they show: open categories and groups only.
      const order: string[] = [];
      for (const c of tree) {
        if (!openCats.has(c.cat)) continue;
        for (const g of c.groups) {
          if (!openGroups.has(`${c.cat}|${g.des}`)) continue;
          for (const r of g.rows.slice(0, SHOW_ROWS)) order.push(r.id);
        }
      }
      const a = order.indexOf(anchor.current);
      const b = order.indexOf(id);
      if (a >= 0 && b >= 0) {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        onSelect([...new Set([...selectedIds, ...order.slice(lo, hi + 1)])]);
        return;
      }
    }
    anchor.current = id;
    onFocus(id);
  };

  // Opening a markup on the sheet (a click there) opens its group here.
  useEffect(() => {
    if (selectedIds.size !== 1) return;
    const id = [...selectedIds][0]!;
    const row = rows.find((r) => r.id === id);
    if (!row) return;
    setOpenCats((prev) => (prev.has(row.cat) ? prev : new Set([...prev, row.cat])));
    setOpenGroups((prev) => {
      const key = `${row.cat}|${row.des}`;
      return prev.has(key) ? prev : new Set([...prev, key]);
    });
    requestAnimationFrame(() => document.getElementById(`auto-row-${id}`)?.scrollIntoView({ block: 'nearest' }));
  }, [selectedIds, rows]);

  useEffect(() => () => {
    if (armTimer.current) window.clearTimeout(armTimer.current);
  }, []);

  /** Two-click delete: the first click arms the button for 3 s. */
  const confirmDelete = (key: string, ids: string[]) => {
    if (armed !== key) {
      setArmed(key);
      if (armTimer.current) window.clearTimeout(armTimer.current);
      armTimer.current = window.setTimeout(() => setArmed(''), 3000);
      return;
    }
    setArmed('');
    onDelete(ids);
  };

  const toggle = (set: Set<string>, key: string) => {
    const next = new Set(set);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  };

  return (
    <div className="rounded-lg border border-border p-2 space-y-1.5" data-testid="auto-list">
      <div className="flex items-center gap-1">
        <p className="flex-1 font-semibold text-content-primary">Detected markups</p>
        {(['page', 'all'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setScope(s)}
            className={`rounded border px-1.5 py-0.5 ${scope === s ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
          >
            {s === 'page' ? 'This sheet' : 'All sheets'}
          </button>
        ))}
      </div>
      {onRoleFilter && (wallRoles.length > 1 || hasHeaderAreas) && (
        <div className="flex flex-wrap items-center gap-1" data-testid="auto-wall-role-filter">
          <span className="text-content-tertiary">Walls:</span>
          {[null, ...wallRoles, ...(hasHeaderAreas ? [HEADER_FILTER] : [])].map((role) => (
            <button
              key={role ?? 'all'}
              type="button"
              onClick={() => onRoleFilter(role)}
              className={`rounded-full border px-1.5 py-0.5 text-[10px] ${roleFilter === role ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
              title={
                role === HEADER_FILTER
                  ? 'Show only the header areas (openings) of the walls - then "Select all" picks every one'
                  : role
                    ? `Show only ${role.toLowerCase()}s, in this list and on the sheet`
                    : 'Show every wall'
              }
              data-testid="auto-wall-role"
            >
              {role === HEADER_FILTER ? 'Header areas' : (role ?? 'All walls')}
            </button>
          ))}
        </div>
      )}
      {tree.length === 0 && (
        <p className="text-content-tertiary">{scope === 'page' ? 'No auto markups on this sheet yet.' : 'No auto markups yet.'}</p>
      )}
      {tree.map((cat) => {
        const meta = autoCategoryMeta(cat.cat);
        const catOpen = openCats.has(cat.cat);
        return (
          <div key={cat.cat} className="rounded border border-border/70">
            <div className="flex items-center bg-surface-secondary/50">
            <button
              type="button"
              onClick={() => setOpenCats((p) => toggle(p, cat.cat))}
              className="flex flex-1 items-center gap-1.5 px-1.5 py-1 hover:bg-surface-secondary"
              data-testid={`auto-list-cat-${cat.cat}`}
            >
              {catOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: meta.color }} />
              <span className="flex-1 text-left font-semibold">{meta.label}</span>
              <span className="text-content-tertiary">{cat.count}</span>
            </button>
            {/* Select every markup of this category on the sheet, e.g. all
                beams, to restyle or delete them together (OE-DELIVERY 2026-11-04-perf-rerun). */}
            <button
              type="button"
              onClick={() => onSelect(cat.groups.flatMap((g) => g.rows.map((r) => r.id)))}
              className="mr-1 rounded px-1.5 py-0.5 text-[10px] font-semibold text-oe-blue hover:bg-oe-blue/10"
              title={`Select all ${meta.label.toLowerCase()} on the sheet`}
              data-testid={`auto-list-select-${cat.cat}`}
            >
              Select all
            </button>
            </div>
            {catOpen &&
              cat.groups.map((g) => {
                const key = `${cat.cat}|${g.des}`;
                const open = openGroups.has(key);
                const ids = g.rows.map((r) => r.id);
                return (
                  <div key={key} className="border-t border-border/60">
                    <div className="flex items-center gap-1 px-1.5 py-1">
                      {editing === `g:${key}` ? (
                        <ProfileInput
                          initial={g.des}
                          onSave={(v) => {
                            setEditing('');
                            onSetProfile(ids, v);
                          }}
                          onCancel={() => setEditing('')}
                        />
                      ) : (
                      <button type="button" onClick={() => setOpenGroups((p) => toggle(p, key))} className="flex-1 flex items-center gap-1 text-left min-w-0">
                        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                        <span className="font-medium text-content-primary shrink-0 max-w-[120px] truncate" title={g.des}>{g.des}</span>
                        <span className="text-content-tertiary shrink-0">×{g.rows.length}</span>
                        {/* Material from the plan (stud / joist / beam size), when it is not the name already. */}
                        {(() => {
                          const mat = g.rows.find((r) => r.material && r.material.replace(/\s+/g, '').toUpperCase() !== g.des.replace(/\s+/g, '').toUpperCase())?.material;
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
                        )}
                        {cat.cat === 'columns' && (() => {
                          const total = g.rows.reduce((acc, r) => acc + (r.heightFt ?? 0), 0);
                          const missing = g.rows.filter((r) => !r.heightFt).length;
                          return (
                            <span className="ml-auto min-w-0 truncate text-content-secondary" title="Total column height">
                              {total > 0 ? `Σ ${formatFeetInches(total)}` : ''}
                              {missing > 0 && total > 0 ? ` (${missing} no height)` : ''}
                            </span>
                          );
                        })()}
                      </button>
                      )}
                      {editing !== `g:${key}` && (
                        <button
                          type="button"
                          title={`Change the profile of all ${g.rows.length}`}
                          className="rounded p-0.5 hover:bg-surface-secondary"
                          onClick={() => setEditing(`g:${key}`)}
                          data-testid="auto-profile-edit-group"
                        >
                          <Pencil size={11} />
                        </button>
                      )}
                      {onRecolor && (
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
                          valueFt={g.rows.every((r) => r.heightFt === g.rows[0]!.heightFt) ? g.rows[0]!.heightFt : null}
                          placeholder="All ht"
                          onSave={(ft) => onSetHeight(ids, ft)}
                          testId="auto-col-height-all"
                        />
                      )}
                      <button type="button" title="Select all of these on the sheet" className="rounded p-0.5 hover:bg-surface-secondary" onClick={() => onSelect(ids)}>
                        <MousePointer2 size={12} />
                      </button>
                      <button
                        type="button"
                        title={armed === key ? 'Click again to delete all' : `Delete all ${g.rows.length}`}
                        className={`rounded px-0.5 py-0.5 ${armed === key ? 'bg-red-600 text-white' : 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30'}`}
                        onClick={() => confirmDelete(key, ids)}
                      >
                        {armed === key ? <span className="px-0.5 text-[10px] font-semibold">Delete {g.rows.length}?</span> : <Trash2 size={12} />}
                      </button>
                    </div>
                    {open && (
                      <div className="pb-1">
                        {g.rows.slice(0, SHOW_ROWS).map((r, i) => {
                          const sel = selectedIds.has(r.id);
                          return (
                            <div
                              key={r.id}
                              id={`auto-row-${r.id}`}
                              className={`group flex items-center gap-1 pl-5 pr-1.5 py-0.5 cursor-pointer ${sel ? 'bg-oe-blue/15' : 'hover:bg-surface-secondary'}`}
                              onClick={(e) => rowClick(e, r.id)}
                              title="Click: select and zoom to it. Ctrl+click: add or remove it. Shift+click: select every markup from the last one clicked"
                              data-testid="auto-list-row"
                            >
                              <Crosshair size={11} className="text-content-tertiary shrink-0" />
                              <span className="text-content-secondary shrink-0">
                                {cat.cat === 'columns' ? `#${i + 1}` : `${i + 1}.`}
                              </span>
                              {scope === 'all' && <span className="text-content-tertiary shrink-0">p{r.page}</span>}
                              {editing === `r:${r.id}` ? (
                                <ProfileInput
                                  initial={r.des}
                                  onSave={(v) => {
                                    setEditing('');
                                    onSetProfile([r.id], v);
                                  }}
                                  onCancel={() => setEditing('')}
                                />
                              ) : (
                                <>
                                  <span className="flex-1 truncate text-content-primary" title={[r.label, r.material].filter(Boolean).join(' · ')}>
                                    {cat.cat === 'columns' ? (r.label ?? r.des) : r.valueText}
                                    {cat.cat === 'walls' && r.segment === 'header' && (
                                      <span className="ml-1 rounded bg-amber-100 px-1 text-[9px] text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">header area</span>
                                    )}
                                    {cat.cat === 'walls' && r.segment !== 'header' && (r.studs ?? 0) > 0 && (
                                      <span className="ml-1 text-content-secondary" data-testid="auto-row-studs">
                                        · {r.studs} studs{r.spacingIn ? ` @ ${r.spacingIn}" o.c.` : ''}
                                      </span>
                                    )}
                                    {cat.cat !== 'columns' && r.material && r.material.replace(/\s+/g, '').toUpperCase() !== r.des.replace(/\s+/g, '').toUpperCase() && (
                                      <span className="ml-1 text-content-tertiary">· {r.material}</span>
                                    )}
                                  </span>
                                  <button
                                    type="button"
                                    title="Change the profile of this markup"
                                    className="rounded p-0.5 text-content-tertiary opacity-60 group-hover:opacity-100 hover:bg-surface-secondary"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditing(`r:${r.id}`);
                                    }}
                                    data-testid="auto-profile-edit"
                                  >
                                    <Pencil size={10} />
                                  </button>
                                </>
                              )}
                              {cat.cat === 'columns' && (
                                <HeightInput valueFt={r.heightFt} onSave={(ft) => onSetHeight([r.id], ft)} testId="auto-col-height" />
                              )}
                              {r.edited && <span className="rounded bg-amber-100 px-1 text-[9px] text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">edited</span>}
                              {r.generated && <span className="rounded bg-sky-100 px-1 text-[9px] text-sky-800 dark:bg-sky-900/40 dark:text-sky-200">gen</span>}
                              <button
                                type="button"
                                title={armed === r.id ? 'Click again to delete' : 'Delete this markup'}
                                className={`rounded p-0.5 ${armed === r.id ? 'bg-red-600 text-white' : 'text-red-600 opacity-60 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-950/30'}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  confirmDelete(r.id, [r.id]);
                                }}
                                data-testid="auto-list-delete"
                              >
                                <Trash2 size={11} />
                              </button>
                            </div>
                          );
                        })}
                        {g.rows.length > SHOW_ROWS && (
                          <p className="pl-5 text-content-tertiary">+{g.rows.length - SHOW_ROWS} more — use “Select” then Delete on the sheet.</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        );
      })}
      <datalist id="auto-profile-options">
        {profileOptions.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
      <p className="text-content-tertiary leading-snug">
        <Pencil size={10} className="inline" /> changes a profile (one markup, or a whole size) when Auto Takeoff read it wrong or not at
        all. Your profile is kept on every re-run.
      </p>
      <p className="text-content-tertiary leading-snug">
        Click a row to zoom to it — its profile text lights up yellow on the sheet. Clicking a markup on the sheet highlights its row here.
        On the sheet, click one markup (a column, a line) and press <kbd>Delete</kbd> to remove just that one. Column heights are saved with the drawing.
      </p>
    </div>
  );
}

export type { AutoCategory };
