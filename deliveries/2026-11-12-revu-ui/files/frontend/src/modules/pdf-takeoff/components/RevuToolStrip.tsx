// OE-DELIVERY: 2026-11-02-revu-tool-strip
/**
 * Revu-style vertical tool strip on the right edge of the drawing: every
 * measure and markup tool, as many as fit the height; the rest open from a
 * "more" button at the bottom. Re-measures on resize.
 */
import { useEffect, useLayoutEffect, useRef, useState, type Ref } from 'react';
import { ChevronDown } from 'lucide-react';
import clsx from 'clsx';
import type { ToolIcon } from './revu-icons';

export interface StripTool {
  tool: string;
  label: string;
  icon: ToolIcon;
  kind: 'select' | 'measure' | 'markup';
  shortcut?: string;
  /** Dotted separator above this tool (Revu groups). */
  sepBefore?: boolean;
}

interface Props {
  tools: StripTool[];
  active: string;
  onSelect: (tool: string) => void;
  /** Ref for the Area button (the area popup anchors to it). */
  areaRef?: Ref<HTMLButtonElement>;
  /** Tool lock (Revu): double-click a tool to keep it on after each markup. */
  locked?: boolean;
  onLock?: (tool: string) => void;
}

const ITEM = 36; // px per button incl. gap (Revu: icon only, name on hover - OE-DELIVERY 2026-11-12-revu-ui update 7)

export function RevuToolStrip({ tools, active, onSelect, areaRef, locked, onLock }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  // Rows that fit the height; more tools wrap into a second column, so every
  // tool stays on screen with its name - nothing hidden behind a "more"
  // button the floating chat bubble can cover (OE-DELIVERY 2026-11-12-revu-ui).
  const [rows, setRows] = useState(tools.length);

  useLayoutEffect(() => {
    const el = boxRef.current?.parentElement;
    if (!el) return;
    const measure = () => {
      // One column (Revu); keep the bottom clear of the floating chat button.
      const h = el.clientHeight - 84;
      setRows(Math.max(4, Math.floor(h / ITEM)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [tools.length]);
  const [moreOpen, setMoreOpen] = useState(false);
  useEffect(() => {
    if (!moreOpen) return;
    const close = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [moreOpen]);

  const btn = (t: StripTool, inMenu = false) => {
    const on = active === t.tool;
    const Icon = t.icon;
    const tip = (t.shortcut ? `${t.label} (${t.shortcut})` : t.label) + (t.kind !== 'select' ? ' - double-click to lock the tool on' : '');
    return (
      <button
        key={t.tool}
        type="button"
        ref={t.tool === 'area' ? areaRef : undefined}
        onClick={() => {
          onSelect(t.tool);
          if (inMenu) setMoreOpen(false);
        }}
        onDoubleClick={() => onLock?.(t.tool)}
        title={tip}
        aria-label={tip}
        aria-pressed={on}
        data-strip-tool={t.tool}
        data-locked={on && locked ? 'true' : undefined}
        className={clsx(
          'relative flex shrink-0 items-center rounded transition-colors',
          inMenu ? 'h-7 w-full gap-2 px-2 text-left text-[12px]' : 'h-[42px] w-[54px] flex-col justify-center gap-0.5 px-0.5',
          // Same look as the left rail: grey icons, blue when on (update 11).
          on ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-secondary hover:text-content-primary',
        )}
      >
        <span className="flex shrink-0" style={{ filter: on && !inMenu ? 'brightness(0) invert(1)' : 'grayscale(1) contrast(1.4)', opacity: on ? 1 : 0.85 }}>
          <Icon size={inMenu ? 15 : 18} />
        </span>
        {/* Tool name under the icon - some users go by the name (update 15). */}
        {!inMenu && (
          <span className="w-full truncate text-center text-[8.5px] leading-[10px]" data-strip-label>
            {t.label}
          </span>
        )}
        {on && locked && !inMenu && (
          <span className="absolute -bottom-0.5 -right-0.5 rounded-sm bg-white px-[1px] text-[7px] leading-none text-content-primary shadow" aria-label="Locked">
            &#128274;
          </span>
        )}
        {inMenu && <span className="min-w-0 flex-1 truncate">{t.label}</span>}
        {inMenu && t.shortcut && <span className="shrink-0 font-mono text-[9px] opacity-70">{t.shortcut}</span>}
      </button>
    );
  };

  // One column that scrolls (update 11); the arrows at the ends scroll it.
  const listRef = useRef<HTMLDivElement>(null);
  const [canUp, setCanUp] = useState(false);
  const [canDown, setCanDown] = useState(false);
  const syncArrows = () => {
    const el = listRef.current;
    if (!el) return;
    setCanUp(el.scrollTop > 2);
    setCanDown(el.scrollTop + el.clientHeight < el.scrollHeight - 2);
  };
  useEffect(() => {
    syncArrows();
  });
  const scrollBy = (dy: number) => listRef.current?.scrollBy({ top: dy, behavior: 'smooth' });
  void rows;
  void moreOpen;
  return (
    <div
      ref={boxRef}
      className="relative flex h-full shrink-0 flex-col items-center rounded-lg border border-border bg-surface-primary p-[3px] pb-[76px]"
      role="toolbar"
      aria-orientation="vertical"
      aria-label="Tools"
      data-testid="revu-tool-strip"
      data-cols={1}
    >
      {canUp && (
        <button type="button" onClick={() => scrollBy(-200)} aria-label="Scroll tools up" className="flex h-5 w-[54px] shrink-0 items-center justify-center rounded text-content-secondary hover:bg-surface-secondary" data-testid="revu-tool-strip-up">
          <ChevronDown size={15} className="rotate-180" />
        </button>
      )}
      <div
        ref={listRef}
        onScroll={syncArrows}
        className="flex min-h-0 flex-1 flex-col items-center gap-[2px] overflow-y-auto [scrollbar-width:thin]"
        data-testid="revu-tool-strip-list"
      >
        {tools.map((t, i) => (
          <div key={t.tool} className="flex flex-col items-center">
            {i > 0 && (tools[i - 1]!.kind !== t.kind || t.sepBefore) && <span className="my-1 w-10 border-t border-dotted border-content-tertiary/60" aria-hidden="true" />}
            {btn(t)}
          </div>
        ))}
      </div>
      {canDown && (
        <button type="button" onClick={() => scrollBy(200)} aria-label="Scroll tools down" title="More tools" className="flex h-6 w-[54px] shrink-0 items-center justify-center rounded text-content-secondary hover:bg-surface-secondary" data-testid="revu-tool-strip-more">
          <ChevronDown size={16} />
        </button>
      )}
    </div>
  );
}
