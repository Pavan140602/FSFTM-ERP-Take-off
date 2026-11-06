// OE-DELIVERY: 2026-11-12-revu-ui (legend properties)
/**
 * Legend Properties, like Revu's properties for a selected legend. Items
 * with ▸ open a child pop-up beside the panel:
 *   Font · Colour · Title ▸ (text, show, size, B/I/U, colour) ·
 *   Columns ▸ (the legend's columns, beside them the Markup list columns
 *   as a picklist - Edit Columns) · Cells ▸ (size, B/I/U, colour) ·
 *   Opacity · Line colour · Legend style ▸ (grid / horizontal / vertical /
 *   outline / none) · Line width (- / +) · Fill · Fill opacity.
 */
import { useState, type ReactNode } from 'react';
import { ArrowDown, ArrowUp, ChevronRight, Minus, Plus, X } from 'lucide-react';
import ColorPicklist from './ColorPicklist';
import { BorderPreview } from './LegendSetupDialog';
import {
  LEGEND_BORDERS,
  LEGEND_DEFAULT_COLUMNS,
  LEGEND_FONTS,
  type LegendSetup,
  type LegendTextStyle,
  legendLook,
} from '../data/legend-setup';

type Child = 'title' | 'columns' | 'cells' | 'style' | null;

interface Props {
  setup: LegendSetup | undefined;
  defaults: { text: string; bg: string; border: LegendSetup['border'] & string };
  columnDefs: { key: string; label: string }[];
  onChange: (patch: Partial<LegendSetup>) => void;
  onClose: () => void;
  /** 'bar' = one horizontal row in the top Properties bar (Revu); child
   *  pop-ups drop down under their item. */
  layout?: 'panel' | 'bar';
}

const btn = 'rounded border border-border px-1.5 py-0.5 text-[11px] hover:bg-surface-secondary';

function Stepper({ value, min, max, step, onChange, testId, suffix }: { value: number; min: number; max: number; step: number; onChange: (v: number) => void; testId: string; suffix?: string }) {
  const clamp = (v: number) => Math.round(Math.min(max, Math.max(min, v)) * 100) / 100;
  return (
    <span className="inline-flex items-center gap-1" data-testid={testId}>
      <button type="button" className={btn} onClick={() => onChange(clamp(value - step))} aria-label="Smaller" data-testid={`${testId}-minus`}>
        <Minus size={10} />
      </button>
      <span className="min-w-[38px] text-center tabular-nums">{value}{suffix ?? ''}</span>
      <button type="button" className={btn} onClick={() => onChange(clamp(value + step))} aria-label="Bigger" data-testid={`${testId}-plus`}>
        <Plus size={10} />
      </button>
    </span>
  );
}

function StyleToggles({ st, onChange, testId }: { st: { bold: boolean; italic: boolean; underline: boolean }; onChange: (p: LegendTextStyle) => void; testId: string }) {
  const t = (k: 'bold' | 'italic' | 'underline', label: ReactNode) => (
    <button
      type="button"
      onClick={() => onChange({ [k]: !st[k] })}
      className={`h-6 w-6 rounded border text-[12px] ${st[k] ? 'border-oe-blue bg-oe-blue/15 text-oe-blue' : 'border-border hover:bg-surface-secondary'}`}
      aria-pressed={st[k]}
      data-testid={`${testId}-${k}`}
    >
      {label}
    </button>
  );
  return (
    <span className="inline-flex gap-1">
      {t('bold', <b>B</b>)}
      {t('italic', <i>I</i>)}
      {t('underline', <u>U</u>)}
    </span>
  );
}

function Row({ label, children, child, open, onOpen, testId }: { label: string; children?: ReactNode; child?: boolean; open?: boolean; onOpen?: () => void; testId: string }) {
  return (
    <div
      className={`flex min-h-[30px] items-center gap-2 border-b border-border/60 px-2.5 py-1 ${child ? 'cursor-pointer hover:bg-surface-secondary' : ''} ${open ? 'bg-oe-blue/10' : ''}`}
      onClick={child ? onOpen : undefined}
      data-testid={testId}
    >
      <span className="w-[86px] shrink-0 text-content-secondary">{label}</span>
      <span className="flex min-w-0 flex-1 items-center justify-end gap-1">{children}</span>
      {child && <ChevronRight size={12} className={open ? 'text-oe-blue' : 'text-content-tertiary'} />}
    </div>
  );
}

