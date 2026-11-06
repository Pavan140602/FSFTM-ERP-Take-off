/**
 * Revu-style Text Box (OE-DELIVERY 2026-11-07-text-box).
 *
 * A text box is a markup with its own type style, like Bluebeam Revu's Text
 * Box: font, size, bold / italic / underline / strike-through, alignment,
 * text colour, fill colour and opacity, border colour / width / style, inner
 * margin and overall opacity. The canvas draw, the in-place editor and the
 * hit-test all lay the text out with the same functions here, so what you
 * type is exactly what lands on the sheet.
 *
 * Sizes are in PDF units (points at 100 %), so a 12 pt box reads 12 pt on
 * the printed sheet.
 */

export type TextAlign = 'left' | 'center' | 'right';
export type BorderStyle = 'solid' | 'dashed' | 'dotted' | 'cloud';

export interface TextStyle {
  font: string;
  size: number;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strike: boolean;
  align: TextAlign;
  /** Text colour; undefined follows the markup colour. */
  color?: string;
  /** Fill colour; null = no fill. */
  fill: string | null;
  fillAlpha: number;
  /** Border colour; null = no border; undefined follows the text colour. */
  border?: string | null;
  borderWidth: number;
  borderStyle: BorderStyle;
  /** Inner margin, PDF units. */
  padding: number;
  /** Whole-box opacity 0..1. */
  opacity: number;
  /** Line height as a multiple of the size. */
  lineHeight: number;
}

export const TEXT_FONTS = ['Arial', 'Helvetica', 'Calibri', 'Verdana', 'Tahoma', 'Times New Roman', 'Georgia', 'Courier New', 'Consolas'] as const;
export const TEXT_SIZES = [6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72] as const;

/** A new text box: Revu's default look (Arial, border in the text colour, no fill). */
export const DEFAULT_TEXT_STYLE: TextStyle = {
  font: 'Arial',
  size: 12,
  bold: false,
  italic: false,
  underline: false,
  strike: false,
  align: 'left',
  fill: null,
  fillAlpha: 1,
  borderWidth: 1,
  borderStyle: 'solid',
  padding: 4,
  opacity: 1,
  lineHeight: 1.25,
};

/** Text boxes made before this delivery: bold 14, no border, no fill. */
export const LEGACY_TEXT_STYLE: TextStyle = {
  ...DEFAULT_TEXT_STYLE,
  font: 'sans-serif',
  size: 14,
  bold: true,
  border: null,
  padding: 5,
  lineHeight: 19 / 14,
};

const HEX_RE = /^#[0-9a-fA-F]{3,8}$/;

function num(v: unknown, lo: number, hi: number): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : undefined;
}

/** A style read back from storage, keeping only valid values. */
export function cleanTextStyle(raw: unknown): Partial<TextStyle> | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const r = raw as Record<string, unknown>;
  const out: Partial<TextStyle> = {};
  if (typeof r.font === 'string' && r.font.length > 0 && r.font.length < 64) out.font = r.font;
  const size = num(r.size, 2, 400);
  if (size !== undefined) out.size = size;
  for (const k of ['bold', 'italic', 'underline', 'strike'] as const) if (typeof r[k] === 'boolean') out[k] = r[k] as boolean;
  if (r.align === 'left' || r.align === 'center' || r.align === 'right') out.align = r.align;
  if (typeof r.color === 'string' && HEX_RE.test(r.color)) out.color = r.color;
  if (r.fill === null || (typeof r.fill === 'string' && HEX_RE.test(r.fill))) out.fill = r.fill as string | null;
  const fa = num(r.fillAlpha, 0, 1);
  if (fa !== undefined) out.fillAlpha = fa;
  if (r.border === null || (typeof r.border === 'string' && HEX_RE.test(r.border))) out.border = r.border as string | null;
  const bw = num(r.borderWidth, 0, 20);
  if (bw !== undefined) out.borderWidth = bw;
  if (r.borderStyle === 'solid' || r.borderStyle === 'dashed' || r.borderStyle === 'dotted' || r.borderStyle === 'cloud') out.borderStyle = r.borderStyle;
  const pad = num(r.padding, 0, 100);
  if (pad !== undefined) out.padding = pad;
  const op = num(r.opacity, 0.05, 1);
  if (op !== undefined) out.opacity = op;
  const lh = num(r.lineHeight, 0.8, 3);
  if (lh !== undefined) out.lineHeight = lh;
  return Object.keys(out).length > 0 ? out : undefined;
}

