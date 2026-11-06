// OE-DELIVERY: 2026-11-02-auto-takeoff
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, Eraser, Info, Loader2, Paintbrush, Sparkles, Wand2 } from 'lucide-react';
import AutoTakeoffList, { type AutoTakeoffListProps } from './AutoTakeoffList';
import { apiGet, apiPost, getErrorMessage } from '../../shared/lib/api';
import {
  MEMBER_TYPES,
  memberScope,
  type MemberType, AUTO_CATEGORIES, type AutoCategory, type AutoItem, type MergeSummary, describeMerge } from './data/auto-takeoff';

/** Auto Takeoff tab of the PDF Measurements right panel.
 *
 * Reads the open drawing on the server (text first, then the lines the
 * text names) and places real, editable markups: beams and other members
 * along their lines with the profile on the line, joist / truss series
 * one line per member, CFS walls by wall tag, columns as counts and bays
 * as areas. Running it again never places a markup twice and never
 * overwrites a markup the estimator edited (see data/auto-takeoff.ts).
 *
 * "Use AI" sends label text (and, for scanned sheets, the page image) to
 * the user's OWN AI provider key saved in Settings > AI.
 */

export interface AutoTakeoffPage {
  page: number;
  scale: string | null;
  units_per_foot: number | null;
  paper_in_per_ft: number | null;
  detail_sheet: boolean;
  counts: Record<string, number>;
  items: AutoItem[];
  note: string | null;
}

export interface AutoTakeoffResponse {
  available: boolean;
  message?: string;
  page_count?: number;
  pages: AutoTakeoffPage[];
  specs?: Record<string, string>;
  /** Schedules / marks read before drawing (OE-DELIVERY 2026-11-04-auto-takeoff-zoom). */
  read?: { schedule_rows: number; wall_types: number; header_jamb_types: number; column_marks: number; sheets_read: number };
  ai?: { requested: boolean; used: boolean; message: string | null; pages: number[]; provider?: string };
}

export interface AutoStyle {
  width: number;
  alpha: number;
  labelMode: 'name' | 'all' | 'value' | 'none';
}

export interface AutoApplyOptions {
  pages: number[];
  categories: AutoCategory[];
  /** Member roles picked (OE-DELIVERY 2026-11-03-auto-takeoff-members). */
  roles?: string[];
  autoCalibrate: boolean;
  removeStale: boolean;
  style: AutoStyle;
}

export interface AutoApplyResult extends MergeSummary {
  calibrated: number[];
}

export interface AutoTakeoffPanelProps {
  documentId: string | null;
  currentPage: number;
  pageCount: number;
  /** Auto markups per category on the current page / whole document. */
  stats: { page: Record<string, number>; total: Record<string, number>; edited: number };
  onApply: (res: AutoTakeoffResponse, opts: AutoApplyOptions) => AutoApplyResult;
  onRestyle: (style: AutoStyle, cats: Set<string>) => number;
  onRemove: (scope: 'page' | 'all', keepEdited: boolean, cats: Set<string>) => number;
  onSelectCategory?: (cat: AutoCategory) => number;
  onJumpToPage: (page: number) => void;
  /** Detected-markups list (OE-DELIVERY 2026-11-02-auto-takeoff-list). */
  list: Omit<AutoTakeoffListProps, 'currentPage'>;
  /** Auto markups the user deleted (re-runs skip them). */
  rejectedCount: number;
  onForgetRejected: () => void;
  /** Light up the profile text of every auto markup on the sheet. */
  highlightAll: boolean;
  onToggleHighlight: (on: boolean) => void;
  /** Draw the auto column markers on the sheet (off: the highlighted
   *  profile text marks them, like Revu). */
  showColumns: boolean;
  onToggleColumns: (on: boolean) => void;
}

interface StatusResponse {
  available: boolean;
  ai: { configured: boolean; provider?: string; model?: string; message?: string };
}

// v2: no profile text on the sheet by default - the highlight shows it (OE-DELIVERY 2026-11-02-revu-markups-list).
// v3: auto markups show profile + length on the line (OE-DELIVERY 2026-11-04-auto-labels).
const STYLE_KEY = 'takeoff.autoTakeoff.v3';

