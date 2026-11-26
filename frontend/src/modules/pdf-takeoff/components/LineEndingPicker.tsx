// FSFTM Start / End line-ending picker (OE-DELIVERY 2026-11-25-fsftm-pdf):
// a compact dropdown that shows each ending as a small drawing.
import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { LINE_ENDINGS, type LineEnding } from '../data/line-endings';

/** SVG preview of a line with the ending on its right end. */
export function LineEndingIcon({ style, flip = false, width = 34 }: { style: LineEnding; flip?: boolean; width?: number }) {
  const y = 7;
  const x1 = 3;
  const x2 = width - 5;
  const s = 6;
  let head: JSX.Element | null = null;
  switch (style) {
    case 'openArrow':
      head = <polyline points={`${x2 - s},${y - s / 2} ${x2},${y} ${x2 - s},${y + s / 2}`} fill="none" />;
      break;
    case 'closedArrow':
      head = <polygon points={`${x2},${y} ${x2 - s},${y - s / 2} ${x2 - s},${y + s / 2}`} fill="currentColor" stroke="none" />;
      break;
    case 'circle':
      head = <circle cx={x2} cy={y} r={2.6} fill="none" />;
      break;
    case 'filledCircle':
      head = <circle cx={x2} cy={y} r={2.6} fill="currentColor" />;
      break;
    case 'square':
      head = <rect x={x2 - 2.5} y={y - 2.5} width={5} height={5} fill="none" />;
      break;
    case 'filledSquare':
      head = <rect x={x2 - 2.5} y={y - 2.5} width={5} height={5} fill="currentColor" />;
      break;
    case 'diamond':
      head = <polygon points={`${x2 + 3},${y} ${x2},${y - 2.5} ${x2 - 3},${y} ${x2},${y + 2.5}`} fill="none" />;
      break;
    case 'butt':
      head = <line x1={x2} y1={y - 4} x2={x2} y2={y + 4} />;
      break;
    case 'slash':
      head = <line x1={x2 - 2.5} y1={y + 4} x2={x2 + 2.5} y2={y - 4} />;
      break;
    default:
      head = null;
  }
  return (
    <svg width={width} height={14} viewBox={`0 0 ${width} 14`} aria-hidden="true" style={flip ? { transform: 'scaleX(-1)' } : undefined} stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <line x1={x1} y1={y} x2={x2} y2={y} />
      {head}
    </svg>
  );
}

export default function LineEndingPicker({
  label,
  value,
  onChange,
  disabled,
  flip = false,
  testId,
}: {
  label: string;
  value: LineEnding | undefined;
  onChange: (v: LineEnding) => void;
  disabled?: boolean;
  /** Draw the previews pointing left (the Start end). */
  flip?: boolean;
  testId: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [open]);
  const cur = value ?? 'none';
  return (
    <div ref={ref} className="relative inline-flex items-center gap-1">
      <span className="text-[10px] text-content-tertiary">{label}:</span>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-6 items-center gap-0.5 rounded border border-border bg-surface-primary px-1 text-content-primary hover:border-oe-blue/60 disabled:opacity-40"
        title={`${label} ending`}
        data-testid={testId}
      >
        <LineEndingIcon style={cur} flip={flip} />
        <ChevronDown size={11} className="text-content-tertiary" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-[150px] rounded-md border border-border bg-surface-elevated py-1 shadow-xl" role="listbox" data-testid={`${testId}-list`}>
          {LINE_ENDINGS.map((e) => (
            <button
              key={e.value}
              type="button"
              role="option"
              aria-selected={cur === e.value}
              onClick={() => { onChange(e.value); setOpen(false); }}
              className="flex w-full items-center gap-2 px-2 py-1 text-left text-content-primary hover:bg-oe-blue hover:text-white"
              title={e.label}
              data-testid={`${testId}-${e.value}`}
            >
              <span className="w-3">{cur === e.value ? <Check size={11} /> : null}</span>
              <LineEndingIcon style={e.value} flip={flip} width={46} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
