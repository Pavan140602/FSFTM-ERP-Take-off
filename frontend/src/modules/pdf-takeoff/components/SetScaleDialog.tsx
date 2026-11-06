// OE-DELIVERY: 2026-11-12-revu-ui (Set Scale / Calibrate, Revu layout - update 14)
/**
 * Revu's "Apply Scale to Pages" / "Calibrate" window:
 *   Pages:     [Current (4)            v]   e.g. 3-5 or 1,5
 *   Scale:     (o) Preset (o) Custom          [Recalibrate] [+ Add Preset]
 *              [0.125   ] [in      v]  =  [1'-0"   ] [ft' in" v]
 *   Precision: [1/4                    v]
 *                                             [Apply Scale] [Cancel]
 * Unit lists on both sides: in, ft, ft' in", in", yd, mi, mm, cm, m, km.
 * After a two-click calibration it opens titled "Calibrate", on Custom,
 * with the measured paper length filled in.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import { DRAWING_SCALE_PRESETS, sameScale, type ScaleConfig } from '../data/scale-helpers';
import { formatFtIn, parseLengthInches, type LengthUnit } from '../data/length-input';

const PT_PER_IN = 72;
const M_PER_IN = 0.0254;

/** Revu's unit list (both sides of the custom scale). */
export const SCALE_UNITS = [
  { id: 'in', label: 'in', perIn: 1 },
  { id: 'ft', label: 'ft', perIn: 12 },
  { id: 'ftin', label: `ft' in"`, perIn: 12 },
  { id: 'inch', label: 'in"', perIn: 1 },
  { id: 'yd', label: 'yd', perIn: 36 },
  { id: 'mi', label: 'mi', perIn: 63360 },
  { id: 'mm', label: 'mm', perIn: 1 / 25.4 },
  { id: 'cm', label: 'cm', perIn: 1 / 2.54 },
  { id: 'm', label: 'm', perIn: 1 / M_PER_IN },
  { id: 'km', label: 'km', perIn: 1000 / M_PER_IN },
] as const;
export type ScaleUnitId = (typeof SCALE_UNITS)[number]['id'];

/** A typed value in the chosen unit -> inches. Marks typed in the text
 *  (', ", ft, in, mm, m ...) win over the unit list, like Revu. */
export function unitTextToInches(text: string, unit: ScaleUnitId): number | null {
  const t = (text || '').trim();
  if (!t) return null;
  const u = SCALE_UNITS.find((x) => x.id === unit)!;
  if (/^\d*\.?\d+$/.test(t) || /^\d+\s*\/\s*\d+$/.test(t) || /^\d+[\s-]+\d+\s*\/\s*\d+$/.test(t)) {
    // A bare number (or fraction) is in the chosen unit.
    const base: LengthUnit = 'in';
    const v = parseLengthInches(t, base);
    return v === null ? null : v * u.perIn;
  }
  const fallback: LengthUnit = unit === 'ftin' || unit === 'ft' ? 'ft' : unit === 'mm' || unit === 'cm' || unit === 'm' || unit === 'yd' ? unit : 'in';
  return parseLengthInches(t, fallback);
}

/** "1-3, 5, 7-8" -> pages within 1..total (sorted, unique). */
export function parsePages(text: string, total: number): number[] {
  const out = new Set<number>();
  for (const part of text.split(/[,;\s]+/)) {
    const m = part.match(/^(\d+)(?:-(\d+))?$/);
    if (!m) continue;
    const a = Number(m[1]);
    const b = m[2] ? Number(m[2]) : a;
    for (let p = Math.max(1, Math.min(a, b)); p <= Math.min(total, Math.max(a, b)); p++) out.add(p);
  }
  return [...out].sort((x, y) => x - y);
}

/** Scale from inches on paper = inches in reality. */
export function customScaleInches(paperIn: number, realIn: number): ScaleConfig | null {
  if (!(paperIn > 0) || !(realIn > 0)) return null;
  return { pixelsPerUnit: (PT_PER_IN * paperIn) / (realIn * M_PER_IN), unitLabel: 'm' };
}

