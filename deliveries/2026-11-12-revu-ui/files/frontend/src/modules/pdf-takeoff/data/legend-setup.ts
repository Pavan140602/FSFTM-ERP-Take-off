// OE-DELIVERY: 2026-11-12-revu-ui (legend setup / properties)
/**
 * Per-legend setup, like Revu's legend properties: title (text, size,
 * style), columns, cells (size, style, colour), font, text colour, opacity,
 * line colour / width / style, fill and fill opacity, and whether it stays
 * live with the sheet (markups of the same Subject and look join it).
 */

export type LegendBorder = 'grid' | 'horizontal' | 'vertical' | 'outline' | 'none';

export interface LegendTextStyle {
  size?: number;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  color?: string;
}

export interface LegendSetup {
  title?: string;
  showTitle?: boolean;
  /** Column keys in order (count, subject, label, material, length, ...). */
  columns?: string[];
  border?: LegendBorder;
  /** Rows follow the sheet: markups drawn later with the same Subject and
   *  look as the picked ones are counted too. */
  live?: boolean;
  /** The markups the legend was made from. */
  ids?: string[];
  /** Markups taken out with Legend ▸ None. */
  excludeIds?: string[];
  font?: string;
  /** Text colour for the whole legend (title / cells may override). */
  textColor?: string;
  titleStyle?: LegendTextStyle;
  cellStyle?: LegendTextStyle;
  /** 0..1 - the whole legend. */
  opacity?: number;
  lineColor?: string;
  lineWidth?: number;
  /** Background; null = no fill. */
  fill?: string | null;
  /** 0..1 */
  fillOpacity?: number;
}

export const LEGEND_BORDERS: { key: LegendBorder; label: string; hint: string }[] = [
  { key: 'grid', label: 'Grid', hint: 'Vertical and horizontal lines' },
  { key: 'horizontal', label: 'Horizontal', hint: 'Lines between rows only' },
  { key: 'vertical', label: 'Vertical', hint: 'Lines between columns only' },
  { key: 'outline', label: 'Outline', hint: 'A frame round the table' },
  { key: 'none', label: 'None', hint: 'No lines' },
];

export const LEGEND_FONTS = ['Arial', 'Helvetica', 'Calibri', 'Verdana', 'Tahoma', 'Segoe UI', 'Times New Roman', 'Georgia', 'Courier New'];

/** Columns a new legend keeps unless the user picks others (Revu's own). */
export const LEGEND_DEFAULT_COLUMNS = ['count', 'subject', 'length', 'area', 'unit'];

export const LEGEND_TITLE_SIZE = 13;
export const LEGEND_CELL_SIZE = 11;

/** Resolved look of one legend (setup over the panel defaults). */
export function legendLook(s: LegendSetup | undefined, defaults: { text: string; bg: string; border: LegendBorder }) {
  const textColor = s?.textColor ?? defaults.text;
  return {
    font: s?.font || 'Arial',
    textColor,
    title: {
      size: s?.titleStyle?.size ?? LEGEND_TITLE_SIZE,
      bold: s?.titleStyle?.bold ?? true,
      italic: s?.titleStyle?.italic ?? false,
      underline: s?.titleStyle?.underline ?? false,
      color: s?.titleStyle?.color ?? textColor,
    },
    cell: {
      size: s?.cellStyle?.size ?? LEGEND_CELL_SIZE,
      bold: s?.cellStyle?.bold ?? false,
      italic: s?.cellStyle?.italic ?? false,
      underline: s?.cellStyle?.underline ?? false,
      color: s?.cellStyle?.color ?? textColor,
    },
    opacity: s?.opacity ?? 1,
    lineColor: s?.lineColor ?? (s?.border ? '#374151' : '#9ca3af'),
    lineWidth: s?.lineWidth ?? 1,
    fill: s?.fill === null ? null : s?.fill ?? defaults.bg,
    fillOpacity: s?.fillOpacity ?? 1,
    border: s?.border ?? defaults.border,
  };
}

