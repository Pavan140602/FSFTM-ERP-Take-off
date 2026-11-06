// OE-DELIVERY: 2026-11-02-revu-workspace
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Check, ChevronRight } from 'lucide-react';

/** Revu-style menu bar for the PDF Measurements workspace.
 *
 * File · Edit · View · Document · Measure · Markup · Tools · Window · Help,
 * each a dropdown of commands with their shortcuts, behaving like a desktop
 * menu: click a title to open, move across titles to switch while one is
 * open, Esc or a click outside closes, submenus open on hover. Every item
 * calls an existing viewer command, so the menus and the toolbars never
 * disagree.
 */

export interface RevuMenuItem {
  label?: string;
  shortcut?: string;
  onClick?: () => void;
  checked?: boolean;
  disabled?: boolean;
  separator?: boolean;
  submenu?: RevuMenuItem[];
  icon?: ReactNode;
  testId?: string;
}

export interface RevuMenu {
  label: string;
  items: RevuMenuItem[];
}

function MenuList(props: { items: RevuMenuItem[]; onDone: () => void; nested?: boolean }) {
  const { items, onDone, nested } = props;
  const [sub, setSub] = useState<number | null>(null);
  return (
    <div
      role="menu"
      className={`min-w-[230px] rounded-md border border-border bg-surface-primary py-1 shadow-xl ${nested ? '' : ''}`}
    >
      {items.map((it, i) =>
        it.separator ? (
          <div key={`sep-${i}`} className="my-1 h-px bg-border" role="separator" />
        ) : (
          <div key={`${it.label}-${i}`} className="relative" onMouseEnter={() => setSub(it.submenu ? i : null)}>
            <button
              type="button"
              role="menuitem"
              disabled={it.disabled}
              data-testid={it.testId}
              onClick={() => {
                if (it.submenu) {
                  setSub(i);
                  return;
                }
                onDone();
                it.onClick?.();
              }}
              className="flex w-full items-center gap-2 px-2.5 py-1 text-left text-[12px] text-content-primary hover:bg-oe-blue hover:text-white disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-content-primary"
            >
              <span className="flex w-4 shrink-0 justify-center">{it.checked ? <Check size={12} /> : it.icon ?? null}</span>
              <span className="flex-1 whitespace-nowrap">{it.label}</span>
              {it.shortcut && <span className="ml-6 text-[11px] opacity-60 whitespace-nowrap">{it.shortcut}</span>}
              {it.submenu && <ChevronRight size={12} className="opacity-70" />}
            </button>
            {it.submenu && sub === i && (
              <div className="absolute left-full top-0 z-10 -mt-1">
                <MenuList items={it.submenu} onDone={onDone} nested />
              </div>
            )}
          </div>
        ),
      )}
    </div>
  );
}

export function RevuMenuBar(props: { menus: RevuMenu[]; right?: ReactNode; title?: ReactNode }) {
  const { menus, right, title } = props;
  const [open, setOpen] = useState<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open === null) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(null);
      }
    };
    window.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey, true);
    return () => {
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onKey, true);
    };
  }, [open]);

  return (
    <div
      ref={rootRef}
      className="flex h-7 shrink-0 select-none items-center gap-0.5 border-b border-border bg-surface-secondary/80 px-1 text-[12px]"
      role="menubar"
      data-testid="revu-menubar"
    >
      {title}
      {menus.map((m, i) => (
        <div key={m.label} className="relative">
          <button
            type="button"
            role="menuitem"
            aria-haspopup="menu"
            aria-expanded={open === i}
            data-testid={`revu-menu-${m.label.toLowerCase()}`}
            onClick={() => setOpen(open === i ? null : i)}
            onMouseEnter={() => {
              if (open !== null) setOpen(i);
            }}
            className={`rounded px-2 py-0.5 ${open === i ? 'bg-oe-blue text-white' : 'text-content-primary hover:bg-surface-tertiary'}`}
          >
            {m.label}
          </button>
          {open === i && (
            <div className="absolute left-0 top-full z-[70] mt-0.5">
              <MenuList items={m.items} onDone={() => setOpen(null)} />
            </div>
          )}
        </div>
      ))}
      <div className="ml-auto flex items-center gap-1">{right}</div>
    </div>
  );
}

export default RevuMenuBar;