interface SavedPrefs {
  cats: AutoCategory[];
  /** Picked member types (MEMBER_TYPES keys). */
  types: string[];
  scope: 'page' | 'all' | 'range';
  range: string;
  useAi: boolean;
  details: boolean;
  calibrate: boolean;
  removeStale: boolean;
  style: AutoStyle;
}

const DEFAULT_PREFS: SavedPrefs = {
  cats: AUTO_CATEGORIES.map((c) => c.key),
  types: MEMBER_TYPES.map((t) => t.key),
  scope: 'page',
  range: '',
  useAi: false,
  details: false,
  calibrate: true,
  removeStale: false,
  style: { width: 1.5, alpha: 0.6, labelMode: 'all' },
};

function loadPrefs(): SavedPrefs {
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
    })();
    if (!raw) return DEFAULT_PREFS;
    const p = JSON.parse(raw) as Partial<SavedPrefs>;
    return {
      ...DEFAULT_PREFS,
      ...p,
      cats: Array.isArray(p.cats) ? (p.cats.filter((c) => AUTO_CATEGORIES.some((a) => a.key === c)) as AutoCategory[]) : DEFAULT_PREFS.cats,
      types: Array.isArray(p.types) ? p.types.filter((k) => MEMBER_TYPES.some((t) => t.key === k)) : DEFAULT_PREFS.types,
      style: { ...DEFAULT_PREFS.style, ...(p.style ?? {}) },
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

/** "3, 12-15" -> [3, 12, 13, 14, 15] (1-based, clamped to the page count). */
export function parsePageRange(text: string, pageCount: number): number[] {
  const out = new Set<number>();
  for (const part of text.split(/[,;\s]+/)) {
    if (!part) continue;
    const m = part.match(/^(\d+)(?:-(\d+))?$/);
    if (!m) continue;
    const a = Number(m[1]);
    const b = m[2] ? Number(m[2]) : a;
    for (let p = Math.min(a, b); p <= Math.max(a, b) && p <= pageCount; p++) if (p >= 1) out.add(p);
  }
  return [...out].sort((x, y) => x - y);
}

const LABEL_MODES: { key: AutoStyle['labelMode']; label: string }[] = [
  { key: 'name', label: 'Profile' },
  { key: 'all', label: 'Profile + length' },
  { key: 'value', label: 'Length' },
  { key: 'none', label: 'None' },
];

export default function AutoTakeoffPanel(props: AutoTakeoffPanelProps) {
  const { documentId, currentPage, pageCount, stats, onApply, onRestyle, onRemove, onJumpToPage, list, rejectedCount, onForgetRejected, highlightAll, onToggleHighlight, showColumns, onToggleColumns } = props;
  const [prefs, setPrefs] = useState<SavedPrefs>(loadPrefs);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [last, setLast] = useState<{ res: AutoTakeoffResponse; summary: AutoApplyResult; pages: number[] } | null>(null);
  const [info, setInfo] = useState('');

  useEffect(() => {
    try {
      localStorage.setItem(STYLE_KEY, JSON.stringify(prefs));
    } catch {
      /* ignore */
    }
  }, [prefs]);

  const refreshStatus = useCallback(() => {
    if (!documentId) {
      setStatus(null);
      return;
    }
    apiGet<StatusResponse>(`/v1/takeoff/documents/${documentId}/auto-takeoff/status/`)
      .then(setStatus)
      .catch(() => setStatus(null));
  }, [documentId]);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const pages = useMemo(() => {
    if (prefs.scope === 'page') return [currentPage];
    if (prefs.scope === 'all') return Array.from({ length: pageCount }, (_, i) => i + 1);
    return parsePageRange(prefs.range, pageCount);
  }, [prefs.scope, prefs.range, currentPage, pageCount]);

  const run = useCallback(async () => {
    if (!documentId || running) return;
    if (pages.length === 0) {
      setError('Enter the pages to read, for example 12-18, 23.');
      return;
    }
    const scope = memberScope(prefs.types);
    if (scope.cats.length === 0) {
      setError('Tick at least one thing to take off.');
      return;
    }
    setRunning(true);
    setError('');
    setInfo('');
    try {
      const res = await apiPost<AutoTakeoffResponse>(
        `/v1/takeoff/documents/${documentId}/auto-takeoff/`,
        {
          pages: prefs.scope === 'all' ? null : pages,
          categories: scope.cats,
          use_ai: prefs.useAi,
          include_details: prefs.details,
        },
        { longRunning: true },
      );
      if (!res.available) {
        setError(res.message ?? 'Auto Takeoff cannot read this drawing.');
        return;
      }
      // Keep only the member types picked (e.g. load bearing headers without
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
        roles: [...scope.roles],
        autoCalibrate: prefs.calibrate,
        removeStale: prefs.removeStale,
        style: prefs.style,
      });
      setLast({ res: kept, summary, pages: res.pages.map((p) => p.page) });
    } catch (err) {
      setError(getErrorMessage(err) || 'Auto Takeoff failed. Check the backend is running, then try again.');
    } finally {
      setRunning(false);
    }
  }, [documentId, running, pages, prefs, onApply]);

  const toggleType = (key: string) =>
    setPrefs((p) => {
      const types = p.types.includes(key) ? p.types.filter((k) => k !== key) : [...p.types, key];
      return { ...p, types, cats: memberScope(types).cats };
    });
  const setGroup = (group: MemberType['group'], on: boolean) =>
    setPrefs((p) => {
      const keys = MEMBER_TYPES.filter((t) => t.group === group).map((t) => t.key);
      const types = on ? [...new Set([...p.types, ...keys])] : p.types.filter((k) => !keys.includes(k));
      return { ...p, types, cats: memberScope(types).cats };
    });

  /** Live look (OE-DELIVERY 2026-11-02-revu-workspace): every slider move
   *  restyles the auto markups on the sheet at once (one frame-coalesced
   *  update), like dragging a property in Revu's Properties panel. */
  const liveTimer = useRef<number | null>(null);
  const pendingStyle = useRef<AutoStyle | null>(null);
  const setStyle = (patch: Partial<AutoStyle>) => {
    setPrefs((p) => {
      const style = { ...p.style, ...patch };
      pendingStyle.current = style;
      if (liveTimer.current == null) {
        liveTimer.current = window.setTimeout(() => {
          liveTimer.current = null;
          if (pendingStyle.current) onRestyle(pendingStyle.current, new Set(p.cats));
        }, 30);
      }
      return { ...p, style };
    });
  };
  useEffect(() => () => {
    if (liveTimer.current != null) window.clearTimeout(liveTimer.current);
  }, []);

  const totals = useMemo(() => {
    if (!last) return null;
    const t: Record<string, number> = {};
    for (const p of last.res.pages) for (const [k, v] of Object.entries(p.counts)) t[k] = (t[k] ?? 0) + v;
    return t;
  }, [last]);

  const notes = useMemo(() => {
    if (!last) return [] as { page: number; text: string }[];
    return last.res.pages.filter((p) => p.note && !(p.detail_sheet && prefs.scope === 'all')).map((p) => ({ page: p.page, text: p.note as string }));
  }, [last, prefs.scope]);

  if (!documentId) {
    return (
      <div className="rounded-lg border border-border bg-surface-secondary/40 p-3 text-[11px] text-content-secondary">
        Auto Takeoff reads the drawing on the server. Upload this PDF to the project, then open it from the documents list.
      </div>
    );
  }

  const aiOk = status?.ai?.configured;
  const anyAuto = Object.values(stats.total).some((v) => v > 0);

  return (
    <div className="space-y-3 text-[11px]" data-testid="auto-takeoff-panel">
      <div className="rounded-lg border border-border p-2.5 space-y-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-content-primary text-[12px]">
          <Wand2 size={14} className="text-oe-blue" />
          Auto Takeoff
        </div>
        <p className="text-content-secondary leading-snug">
          Reads the sheet text (sizes, joist callouts, wall tags), finds the lines they name and places editable markups.
          Re-running never places a markup twice and never overwrites one you edited.
        </p>
        {status && !status.available && (
          <p className="text-amber-600">This drawing is open as a local file. Upload it to the project so the server can read it.</p>
        )}
        <div className="flex items-start gap-1.5">
          <Sparkles size={12} className={aiOk ? 'text-emerald-600 mt-0.5' : 'text-content-tertiary mt-0.5'} />
          {aiOk ? (
            <span className="text-content-secondary">
              AI ready: <b>{status?.ai.provider}</b>
              {status?.ai.model ? ` (${status.ai.model})` : ''} from your Settings.
            </span>
          ) : (
            <span className="text-content-secondary">
              No AI key yet. Rules-only Auto Takeoff works without one. To read custom tags and scanned sheets, add your key in{' '}
              <a href="/settings" className="text-oe-blue underline" target="_blank" rel="noreferrer">
                Settings &gt; AI
              </a>{' '}
              <button type="button" className="text-oe-blue underline" onClick={refreshStatus}>
                (re-check)
              </button>
            </span>
          )}
        </div>
      </div>

      <div className="space-y-1">
        <p className="font-semibold text-content-secondary">What to take off</p>
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
        })}
      </div>

      <div className="space-y-1">
        <p className="font-semibold text-content-secondary">Pages</p>
        <div className="flex gap-1">
          {(['page', 'all', 'range'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setPrefs((p) => ({ ...p, scope: s }))}
              className={`flex-1 rounded border px-2 py-1 ${prefs.scope === s ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
            >
              {s === 'page' ? `This sheet (${currentPage})` : s === 'all' ? `All ${pageCount}` : 'Pages…'}
            </button>
          ))}
        </div>
        {prefs.scope === 'range' && (
          <input
            type="text"
            value={prefs.range}
            onChange={(e) => setPrefs((p) => ({ ...p, range: e.target.value }))}
            placeholder="e.g. 17-24, 26"
            className="w-full rounded border border-border bg-surface-primary px-2 py-1"
          />
        )}
      </div>

      <div className="space-y-1">
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.useAi} onChange={(e) => setPrefs((p) => ({ ...p, useAi: e.target.checked }))} data-testid="auto-use-ai" />
          <span>
            <b>Use AI</b> <span className="text-content-tertiary">(your key) — reads custom truss / wall tags and scanned sheets</span>
          </span>
        </label>
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.calibrate} onChange={(e) => setPrefs((p) => ({ ...p, calibrate: e.target.checked }))} />
          <span>Set the sheet scale from the drawing when a page is not calibrated</span>
        </label>
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.removeStale} onChange={(e) => setPrefs((p) => ({ ...p, removeStale: e.target.checked }))} />
          <span>Replace auto markups no longer found <span className="text-content-tertiary">(markups you edited are always kept)</span></span>
        </label>
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.details} onChange={(e) => setPrefs((p) => ({ ...p, details: e.target.checked }))} />
          <span>Include detail sheets <span className="text-content-tertiary">(scales larger than 1/2&quot; = 1&apos;-0&quot;)</span></span>
        </label>
      </div>

      <div className="rounded-lg border border-border p-2 space-y-1.5">
        <p className="font-semibold text-content-secondary flex items-center gap-1">
          <Paintbrush size={12} /> Markup look
        </p>
        <label className="flex items-center gap-2">
          <span className="w-16 text-content-secondary">Line weight</span>
          <input type="range" min={0.5} max={8} step={0.5} value={prefs.style.width} onChange={(e) => setStyle({ width: Number(e.target.value) })} className="flex-1" />
          <span className="w-8 text-right">{prefs.style.width}</span>
        </label>
        <label className="flex items-center gap-2">
          <span className="w-16 text-content-secondary">Opacity</span>
          <input type="range" min={0.1} max={1} step={0.05} value={prefs.style.alpha} onChange={(e) => setStyle({ alpha: Number(e.target.value) })} className="flex-1" />
          <span className="w-8 text-right">{Math.round(prefs.style.alpha * 100)}%</span>
        </label>
        <div className="flex items-center gap-1 flex-wrap">
          <span className="w-16 text-content-secondary">Label</span>
          {LABEL_MODES.map((l) => (
            <button
              key={l.key}
              type="button"
              onClick={() => setStyle({ labelMode: l.key })}
              className={`rounded border px-1.5 py-0.5 ${prefs.style.labelMode === l.key ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-secondary hover:bg-surface-secondary'}`}
            >
              {l.label}
            </button>
          ))}
        </div>
        <p className="text-content-tertiary leading-snug">
          Changes apply live to the auto markups on the sheet. A thin, see-through line lets you check the framing line underneath is covered.
        </p>
        {anyAuto && (
          <button
            type="button"
            className="w-full rounded border border-border px-2 py-1 hover:bg-surface-secondary"
            onClick={() => {
              const n = onRestyle(prefs.style, new Set(prefs.cats));
              setInfo(n ? `Restyled ${n} auto markups.` : 'No auto markups in the ticked categories.');
            }}
          >
            Re-apply to every auto markup in the ticked categories
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={() => void run()}
        disabled={running || status?.available === false}
        className="w-full flex items-center justify-center gap-1.5 rounded-md bg-oe-blue px-3 py-2 text-[12px] font-semibold text-white hover:bg-oe-blue/90 disabled:opacity-50"
        data-testid="auto-run"
      >
        {running ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
        {running ? 'Reading the drawing…' : anyAuto ? 'Re-run Auto Takeoff' : 'Run Auto Takeoff'}
      </button>

      {error && <p className="rounded border border-red-300 bg-red-50 px-2 py-1 text-red-700 dark:bg-red-950/30 dark:text-red-300">{error}</p>}
      {info && <p className="text-content-secondary">{info}</p>}

      {last && (
        <div className="rounded-lg border border-border p-2 space-y-1.5" data-testid="auto-result">
          <p className="flex items-center gap-1 font-semibold text-content-primary">
            <CheckCircle2 size={12} className="text-emerald-600" /> {describeMerge(last.summary)}
          </p>
          {totals && (
            <p className="text-content-secondary">
              Found:{' '}
              {AUTO_CATEGORIES.filter((c) => (totals[c.key] ?? 0) > 0)
                .map((c) => `${totals[c.key]} ${c.label.toLowerCase()}`)
                .join(', ') || 'nothing on these pages'}
            </p>
          )}
          {last.summary.rejected > 0 && (
            <p className="text-content-secondary" data-testid="auto-rejected-note">
              {last.summary.rejected} were skipped because you deleted them earlier.{' '}
              <button
                type="button"
                className="font-semibold text-oe-blue underline"
                onClick={() => {
                  onForgetRejected();
                  void run();
                }}
                data-testid="auto-bring-back"
              >
                Bring them back and re-run
              </button>
            </p>
          )}
          {last.res.read && (
            <p className="text-content-secondary" data-testid="auto-read-first">
              Read first: {last.res.read.sheets_read} sheet{last.res.read.sheets_read === 1 ? '' : 's'} of schedules and notes
              {last.res.read.wall_types ? ` · ${last.res.read.wall_types} wall types` : ''}
              {last.res.read.header_jamb_types ? ` · ${last.res.read.header_jamb_types} header/jamb types` : ''}
              {last.res.read.column_marks ? ` · ${last.res.read.column_marks} column marks` : ''}
              {last.res.read.schedule_rows ? ` · ${last.res.read.schedule_rows} schedule rows` : ''}
            </p>
          )}
          {last.summary.calibrated.length > 0 && (
            <p className="text-content-secondary">
              Scale set from the drawing on page{last.summary.calibrated.length > 1 ? 's' : ''} {last.summary.calibrated.join(', ')} — check one known dimension.
            </p>
          )}
          {last.res.ai?.requested && (
            <p className={last.res.ai.used ? 'text-emerald-700' : 'text-amber-600'}>
              {last.res.ai.used ? `AI read page${last.res.ai.pages.length > 1 ? 's' : ''} ${last.res.ai.pages.join(', ')}.` : 'AI was not used.'}{' '}
              {last.res.ai.message ?? ''}
            </p>
          )}
          {!last.res.ai?.requested && last.res.ai?.message && <p className="text-amber-600">{last.res.ai.message}</p>}
          {last.res.pages.length > 1 && (
            <div className="max-h-40 overflow-auto space-y-0.5">
              {last.res.pages
                .filter((p) => p.items.length > 0)
                .map((p) => (
                  <button
                    key={p.page}
                    type="button"
                    onClick={() => onJumpToPage(p.page)}
                    className={`w-full flex items-center justify-between rounded px-1.5 py-0.5 text-left hover:bg-surface-secondary ${p.page === currentPage ? 'bg-oe-blue/10' : ''}`}
                  >
                    <span>Page {p.page}</span>
                    <span className="text-content-tertiary">
                      {Object.entries(p.counts)
                        .map(([k, v]) => `${v} ${k}`)
                        .join(' · ')}
                    </span>
                  </button>
                ))}
            </div>
          )}
          {notes.slice(0, 4).map((n) => (
            <p key={n.page} className="flex gap-1 text-amber-700">
              <Info size={12} className="shrink-0 mt-0.5" /> Page {n.page}: {n.text}
            </p>
          ))}
        </div>
      )}

      {anyAuto && (
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={highlightAll} onChange={(e) => onToggleHighlight(e.target.checked)} data-testid="auto-highlight-all" />
          <span>
            Highlight profile text on the sheet <span className="text-content-tertiary">(selected ones always light up)</span>
          </span>
        </label>
      )}
      {anyAuto && (
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showColumns} onChange={(e) => onToggleColumns(e.target.checked)} data-testid="auto-show-columns" />
          <span>
            Show column markers on the sheet <span className="text-content-tertiary">(off: only the profile highlight, like Revu)</span>
          </span>
        </label>
      )}
      {anyAuto && <AutoTakeoffList {...list} currentPage={currentPage} />}

      {anyAuto && (
        <div className="rounded-lg border border-border p-2 space-y-1.5">
          <p className="font-semibold text-content-secondary">Clear auto markups</p>
          {stats.edited > 0 && <p className="text-content-tertiary">{stats.edited} auto markup(s) edited by you — re-runs keep them as they are.</p>}
          <div className="flex gap-1">
            <button
              type="button"
              className="flex-1 flex items-center justify-center gap-1 rounded border border-border px-1.5 py-1 hover:bg-surface-secondary"
              onClick={() => {
                const n = onRemove('page', true, new Set(prefs.cats));
                setInfo(`Removed ${n} unedited auto markups on this sheet.`);
              }}
            >
              <Eraser size={12} /> Clear this sheet
            </button>
            <button
              type="button"
              className="flex-1 flex items-center justify-center gap-1 rounded border border-border px-1.5 py-1 hover:bg-surface-secondary"
              onClick={() => {
                const n = onRemove('all', true, new Set(prefs.cats));
                setInfo(`Removed ${n} unedited auto markups in the document.`);
              }}
            >
              <Eraser size={12} /> Clear all sheets
            </button>
          </div>
          <p className="text-content-tertiary">Clearing keeps markups you edited. Only the ticked categories are cleared.</p>
          {rejectedCount > 0 && (
            <p className="text-content-tertiary">
              {rejectedCount} markup(s) you deleted stay deleted on re-runs.{' '}
              <button
                type="button"
                className="text-oe-blue underline"
                onClick={() => {
                  onForgetRejected();
                  setInfo('Deleted markups can be placed again by the next run.');
                }}
              >
                Allow them again
              </button>
            </p>
          )}
        </div>
      )}

      <div className="rounded-lg border border-dashed border-border p-2 text-content-secondary space-y-0.5">
        <p className="font-semibold">Editing auto markups</p>
        <p>Drag a line end to extend or shorten it, drag the line to move it.</p>
        <p>
          <kbd>←↑→↓</kbd> move · <kbd>Shift</kbd> ×10 · <kbd>Alt</kbd>+<kbd>→</kbd>/<kbd>↑</kbd> longer · <kbd>Alt</kbd>+<kbd>←</kbd>/<kbd>↓</kbd> shorter
          (at the end you clicked, otherwise both ends)
        </p>
      </div>
    </div>
  );
}
