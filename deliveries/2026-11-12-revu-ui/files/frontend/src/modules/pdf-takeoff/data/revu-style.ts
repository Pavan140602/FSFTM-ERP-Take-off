// OE-DELIVERY: 2026-11-02-revu-properties
/**
 * Revu-style markup properties for the PDF takeoff viewer.
 *
 *  - Line style (solid / dashed / dotted / dash-dot) and a fill colour that is
 *    independent of the line colour, per markup.
 *  - Label mode per markup: everything, value only, name only, or hidden.
 *  - Tool properties: the style the NEXT markup of a tool is drawn with, kept
 *    per tool in localStorage (Revu's "properties of the selected tool").
 *  - Show / hide by markup type (Revu's markup-list filter).
 *
 * Pure helpers so they unit-test without the viewer.
 */

import { cleanLabelStyle, type LabelStyle } from '../../../features/takeoff/lib/takeoff-revu-props';

export type LineStyle = 'solid' | 'dashed' | 'dotted' | 'dashdot';
export type LabelMode = 'all' | 'value' | 'name' | 'none';

export const LINE_STYLES: readonly LineStyle[] = ['solid', 'dashed', 'dotted', 'dashdot'];
export const LABEL_MODES: readonly LabelMode[] = ['all', 'value', 'name', 'none'];

export function isLineStyle(v: unknown): v is LineStyle {
  return typeof v === 'string' && (LINE_STYLES as readonly string[]).includes(v);
}
export function isLabelMode(v: unknown): v is LabelMode {
  return typeof v === 'string' && (LABEL_MODES as readonly string[]).includes(v);
}

/**
 * Canvas dash pattern for a line style. ``unit`` is the device-pixel size of
 * one stroke width, so the pattern scales with the line like Revu's does.
 */
export function lineDashFor(style: LineStyle | undefined, unit: number): number[] {
  const u = Math.max(1, unit);
  switch (style) {
    case 'dashed':
      return [6 * u, 4 * u];
    case 'dotted':
      return [1 * u, 3 * u];
    case 'dashdot':
      return [8 * u, 3 * u, 1 * u, 3 * u];
    default:
      return [];
  }
}

/** Which label parts a markup shows, given its mode (undefined = global). */
export function labelParts(mode: LabelMode | undefined): { name: boolean; value: boolean; material: boolean } {
  switch (mode) {
    case 'value':
      return { name: false, value: true, material: false };
    case 'name':
      return { name: true, value: false, material: true };
    case 'none':
      return { name: false, value: false, material: false };
    default:
      return { name: true, value: true, material: true };
  }
}

/** The style fields a tool remembers for its next markup. */
export interface ToolStyle extends LabelStyle {
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  lineStyle?: LineStyle;
  fillAlpha?: number;
  strokeAlpha?: number;
  labelMode?: LabelMode;
}

export type ToolStyles = Record<string, ToolStyle>;

const TOOL_STYLE_KEY = 'takeoff.toolStyles.v1';
const HEX = /^#[0-9a-f]{6}$/i;

function clean(raw: unknown): ToolStyle | null {
  if (!raw || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  const out: ToolStyle = {};
  if (typeof o.color === 'string' && HEX.test(o.color)) out.color = o.color;
  if (typeof o.fillColor === 'string' && HEX.test(o.fillColor)) out.fillColor = o.fillColor;
  if (typeof o.strokeWidth === 'number' && o.strokeWidth >= 0.5 && o.strokeWidth <= 100) out.strokeWidth = o.strokeWidth;
  if (isLineStyle(o.lineStyle)) out.lineStyle = o.lineStyle;
  if (typeof o.fillAlpha === 'number' && o.fillAlpha >= 0 && o.fillAlpha <= 1) out.fillAlpha = o.fillAlpha;
  if (typeof o.strokeAlpha === 'number' && o.strokeAlpha >= 0 && o.strokeAlpha <= 1) out.strokeAlpha = o.strokeAlpha;
  if (isLabelMode(o.labelMode)) out.labelMode = o.labelMode;
  Object.assign(out, cleanLabelStyle(o));
  return Object.keys(out).length ? out : null;
}

/** Parse stored tool styles, dropping anything malformed. */
export function parseToolStyles(raw: string | null): ToolStyles {
  if (!raw) return {};
  try {
    const obj = JSON.parse(raw) as unknown;
    if (!obj || typeof obj !== 'object') return {};
    const out: ToolStyles = {};
    for (const [tool, v] of Object.entries(obj as Record<string, unknown>)) {
      const c = clean(v);
      if (c) out[tool] = c;
    }
    return out;
  } catch {
    return {};
  }
}

export function loadToolStyles(): ToolStyles {
  try {
    return parseToolStyles(localStorage.getItem(TOOL_STYLE_KEY));
  } catch {
    return {};
  }
}

export function saveToolStyles(styles: ToolStyles): void {
  try {
    localStorage.setItem(TOOL_STYLE_KEY, JSON.stringify(styles));
  } catch {
    /* private mode / quota: the styles just do not persist */
  }
}

/** Merge a patch into one tool's style; undefined values clear that field. */
export function patchToolStyle(styles: ToolStyles, tool: string, patch: Partial<ToolStyle>): ToolStyles {
  const merged: Record<string, unknown> = { ...(styles[tool] ?? {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (v === undefined) delete merged[k];
    else merged[k] = v;
  }
  const c = clean(merged);
  const next = { ...styles };
  if (c) next[tool] = c;
  else delete next[tool];
  return next;
}

/** Fields to spread into a new markup drawn with ``tool``. */
export function styleFieldsFor(styles: ToolStyles, tool: string): ToolStyle {
  return { ...(styles[tool] ?? {}) };
}

/** Human names for the show/hide-by-type list, Revu wording. */
export const TYPE_LABELS: Record<string, string> = {
  distance: 'Length',
  polyline: 'Polylength',
  polylineMarkup: 'Polyline',
  cloudPlus: 'Cloud+',
  area: 'Area',
  volume: 'Volume',
  count: 'Count',
  perimeter: 'Perimeter',
  diameter: 'Diameter',
  radiusCenter: 'Radius',
  radius3Point: 'Radius (3-pt)',
  angle: 'Angle',
  arc: 'Arc length',
  polygonCutout: 'Polygon cutout',
  ellipseCutout: 'Ellipse cutout',
  dynamicFill: 'Dynamic fill',
  text: 'Text',
  cloud: 'Cloud',
  arrow: 'Arrow',
  rectangle: 'Rectangle',
  highlight: 'Highlight',
  line: 'Line',
  polygon: 'Polygon',
  ellipse: 'Ellipse',
  pen: 'Pen',
  callout: 'Callout',
  stamp: 'Stamp',
  legend: 'Legend',
};

/** Revu-like wheel zoom: a mouse-wheel notch is one clear step, a trackpad
 *  glides proportionally. Returns the multiplicative zoom factor. */
export function wheelZoomFactor(deltaY: number, deltaMode: number): number {
  if (!Number.isFinite(deltaY) || deltaY === 0) return 1;
  // Line / page delta modes (Firefox mouse wheels) and big pixel deltas are
  // notches: 1.2x per notch, as in Revu.
  const notch = deltaMode !== 0 || Math.abs(deltaY) >= 50;
  if (notch) {
    const notches = deltaMode === 0 ? Math.max(1, Math.round(Math.abs(deltaY) / 100)) : Math.max(1, Math.round(Math.abs(deltaY)));
    return Math.pow(deltaY < 0 ? 1.2 : 1 / 1.2, Math.min(notches, 4));
  }
  return Math.pow(1.0025, -deltaY);
}
