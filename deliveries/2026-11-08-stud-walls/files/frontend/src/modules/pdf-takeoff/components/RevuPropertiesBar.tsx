// OE-DELIVERY: 2026-11-02-revu-properties-bar
/**
 * Revu Properties toolbar: one row above the drawing that edits whatever is
 * selected (every selected markup at once) or, with nothing selected, the
 * armed tool's defaults for the next markup. Label, colour, line type,
 * thickness, fill, opacity %, length and area units, caption pick list,
 * caption font / size / colour / style, and the selection totals.
 */
import { useEffect, useRef, useState } from 'react';
import ColorPicklist from './ColorPicklist';
import clsx from 'clsx';
import { Bold, Briefcase, ChevronDown, Italic, Underline } from 'lucide-react';
import {
  AREA_DISP_UNITS,
  CAPTION_LABELS,
  DISP_UNITS,
  captionOptionsFor,
  hasAreaUnit,
  hasLengthUnit,
  type AreaDispUnit,
  type CaptionKey,
  type DispUnit,
} from '../../../features/takeoff/lib/takeoff-revu-props';
import { FT_TO_M, formatFeetInches, parseFeetInches } from '../data/auto-takeoff';

export interface PropsBarValue {
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  lineStyle?: 'solid' | 'dashed' | 'dotted' | 'dashdot';
  fillAlpha?: number;
  strokeAlpha?: number;
  dispUnit?: DispUnit;
  dispAreaUnit?: AreaDispUnit;
  captions?: CaptionKey[];
  labelFont?: string;
  labelBold?: boolean;
  labelItalic?: boolean;
  labelUnderline?: boolean;
  labelTextSize?: number;
  labelNameColor?: string;
  labelMode?: 'all' | 'value' | 'name' | 'none';
  /** Wall height in metres (linear measurements; drives Wall Area). */
  wallHeight?: number;
}

export type PropsBarPatch = Partial<PropsBarValue> & {
  labelMaterialSize?: number;
  labelDimSize?: number;
  labelMaterialColor?: string;
  labelDimColor?: string;
};

interface Props {
  /** 'selection' edits the selected markups, 'tool' the armed tool's defaults. */
  mode: 'selection' | 'tool' | 'none';
  /** Markup type the bar is showing (first selected, or the armed tool). */
  type: string;
  /** Human name of what is being edited ("3 markups", "Length tool"). */
  title: string;
  value: PropsBarValue;
  /** Subject (the markup's category, e.g. "Beam") and Label (the text shown
   *  on the sheet, e.g. "W12X26"), as in Revu. Undefined hides the field. */
  subject?: string;
  onSubject?: (v: string) => void;
  label?: string;
  onLabel?: (v: string) => void;
  /** Wall height edit, metres (undefined clears). */
  onWallHeight?: (m: number | undefined) => void;
  onPatch: (patch: PropsBarPatch) => void;
  /** Revu "Add to Tool Chest" for the selection. */
  onAddToChest?: () => void;
  /** Lay out framing across the selected outline (OE-DELIVERY 2026-11-04-framing-layout). */
  onLayoutFraming?: () => void;
  /** Selection totals, already formatted. */
  totals?: string;
  /** Fallbacks shown when the markup has no override. */
  defaults: { color: string; font: string; size: number; textColor: string; bold: boolean; italic: boolean };
}

/** Text field that commits on Enter / blur, Esc reverts. */
function TextField({ value, onCommit, placeholder, width, testId }: { value: string; onCommit: (v: string) => void; placeholder: string; width: string; testId: string }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <input
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => { if (draft !== value) onCommit(draft); }}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') setDraft(value);
      }}
      className={clsx(sel, width)}
      placeholder={placeholder}
      data-testid={testId}
    />
  );
}

/** Which controls a markup type has (Revu shows only what applies). */
const MEASURE = new Set(['distance', 'polyline', 'area', 'volume', 'count', 'perimeter', 'diameter', 'radiusCenter', 'radius3Point', 'angle', 'arc', 'polygonCutout', 'ellipseCutout', 'dynamicFill', 'rectarea']);
const NO_STROKE = new Set(['text', 'stamp', 'highlight', 'count']);
// Text boxes style their text from the Text Box bar on the sheet (OE-DELIVERY 2026-11-07-text-box).
const NO_TEXT = new Set(['highlight', 'text']);
const WALLABLE = new Set(['distance', 'polyline']);

