// OE-DELIVERY: 2026-11-02-revu-tool-chest
/**
 * Bluebeam Revu-style Tool Chest panel: collapsible tool sets with a preview
 * tile per tool, Drawing / Properties mode per set, icon or list view, drag a
 * tool to another set, add the selected markups as tools, rename / delete.
 */
import { useState, type ReactNode } from 'react';
import clsx from 'clsx';
import {
  ChevronDown,
  ChevronRight,
  FolderPlus,
  LayoutGrid,
  Library,
  SquarePlus,
  List,
  Paintbrush,
  PenTool,
  Pencil,
  Plus,
  Trash2,
  X,
  type LucideIcon,
} from 'lucide-react';
import {
  FAMILY_NAMES,
  RECENT_ID,
  addItem,
  addSet,
  newId,
  shapeFamily,
  type ShapeFamily,
  deleteSet,
  moveItem,
  patchItem,
  patchSet,
  removeItem,
  type ChestItem,
  type ChestSet,
} from '../data/tool-chest-sets';

interface Props {
  sets: ChestSet[];
  onChange: (sets: ChestSet[]) => void;
  /** Draw with this tool (Drawing mode, or nothing selected). */
  onUse: (item: ChestItem) => void;
  /** Apply this tool's properties to the selected markups (Properties mode). */
  onApply: (item: ChestItem) => void;
  /** Add the selected markups to a set as tools. */
  onAddSelection: (setId: string) => void;
  selectionCount: number;
  activeItemId: string | null;
  iconFor: (tool: string) => LucideIcon | undefined;
  typeLabel: (tool: string) => string;
  /** Extra sections under the sets. */
  children?: ReactNode;
  /** Tool types offered by "New tool". */
  toolTypes: { tool: string; label: string }[];
  /** Re-add the structural (W / WT / HSS / L / CFS / deck) tool sets. */
  onAddStructural?: () => void;
}

const DASH: Record<string, string | undefined> = { dashed: '5 3', dotted: '1 3', dashdot: '7 3 1 3' };
const AREAL = new Set(['area', 'rectarea', 'volume', 'polygon', 'rectangle', 'ellipse', 'cloud', 'highlight', 'dynamicFill', 'polygonCutout', 'ellipseCutout']);

/** Cross-section drawing of a member family (structural tools). */
function ShapeGlyph({ fam, color }: { fam: ShapeFamily; color: string }) {
  const sw = { stroke: color, strokeWidth: 3, fill: 'none', strokeLinejoin: 'miter' as const };
  switch (fam) {
    case 'W':
      return (<g fill={color}><rect x="6" y="5" width="18" height="3.5" /><rect x="13.3" y="8.5" width="3.4" height="13" /><rect x="6" y="21.5" width="18" height="3.5" /></g>);
    case 'WT':
      return (<g fill={color}><rect x="6" y="6" width="18" height="3.5" /><rect x="13.3" y="9.5" width="3.4" height="15" /></g>);
    case 'HSS':
      return <rect x="7.5" y="6.5" width="15" height="17" rx="1.5" {...sw} />;
    case 'HSSR':
      return <circle cx="15" cy="15" r="8.5" {...sw} />;
    case 'L':
      return <path d="M9 5 V23.5 H25" {...sw} />;
    case 'C':
      return <path d="M23 6.5 H9.5 V23.5 H23" {...sw} />;
    case 'CFS-S':
      return <path d="M20 10 V6.5 H10 V23.5 H20 V20" {...sw} strokeWidth={2.4} />;
    case 'CFS-T':
      return <path d="M8 8 V23 H22 V8" {...sw} strokeWidth={2.4} />;
    case 'DECK':
      return <path d="M2 19 H6 L8.5 10 H12.5 L15 19 H18 L20.5 10 H24.5 L27 19 H29" {...sw} strokeWidth={2} />;
    case 'HDR':
      return (<g {...sw} strokeWidth={2.2}><path d="M6 7 H24 V23 H6 Z" /><path d="M15 7 V23" /></g>);
    case 'JAMB':
      return (<g {...sw} strokeWidth={2.2}><path d="M13 6 H7 V24 H13" /><path d="M17 6 H23 V24 H17" /></g>);
    case 'JOIST':
      return (<g {...sw} strokeWidth={1.8}><path d="M3 8 H27 M3 22 H27" /><path d="M3 22 L7 8 L11 22 L15 8 L19 22 L23 8 L27 22" /></g>);
    default:
      return null;
  }
}

