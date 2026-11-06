// OE-DELIVERY: 2026-11-02-revu-tool-strip
/**
 * Revu-style vertical tool strip on the right edge of the drawing: every
 * measure and markup tool, as many as fit the height; the rest open from a
 * "more" button at the bottom. Re-measures on resize.
 */
import { useEffect, useLayoutEffect, useRef, useState, type Ref } from 'react';
import clsx from 'clsx';
import { ChevronsDown, type LucideIcon } from 'lucide-react';

export interface StripTool {
  tool: string;
  label: string;
  icon: LucideIcon;
  kind: 'select' | 'measure' | 'markup';
  shortcut?: string;
}

interface Props {
  tools: StripTool[];
  active: string;
  onSelect: (tool: string) => void;
  /** Ref for the Area button (the area popup anchors to it). */
  areaRef?: Ref<HTMLButtonElement>;
}

const ITEM = 30; // px per button incl. gap
const SEP = 9;

export function RevuToolStrip({ tools, active, onSelect, areaRef }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(tools.length);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const measure = () => {
      const h = el.clientHeight - 8;
      // separators between kinds take a little room too
      const seps = 2 * SEP;
      const all = tools.length * ITEM + seps;
      if (all <= h) setFit(tools.length);
      else setFit(Math.max(1, Math.floor((h - seps - ITEM) / ITEM)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [tools.length]);

  useEffect(() => {
    if (!moreOpen) return;
    const close = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
    };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [moreOpen]);

  const shown = tools.slice(0, fit);
  const hidden = tools.slice(fit);
  const btn = (t: StripTool, inMenu = false) => {
    const on = active === t.tool;
    const Icon = t.icon;
    const tip = t.shortcut ? `${t.label} (${t.shortcut})` : t.label;
    return (
      <button
        key={t.tool}
        type="button"
        ref={t.tool === 'area' ? areaRef : undefined}
        onClick={() => {
          onSelect(t.tool);
          if (inMenu) setMoreOpen(false);
        }}
        title={tip}
        aria-label={tip}
        aria-pressed={on}
        data-strip-tool={t.tool}
        className={clsx(
          'flex shrink-0 items-center rounded transition-colors',
          inMenu ? 'h-7 w-full gap-2 px-2 text-left text-[12px]' : 'h-7 w-7 justify-center',
          on
            ? t.kind === 'markup'
              ? 'bg-orange-500 text-white'
              : 'bg-oe-blue text-white'
            : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
        )}
      >
        <Icon size={15} className="shrink-0" />
        {inMenu && <span className="min-w-0 flex-1 truncate">{t.label}</span>}
        {inMenu && t.shortcut && <span className="shrink-0 font-mono text-[9px] opacity-70">{t.shortcut}</span>}
      </button>
    );
  };

  return (
    <div
      ref={boxRef}
      className="relative flex h-full w-9 shrink-0 flex-col items-center gap-[2px] rounded-lg border border-border bg-surface-secondary/70 py-1"
      role="toolbar"
      aria-orientation="vertical"
      aria-label="Tools"
      data-testid="revu-tool-strip"
      data-fit={fit}
    >
      {shown.map((t, i) => (
        <div key={t.tool} className="flex flex-col items-center">
          {i > 0 && shown[i - 1]!.kind !== t.kind && <span className="my-1 h-px w-5 bg-border" aria-hidden="true" />}
          {btn(t)}
        </div>
      ))}
      {hidden.length > 0 && (
        <div className="relative mt-auto" ref={moreRef}>
          <button
            type="button"
            onClick={() => setMoreOpen((o) => !o)}
            className={clsx(
              'flex h-7 w-7 items-center justify-center rounded',
              hidden.some((t) => t.tool === active) ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-secondary hover:bg-surface-tertiary',
            )}
            title={`${hidden.length} more tools`}
            aria-label={`${hidden.length} more tools`}
            aria-expanded={moreOpen}
            data-testid="revu-tool-strip-more"
          >
            <ChevronsDown size={15} />
          </button>
          {moreOpen && (
            <div className="absolute bottom-0 right-full z-50 mr-1 max-h-[70vh] w-48 overflow-y-auto rounded-md border border-border bg-surface-elevated p-1 shadow-lg" data-testid="revu-tool-strip-menu">
              {hidden.map((t) => btn(t, true))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