const AREAL = new Set(['area', 'rectarea', 'volume', 'count', 'rectangle', 'highlight', 'polygon', 'ellipse', 'cloud', 'dynamicFill', 'polygonCutout', 'ellipseCutout', 'callout']);
const FONTS = ['Arial', 'Helvetica', 'Calibri', 'Segoe UI', 'Tahoma', 'Verdana', 'Times New Roman', 'Georgia', 'Courier New', 'Consolas'];
const WIDTHS = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20];
const SIZES = [6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 40, 48, 64, 72];

const sel = 'h-6 rounded border border-border bg-surface-primary px-1 text-[11px] text-content-primary focus:border-oe-blue focus:outline-none disabled:opacity-40';
const lab = 'select-none text-[10px] font-medium text-content-tertiary';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex shrink-0 items-center gap-1">
      <span className={lab}>{label}</span>
      {children}
    </label>
  );
}

function Sep() {
  return <span className="mx-0.5 h-5 w-px shrink-0 bg-border" aria-hidden="true" />;
}

/** Caption pick list: tick what the caption shows; closes on outside click. */
function CaptionPicker({
  options,
  value,
  labelMode,
  onChange,
  disabled,
}: {
  options: CaptionKey[];
  value: CaptionKey[] | undefined;
  labelMode?: 'all' | 'value' | 'name' | 'none';
  onChange: (v: CaptionKey[] | undefined) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', esc);
    };
  }, [open]);
  // With no pick list yet, tick what the markup shows today.
  const primary = options.filter((o) => o !== 'label').slice(0, 1);
  const current =
    value ??
    (labelMode === 'none' ? [] : labelMode === 'name' ? ['label' as CaptionKey] : labelMode === 'value' ? primary : (['label', ...primary] as CaptionKey[]));
  const summary = value ? (value.length ? value.map((c) => CAPTION_LABELS[c]).join(', ') : 'None') : 'Default';
  return (
    <div className="relative shrink-0" ref={ref}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={clsx(sel, 'inline-flex max-w-[150px] items-center gap-1')}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={summary}
        data-testid="props-caption"
      >
        <span className="truncate">{summary}</span>
        <ChevronDown size={11} className="shrink-0" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-44 rounded-md border border-border bg-surface-elevated p-1 shadow-lg" role="listbox" data-testid="props-caption-list">
          {options.map((c) => {
            const on = current.includes(c);
            return (
              <label key={c} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-[11px] hover:bg-surface-secondary">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => {
                    const next = on ? current.filter((x) => x !== c) : [...current, c];
                    onChange(options.filter((o) => next.includes(o)));
                  }}
                  data-testid={`props-caption-${c}`}
                />
                {CAPTION_LABELS[c]}
              </label>
            );
          })}
          <div className="mt-1 flex justify-between border-t border-border px-1 pt-1">
            <button type="button" className="text-[10px] text-content-tertiary underline hover:text-content-primary" onClick={() => { onChange(undefined); setOpen(false); }}>
              Default
            </button>
            <button type="button" className="rounded bg-oe-blue px-2 py-0.5 text-[10px] font-semibold text-white" onClick={() => setOpen(false)} data-testid="props-caption-close">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function RevuPropertiesBar({ mode, type, title, value, subject, onSubject, label, onLabel, onWallHeight, onPatch, totals, defaults, onAddToChest, onLayoutFraming }: Props) {
  const off = mode === 'none';
  const areal = AREAL.has(type) && type !== 'count';
  const measure = MEASURE.has(type);
  const stroke = !NO_STROKE.has(type);
  const textCtl = !NO_TEXT.has(type);
  const opacity = Math.round(((areal ? value.fillAlpha : value.strokeAlpha) ?? (areal ? 0.3 : 1)) * 100);
  const toggle = (k: 'labelBold' | 'labelItalic' | 'labelUnderline', fallback: boolean) => onPatch({ [k]: !(value[k] ?? fallback) });
  const metricHeight = value.dispUnit === 'mm' || value.dispUnit === 'cm' || value.dispUnit === 'm' || value.dispUnit === 'km';
  const heightText = value.wallHeight
    ? metricHeight
      ? `${+(value.wallHeight).toFixed(3)} m`
      : formatFeetInches(value.wallHeight / FT_TO_M)
    : '';
  const commitHeight = (txt: string) => {
    const t = txt.trim();
    if (!t) return onWallHeight?.(undefined);
    const metric = t.match(/^(\d+(?:\.\d+)?)\s*(mm|cm|m)$/i);
    if (metric) {
      const v = Number(metric[1]) * ({ mm: 0.001, cm: 0.01, m: 1 } as Record<string, number>)[metric[2]!.toLowerCase()]!;
      if (v > 0) onWallHeight?.(v);
      return;
    }
    const ft = parseFeetInches(/['"]/.test(t) || !metricHeight ? t : `${t}'`);
    if (ft && ft > 0) onWallHeight?.(ft * FT_TO_M);
  };
  return (
    <div
      className={clsx(
        'flex min-h-[30px] flex-wrap items-center gap-x-1.5 gap-y-1 rounded-md border border-border bg-surface-secondary/60 px-2 py-0.5',
        off && 'opacity-70',
      )}
      role="toolbar"
      aria-label="Properties"
      data-testid="revu-properties-bar"
      data-mode={mode}
    >
      {/* Revu-style tab naming what is being edited. */}
      <span
        className="-my-0.5 shrink-0 select-none rounded-t-md border-b-2 border-oe-blue bg-surface-primary px-2 pt-1.5 text-[11px] font-bold text-oe-blue"
        title={title}
        data-testid="props-tab"
      >
        {off ? 'Properties' : title}
      </span>
      {subject !== undefined && (
        <Field label="Subject">
          <TextField value={subject} onCommit={(v) => onSubject?.(v)} placeholder="Subject" width="w-24" testId="props-subject" />
        </Field>
      )}
      {label !== undefined && (
        <Field label="Label">
          <TextField value={label} onCommit={(v) => onLabel?.(v)} placeholder="Label" width="w-28" testId="props-label" />
        </Field>
      )}
      <Sep />
      <Field label="Colour">
        {off ? (
          <input type="color" disabled value={value.color ?? defaults.color} readOnly className="h-6 w-7 rounded border border-border bg-transparent p-0 opacity-40" data-testid="props-color" />
        ) : (
          // Revu-style colour picklist (OE-DELIVERY 2026-11-08-stud-walls).
          <ColorPicklist value={value.color ?? defaults.color} onChange={(c) => c && onPatch({ color: c })} title="Colour" testId="props-color" size={22} />
        )}
      </Field>
      {stroke && (<>
      <Field label="Line">
        <select disabled={off} value={value.lineStyle ?? 'solid'} onChange={(e) => onPatch({ lineStyle: e.target.value as PropsBarValue['lineStyle'] })} className={sel} data-testid="props-linestyle">
          <option value="solid">━━ Solid</option>
          <option value="dashed">╍╍ Dashed</option>
          <option value="dotted">┈┈ Dotted</option>
          <option value="dashdot">━·━ Dash-dot</option>
        </select>
      </Field>
      <Field label="Width">
        <select disabled={off} value={String(value.strokeWidth ?? 2)} onChange={(e) => onPatch({ strokeWidth: Number(e.target.value) })} className={sel} data-testid="props-width">
          {Array.from(new Set([...WIDTHS, value.strokeWidth ?? 2])).sort((a, b) => a - b).map((w) => (
            <option key={w} value={w}>{w} px</option>
          ))}
        </select>
      </Field>
      </>)}
      {areal && (
        <Field label="Fill">
          {off ? (
            <input type="color" disabled value={value.fillColor ?? value.color ?? defaults.color} readOnly className="h-6 w-7 rounded border border-border bg-transparent p-0 opacity-40" data-testid="props-fill" />
          ) : (
            <ColorPicklist value={value.fillColor ?? value.color ?? defaults.color} onChange={(c) => c && onPatch({ fillColor: c })} title="Fill" testId="props-fill" size={22} />
          )}
        </Field>
      )}
      <Field label="Opacity">
        <input
          type="number"
          min={0}
          max={100}
          step={5}
          disabled={off}
          value={opacity}
          onChange={(e) => {
            const v = Math.max(0, Math.min(100, Number(e.target.value) || 0)) / 100;
            onPatch(areal ? { fillAlpha: v } : { strokeAlpha: v });
          }}
          onKeyDown={(e) => e.stopPropagation()}
          className={clsx(sel, 'w-12 text-right')}
          data-testid="props-opacity"
        />
        <span className={lab}>%</span>
      </Field>
      <Sep />
      {measure && type !== 'angle' && type !== 'count' && hasLengthUnit(type) && (
        <Field label="Units">
          <select disabled={off} value={value.dispUnit ?? ''} onChange={(e) => onPatch({ dispUnit: (e.target.value || undefined) as DispUnit | undefined })} className={sel} data-testid="props-unit">
            <option value="">Default</option>
            {DISP_UNITS.map((u) => (
              <option key={u.id} value={u.id}>{u.label}</option>
            ))}
          </select>
        </Field>
      )}
      {measure && hasAreaUnit(type) && (WALLABLE.has(type) ? Boolean(value.wallHeight) : true) && (
        <Field label="Area">
          <select disabled={off} value={value.dispAreaUnit ?? ''} onChange={(e) => onPatch({ dispAreaUnit: (e.target.value || undefined) as AreaDispUnit | undefined })} className={sel} data-testid="props-area-unit">
            <option value="">Default</option>
            {AREA_DISP_UNITS.map((u) => (
              <option key={u.id} value={u.id}>{u.label}</option>
            ))}
          </select>
        </Field>
      )}
      {WALLABLE.has(type) && onWallHeight && (
        <Field label="Height">
          <TextField value={heightText} onCommit={commitHeight} placeholder={metricHeight ? '2.7 m' : "9'-0\""} width="w-20" testId="props-height" />
        </Field>
      )}
      {measure && (
      <Field label="Caption">
        <CaptionPicker disabled={off} options={captionOptionsFor(type)} value={value.captions} labelMode={value.labelMode} onChange={(c) => onPatch({ captions: c })} />
      </Field>
      )}
      {textCtl && (<>
      <Sep />
      <Field label="Font">
        <select disabled={off} value={value.labelFont ?? defaults.font} onChange={(e) => onPatch({ labelFont: e.target.value })} className={clsx(sel, 'w-24')} data-testid="props-font">
          {Array.from(new Set([...FONTS, value.labelFont ?? defaults.font])).map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
      </Field>
      <Field label="Size">
        <select
          disabled={off}
          value={String(Math.round((value.labelTextSize ?? defaults.size) * 2) / 2)}
          onChange={(e) => {
            const s = Number(e.target.value);
            onPatch({ labelTextSize: s, labelMaterialSize: s, labelDimSize: s });
          }}
          className={sel}
          data-testid="props-text-size"
        >
          {Array.from(new Set([...SIZES, Math.round((value.labelTextSize ?? defaults.size) * 2) / 2])).sort((a, b) => a - b).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </Field>
      <input
        type="color"
        disabled={off}
        value={value.labelNameColor ?? value.color ?? defaults.textColor}
        onChange={(e) => onPatch({ labelNameColor: e.target.value, labelMaterialColor: e.target.value, labelDimColor: e.target.value })}
        className="h-6 w-7 shrink-0 cursor-pointer rounded border border-border bg-transparent p-0 disabled:opacity-40"
        title="Text colour"
        aria-label="Text colour"
        data-testid="props-text-color"
      />
      <div className="flex shrink-0 items-center rounded border border-border bg-surface-primary">
        {([
          ['labelBold', Bold, 'Bold', defaults.bold],
          ['labelItalic', Italic, 'Italic', defaults.italic],
          ['labelUnderline', Underline, 'Underline', false],
        ] as const).map(([k, Icon, name, fb]) => {
          const on = value[k] ?? fb;
          return (
            <button
              key={k}
              type="button"
              disabled={off}
              onClick={() => toggle(k, fb)}
              aria-pressed={on}
              title={name}
              aria-label={name}
              className={clsx('flex h-6 w-6 items-center justify-center disabled:opacity-40', on ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-tertiary')}
              data-testid={`props-${name.toLowerCase()}`}
            >
              <Icon size={12} />
            </button>
          );
        })}
      </div>
      </>)}
      {totals && (
        <>
          <Sep />
          <span className="shrink-0 whitespace-nowrap text-[11px] font-semibold tabular-nums text-content-primary" data-testid="props-totals">
            <span className={lab}>Totals </span>
            {totals}
          </span>
        </>
      )}
      {onLayoutFraming && mode === 'selection' && (type === 'area' || type === 'polygon') && (
        <button
          type="button"
          onClick={onLayoutFraming}
          className="flex h-6 shrink-0 items-center gap-1 rounded border border-oe-blue/50 bg-oe-blue/5 px-2 text-[10px] font-semibold text-oe-blue hover:bg-oe-blue/10"
          title="Place trusses / joists / hat channels across this outline at a spacing"
          data-testid="props-layout-framing"
        >
          Lay out framing
        </button>
      )}
      {onAddToChest && mode === 'selection' && (
        <button
          type="button"
          onClick={onAddToChest}
          className="ml-auto flex h-6 shrink-0 items-center gap-1 rounded border border-border bg-surface-primary px-2 text-[10px] font-semibold text-content-secondary hover:border-oe-blue hover:text-oe-blue"
          title="Add the selected markups to the Tool Chest"
          data-testid="props-add-to-chest"
        >
          <Briefcase size={11} /> Add to Tool Chest
        </button>
      )}
      {off && <span className="ml-1 shrink-0 text-[11px] text-content-tertiary">Select a markup or pick a tool to change its properties</span>}
    </div>
  );
}