const SHORT: Record<ShapeFamily, string> = { W: 'W', WT: 'WT', HSS: 'HSS', HSSR: 'HSS', L: 'L', C: 'C', 'CFS-S': 'CFS', 'CFS-T': 'TRK', DECK: 'DECK', JOIST: 'JST', HDR: 'HDR', JAMB: 'JMB' };

/** Inline "New tool" form for a set. */
function NewToolForm({ toolTypes, onSave, onCancel }: { toolTypes: { tool: string; label: string }[]; onSave: (it: ChestItem) => void; onCancel: () => void }) {
  const [tool, setTool] = useState(toolTypes.some((t) => t.tool === 'distance') ? 'distance' : toolTypes[0]?.tool ?? 'distance');
  const [subject, setSubject] = useState('');
  const [label, setLabel] = useState('');
  const [name, setName] = useState('');
  const [color, setColor] = useState('#2563EB');
  const [width, setWidth] = useState(3);
  const [line, setLine] = useState<'solid' | 'dashed' | 'dotted' | 'dashdot'>('solid');
  const fam = shapeFamily(label, subject);
  const inp = 'h-6 w-full rounded border border-border bg-surface-primary px-1 text-[11px]';
  return (
    <div className="space-y-1 border-t border-border p-1.5 text-[10px]" data-testid="chest-new-tool">
      <div className="grid grid-cols-[52px_1fr] items-center gap-1">
        <span className="text-content-tertiary">Type</span>
        <select value={tool} onChange={(e) => setTool(e.target.value)} className={inp} data-testid="chest-new-type">
          {toolTypes.map((t) => <option key={t.tool} value={t.tool}>{t.label}</option>)}
        </select>
        <span className="text-content-tertiary">Subject</span>
        <input value={subject} onChange={(e) => setSubject(e.target.value)} onKeyDown={(e) => e.stopPropagation()} placeholder="W Beam" className={inp} data-testid="chest-new-subject" />
        <span className="text-content-tertiary">Label</span>
        <input value={label} onChange={(e) => setLabel(e.target.value)} onKeyDown={(e) => e.stopPropagation()} placeholder="W12X26" className={inp} data-testid="chest-new-label" />
        <span className="text-content-tertiary">Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.stopPropagation()} placeholder={label || subject || 'Tool name'} className={inp} data-testid="chest-new-name" />
        <span className="text-content-tertiary">Look</span>
        <span className="flex items-center gap-1">
          <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-6 w-7 rounded border border-border p-0" />
          <select value={width} onChange={(e) => setWidth(Number(e.target.value))} className="h-6 rounded border border-border bg-surface-primary px-1 text-[11px]">
            {[1, 1.5, 2, 3, 4, 6, 8].map((w) => <option key={w} value={w}>{w} px</option>)}
          </select>
          <select value={line} onChange={(e) => setLine(e.target.value as typeof line)} className="h-6 min-w-0 flex-1 rounded border border-border bg-surface-primary px-1 text-[11px]">
            <option value="solid">Solid</option>
            <option value="dashed">Dashed</option>
            <option value="dotted">Dotted</option>
            <option value="dashdot">Dash-dot</option>
          </select>
        </span>
      </div>
      {fam && <p className="text-content-tertiary">Shows as: <b>{FAMILY_NAMES[fam]}</b></p>}
      <div className="flex justify-end gap-1 pt-0.5">
        <button type="button" onClick={onCancel} className="rounded px-2 py-0.5 text-content-secondary hover:bg-surface-tertiary">Cancel</button>
        <button
          type="button"
          disabled={!label.trim() && !subject.trim() && !name.trim()}
          onClick={() => {
            const lab = label.trim().toUpperCase() || undefined;
            onSave({
              id: newId('tool'),
              name: name.trim() || lab || subject.trim() || tool,
              tool,
              subject: subject.trim() || (fam ? FAMILY_NAMES[fam] : undefined),
              label: lab,
              style: { color, strokeWidth: width, lineStyle: line },
            });
          }}
          className="rounded bg-oe-blue px-2 py-0.5 font-semibold text-white disabled:opacity-40"
          data-testid="chest-new-save"
        >
          Save tool
        </button>
      </div>
    </div>
  );
}

