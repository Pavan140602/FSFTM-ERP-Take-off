// OE-DELIVERY: 2026-11-12-revu-ui (legend setup)
/**
 * Legend Setup, like Revu's: title (and the title row on / off), the
 * columns to keep (tick, and move up / down), the table lines (grid,
 * horizontal only, vertical only, outline, none) with a small preview, and
 * whether the legend stays live with the page.
 */
import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, X } from 'lucide-react';
import { LEGEND_BORDERS, LEGEND_DEFAULT_COLUMNS, type LegendBorder, type LegendSetup } from '../data/legend-setup';

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initial?: LegendSetup;
  columnDefs: { key: string; label: string }[];
  markupCount?: number;
  onCancel: () => void;
  onSave: (setup: LegendSetup) => void;
}

export function BorderPreview({ kind, title }: { kind: LegendBorder; title: boolean }) {
  const top = title ? 9 : 2;
  return (
    <svg width="54" height="38" viewBox="0 0 54 38" aria-hidden="true">
      <rect x="1" y="1" width="52" height="36" fill="#fff" stroke="#d1d5db" />
      {title && <rect x="14" y="3" width="26" height="3" rx="1" fill="#374151" />}
      {[0, 1, 2, 3].map((r) => (
        <g key={r}>
          <rect x="5" y={top + 3 + r * 7} width="4" height="3" fill={['#ef4444', '#3b82f6', '#10b981', '#f59e0b'][r]} />
          <rect x="13" y={top + 3.5 + r * 7} width="16" height="2" fill="#9ca3af" />
          <rect x="35" y={top + 3.5 + r * 7} width="12" height="2" fill="#9ca3af" />
        </g>
      ))}
      <g stroke="#111827" strokeWidth="0.8" fill="none">
        {(kind === 'grid' || kind === 'outline') && <rect x="3" y={top} width="48" height={34 - top} />}
        {(kind === 'grid' || kind === 'horizontal') && [1, 2, 3].map((r) => <line key={r} x1="3" x2="51" y1={top + r * 7 + 1} y2={top + r * 7 + 1} />)}
        {(kind === 'grid' || kind === 'vertical') && [11, 32].map((x) => <line key={x} x1={x} x2={x} y1={top} y2={36} />)}
      </g>
    </svg>
  );
}