function fmtIn(x: number): string {
  const f = [1, 2, 4, 8, 16, 32, 64].find((d) => Math.abs(x * d - Math.round(x * d)) < 1e-6);
  if (!f) return `${+x.toFixed(4)}"`;
  if (f === 1) return `${x}"`;
  const w = Math.floor(x);
  const n = Math.round((x - w) * f);
  return `${w ? `${w} ` : ''}${n}/${f}"`;
}

interface Props {
  open: boolean;
  currentPage: number;
  totalPages: number;
  imperial: boolean;
  current?: ScaleConfig;
  precision: number;
  /** Why it opened (e.g. "Sheet 2 has no scale yet"). */
  reason?: string;
  /** Calibrate mode: the two clicks measured this many inches on paper. */
  calibratedPaperIn?: number;
  /** Pages picked before a calibration (kept for the Calibrate window). */
  initialPages?: number[];
  /** The user's saved custom scales (listed under Preset). */
  extraPresets?: { label: string; scale: ScaleConfig }[];
  onAddPreset?: (label: string, scale: ScaleConfig) => void;
  onApply: (r: { pages: number[]; scale: ScaleConfig; label: string; precision: number }) => void;
  onCalibrate: (pages: number[], precision: number) => void;
  onCancel: () => void;
}

const DENOMS = [1, 2, 4, 8, 16, 32, 64];