/** Small drawing of how the tool's markup looks (colour, line, fill). */
function Preview({ item, Icon, size }: { item: ChestItem; Icon?: LucideIcon; size: number }) {
  const s = item.style;
  const color = s.color ?? '#3B82F6';
  const fam = shapeFamily(item.label, item.name, item.subject);
  if (fam) {
    return (
      <span className="relative inline-flex shrink-0 items-center justify-center rounded border border-border bg-white" style={{ width: size, height: size }} title={FAMILY_NAMES[fam]}>
        <svg width={size - 8} height={size - 8} viewBox="0 0 30 30" aria-hidden="true"><ShapeGlyph fam={fam} color={color} /></svg>
        <span className="absolute -bottom-1 -right-1 rounded border border-border bg-surface-primary px-0.5 text-[7px] font-bold leading-[10px] text-content-secondary">{SHORT[fam]}</span>
      </span>
    );
  }
  const w = Math.max(1, Math.min(6, (s.strokeWidth ?? 2) * 0.8));
  const dash = s.lineStyle ? DASH[s.lineStyle] : undefined;
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center rounded border border-border bg-white" style={{ width: size, height: size }}>
      <svg width={size - 6} height={size - 6} viewBox="0 0 30 30" aria-hidden="true">
        {item.tool === 'count' ? (
          <circle cx="15" cy="15" r="7" fill={color} fillOpacity={s.fillAlpha ?? 0.6} stroke={color} strokeWidth={1.5} />
        ) : AREAL.has(item.tool) ? (
          <rect x="4" y="7" width="22" height="16" fill={s.fillColor ?? color} fillOpacity={s.fillAlpha ?? 0.3} stroke={color} strokeWidth={w} strokeDasharray={dash} />
        ) : item.tool === 'text' || item.tool === 'callout' || item.tool === 'stamp' ? (
          <text x="15" y="20" textAnchor="middle" fontSize="14" fontWeight={s.labelBold ? 700 : 500} fontStyle={s.labelItalic ? 'italic' : undefined} fill={s.labelNameColor ?? color}>Aa</text>
        ) : (
          <line x1="4" y1="22" x2="26" y2="8" stroke={color} strokeOpacity={s.strokeAlpha ?? 1} strokeWidth={w} strokeDasharray={dash} strokeLinecap="round" />
        )}
      </svg>
      {Icon && (
        <span className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border border-border bg-surface-primary text-content-secondary">
          <Icon size={9} />
        </span>
      )}
    </span>
  );
}

