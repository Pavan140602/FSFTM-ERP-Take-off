// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Keyboard shortcut map for the PDF Takeoff toolbar.
 *
 * Bluebeam Revu default keys: V select, L line, A arrow, R rectangle,
 * E ellipse, C cloud, T text, Q callout, H highlight, P pen, J dynamic fill;
 * measurements on Shift+Alt (L length, A area, C count, ...).
 */

import type { MeasureTool } from './takeoff-types';

/** Single-key → tool map (lowercased keys). */
export const TOOL_SHORTCUT_MAP: Readonly<Record<string, MeasureTool>> = {
  // Bluebeam Revu single-key defaults (OE-DELIVERY 2026-11-02-revu-shortcuts);
  // the Shift+Alt measurement keys live in modules/pdf-takeoff/data/revu-shortcuts.ts.
  v: 'select',
  l: 'line',
  a: 'arrow',
  r: 'rectangle',
  e: 'ellipse',
  c: 'cloud',
  k: 'cloud',
  t: 'text',
  w: 'text',
  q: 'callout',
  n: 'callout',
  h: 'highlight',
  p: 'pen',
  j: 'dynamicFill',
};

/** Reverse map — tool → uppercase shortcut letter, for tooltip suffixes.
 *  Partial so a stale takeoff-types.ts (missing new tools) never breaks the build. */
export const SHORTCUT_LETTER: Partial<Readonly<Record<MeasureTool, string>>> = {
  select: 'V',
  distance: 'Shift+Alt+L',
  polyline: 'Shift+Alt+Q',
  area: 'Shift+Alt+A',
  volume: 'Shift+Alt+V',
  count: 'Shift+Alt+C',
  perimeter: 'Shift+Alt+P',
  diameter: 'Shift+Alt+D',
  radiusCenter: 'Shift+Alt+U',
  angle: 'Shift+Alt+G',
  dynamicFill: 'J',
  rectangle: 'R',
  text: 'T',
  highlight: 'H',
  cloud: 'C',
  arrow: 'A',
  line: 'L',
  polygon: 'Shift+P',
  ellipse: 'E',
  pen: 'P',
  callout: 'Q',
};

/**
 * Resolve a raw keyboard event `key` to the matching tool, or `null` if the
 * key is not a tool shortcut.  Case-insensitive.
 */
export function shortcutToTool(key: string): MeasureTool | null {
  if (!key || key.length !== 1) return null;
  return TOOL_SHORTCUT_MAP[key.toLowerCase()] ?? null;
}

/** Build a tooltip label with the shortcut letter suffix. */
export function labelWithShortcut(label: string, tool: MeasureTool): string {
  const letter = SHORTCUT_LETTER[tool];
  return letter ? `${label} (${letter})` : label;
}

/**
 * Guard: should a keyboard shortcut fire in the current focus context?
 *
 * Returns false when the event target is a text input, textarea or
 * contenteditable element — so typing in the properties panel never
 * switches tools.
 */
export function shouldHandleShortcut(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return true;
  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return false;
  if (target.isContentEditable) return false;
  return true;
}
