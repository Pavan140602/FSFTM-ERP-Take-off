"""Update 15c: Revu tool popover on the properties bar - Subject, Label,
Layer, Set as Default, Add to Tool Chest - for an armed tool or selected
markups (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")

# ── RevuPropertiesBar: the popover ──
q = base / "components/RevuPropertiesBar.tsx"
t = q.read_text(encoding="utf-8")


def trep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)


trep("""interface Props {
  /** 'selection' edits the selected markups, 'tool' the armed tool's defaults. */""", """/** Revu's tool popover (update 15): Subject, Label, Layer, Set as Default,
 *  Add to Tool Chest. */
export interface ToolPopover {
  icon?: ComponentType<{ size?: number | string; className?: string }>;
  subject: string;
  label: string;
  layer: string;
  layers: string[];
  onSubject: (v: string) => void;
  onLabel: (v: string) => void;
  onLayer: (v: string) => void;
  onSetDefault: () => void;
  chestSets: { id: string; name: string }[];
  onAddToChest: (setId: string) => void;
}

interface Props {
  popover?: ToolPopover;
  /** 'selection' edits the selected markups, 'tool' the armed tool's defaults. */""")
trep("export function RevuPropertiesBar({ mode, type, title, value, subject, onSubject, label, onLabel, onWallHeight, onPatch, totals, defaults, onAddToChest, onLayoutFraming }: Props) {",
     "export function RevuPropertiesBar({ mode, type, title, value, subject, onSubject, label, onLabel, onWallHeight, onPatch, totals, defaults, onAddToChest, onLayoutFraming, popover }: Props) {\n  const [popOpen, setPopOpen] = useState(false);\n  const [chestOpen, setChestOpen] = useState(false);")
trep("""      {/* Revu-style tab naming what is being edited. */}
      <span
        className="-my-0.5 shrink-0 select-none rounded-t-md border-b-2 border-oe-blue bg-surface-primary px-2 pt-1.5 text-[11px] font-bold text-oe-blue"
        title={title}
        data-testid="props-tab"
      >
        {off ? 'Properties' : title}
      </span>""", """      {/* Revu tool button: icon + name; the arrow opens Subject / Label /
          Layer / Set as Default / Add to Tool Chest (update 15). */}
      <div className="relative -my-0.5 shrink-0">
        <button
          type="button"
          disabled={off || !popover}
          onClick={() => { setPopOpen((v) => !v); setChestOpen(false); }}
          className="flex select-none items-center gap-1 rounded-t-md border-b-2 border-oe-blue bg-surface-primary px-2 pt-1 pb-0.5 text-[11px] font-bold text-oe-blue disabled:cursor-default"
          title={popover ? `${title} - Subject, Label, Layer, Set as Default, Add to Tool Chest` : title}
          data-testid="props-tab"
          aria-expanded={popOpen}
        >
          {popover?.icon && <popover.icon size={15} />}
          <span>{off ? 'Properties' : title}</span>
          {popover && !off && <ChevronDown size={11} />}
        </button>
        {popOpen && popover && !off && (
          <div className="absolute left-0 top-full z-50 mt-1 w-[330px] rounded-md border border-border bg-surface-elevated p-2.5 shadow-xl" data-testid="props-tool-popover">
            <div className="grid grid-cols-[52px_1fr] items-center gap-x-2 gap-y-1.5 text-[11px]">
              <span className="text-right text-content-secondary">Subject:</span>
              <TextField value={popover.subject} onCommit={popover.onSubject} placeholder="e.g. Polylength Measurement" width="w-full" testId="pop-subject" />
              <span className="text-right text-content-secondary">Label:</span>
              <TextField value={popover.label} onCommit={popover.onLabel} placeholder="e.g. W12x26" width="w-full" testId="pop-label" />
              <span className="text-right text-content-secondary">Layer:</span>
              <select value={popover.layer} onChange={(e) => popover.onLayer(e.target.value)} className={clsx(sel, 'w-full')} data-testid="pop-layer">
                {Array.from(new Set([popover.layer, ...popover.layers])).filter(Boolean).map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              <button type="button" onClick={() => { popover.onSetDefault(); setPopOpen(false); }} className="h-7 rounded border border-border bg-surface-primary text-[11px] hover:bg-surface-secondary" data-testid="pop-set-default">
                Set as Default
              </button>
              <div className="relative">
                <button type="button" onClick={() => setChestOpen((v) => !v)} className="flex h-7 w-full items-center justify-center gap-1 rounded border border-border bg-surface-primary text-[11px] hover:bg-surface-secondary" data-testid="pop-add-chest">
                  Add to Tool Chest <ChevronDown size={11} />
                </button>
                {chestOpen && (
                  <div className="absolute right-0 top-full z-50 mt-1 max-h-64 w-52 overflow-y-auto rounded border border-border bg-surface-elevated py-1 shadow-lg" data-testid="pop-chest-list">
                    {popover.chestSets.map((cs) => (
                      <button key={cs.id} type="button" onClick={() => { popover.onAddToChest(cs.id); setChestOpen(false); setPopOpen(false); }} className="block w-full truncate px-2 py-1 text-left text-[11px] hover:bg-oe-blue hover:text-white">
                        {cs.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>""")
if "useState" not in t.split("\n", 30)[0:30].__str__():
    pass
if "import { useState" not in t and "useState," not in t and ", useState" not in t:
    t = t.replace("import ", "import { useState } from 'react';\nimport ", 1)
if "ComponentType" not in t.split("export interface ToolPopover")[0]:
    t = t.replace("import ", "import type { ComponentType } from 'react';\nimport ", 1)
if "ChevronDown" not in t.split("export interface ToolPopover")[0]:
    t = t.replace("import ", "import { ChevronDown } from 'lucide-react';\nimport ", 1)
q.write_text(t, encoding="utf-8")

# ── Viewer: feed it ──
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# Tool Subject / Label as state (mirrors the refs) + per-tool defaults.
rep("""  const toolSubjectRef = useRef<string | null>(null);""", """  const toolSubjectRef = useRef<string | null>(null);
  /** Armed tool's Subject / Label for the popover (mirrors the refs, update 15). */
  const [toolSL, setToolSL] = useState<{ subject: string; label: string }>({ subject: '', label: '' });
  /** Per-tool Subject / Label saved with Set as Default. */
  const toolSLDefaultsRef = useRef<Record<string, { subject?: string; label?: string; group?: string }>>(
    (() => { try { return JSON.parse(localStorage.getItem('oe-tool-sl-defaults') || '{}'); } catch { return {}; } })(),
  );""")
rep("""    // A manual tool switch drops the chest tool's sticky label + subject.
    toolLabelRef.current = null;
    toolSubjectRef.current = null;""", """    // A manual tool switch drops the chest tool's sticky label + subject,
    // then applies the tool's own defaults (Set as Default, update 15).
    {
      const d = toolSLDefaultsRef.current[tool] ?? {};
      toolLabelRef.current = d.label || null;
      toolSubjectRef.current = d.subject || null;
      setToolSL({ subject: d.subject || '', label: d.label || '' });
      if (d.group) setActiveGroup(d.group);
    }""")
rep("""      toolSubjectRef.current = item.subject ?? null;
      toolLabelRef.current = item.label ?? null;""", """      toolSubjectRef.current = item.subject ?? null;
      toolLabelRef.current = item.label ?? null;
      setToolSL({ subject: item.subject ?? '', label: item.label ?? '' });""")

# Popover data.
rep("""  const chestIconFor = useCallback((tool: string) => stripTools.find((x) => x.tool === tool)?.icon, [stripTools]);""",
    """  const chestIconFor = useCallback((tool: string) => stripTools.find((x) => x.tool === tool)?.icon, [stripTools]);
  /** Revu tool popover on the properties bar (update 15). */
  const toolPopover = (() => {
    const sets = chestSets.filter((x) => !x.recent).map((x) => ({ id: x.id, name: x.name }));
    if (propsBar.mode === 'selection') {
      const first = propsSelected[0];
      return {
        icon: chestIconFor(propsBar.type),
        subject: propsBar.subject ?? '',
        label: propsBar.label ?? '',
        layer: first?.group || 'General',
        layers: availableGroups,
        onSubject: setPropsSubject,
        onLabel: setPropsLabel,
        onLayer: (g: string) => setMeasurements((prev) => prev.map((m) => (propsSelectedIds.has(m.id) && !m.locked ? { ...m, group: g } : m))),
        onSetDefault: () => {
          if (!first) return;
          const it = itemFromMarkup(first as unknown as Parameters<typeof itemFromMarkup>[0]);
          setToolStyles((prev) => patchToolStyle(prev, first.type, it.style as Partial<ToolStyle>));
          toolSLDefaultsRef.current = { ...toolSLDefaultsRef.current, [first.type]: { subject: it.subject, label: it.label, group: first.group || undefined } };
          try { localStorage.setItem('oe-tool-sl-defaults', JSON.stringify(toolSLDefaultsRef.current)); } catch { /* ignore */ }
          addToast({ type: 'success', title: 'Set as default', message: `${TYPE_LABELS[first.type] ?? first.type}: new markups use this look, Subject and Label.` });
        },
        chestSets: sets,
        onAddToChest: (id: string) => addSelectionToChest(id),
      };
    }
    if (propsBar.mode === 'tool') {
      const tool = activeTool as string;
      return {
        icon: chestIconFor(tool),
        subject: toolSL.subject,
        label: toolSL.label,
        layer: activeGroup,
        layers: availableGroups,
        onSubject: (v: string) => { toolSubjectRef.current = v.trim() || null; setToolSL((x) => ({ ...x, subject: v.trim() })); },
        onLabel: (v: string) => { toolLabelRef.current = v.trim() || null; setToolSL((x) => ({ ...x, label: v.trim() })); },
        onLayer: (g: string) => setActiveGroup(g),
        onSetDefault: () => {
          toolSLDefaultsRef.current = { ...toolSLDefaultsRef.current, [tool]: { subject: toolSL.subject || undefined, label: toolSL.label || undefined, group: activeGroup } };
          try { localStorage.setItem('oe-tool-sl-defaults', JSON.stringify(toolSLDefaultsRef.current)); } catch { /* ignore */ }
          addToast({ type: 'success', title: 'Set as default', message: `${TYPE_LABELS[tool] ?? tool}: this look, Subject and Label are used every time.` });
        },
        chestSets: sets,
        onAddToChest: (id: string) => {
          const style = styleFieldsFor(toolStyles, tool);
          const name = toolSL.label || toolSL.subject || (TYPE_LABELS[tool] ?? tool);
          setChestSets((prev) => chestAddItem(prev, id, { id: `tool_${Date.now()}`, name, tool, subject: toolSL.subject || undefined, label: toolSL.label || undefined, group: activeGroup, style }));
          addToast({ type: 'success', title: `Added to ${chestSets.find((x) => x.id === id)?.name ?? 'Tool Chest'}`, message: name });
        },
      };
    }
    return undefined;
  })();""")
rep("""              <RevuPropertiesBar
                mode={propsBar.mode}""", """              <RevuPropertiesBar
                popover={toolPopover}
                mode={propsBar.mode}""")
p.write_text(s, encoding="utf-8")
print("ok")