/** Canvas font string. */
export function legendFont(st: { size: number; bold: boolean; italic: boolean }, px: number, family: string): string {
  return `${st.italic ? 'italic ' : ''}${st.bold ? 'bold ' : ''}${px}px "${family}", sans-serif`;
}

function cleanText(v: unknown): LegendTextStyle | undefined {
  if (!v || typeof v !== 'object') return undefined;
  const o = v as Record<string, unknown>;
  const out: LegendTextStyle = {};
  if (typeof o.size === 'number' && o.size >= 4 && o.size <= 72) out.size = o.size;
  for (const k of ['bold', 'italic', 'underline'] as const) if (typeof o[k] === 'boolean') out[k] = o[k] as boolean;
  if (typeof o.color === 'string' && /^#[0-9a-f]{6}$/i.test(o.color)) out.color = o.color;
  return Object.keys(out).length ? out : undefined;
}

const hex = (v: unknown) => (typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v) ? v : undefined);
const unit = (v: unknown) => (typeof v === 'number' && v >= 0 && v <= 1 ? v : undefined);

export function cleanLegendSetup(v: unknown): LegendSetup | undefined {
  if (!v || typeof v !== 'object') return undefined;
  const o = v as Record<string, unknown>;
  const out: LegendSetup = {};
  if (typeof o.title === 'string') out.title = o.title.slice(0, 120);
  if (typeof o.showTitle === 'boolean') out.showTitle = o.showTitle;
  if (Array.isArray(o.columns)) out.columns = o.columns.filter((c): c is string => typeof c === 'string').slice(0, 40);
  if (typeof o.border === 'string' && LEGEND_BORDERS.some((b) => b.key === o.border)) out.border = o.border as LegendBorder;
  if (typeof o.live === 'boolean') out.live = o.live;
  if (Array.isArray(o.ids)) out.ids = o.ids.filter((c): c is string => typeof c === 'string').slice(0, 5000);
  if (Array.isArray(o.excludeIds)) out.excludeIds = o.excludeIds.filter((c): c is string => typeof c === 'string').slice(0, 5000);
  if (typeof o.font === 'string' && o.font.length <= 60) out.font = o.font;
  if (hex(o.textColor)) out.textColor = hex(o.textColor);
  const ts = cleanText(o.titleStyle);
  if (ts) out.titleStyle = ts;
  const cs = cleanText(o.cellStyle);
  if (cs) out.cellStyle = cs;
  if (unit(o.opacity) !== undefined) out.opacity = unit(o.opacity);
  if (hex(o.lineColor)) out.lineColor = hex(o.lineColor);
  if (typeof o.lineWidth === 'number' && o.lineWidth >= 0 && o.lineWidth <= 12) out.lineWidth = o.lineWidth;
  if (o.fill === null) out.fill = null;
  else if (hex(o.fill)) out.fill = hex(o.fill);
  if (unit(o.fillOpacity) !== undefined) out.fillOpacity = unit(o.fillOpacity);
  return Object.keys(out).length ? out : undefined;
}

/** Row heights of a legend at scale 1 (PDF units), from its font sizes. */
export function legendMetrics(s: LegendSetup | undefined, padV: number) {
  const tf = (s?.titleStyle?.size ?? LEGEND_TITLE_SIZE) / LEGEND_TITLE_SIZE;
  const cf = (s?.cellStyle?.size ?? LEGEND_CELL_SIZE) / LEGEND_CELL_SIZE;
  return {
    tf,
    cf,
    titleH: 30 * tf + padV,
    colH: 16 * cf + padV,
    rowH: 24 * cf + padV,
    pad: 10,
  };
}

export function legendTotalHeight(rowCount: number, met: ReturnType<typeof legendMetrics>, showTitle: boolean): number {
  return (showTitle ? met.titleH : 0) + met.colH + rowCount * met.rowH + met.pad;
}
