# OE-DELIVERY 2026-11-03-revu-tool-chest-structural: chest UI (shape icons, new tool, structural sets)
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')


def rep(a, b):
    global s
    if s.count(a) != 1:
        print('ANCHOR FAIL', s.count(a), a[:90])
        sys.exit(1)
    s = s.replace(a, b)


rep("""  FolderPlus,
  LayoutGrid,""", """  FolderPlus,
  LayoutGrid,
  Library,
  SquarePlus,""")
rep("""import {
  RECENT_ID,
  addSet,""", """import {
  FAMILY_NAMES,
  RECENT_ID,
  addItem,
  addSet,
  newId,
  shapeFamily,
  type ShapeFamily,""")
rep("""  /** Extra sections under the sets (material libraries). */
  children?: ReactNode;
}""", """  /** Extra sections under the sets. */
  children?: ReactNode;
  /** Tool types offered by "New tool". */
  toolTypes: { tool: string; label: string }[];
  /** Re-add the structural (W / WT / HSS / L / CFS / deck) tool sets. */
  onAddStructural?: () => void;
}""")

GLYPHS = r'''/** Cross-section drawing of a member family (structural tools). */
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
    case 'JOIST':
      return (<g {...sw} strokeWidth={1.8}><path d="M3 8 H27 M3 22 H27" /><path d="M3 22 L7 8 L11 22 L15 8 L19 22 L23 8 L27 22" /></g>);
    default:
      return null;
  }
}

const SHORT: Record<ShapeFamily, string> = { W: 'W', WT: 'WT', HSS: 'HSS', HSSR: 'HSS', L: 'L', C: 'C', 'CFS-S': 'CFS', 'CFS-T': 'TRK', DECK: 'DECK', JOIST: 'JST' };

/** Inline "New tool" form for a set. */
function NewToolForm({ toolTypes, onSave, onCancel }: { toolTypes: { tool: string; label: string }[]; onSave: (it: ChestItem) => void; onCancel: () => void }) {
  const [tool, setTool] = useState(toolTypes[1]?.tool ?? 'distance');
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

'''
PREVIEW_ANCHOR = "/** Small drawing of how the tool's markup looks (colour, line, fill). */"
rep(PREVIEW_ANCHOR, GLYPHS + PREVIEW_ANCHOR)

rep("""function Preview({ item, Icon, size }: { item: ChestItem; Icon?: LucideIcon; size: number }) {
  const s = item.style;
  const color = s.color ?? '#3B82F6';""", """function Preview({ item, Icon, size }: { item: ChestItem; Icon?: LucideIcon; size: number }) {
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
  }""")

rep("""export function RevuToolChest({ sets, onChange, onUse, onApply, onAddSelection, selectionCount, activeItemId, iconFor, typeLabel, children }: Props) {""",
    """export function RevuToolChest({ sets, onChange, onUse, onApply, onAddSelection, selectionCount, activeItemId, iconFor, typeLabel, children, toolTypes, onAddStructural }: Props) {
  const [creatingIn, setCreatingIn] = useState<string | null>(null);""")

rep("""        <button
          type="button"
          onClick={() => onChange(addSet(sets, `Tool Set ${sets.length}`))}""", """        {onAddStructural && (
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
          onClick={() => onChange(addSet(sets, `Tool Set ${sets.length}`))}""")

rep("""              {!set.recent && (
                <button
                  type="button"
                  disabled={selectionCount === 0}""", """              {!set.recent && (
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
                  disabled={selectionCount === 0}""")

rep("""            </header>
            {open && (""", """            </header>
            {creatingIn === set.id && (
              <NewToolForm
                toolTypes={toolTypes}
                onCancel={() => setCreatingIn(null)}
                onSave={(it) => { onChange(addItem(sets, set.id, it)); setCreatingIn(null); }}
              />
            )}
            {open && (""")

rep("""                  {set.recent ? 'Tools you draw with appear here.' : 'Select markups and press + to add them, or drag a tool here.'}""",
    """                  {set.recent ? 'Tools you draw with appear here.' : 'Press the new-tool button to make a tool, select markups and press + to add them, or drag a tool here.'}""")

rep("""                            {[typeLabel(item.tool), item.subject, item.label].filter(Boolean).join(' · ')}""",
    """                            {[(() => { const f = shapeFamily(item.label, item.name, item.subject); return f ? FAMILY_NAMES[f] : typeLabel(item.tool); })(), item.subject, item.label].filter(Boolean).filter((v, i, arr) => arr.indexOf(v) === i).join(' · ')}""")

p.write_text(s, encoding='utf-8')
print('ok')