export function SetScaleDialog({
  open, currentPage, totalPages, imperial, current, precision, reason, calibratedPaperIn, initialPages,
  extraPresets = [], onAddPreset, onApply, onCalibrate, onCancel,
}: Props) {
  const [pagesMode, setPagesMode] = useState<'current' | 'all' | 'custom'>('current');
  const [range, setRange] = useState('');
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');
  const [presetLabel, setPresetLabel] = useState('');
  const [paper, setPaper] = useState('0.125');
  const [pu, setPu] = useState<ScaleUnitId>('in');
  const [real, setReal] = useState(`1'-0"`);
  const [ru, setRu] = useState<ScaleUnitId>('ftin');
  const [prec, setPrec] = useState(precision);
  const [pagesMenu, setPagesMenu] = useState(false);
  const [added, setAdded] = useState('');
  const wasOpen = useRef(false);
  const calibrating = calibratedPaperIn !== undefined && calibratedPaperIn > 0;

  const presets = useMemo(
    () => [
      ...DRAWING_SCALE_PRESETS.filter((p) => (imperial ? p.group !== 'metric' : true)),
      ...extraPresets.map((x) => ({ label: x.label, scale: x.scale, group: 'saved' as const })),
    ],
    [imperial, extraPresets],
  );

  useEffect(() => {
    if (!open) {
      wasOpen.current = false;
      return;
    }
    if (wasOpen.current) return;
    wasOpen.current = true;
    const match = current ? presets.find((p) => sameScale(p.scale, current)) : undefined;
    setPresetLabel(match?.label ?? (imperial ? '1/8" = 1\'-0"' : '1:100'));
    setPagesMenu(false);
    setAdded('');
    setPrec(precision);
    // Pages: what was picked before a calibration, else the current page.
    const ip = initialPages ?? [];
    if (ip.length > 1 && ip.length === totalPages) setPagesMode('all');
    else if (ip.length > 1 || (ip.length === 1 && ip[0] !== currentPage)) {
      setPagesMode('custom');
      setRange(ip.join(', '));
    } else {
      setPagesMode('current');
      setRange(String(currentPage));
    }
    if (calibrating) {
      // Calibrate: the measured paper length = the length typed in.
      setMode('custom');
      setPaper(String(+calibratedPaperIn!.toFixed(6)));
      setPu('in');
      setReal(imperial ? `1'-0"` : '1');
      setRu(imperial ? 'ftin' : 'm');
    } else {
      setMode('preset');
      setPaper(imperial ? '0.125' : '1');
      setPu(imperial ? 'in' : 'cm');
      setReal(imperial ? `1'-0"` : '1');
      setRu(imperial ? 'ftin' : 'm');
    }
  }, [open, current, presets, imperial, currentPage, precision, calibrating, calibratedPaperIn, initialPages, totalPages]);

  if (!open) return null;

  const pagesText = pagesMode === 'current' ? `Current (${currentPage})` : pagesMode === 'all' ? `All Pages (1-${totalPages})` : range;
  const pages =
    pagesMode === 'current'
      ? [currentPage]
      : pagesMode === 'all'
        ? Array.from({ length: totalPages }, (_, i) => i + 1)
        : parsePages(range, totalPages);
  const preset = presets.find((p) => p.label === presetLabel);
  const paperIn = unitTextToInches(paper, pu);
  const realIn = unitTextToInches(real, ru);
  const custom = paperIn && realIn ? customScaleInches(paperIn, realIn) : null;
  const scale = mode === 'preset' ? preset?.scale : custom;
  const customLabel = paperIn && realIn ? `${fmtIn(paperIn)} = ${formatFtIn(realIn)}` : '';
  const label = mode === 'preset' ? presetLabel : customLabel;
  const ok = Boolean(scale) && pages.length > 0;
  const sel = 'h-7 rounded border border-border bg-surface-primary px-1.5 text-xs';
  const fieldLabel = 'w-[70px] shrink-0 pt-1.5 text-right text-xs text-content-secondary';
  const unitSelect = (value: ScaleUnitId, onChange: (u: ScaleUnitId) => void, testId: string) => (
    <select value={value} onChange={(e) => onChange(e.target.value as ScaleUnitId)} className={`${sel} w-[92px]`} data-testid={testId}>
      {SCALE_UNITS.map((u) => <option key={u.id} value={u.id}>{u.label}</option>)}
    </select>
  );

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30" onMouseDown={onCancel} data-testid="set-scale-dialog" data-calibrating={calibrating ? 'true' : undefined}>
      <div className="w-[520px] max-w-[95vw] overflow-hidden rounded-md border border-border bg-surface-elevated shadow-2xl" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label={calibrating ? 'Calibrate' : 'Apply Scale to Pages'}>
        <div className="flex items-center bg-neutral-900 px-3 py-2 text-white">
          <span className="flex-1 text-[13px]" data-testid="set-scale-title">{calibrating ? 'Calibrate' : 'Apply Scale to Pages'}</span>
          <button type="button" onClick={onCancel} className="rounded p-0.5 text-white/80 hover:bg-white/10" aria-label="Close">
            <X size={15} />
          </button>
        </div>
        <div className="space-y-3 px-5 py-4 text-xs">
          {reason && <div className="rounded bg-amber-50 px-2 py-1.5 text-[11px] text-amber-800" data-testid="set-scale-reason">{reason}</div>}
          {/* Pages */}
          <div className="flex gap-2">
            <span className={fieldLabel}>Pages:</span>
            <div className="relative flex flex-1 flex-col gap-0.5">
              <div className="flex">
                <input
                  value={pagesText}
                  onChange={(e) => { setPagesMode('custom'); setRange(e.target.value); }}
                  onFocus={(e) => e.target.select()}
                  className={`${sel} min-w-0 flex-1 rounded-r-none`}
                  data-testid="set-scale-pages"
                />
                <button type="button" onClick={() => setPagesMenu((v) => !v)} className="h-7 rounded-r border border-l-0 border-border px-1.5 hover:bg-surface-secondary" aria-label="Pages" data-testid="set-scale-pages-menu">
                  <ChevronDown size={13} />
                </button>
              </div>
              {pagesMenu && (
                <div className="absolute left-0 right-0 top-7 z-10 rounded border border-border bg-surface-elevated py-0.5 shadow-lg">
                  {([['current', `Current (${currentPage})`], ['all', `All Pages (1-${totalPages})`]] as const).map(([k, txt]) => (
                    <button key={k} type="button" onClick={() => { setPagesMode(k); setPagesMenu(false); }} className="block w-full px-2 py-1 text-left hover:bg-oe-blue hover:text-white" data-testid={`set-scale-pages-${k}`}>
                      {txt}
                    </button>
                  ))}
                </div>
              )}
              <span className="text-[10px] italic text-content-tertiary">
                e.g. 3-5 or 1,5{pagesMode === 'custom' ? ` - ${pages.length} page${pages.length === 1 ? '' : 's'}` : ''}
              </span>
            </div>
          </div>
          {/* Scale */}
          <div className="flex gap-2">
            <span className={fieldLabel}>Scale:</span>
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <div className="flex h-7 items-center gap-4">
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="set-scale-mode" checked={mode === 'preset'} onChange={() => setMode('preset')} data-testid="set-scale-mode-preset" />
                  Preset
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="set-scale-mode" checked={mode === 'custom'} onChange={() => setMode('custom')} data-testid="set-scale-mode-custom" />
                  Custom
                </label>
                <span className="flex-1" />
                <button
                  type="button"
                  onClick={() => pages.length && onCalibrate(pages, prec)}
                  className="h-7 rounded border border-border px-2.5 hover:bg-surface-secondary"
                  title="Click two points of a known length on the sheet, then type that length"
                  data-testid="set-scale-calibrate"
                >
                  {calibrating || current ? 'Recalibrate' : 'Calibrate'}
                </button>
                {onAddPreset && (
                  <button
                    type="button"
                    disabled={mode !== 'custom' || !custom}
                    onClick={() => {
                      if (!custom || !customLabel) return;
                      onAddPreset(customLabel, custom);
                      setAdded(customLabel);
                    }}
                    className="h-7 rounded border border-border px-2.5 hover:bg-surface-secondary disabled:opacity-40"
                    title="Save this custom scale to the Preset list"
                    data-testid="set-scale-add-preset"
                  >
                    + Add Preset
                  </button>
                )}
              </div>
              {mode === 'preset' ? (
                <select value={presetLabel} onChange={(e) => setPresetLabel(e.target.value)} className={`${sel} w-full`} data-testid="set-scale-preset">
                  {(['architectural', 'civil', 'metric', 'saved'] as const).map((g) => {
                    const list = presets.filter((p) => p.group === g);
                    if (!list.length) return null;
                    return (
                      <optgroup key={g} label={g === 'architectural' ? 'Architectural' : g === 'civil' ? 'Engineering' : g === 'metric' ? 'Metric' : 'Saved'}>
                        {list.map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
                      </optgroup>
                    );
                  })}
                </select>
              ) : (
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5">
                    <input value={paper} onChange={(e) => setPaper(e.target.value)} className={`${sel} min-w-0 flex-1`} title="Length on the paper" data-testid="set-scale-paper" />
                    {unitSelect(pu, setPu, 'set-scale-paper-unit')}
                    <span className="px-0.5 text-content-secondary">=</span>
                    <input value={real} onChange={(e) => setReal(e.target.value)} className={`${sel} min-w-0 flex-1`} title="Real length" data-testid="set-scale-real" autoFocus={calibrating} />
                    {unitSelect(ru, setRu, 'set-scale-real-unit')}
                  </div>
                  <div className={`text-[10px] ${custom ? 'text-content-tertiary' : 'text-semantic-error'}`} data-testid="set-scale-custom-read">
                    {custom
                      ? `${fmtIn(paperIn!)} on paper = ${formatFtIn(realIn!)} (${+realIn!.toFixed(3)} in)${added === customLabel ? ' - saved to presets' : ''}`
                      : `Type lengths like 0.125, 1/8, 12, 12.5, 12', 12'-6", 300 mm`}
                  </div>
                </div>
              )}
            </div>
          </div>
          {/* Precision */}
          <div className="flex gap-2">
            <span className={fieldLabel}>Precision:</span>
            <select value={prec} onChange={(e) => setPrec(Number(e.target.value))} className={`${sel} flex-1`} data-testid="set-scale-precision">
              {DENOMS.map((d) => <option key={d} value={d}>{d === 1 ? '1' : `1/${d}`}</option>)}
            </select>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 pb-4">
          <button
            type="button"
            disabled={!ok}
            onClick={() => scale && onApply({ pages, scale, label, precision: prec })}
            className="min-w-[86px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
            data-testid="set-scale-apply"
          >
            Apply Scale
          </button>
          <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary" data-testid="set-scale-cancel">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