/** The full style of a text markup: its own settings over the defaults
 *  (legacy look for boxes with no style of their own). */
export function resolveTextStyle(own: Partial<TextStyle> | undefined): TextStyle {
  return own ? { ...DEFAULT_TEXT_STYLE, ...own } : LEGACY_TEXT_STYLE;
}

/** CSS font for a style at a pixel size. */
export function fontCss(s: TextStyle, px: number): string {
  const fam = s.font === 'sans-serif' ? 'Arial, Helvetica, sans-serif' : `"${s.font}", Arial, Helvetica, sans-serif`;
  return `${s.italic ? 'italic ' : ''}${s.bold ? 'bold ' : ''}${px}px ${fam}`;
}

let measureCtx: CanvasRenderingContext2D | null | undefined;
function ctxForMeasure(): CanvasRenderingContext2D | null {
  if (measureCtx === undefined) {
    try {
      measureCtx = document.createElement('canvas').getContext('2d');
    } catch {
      measureCtx = null;
    }
  }
  return measureCtx;
}

/** Width of a string in PDF units for a style. */
export function measureText(text: string, s: TextStyle): number {
  const ctx = ctxForMeasure();
  if (!ctx) return text.length * s.size * 0.55;
  ctx.font = fontCss(s, s.size);
  return ctx.measureText(text).width;
}

/** Wrap text to an inner width (PDF units), keeping typed line breaks and
 *  breaking a word longer than the line. */
export function wrapText(text: string, innerWidth: number, s: TextStyle, measure: (t: string) => number = (t) => measureText(t, s)): string[] {
  const maxW = Math.max(s.size, innerWidth);
  const out: string[] = [];
  for (const para of (text ?? '').split('\n')) {
    const words = para.split(/(\s+)/).filter((w) => w.length > 0);
    if (words.length === 0) {
      out.push('');
      continue;
    }
    let line = '';
    for (const w of words) {
      const trial = line + w;
      if (line.trim() && measure(trial.trimEnd()) > maxW && w.trim()) {
        out.push(line.trimEnd());
        line = '';
      }
      if (!w.trim() && !line) continue; // no leading space on a new line
      // A single word wider than the box breaks by characters.
      if (w.trim() && measure(w) > maxW) {
        let chunk = line;
        for (const ch of w) {
          if (chunk && measure(chunk + ch) > maxW) {
            out.push(chunk);
            chunk = '';
          }
          chunk += ch;
        }
        line = chunk;
        continue;
      }
      line += w;
    }
    out.push(line.trimEnd());
  }
  return out.length > 0 ? out : [''];
}

/** Lines and the box height the content needs at a width. */
export function layoutTextBox(text: string, width: number, s: TextStyle, measure?: (t: string) => number): { lines: string[]; contentHeight: number } {
  const lines = wrapText(text, width - 2 * s.padding - s.borderWidth, s, measure);
  const contentHeight = lines.length * s.size * s.lineHeight + 2 * s.padding + s.borderWidth;
  return { lines, contentHeight };
}

/** Width that fits the longest typed line (no wrapping), for a new box. */
export function naturalWidth(text: string, s: TextStyle): number {
  const longest = Math.max(0, ...(text || '').split('\n').map((l) => measureText(l, s)));
  return Math.ceil(longest + 2 * s.padding + s.borderWidth + 2);
}

function cloudRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  // Scallops along each side, bulging outward.
  const side = (x0: number, y0: number, x1: number, y1: number) => {
    const len = Math.hypot(x1 - x0, y1 - y0);
    const n = Math.max(1, Math.round(len / (2 * r)));
    const dx = (x1 - x0) / n;
    const dy = (y1 - y0) / n;
    const ang = Math.atan2(dy, dx);
    for (let i = 0; i < n; i++) {
      const cx = x0 + dx * (i + 0.5);
      const cy = y0 + dy * (i + 0.5);
      ctx.arc(cx, cy, Math.hypot(dx, dy) / 2, ang + Math.PI, ang, false);
    }
  };
  ctx.moveTo(x, y);
  side(x, y, x + w, y);
  side(x + w, y, x + w, y + h);
  side(x + w, y + h, x, y + h);
  side(x, y + h, x, y);
}

/**
 * Draw a text box. (x, y) is its top-left corner and k the screen pixels
 * per PDF unit (zoom × device pixel ratio). ``markupColour`` is used where
 * the style follows the markup colour.
 */
export function drawTextBox(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  lines: string[],
  s: TextStyle,
  k: number,
  markupColour: string,
): void {
  const text = s.color || markupColour;
  const border = s.border === undefined ? text : s.border;
  ctx.save();
  ctx.globalAlpha *= s.opacity;
  const X = x * k;
  const Y = y * k;
  const W = w * k;
  const H = h * k;
  if (s.fill) {
    ctx.save();
    ctx.globalAlpha *= s.fillAlpha;
    ctx.fillStyle = s.fill;
    ctx.fillRect(X, Y, W, H);
    ctx.restore();
  }
  if (border && s.borderWidth > 0) {
    ctx.strokeStyle = border;
    ctx.lineWidth = Math.max(1, s.borderWidth * k);
    ctx.setLineDash(
      s.borderStyle === 'dashed' ? [6 * k, 4 * k] : s.borderStyle === 'dotted' ? [Math.max(1, s.borderWidth * k), 3 * k] : [],
    );
    ctx.beginPath();
    if (s.borderStyle === 'cloud') cloudRect(ctx, X, Y, W, H, Math.max(4, s.size * 0.6) * k);
    else ctx.rect(X, Y, W, H);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  const px = s.size * k;
  ctx.font = fontCss(s, px);
  ctx.fillStyle = text;
  ctx.textBaseline = 'top';
  const inner = (w - 2 * s.padding - s.borderWidth) * k;
  const left = X + (s.padding + s.borderWidth / 2) * k;
  ctx.save();
  // Text never spills outside its box (a box resized smaller clips).
  ctx.beginPath();
  ctx.rect(X, Y, W, H);
  ctx.clip();
  lines.forEach((line, i) => {
    const lw = ctx.measureText(line).width;
    const lx = s.align === 'center' ? left + (inner - lw) / 2 : s.align === 'right' ? left + inner - lw : left;
    const ly = Y + (s.padding + s.borderWidth / 2) * k + i * s.size * s.lineHeight * k + ((s.lineHeight - 1) * px) / 2;
    ctx.fillText(line, lx, ly);
    if ((s.underline || s.strike) && lw > 0) {
      ctx.strokeStyle = text;
      ctx.lineWidth = Math.max(1, px / 14);
      ctx.beginPath();
      if (s.underline) {
        ctx.moveTo(lx, ly + px * 1.02);
        ctx.lineTo(lx + lw, ly + px * 1.02);
      }
      if (s.strike) {
        ctx.moveTo(lx, ly + px * 0.55);
        ctx.lineTo(lx + lw, ly + px * 0.55);
      }
      ctx.stroke();
    }
  });
  ctx.restore();
  ctx.textBaseline = 'alphabetic';
  ctx.restore();
}

const STYLE_KEY = 'takeoff.textBox.style.v1';

/** The style new text boxes start with (the last one set with the Text Box
 *  tool active, like Revu's tool defaults). */
export function loadToolTextStyle(): Partial<TextStyle> {
  try {
    const raw = localStorage.getItem(STYLE_KEY);
    return (raw && cleanTextStyle(JSON.parse(raw))) || {};
  } catch {
    return {};
  }
}

export function saveToolTextStyle(s: Partial<TextStyle>): void {
  try {
    localStorage.setItem(STYLE_KEY, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}