export function RevuToolChest({ sets, onChange, onUse, onApply, onAddSelection, selectionCount, activeItemId, iconFor, typeLabel, children, toolTypes, onAddStructural }: Props) {
  const [creatingIn, setCreatingIn] = useState<string | null>(null);
  const [view, setView] = useState<'icons' | 'list'>(() => {
    try { return localStorage.getItem('takeoff.toolChest.view') === 'list' ? 'list' : 'icons'; } catch { return 'icons'; }
  });
  const [renaming, setRenaming] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [dropSet, setDropSet] = useState<string | null>(null);
  const setViewMode = (v: 'icons' | 'list') => {
    setView(v);
    try { localStorage.setItem('takeoff.toolChest.view', v); } catch { /* ignore */ }
  };

  const nameInput = (id: string, value: string, commit: (v: string) => void) => (
    <input
      autoFocus
      defaultValue={value}
      onClick={(e) => e.stopPropagation()}
      onBlur={(e) => { commit(e.target.value.trim() || value); setRenaming(null); }}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') setRenaming(null);
      }}
      className="w-full min-w-0 rounded border border-oe-blue bg-surface-primary px-1 text-[11px]"
      data-testid={`chest-rename-${id}`}
    />
  );

  return (
    <div className="flex flex-col gap-2" data-testid="revu-tool-chest">
      <div className="flex items-center gap-1 border-b border-border pb-1.5">
        <span className="flex-1 text-[11px] font-bold uppercase tracking-wider text-content-tertiary">Tool Chest</span>
        {onAddStructural && (
          <button
            type="button"
            onClick={onAddStructural}
            className="flex h-6 w-6 items-center justify-center rounded text-content-secondary hover:bg-surface-tertiary"
            title="Add the structural tool sets (W, WT, HSS, L, CFS, deck)"
            aria-label="Add structural tool sets"
            data-testid="chest-add-structural"
          >
            <Library size={14} />
          </button>
        )}
        <button
          type="button"
          onClick={() => onChange(addSet(sets, `Tool Set ${sets.length}`))}
          className="flex h-6 w-6 items-center justify-center rounded text-content-secondary hover:bg-surface-tertiary"
          title="New tool set"
          aria-label="New tool set"
          data-testid="chest-add-set"
        >
          <FolderPlus size={14} />
        </button>
        <div className="flex rounded border border-border">
          {(['icons', 'list'] as const).map((v) => {
            const VIcon = v === 'icons' ? LayoutGrid : List;
            return (
              <button
                key={v}
                type="button"
                onClick={() => setViewMode(v)}
                aria-pressed={view === v}
                title={v === 'icons' ? 'Icon view' : 'Detail view'}
                className={clsx('flex h-6 w-6 items-center justify-center', view === v ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-tertiary')}
                data-testid={`chest-view-${v}`}
              >
                <VIcon size={12} />
              </button>
            );
          })}
        </div>
      </div>

      {sets.map((set) => {
        const open = !set.collapsed;
        return (
          <section
            key={set.id}
            className={clsx('rounded-md border', dropSet === set.id ? 'border-oe-blue bg-oe-blue/5' : 'border-border/70')}
            onDragOver={(e) => {
              if (!dragId || set.id === RECENT_ID) return;
              e.preventDefault();
              setDropSet(set.id);
            }}
            onDragLeave={() => setDropSet((d) => (d === set.id ? null : d))}
            onDrop={(e) => {
              e.preventDefault();
              if (dragId) onChange(moveItem(sets, dragId, set.id));
              setDragId(null);
              setDropSet(null);
            }}
            data-testid={`chest-set-${set.id}`}
          >
            <header className="group flex items-center gap-1 bg-surface-secondary/60 px-1.5 py-1">
              <button
                type="button"
                onClick={() => onChange(patchSet(sets, set.id, { collapsed: open }))}
                className="flex min-w-0 flex-1 items-center gap-1 text-left"
                aria-expanded={open}
              >
                {open ? <ChevronDown size={12} className="shrink-0 text-content-tertiary" /> : <ChevronRight size={12} className="shrink-0 text-content-tertiary" />}
                {renaming === set.id ? (
                  nameInput(set.id, set.name, (v) => onChange(patchSet(sets, set.id, { name: v })))
                ) : (
                  <span className="truncate text-[11px] font-semibold text-content-primary">{set.name}</span>
                )}
                <span className="shrink-0 text-[10px] text-content-tertiary">({set.items.length})</span>
              </button>
              <button
                type="button"
                onClick={() => onChange(patchSet(sets, set.id, { mode: set.mode === 'drawing' ? 'properties' : 'drawing' }))}
                className={clsx('flex h-5 items-center gap-0.5 rounded px-1 text-[9px] font-semibold', set.mode === 'properties' ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300' : 'bg-oe-blue/10 text-oe-blue')}
                title={set.mode === 'properties' ? 'Properties mode: clicking a tool applies its properties to the selected markups' : 'Drawing mode: clicking a tool starts drawing with it'}
                data-testid={`chest-mode-${set.id}`}
              >
                {set.mode === 'properties' ? <Paintbrush size={10} /> : <PenTool size={10} />}
                {set.mode === 'properties' ? 'Properties' : 'Drawing'}
              </button>
              {!set.recent && (
                <button
                  type="button"
                  onClick={() => { setCreatingIn(set.id); if (set.collapsed) onChange(patchSet(sets, set.id, { collapsed: false })); }}
                  className="flex h-5 w-5 items-center justify-center rounded text-content-secondary hover:bg-surface-tertiary"
                  title="New tool"
                  aria-label="New tool"
                  data-testid={`chest-new-${set.id}`}
                >
                  <SquarePlus size={12} />
                </button>
              )}
              {!set.recent && (
                <button
                  type="button"
                  disabled={selectionCount === 0}
                  onClick={() => onAddSelection(set.id)}
                  className="flex h-5 w-5 items-center justify-center rounded text-content-secondary hover:bg-surface-tertiary disabled:opacity-30"
                  title={selectionCount ? `Add ${selectionCount} selected markup${selectionCount === 1 ? '' : 's'} as tools` : 'Select markups to add them here'}
                  aria-label="Add selected markups"
                  data-testid={`chest-add-selection-${set.id}`}
                >
                  <Plus size={12} />
                </button>
              )}
              {!set.recent && (
                <button type="button" onClick={() => setRenaming(set.id)} className="hidden h-5 w-5 items-center justify-center rounded text-content-tertiary hover:text-oe-blue group-hover:flex" title="Rename set" aria-label="Rename set">
                  <Pencil size={11} />
                </button>
              )}
              {set.recent ? (
                set.items.length > 0 && (
                  <button type="button" onClick={() => onChange(patchSet(sets, set.id, { items: [] }))} className="hidden h-5 items-center rounded px-1 text-[9px] text-content-tertiary hover:text-red-500 group-hover:flex" title="Clear recent tools">
                    Clear
                  </button>
                )
              ) : (
                <button
                  type="button"
                  onClick={() => { if (set.items.length === 0 || window.confirm(`Delete tool set "${set.name}" and its ${set.items.length} tools?`)) onChange(deleteSet(sets, set.id)); }}
                  className="hidden h-5 w-5 items-center justify-center rounded text-content-tertiary hover:text-red-500 group-hover:flex"
                  title="Delete set"
                  aria-label="Delete set"
                >
                  <Trash2 size={11} />
                </button>
              )}
            </header>
            {creatingIn === set.id && (
              <NewToolForm
                toolTypes={toolTypes}
                onCancel={() => setCreatingIn(null)}
                onSave={(it) => { onChange(addItem(sets, set.id, it)); setCreatingIn(null); }}
              />
            )}
            {open && (
              set.items.length === 0 ? (
                <p className="px-2 py-2 text-[10px] italic text-content-tertiary">
                  {set.recent ? 'Tools you draw with appear here.' : 'Press the new-tool button to make a tool, select markups and press + to add them, or drag a tool here.'}
                </p>
              ) : view === 'icons' ? (
                <div className="grid grid-cols-[repeat(auto-fill,minmax(58px,1fr))] gap-1 p-1.5">
                  {set.items.map((item) => (
                    <div key={item.id} className="group relative">
                      <button
                        type="button"
                        draggable
                        onDragStart={() => setDragId(item.id)}
                        onDragEnd={() => { setDragId(null); setDropSet(null); }}
                        onClick={() => (set.mode === 'properties' && selectionCount > 0 ? onApply(item) : onUse(item))}
                        onDoubleClick={() => setRenaming(item.id)}
                        className={clsx(
                          'flex w-full flex-col items-center gap-0.5 rounded p-1 text-center transition-colors',
                          activeItemId === item.id ? 'bg-oe-blue/15 ring-1 ring-oe-blue' : 'hover:bg-surface-secondary',
                        )}
                        title={[item.name, item.subject && `Subject: ${item.subject}`, item.label && `Label: ${item.label}`, typeLabel(item.tool)].filter(Boolean).join('\n')}
                        data-testid={`chest-item-${item.id}`}
                      >
                        <Preview item={item} Icon={iconFor(item.tool)} size={34} />
                        {renaming === item.id ? (
                          nameInput(item.id, item.name, (v) => onChange(patchItem(sets, item.id, { name: v })))
                        ) : (
                          <span className="line-clamp-2 w-full break-words text-[9px] leading-tight text-content-primary">{item.name}</span>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => onChange(removeItem(sets, item.id))}
                        className="absolute right-0 top-0 hidden h-4 w-4 items-center justify-center rounded-full bg-surface-primary text-content-tertiary shadow hover:text-red-500 group-hover:flex"
                        title="Remove tool"
                        aria-label="Remove tool"
                      >
                        <X size={9} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <ul className="divide-y divide-border/50">
                  {set.items.map((item) => (
                    <li
                      key={item.id}
                      draggable
                      onDragStart={() => setDragId(item.id)}
                      onDragEnd={() => { setDragId(null); setDropSet(null); }}
                      className={clsx('group flex items-center gap-2 px-1.5 py-1', activeItemId === item.id ? 'bg-oe-blue/10' : 'hover:bg-surface-secondary/60')}
                    >
                      <button
                        type="button"
                        onClick={() => (set.mode === 'properties' && selectionCount > 0 ? onApply(item) : onUse(item))}
                        className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        data-testid={`chest-item-${item.id}`}
                      >
                        <Preview item={item} Icon={iconFor(item.tool)} size={26} />
                        <span className="min-w-0 flex-1">
                          {renaming === item.id ? (
                            nameInput(item.id, item.name, (v) => onChange(patchItem(sets, item.id, { name: v })))
                          ) : (
                            <span className="block truncate text-[11px] font-semibold text-content-primary">{item.name}</span>
                          )}
                          <span className="block truncate text-[9px] text-content-tertiary">
                            {[(() => { const f = shapeFamily(item.label, item.name, item.subject); return f ? FAMILY_NAMES[f] : typeLabel(item.tool); })(), item.subject, item.label].filter(Boolean).filter((v, i, arr) => arr.indexOf(v) === i).join(' · ')}
                          </span>
                        </span>
                      </button>
                      <button type="button" onClick={() => setRenaming(item.id)} className="hidden text-content-tertiary hover:text-oe-blue group-hover:block" title="Rename" aria-label="Rename">
                        <Pencil size={11} />
                      </button>
                      <button type="button" onClick={() => onChange(removeItem(sets, item.id))} className="hidden text-content-tertiary hover:text-red-500 group-hover:block" title="Remove tool" aria-label="Remove tool">
                        <X size={12} />
                      </button>
                    </li>
                  ))}
                </ul>
              )
            )}
          </section>
        );
      })}
      <p className="text-[10px] leading-snug text-content-tertiary">
        Click a tool to draw with it. Sets in Properties mode apply the tool to the selected markups instead. Drag tools between sets; double-click to rename.
      </p>
      {children}
    </div>
  );
}