export function LegendPropertiesPanel({ setup, defaults, columnDefs, onChange, onClose, layout = 'panel' }: Props) {
  const [child, setChild] = useState<Child>(null);
  const look = legendLook(setup, defaults);
  const cols = (setup?.columns ?? LEGEND_DEFAULT_COLUMNS).filter((k) => columnDefs.some((c) => c.key === k));
  const labelOf = (k: string) => columnDefs.find((c) => c.key === k)?.label ?? k;
  const open = (c: Child) => setChild((v) => (v === c ? null : c));
  const setCols = (next: string[]) => onChange({ columns: next });
  const move = (k: string, d: -1 | 1) => {
    const i = cols.indexOf(k);
    const j = i + d;
    if (i < 0 || j < 0 || j >= cols.length) return;
    const next = [...cols];
    [next[i], next[j]] = [next[j]!, next[i]!];
    setCols(next);
  };

  const childBody = (c: Child) => (
    <>
          {c === 'title' && (
            <div className="w-[230px] space-y-2 p-2.5">
              <div className="font-semibold text-content-primary">Title</div>
              <input value={setup?.title ?? 'Legend'} onChange={(e) => onChange({ title: e.target.value })} className="h-7 w-full rounded border border-border bg-surface-primary px-2" data-testid="legend-props-title-text" />
              <label className="flex items-center gap-1.5 text-content-secondary">
                <input type="checkbox" checked={setup?.showTitle !== false} onChange={(e) => onChange({ showTitle: e.target.checked })} data-testid="legend-props-title-show" />
                Show the title on top
              </label>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Font size</span>
                <Stepper value={look.title.size} min={6} max={48} step={1} onChange={(v) => onChange({ titleStyle: { ...setup?.titleStyle, size: v } })} testId="legend-props-title-size" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Style</span>
                <StyleToggles st={look.title} onChange={(p) => onChange({ titleStyle: { ...setup?.titleStyle, ...p } })} testId="legend-props-title-style" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Colour</span>
                <ColorPicklist value={look.title.color} onChange={(c) => c && onChange({ titleStyle: { ...setup?.titleStyle, color: c } })} title="Title colour" testId="legend-props-title-colour" size={20} />
              </div>
            </div>
          )}
          {c === 'cells' && (
            <div className="w-[230px] space-y-2 p-2.5">
              <div className="font-semibold text-content-primary">Cells</div>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Font size</span>
                <Stepper value={look.cell.size} min={6} max={36} step={1} onChange={(v) => onChange({ cellStyle: { ...setup?.cellStyle, size: v } })} testId="legend-props-cell-size" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Style</span>
                <StyleToggles st={look.cell} onChange={(p) => onChange({ cellStyle: { ...setup?.cellStyle, ...p } })} testId="legend-props-cell-style" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-content-secondary">Colour</span>
                <ColorPicklist value={look.cell.color} onChange={(c) => c && onChange({ cellStyle: { ...setup?.cellStyle, color: c } })} title="Cell colour" testId="legend-props-cell-colour" size={20} />
              </div>
            </div>
          )}
          {c === 'style' && (
            <div className="grid w-[200px] grid-cols-3 gap-1.5 p-2.5">
              <div className="col-span-3 font-semibold text-content-primary">Legend style</div>
              {LEGEND_BORDERS.map((b) => (
                <button
                  key={b.key}
                  type="button"
                  onClick={() => onChange({ border: b.key })}
                  title={b.hint}
                  className={`flex flex-col items-center gap-0.5 rounded border p-1 ${look.border === b.key ? 'border-oe-blue bg-oe-blue/10' : 'border-border hover:bg-surface-secondary'}`}
                  aria-pressed={look.border === b.key}
                  data-testid={`legend-props-style-${b.key}`}
                >
                  <BorderPreview kind={b.key} title={setup?.showTitle !== false} />
                  <span className="text-[10px]">{b.label}</span>
                </button>
              ))}
            </div>
          )}
          {c === 'columns' && (
            <div className="flex">
              <div className="w-[190px] border-r border-border p-2.5">
                <div className="mb-1 font-semibold text-content-primary">In the legend</div>
                {cols.map((k) => (
                  <div key={k} className="flex items-center gap-1 rounded px-1 py-0.5 hover:bg-surface-secondary" data-testid={`legend-props-col-in-${k}`}>
                    <span className="flex-1 truncate">{labelOf(k)}</span>
                    <button type="button" onClick={() => move(k, -1)} className="rounded p-0.5 text-content-tertiary hover:bg-surface-tertiary" aria-label="Up"><ArrowUp size={10} /></button>
                    <button type="button" onClick={() => move(k, 1)} className="rounded p-0.5 text-content-tertiary hover:bg-surface-tertiary" aria-label="Down"><ArrowDown size={10} /></button>
                    <button type="button" onClick={() => cols.length > 1 && setCols(cols.filter((x) => x !== k))} className="rounded p-0.5 text-content-tertiary hover:bg-surface-tertiary" aria-label="Remove"><X size={10} /></button>
                  </div>
                ))}
              </div>
              <div className="w-[190px] p-2.5">
                <div className="mb-1 font-semibold text-content-primary">Markup list columns</div>
                <div className="mb-1 text-[10px] text-content-tertiary">Edit Columns: tick to keep in the legend</div>
                <div className="max-h-[240px] overflow-y-auto">
                  {columnDefs.map((c) => (
                    <label key={c.key} className="flex items-center gap-1.5 rounded px-1 py-0.5 hover:bg-surface-secondary">
                      <input
                        type="checkbox"
                        checked={cols.includes(c.key)}
                        onChange={() => setCols(cols.includes(c.key) ? (cols.length > 1 ? cols.filter((x) => x !== c.key) : cols) : [...cols, c.key])}
                        data-testid={`legend-props-col-${c.key}`}
                      />
                      <span className="truncate">{c.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
    </>
  );

  if (layout === 'bar') {
    const drop = (c: Child, label: string, value: string, testId: string) => (
      <span className="relative" data-testid={testId}>
        <button
          type="button"
          onClick={() => open(c)}
          className={`flex h-6 max-w-[170px] items-center gap-1 rounded border px-1.5 ${child === c ? 'border-oe-blue bg-oe-blue/10' : 'border-border hover:bg-surface-secondary'}`}
          aria-expanded={child === c}
          data-testid={`${testId}-button`}
        >
          <span className="text-content-secondary">{label}</span>
          <span className="truncate text-content-primary">{value}</span>
          <ChevronRight size={11} className={`shrink-0 ${child === c ? 'rotate-90 text-oe-blue' : 'text-content-tertiary'}`} />
        </button>
        {child === c && (
          <div className="absolute left-0 top-full z-50 mt-1 rounded-lg border border-border bg-surface-elevated shadow-xl" data-testid={`legend-props-child-${c}`}>
            {childBody(c)}
          </div>
        )}
      </span>
    );
    const lab = (t: string) => <span className="text-content-secondary">{t}</span>;
    return (
      <div
        className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-border bg-surface-primary px-2.5 py-1.5 text-[11px] shadow-xs"
        data-testid="legend-props"
        data-layout="bar"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <span className="border-b-2 border-oe-blue pb-0.5 font-semibold text-oe-blue">Legend</span>
        <span className="flex items-center gap-1">{lab('Font')}
          <select value={look.font} onChange={(e) => onChange({ font: e.target.value })} className="h-6 rounded border border-border bg-surface-primary px-1" data-testid="legend-props-font-select">
            {LEGEND_FONTS.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </span>
        <span className="flex items-center gap-1">{lab('Colour')}<ColorPicklist value={look.textColor} onChange={(x) => x && onChange({ textColor: x })} title="Text colour" testId="legend-props-text-colour" size={20} /></span>
        {drop('title', 'Title', setup?.showTitle === false ? 'hidden' : setup?.title || 'Legend', 'legend-props-title')}
        {drop('columns', 'Columns', String(cols.length), 'legend-props-columns')}
        {drop('cells', 'Cells', `${look.cell.size} pt`, 'legend-props-cells')}
        <span className="flex items-center gap-1">{lab('Opacity')}
          <input type="range" min={10} max={100} value={Math.round(look.opacity * 100)} onChange={(e) => onChange({ opacity: Number(e.target.value) / 100 })} className="w-16" data-testid="legend-props-opacity-range" />
          <span className="w-8 tabular-nums">{Math.round(look.opacity * 100)}%</span>
        </span>
        <span className="flex items-center gap-1">{lab('Line')}<ColorPicklist value={look.lineColor} onChange={(x) => x && onChange({ lineColor: x })} title="Line colour" testId="legend-props-line-colour-pick" size={20} /></span>
        {drop('style', 'Style', LEGEND_BORDERS.find((bd) => bd.key === look.border)?.label ?? '', 'legend-props-style')}
        <span className="flex items-center gap-1">{lab('Width')}<Stepper value={look.lineWidth} min={0} max={8} step={0.5} onChange={(v) => onChange({ lineWidth: v })} testId="legend-props-line-width-step" suffix=" pt" /></span>
        <span className="flex items-center gap-1">{lab('Fill')}<ColorPicklist value={look.fill} allowNone onChange={(x) => onChange({ fill: x })} title="Fill" testId="legend-props-fill-pick" size={20} /></span>
        <span className="flex items-center gap-1">{lab('Fill opacity')}
          <input type="range" min={0} max={100} value={Math.round(look.fillOpacity * 100)} onChange={(e) => onChange({ fillOpacity: Number(e.target.value) / 100 })} className="w-16" data-testid="legend-props-fill-opacity-range" />
          <span className="w-8 tabular-nums">{Math.round(look.fillOpacity * 100)}%</span>
        </span>
        <label className="flex items-center gap-1 text-content-secondary">
          <input type="checkbox" checked={setup?.live !== false} onChange={(e) => onChange({ live: e.target.checked })} data-testid="legend-props-live" />
          Live
        </label>
      </div>
    );
  }

  return (
    <div className="relative w-[268px] rounded-lg border border-border bg-surface-elevated text-xs shadow-xl" data-testid="legend-props" onMouseDown={(e) => e.stopPropagation()}>
      <div className="flex items-center border-b border-border px-2.5 py-2">
        <span className="flex-1 font-semibold text-content-primary">Legend Properties</span>
        <button type="button" onClick={onClose} className="rounded p-0.5 text-content-tertiary hover:bg-surface-secondary" aria-label="Close" data-testid="legend-props-close">
          <X size={13} />
        </button>
      </div>
      <Row label="Font" testId="legend-props-font">
        <select value={look.font} onChange={(e) => onChange({ font: e.target.value })} className="h-6 w-full rounded border border-border bg-surface-primary px-1" data-testid="legend-props-font-select">
          {LEGEND_FONTS.map((f) => <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>)}
        </select>
      </Row>
      <Row label="Colour" testId="legend-props-colour">
        <ColorPicklist value={look.textColor} onChange={(c) => c && onChange({ textColor: c })} title="Text colour" testId="legend-props-text-colour" size={20} />
      </Row>
      <Row label="Title" child open={child === 'title'} onOpen={() => open('title')} testId="legend-props-title">
        <span className="truncate text-content-tertiary">{setup?.showTitle === false ? 'hidden' : setup?.title || 'Legend'}</span>
      </Row>
      <Row label="Columns" child open={child === 'columns'} onOpen={() => open('columns')} testId="legend-props-columns">
        <span className="truncate text-content-tertiary">{cols.map(labelOf).join(', ')}</span>
      </Row>
      <Row label="Cells" child open={child === 'cells'} onOpen={() => open('cells')} testId="legend-props-cells">
        <span className="text-content-tertiary">{look.cell.size} pt{look.cell.bold ? ', bold' : ''}{look.cell.italic ? ', italic' : ''}</span>
      </Row>
      <Row label="Opacity" testId="legend-props-opacity">
        <input type="range" min={10} max={100} value={Math.round(look.opacity * 100)} onChange={(e) => onChange({ opacity: Number(e.target.value) / 100 })} className="w-24" data-testid="legend-props-opacity-range" />
        <span className="w-8 text-right tabular-nums">{Math.round(look.opacity * 100)}%</span>
      </Row>
      <Row label="Line colour" testId="legend-props-line-colour">
        <ColorPicklist value={look.lineColor} onChange={(c) => c && onChange({ lineColor: c })} title="Line colour" testId="legend-props-line-colour-pick" size={20} />
      </Row>
      <Row label="Legend style" child open={child === 'style'} onOpen={() => open('style')} testId="legend-props-style">
        <span className="text-content-tertiary">{LEGEND_BORDERS.find((b) => b.key === look.border)?.label}</span>
      </Row>
      <Row label="Line width" testId="legend-props-line-width">
        <Stepper value={look.lineWidth} min={0} max={8} step={0.5} onChange={(v) => onChange({ lineWidth: v })} testId="legend-props-line-width-step" suffix=" pt" />
      </Row>
      <Row label="Fill" testId="legend-props-fill">
        <ColorPicklist value={look.fill} allowNone onChange={(c) => onChange({ fill: c })} title="Fill" testId="legend-props-fill-pick" size={20} />
      </Row>
      <Row label="Fill opacity" testId="legend-props-fill-opacity">
        <input type="range" min={0} max={100} value={Math.round(look.fillOpacity * 100)} onChange={(e) => onChange({ fillOpacity: Number(e.target.value) / 100 })} className="w-24" data-testid="legend-props-fill-opacity-range" />
        <span className="w-8 text-right tabular-nums">{Math.round(look.fillOpacity * 100)}%</span>
      </Row>
      <label className="flex items-center gap-1.5 px-2.5 py-2 text-content-secondary">
        <input type="checkbox" checked={setup?.live !== false} onChange={(e) => onChange({ live: e.target.checked })} data-testid="legend-props-live" />
        Live: add markups drawn later on this sheet
      </label>

      {child && (
        <div className="absolute right-full top-0 mr-1.5 rounded-lg border border-border bg-surface-elevated shadow-xl" data-testid={`legend-props-child-${child}`}>
          {childBody(child)}
        </div>
      )}
    </div>
  );
}