export function LegendSetupDialog({ open, mode, initial, columnDefs, markupCount, onCancel, onSave }: Props) {
  const [title, setTitle] = useState('Legend');
  const [showTitle, setShowTitle] = useState(true);
  const [cols, setCols] = useState<string[]>(LEGEND_DEFAULT_COLUMNS);
  const [border, setBorder] = useState<LegendBorder>('grid');
  const [live, setLive] = useState(true);

  // Load the values once each time the window opens (not on every redraw).
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open) {
      wasOpen.current = false;
      return;
    }
    if (wasOpen.current) return;
    wasOpen.current = true;
    setTitle(initial?.title ?? 'Legend');
    setShowTitle(initial?.showTitle ?? true);
    setCols((initial?.columns ?? LEGEND_DEFAULT_COLUMNS).filter((k) => columnDefs.some((c) => c.key === k)));
    setBorder(initial?.border ?? 'grid');
    setLive(initial?.live ?? true);
  }, [open, initial, columnDefs]);

  if (!open) return null;
  const labelOf = (k: string) => columnDefs.find((c) => c.key === k)?.label ?? k;
  const toggle = (k: string) =>
    setCols((prev) => (prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]));
  const move = (k: string, d: -1 | 1) =>
    setCols((prev) => {
      const i = prev.indexOf(k);
      const j = i + d;
      if (i < 0 || j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j]!, next[i]!];
      return next;
    });
  // Ticked columns first in their order, then the rest.
  const ordered = [...cols, ...columnDefs.map((c) => c.key).filter((k) => !cols.includes(k))];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30" onMouseDown={onCancel} data-testid="legend-setup-dialog">
      <div
        className="w-[520px] max-w-[95vw] rounded-lg border border-border bg-surface-elevated shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Legend Setup"
      >
        <div className="flex items-center border-b border-border px-4 py-2.5">
          <span className="flex-1 text-sm font-semibold text-content-primary">Legend Setup</span>
          {markupCount != null && <span className="mr-3 text-[11px] text-content-tertiary">{markupCount} markup{markupCount === 1 ? '' : 's'} picked</span>}
          <button type="button" onClick={onCancel} className="rounded p-1 text-content-tertiary hover:bg-surface-secondary" aria-label="Close">
            <X size={14} />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4 p-4 text-xs">
          <div className="space-y-3">
            <div>
              <div className="mb-1 font-semibold text-content-secondary">Title</div>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="h-7 w-full rounded border border-border bg-surface-primary px-2"
                data-testid="legend-setup-title"
              />
              <label className="mt-1.5 flex items-center gap-1.5 text-content-secondary">
                <input type="checkbox" checked={showTitle} onChange={(e) => setShowTitle(e.target.checked)} data-testid="legend-setup-show-title" />
                Show the title row on top
              </label>
            </div>
            <div>
              <div className="mb-1 font-semibold text-content-secondary">Table lines</div>
              <div className="grid grid-cols-3 gap-1.5">
                {LEGEND_BORDERS.map((b) => (
                  <button
                    key={b.key}
                    type="button"
                    onClick={() => setBorder(b.key)}
                    title={b.hint}
                    className={`flex flex-col items-center gap-0.5 rounded border p-1 ${border === b.key ? 'border-oe-blue bg-oe-blue/10' : 'border-border hover:bg-surface-secondary'}`}
                    aria-pressed={border === b.key}
                    data-testid={`legend-setup-border-${b.key}`}
                  >
                    <BorderPreview kind={b.key} title={showTitle} />
                    <span className="text-[10px]">{b.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-start gap-1.5 text-content-secondary">
              <input type="checkbox" className="mt-0.5" checked={live} onChange={(e) => setLive(e.target.checked)} data-testid="legend-setup-live" />
              <span>Keep it live: markups drawn later on this page with the same Subject and colour are added to the legend</span>
            </label>
          </div>
          <div>
            <div className="mb-1 font-semibold text-content-secondary">Columns <span className="font-normal text-content-tertiary">(symbol always shows)</span></div>
            <div className="max-h-[260px] overflow-y-auto rounded border border-border">
              {ordered.map((k) => {
                const on = cols.includes(k);
                return (
                  <div key={k} className="flex items-center gap-1.5 border-b border-border/60 px-2 py-1 last:border-b-0">
                    <input type="checkbox" checked={on} onChange={() => toggle(k)} data-testid={`legend-setup-col-${k}`} />
                    <span className={`flex-1 ${on ? 'text-content-primary' : 'text-content-tertiary'}`}>{labelOf(k)}</span>
                    {on && (
                      <>
                        <button type="button" onClick={() => move(k, -1)} className="rounded p-0.5 text-content-tertiary hover:bg-surface-secondary" aria-label={`Move ${labelOf(k)} up`}>
                          <ArrowUp size={11} />
                        </button>
                        <button type="button" onClick={() => move(k, 1)} className="rounded p-0.5 text-content-tertiary hover:bg-surface-secondary" aria-label={`Move ${labelOf(k)} down`}>
                          <ArrowDown size={11} />
                        </button>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-2.5">
          <span className="mr-auto text-[11px] text-content-tertiary">Drag a corner of the legend to make it bigger or smaller - everything in it scales together.</span>
          <button type="button" onClick={onCancel} className="rounded border border-border px-3 py-1 text-xs hover:bg-surface-secondary">
            Cancel
          </button>
          <button
            type="button"
            disabled={cols.length === 0}
            onClick={() => onSave({ title: title.trim() || 'Legend', showTitle, columns: cols, border, live })}
            className="rounded bg-oe-blue px-3 py-1 text-xs font-semibold text-white disabled:opacity-40"
            data-testid="legend-setup-ok"
          >
            {mode === 'create' ? 'Place legend' : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  );
}
