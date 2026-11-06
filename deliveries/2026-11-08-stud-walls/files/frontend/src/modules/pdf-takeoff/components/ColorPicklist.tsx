// OE-DELIVERY: 2026-11-08-stud-walls
/**
 * Colour picklist like Bluebeam Revu's: a palette of standard colours in a
 * grid, the colours used lately, "No colour" where it applies, and "More
 * colours…" for anything else. Opens from a small swatch button.
 */
import { useEffect, useRef, useState } from 'react';

/** Revu-style standard palette: 8 hues x 5 tints, then greys. */
export const REVU_PALETTE: string[] = [
  // full colours
  '#FF0000', '#FF8000', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF', '#8000FF', '#FF00FF',
  // dark
  '#800000', '#804000', '#808000', '#008000', '#008080', '#000080', '#400080', '#800080',
  // medium
  '#C00000', '#E46C0A', '#C4BD00', '#00B050', '#0098A6', '#0070C0', '#7030A0', '#C0007A',
  // light
  '#FF9999', '#FFC080', '#FFFF99', '#99FF99', '#99FFFF', '#99CCFF', '#CC99FF', '#FF99FF',
  // pale
  '#FFE0E0', '#FFF0D9', '#FFFFE0', '#E0FFE0', '#E0FFFF', '#E0F0FF', '#F0E0FF', '#FFE0FF',
  // greys
  '#000000', '#262626', '#404040', '#595959', '#808080', '#A6A6A6', '#D9D9D9', '#FFFFFF',
];

const RECENT_KEY = 'takeoff.colorPicklist.recent';

function loadRecent(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    return Array.isArray(v) ? v.filter((c) => typeof c === 'string' && /^#[0-9a-f]{6}$/i.test(c)).slice(0, 8) : [];
  } catch {
    return [];
  }
}

function pushRecent(c: string): void {
  try {
    const next = [c.toUpperCase(), ...loadRecent().filter((x) => x.toUpperCase() !== c.toUpperCase())].slice(0, 8);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

export interface ColorPicklistProps {
  value: string | null;
  onChange: (colour: string | null) => void;
  /** Offer "No colour" (fill / border off). */
  allowNone?: boolean;
  title?: string;
  testId?: string;
  /** Swatch size in px. */
  size?: number;
}

export default function ColorPicklist({ value, onChange, allowNone, title = 'Colour', testId = 'color-picklist', size = 20 }: ColorPicklistProps) {
  const [open, setOpen] = useState(false);
  const [recent, setRecent] = useState<string[]>([]);
  const box = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    setRecent(loadRecent());
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);
  const pick = (c: string | null) => {
    if (c) pushRecent(c);
    onChange(c);
    setOpen(false);
  };
  const cell = (c: string, key: string) => (
    <button
      key={key}
      type="button"
      title={c}
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => pick(c)}
      className={`h-4 w-4 rounded-sm border ${value && value.toUpperCase() === c.toUpperCase() ? 'border-oe-blue ring-2 ring-oe-blue/60' : 'border-black/15 hover:scale-125'} transition-transform`}
      style={{ background: c }}
      data-testid={`${testId}-cell`}
    />
  );
  return (
    <span ref={box} className="relative inline-flex">
      <button
        type="button"
        title={title}
        aria-label={title}
        aria-expanded={open}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => setOpen((o) => !o)}
        className="rounded border border-border"
        style={{
          width: size,
          height: size,
          background: value ?? 'repeating-linear-gradient(45deg,#fff 0 3px,#e5e7eb 3px 6px)',
        }}
        data-testid={testId}
      />
      {open && (
        <div
          className="absolute left-0 top-full z-50 mt-1 w-[176px] rounded-md border border-border bg-surface-elevated p-2 shadow-xl"
          data-text-format-bar=""
          data-testid={`${testId}-menu`}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="grid grid-cols-8 gap-1">{REVU_PALETTE.map((c, i) => cell(c, `p${i}`))}</div>
          {recent.length > 0 && (
            <>
              <p className="mt-2 text-[10px] text-content-tertiary">Recent</p>
              <div className="mt-0.5 grid grid-cols-8 gap-1">{recent.map((c, i) => cell(c, `r${i}`))}</div>
            </>
          )}
          <div className="mt-2 flex items-center justify-between gap-1 text-[11px]">
            {allowNone ? (
              <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => pick(null)} className="rounded px-1 hover:bg-surface-secondary" data-testid={`${testId}-none`}>
                No colour
              </button>
            ) : (
              <span />
            )}
            <label className="cursor-pointer rounded px-1 text-oe-blue hover:bg-surface-secondary">
              More colours…
              <input
                type="color"
                className="sr-only"
                value={value && /^#[0-9a-f]{6}$/i.test(value) ? value : '#ff0000'}
                onChange={(e) => pick(e.target.value)}
                data-testid={`${testId}-more`}
              />
            </label>
          </div>
        </div>
      )}
    </span>
  );
}
