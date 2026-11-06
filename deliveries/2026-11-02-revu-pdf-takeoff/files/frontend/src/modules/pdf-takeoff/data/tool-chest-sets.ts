// OE-DELIVERY: 2026-11-02-revu-tool-chest
/**
 * Bluebeam Revu-style Tool Chest: named tool sets (Recent Tools, My Tools and
 * any the user adds), each holding tools that remember their markup type,
 * Subject, Label, group and every property (colour, line, width, fill,
 * opacity, units, caption, text style). A set is in Drawing mode (click =
 * draw with that tool) or Properties mode (click = apply the tool's
 * properties to the selected markups). Pure helpers, stored in localStorage.
 */
import { cleanLabelStyle } from '../../../features/takeoff/lib/takeoff-revu-props';
import { parseToolStyles, type ToolStyle } from './revu-style';

export interface ChestItem {
  id: string;
  name: string;
  tool: string;
  subject?: string;
  label?: string;
  group?: string;
  style: ToolStyle;
}

export interface ChestSet {
  id: string;
  name: string;
  mode: 'drawing' | 'properties';
  collapsed?: boolean;
  /** The automatic Recent Tools set. */
  recent?: boolean;
  items: ChestItem[];
}

export const RECENT_ID = 'recent';
export const RECENT_MAX = 12;
const KEY = 'takeoff.toolChest.v2';
const OLD_KEY = 'takeoff.toolChest.v1';

export function newId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function cleanStyle(raw: unknown): ToolStyle {
  const parsed = parseToolStyles(JSON.stringify({ x: raw ?? {} }));
  return parsed.x ?? {};
}

function cleanItem(raw: unknown): ChestItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  if (typeof o.id !== 'string' || typeof o.name !== 'string' || typeof o.tool !== 'string') return null;
  const item: ChestItem = { id: o.id, name: o.name.slice(0, 80), tool: o.tool, style: cleanStyle(o.style) };
  if (typeof o.subject === 'string' && o.subject) item.subject = o.subject.slice(0, 120);
  if (typeof o.label === 'string' && o.label) item.label = o.label.slice(0, 120);
  if (typeof o.group === 'string' && o.group) item.group = o.group.slice(0, 120);
  return item;
}

export function defaultSets(): ChestSet[] {
  return [
    { id: RECENT_ID, name: 'Recent Tools', mode: 'drawing', recent: true, items: [] },
    { id: 'my-tools', name: 'My Tools', mode: 'drawing', items: [] },
  ];
}

/** Parse stored sets; always returns Recent Tools first. */
export function parseSets(raw: string | null): ChestSet[] {
  let sets: ChestSet[] = [];
  try {
    const arr = raw ? (JSON.parse(raw) as unknown) : null;
    if (Array.isArray(arr)) {
      for (const s of arr) {
        if (!s || typeof s !== 'object') continue;
        const o = s as Record<string, unknown>;
        if (typeof o.id !== 'string' || typeof o.name !== 'string') continue;
        sets.push({
          id: o.id,
          name: o.name.slice(0, 80),
          mode: o.mode === 'properties' ? 'properties' : 'drawing',
          collapsed: o.collapsed === true,
          recent: o.id === RECENT_ID,
          items: Array.isArray(o.items) ? (o.items.map(cleanItem).filter(Boolean) as ChestItem[]) : [],
        });
      }
    }
  } catch {
    sets = [];
  }
  if (sets.length === 0) sets = defaultSets();
  if (!sets.some((s) => s.id === RECENT_ID)) sets.unshift(defaultSets()[0]!);
  const recent = sets.find((s) => s.id === RECENT_ID)!;
  return [recent, ...sets.filter((s) => s.id !== RECENT_ID)];
}

/** The v1 chest (flat list of saved tools) becomes "My Tools". */
export function migrateV1(raw: string | null): ChestItem[] {
  try {
    const arr = raw ? (JSON.parse(raw) as unknown) : null;
    if (!Array.isArray(arr)) return [];
    return arr
      .filter((t) => t && typeof t.id === 'string' && typeof t.tool === 'string')
      .map((t) => ({
        id: String(t.id),
        name: String(t.name ?? t.tool),
        tool: String(t.tool),
        subject: typeof t.subject === 'string' ? t.subject : undefined,
        label: typeof t.label === 'string' ? t.label : undefined,
        group: typeof t.group === 'string' ? t.group : undefined,
        style: cleanStyle({ color: t.color }),
      }));
  } catch {
    return [];
  }
}

