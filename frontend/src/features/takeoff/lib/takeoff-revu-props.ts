// OE-DELIVERY: 2026-11-02-revu-properties-bar
/**
 * Revu Properties toolbar: per-markup units, area units, caption pick list,
 * caption text style, and selection totals. Pure helpers so they unit-test
 * without the viewer.
 */

/** Length unit a markup's caption reads in. */
export type DispUnit = 'in' | 'ft' | 'ftin' | 'mm' | 'cm' | 'm' | 'km';
/** Area unit a markup's caption reads in. */
export type AreaDispUnit = 'sq in' | 'sq ft' | 'sq cm' | 'sq m' | 'sq mm';
/** What a markup's caption shows (Revu "Caption" pick list). */
export type CaptionKey = 'label' | 'length' | 'area' | 'perimeter' | 'wallArea' | 'depth' | 'volume' | 'count';

export const DISP_UNITS: readonly { id: DispUnit; label: string }[] = [
  { id: 'in', label: 'in' },
  { id: 'ft', label: 'ft' },
  { id: 'ftin', label: "ft-in" },
  { id: 'mm', label: 'mm' },
  { id: 'cm', label: 'cm' },
  { id: 'm', label: 'm' },
  { id: 'km', label: 'km' },
];
export const AREA_DISP_UNITS: readonly { id: AreaDispUnit; label: string }[] = [
  { id: 'sq in', label: 'sq in' },
  { id: 'sq ft', label: 'sq ft' },
  { id: 'sq cm', label: 'sq cm' },
  { id: 'sq m', label: 'sq m' },
  { id: 'sq mm', label: 'sq mm' },
];
export const CAPTION_LABELS: Record<CaptionKey, string> = {
  label: 'Label',
  length: 'Length',
  area: 'Area',
  perimeter: 'Perimeter',
  wallArea: 'Wall Area',
  depth: 'Depth',
  volume: 'Volume',
  count: 'Count',
};

export function isDispUnit(v: unknown): v is DispUnit {
  return typeof v === 'string' && DISP_UNITS.some((u) => u.id === v);
}
export function isAreaDispUnit(v: unknown): v is AreaDispUnit {
  return typeof v === 'string' && AREA_DISP_UNITS.some((u) => u.id === v);
}
export function isCaptionKey(v: unknown): v is CaptionKey {
  return typeof v === 'string' && v in CAPTION_LABELS;
}

const LINEAR = new Set(['distance', 'polyline', 'perimeter', 'diameter', 'radiusCenter', 'radius3Point', 'arc', 'line']);
const AREAL = new Set(['area', 'rectarea', 'polygonCutout', 'ellipseCutout', 'dynamicFill']);

/** Caption choices that make sense for a markup type (Revu shows the same
 *  list for every tool; the irrelevant ones are left out here). */
export function captionOptionsFor(type: string): CaptionKey[] {
  if (LINEAR.has(type)) return ['label', 'length', 'wallArea', 'depth'];
  if (AREAL.has(type)) return ['label', 'area', 'perimeter', 'depth', 'volume'];
  if (type === 'volume') return ['label', 'volume', 'area', 'perimeter', 'depth'];
  if (type === 'count') return ['label', 'count'];
  return ['label'];
}
export function hasLengthUnit(type: string): boolean {
  return LINEAR.has(type) || AREAL.has(type) || type === 'volume';
}
export function hasAreaUnit(type: string): boolean {
  return AREAL.has(type) || type === 'volume' || LINEAR.has(type);
}

/** Metres per display length unit. */
export const METRES_PER: Record<Exclude<DispUnit, 'ftin'>, number> = {
  in: 0.0254,
  ft: 0.3048,
  mm: 0.001,
  cm: 0.01,
  m: 1,
  km: 1000,
};
/** Square metres per display area unit. */
export const SQM_PER: Record<AreaDispUnit, number> = {
  'sq in': 0.00064516,
  'sq ft': 0.09290304,
  'sq cm': 1e-4,
  'sq m': 1,
  'sq mm': 1e-6,
};

/** Label text style stored on a markup and its metadata (``label_style``). */
export interface LabelStyle {
  labelFont?: string;
  labelBold?: boolean;
  labelItalic?: boolean;
  labelUnderline?: boolean;
  labelTextSize?: number;
  labelMaterialSize?: number;
  labelDimSize?: number;
  labelNameColor?: string;
  labelMaterialColor?: string;
  labelDimColor?: string;
  dispUnit?: DispUnit;
  dispAreaUnit?: AreaDispUnit;
  captions?: CaptionKey[];
}

const HEX = /^#[0-9a-f]{6}$/i;
const FONT = /^[A-Za-z0-9 \-]{1,40}$/;

/** Keep only well-formed label style fields (metadata / localStorage input). */
export function cleanLabelStyle(raw: unknown): LabelStyle {
  const out: LabelStyle = {};
  if (!raw || typeof raw !== 'object') return out;
  const o = raw as Record<string, unknown>;
  if (typeof o.labelFont === 'string' && FONT.test(o.labelFont)) out.labelFont = o.labelFont;
  for (const k of ['labelBold', 'labelItalic', 'labelUnderline'] as const) {
    if (typeof o[k] === 'boolean') out[k] = o[k] as boolean;
  }
  for (const k of ['labelTextSize', 'labelMaterialSize', 'labelDimSize'] as const) {
    const v = o[k];
    if (typeof v === 'number' && v >= 4 && v <= 200) out[k] = v;
  }
  for (const k of ['labelNameColor', 'labelMaterialColor', 'labelDimColor'] as const) {
    const v = o[k];
    if (typeof v === 'string' && HEX.test(v)) out[k] = v;
  }
  if (isDispUnit(o.dispUnit)) out.dispUnit = o.dispUnit;
  if (isAreaDispUnit(o.dispAreaUnit)) out.dispAreaUnit = o.dispAreaUnit;
  if (Array.isArray(o.captions)) {
    const caps = o.captions.filter(isCaptionKey);
    out.captions = Array.from(new Set(caps));
  }
  return out;
}

/** The label style fields of a markup, for the metadata blob (null = none). */
export function labelStyleOf(m: LabelStyle): LabelStyle | null {
  const c = cleanLabelStyle(m);
  return Object.keys(c).length ? c : null;
}

/** CSS font weight/style prefix for a markup, falling back to the globals. */
export function fontPrefix(m: LabelStyle, globalBold: boolean, globalItalic: boolean): string {
  const italic = m.labelItalic ?? globalItalic;
  const bold = m.labelBold ?? globalBold;
  return `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}`;
}

export interface TotalsInput {
  type: string;
  value: number;
  unit?: string;
  points: unknown[];
  area?: number;
  wallHeight?: number;
}
/** Sum a selection the way Revu's Properties toolbar totals it. */
export function selectionTotals(ms: readonly TotalsInput[]): { length: number; area: number; volume: number; count: number; n: number } {
  let length = 0;
  let area = 0;
  let volume = 0;
  let count = 0;
  for (const m of ms) {
    const v = Number.isFinite(m.value) ? m.value : 0;
    if (LINEAR.has(m.type)) {
      length += v;
      if (m.wallHeight && m.wallHeight > 0 && (m.type === 'distance' || m.type === 'polyline')) area += v * m.wallHeight;
    } else if (AREAL.has(m.type)) area += m.type === 'polygonCutout' || m.type === 'ellipseCutout' ? -Math.abs(v) : v;
    else if (m.type === 'volume') volume += v;
    else if (m.type === 'count') count += m.points.length;
  }
  return { length, area, volume, count, n: ms.length };
}