export function loadSets(): ChestSet[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return parseSets(raw);
    const sets = defaultSets();
    const old = migrateV1(localStorage.getItem(OLD_KEY));
    if (old.length) sets[1]!.items = old;
    return sets;
  } catch {
    return defaultSets();
  }
}

export function saveSets(sets: ChestSet[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(sets));
  } catch {
    /* private mode: the chest just does not persist */
  }
}

/** Two tools are "the same" for Recent Tools when type, Subject, Label and look match. */
export function itemSignature(i: Pick<ChestItem, 'tool' | 'subject' | 'label' | 'style'>): string {
  const s = i.style;
  return [i.tool, i.subject ?? '', i.label ?? '', s.color ?? '', s.strokeWidth ?? '', s.lineStyle ?? '', s.fillColor ?? ''].join('|');
}

/** Put a tool at the top of Recent Tools (deduplicated, capped). */
export function recordRecent(sets: ChestSet[], item: ChestItem): ChestSet[] {
  const sig = itemSignature(item);
  return sets.map((s) => {
    if (s.id !== RECENT_ID) return s;
    const rest = s.items.filter((x) => itemSignature(x) !== sig);
    return { ...s, items: [item, ...rest].slice(0, RECENT_MAX) };
  });
}

export function addItem(sets: ChestSet[], setId: string, item: ChestItem): ChestSet[] {
  return sets.map((s) => (s.id === setId ? { ...s, items: [...s.items, item] } : s));
}
export function removeItem(sets: ChestSet[], itemId: string): ChestSet[] {
  return sets.map((s) => ({ ...s, items: s.items.filter((i) => i.id !== itemId) }));
}
export function patchItem(sets: ChestSet[], itemId: string, patch: Partial<ChestItem>): ChestSet[] {
  return sets.map((s) => ({ ...s, items: s.items.map((i) => (i.id === itemId ? { ...i, ...patch } : i)) }));
}
/** Move (or, out of Recent Tools, copy) a tool into another set. */
export function moveItem(sets: ChestSet[], itemId: string, toSetId: string): ChestSet[] {
  const from = sets.find((s) => s.items.some((i) => i.id === itemId));
  const item = from?.items.find((i) => i.id === itemId);
  if (!from || !item || from.id === toSetId || toSetId === RECENT_ID) return sets;
  const copy = from.id === RECENT_ID ? { ...item, id: newId('tool') } : item;
  return sets.map((s) => {
    if (s.id === toSetId) return { ...s, items: [...s.items, copy] };
    if (s.id === from.id && from.id !== RECENT_ID) return { ...s, items: s.items.filter((i) => i.id !== itemId) };
    return s;
  });
}
export function addSet(sets: ChestSet[], name: string): ChestSet[] {
  return [...sets, { id: newId('set'), name: name.trim() || 'New Tool Set', mode: 'drawing', items: [] }];
}
export function patchSet(sets: ChestSet[], setId: string, patch: Partial<ChestSet>): ChestSet[] {
  return sets.map((s) => (s.id === setId ? { ...s, ...patch } : s));
}
export function deleteSet(sets: ChestSet[], setId: string): ChestSet[] {
  return setId === RECENT_ID ? sets : sets.filter((s) => s.id !== setId);
}

interface MarkupLike {
  type: string;
  annotation?: string;
  group?: string;
  customFields?: Record<string, string>;
  [k: string]: unknown;
}
const STYLE_KEYS = ['color', 'fillColor', 'strokeWidth', 'lineStyle', 'fillAlpha', 'strokeAlpha', 'labelMode'] as const;

/** A tool built from an existing markup (Revu "Add to Tool Chest"). */
export function itemFromMarkup(m: MarkupLike, name?: string): ChestItem {
  const style: Record<string, unknown> = {};
  for (const k of STYLE_KEYS) if (m[k] !== undefined) style[k] = m[k];
  Object.assign(style, cleanLabelStyle(m));
  const subject = m.customFields?.Subject?.trim() || undefined;
  const label = (m.annotation ?? '').trim() || m.customFields?.Material?.trim() || undefined;
  return {
    id: newId('tool'),
    name: name ?? (label || subject || m.type),
    tool: m.type,
    subject,
    label,
    group: m.group || undefined,
    style: cleanStyle(style),
  };
}
