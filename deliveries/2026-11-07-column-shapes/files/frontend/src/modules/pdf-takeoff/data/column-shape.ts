/**
 * Column symbols drawn by shape (OE-DELIVERY 2026-11-07-column-shapes).
 *
 * Every column markup - found by Auto Takeoff or placed by hand with a
 * profile - is drawn as the section it is, so anyone reading the sheet sees
 * what each column is:
 *   - wide flange (W, HP, S, M): an I, web along the symbol's long side, turned
 *     the way it is drawn on the plan;
 *   - square HSS: a square;
 *   - rectangular HSS: a rectangle, turned like the plan symbol;
 *   - round HSS / pipe: a circle.
 */

export type ColumnShapeKind = 'wide-flange' | 'hss-square' | 'hss-rect' | 'round' | 'unknown';

export interface ColumnShape {
  kind: ColumnShapeKind;
  /** Nominal depth and width in inches (long side first) when the profile says. */
  d?: number;
  b?: number;
}

const WF_RE = /^(?:W|HP|S|M)\s*(\d+(?:\.\d+)?)\s*X\s*\d+/i;
const HSS_RE = /^HSS\s*(\d+(?:\.\d+)?)\s*X\s*(\d*\.?\d+)(?:\s*X\s*([\d./]+))?/i;
const PIPE_RE = /^(?:PIPE|STD\s*PIPE|XS\s*PIPE|XXS\s*PIPE)/i;

/** Shape of a column from its profile text (W14X90, HSS8X8X1/2, HSS8X4X1/4,
 *  HSS6.625X.280, PIPE6STD ...). */
export function columnShape(profile: string | null | undefined): ColumnShape {
  const p = (profile ?? '').trim().toUpperCase().replace(/\s+/g, '');
  if (!p) return { kind: 'unknown' };
  if (PIPE_RE.test(p)) return { kind: 'round' };
  const w = WF_RE.exec(p);
  if (w) {
    const d = Number(w[1]);
    // Flange width of a W section is roughly half to the full depth; draw the
    // usual proportion when the symbol on the sheet does not tell.
    return { kind: 'wide-flange', d, b: Math.max(4, Math.min(d, d * 0.6)) };
  }
  const h = HSS_RE.exec(p);
  if (h) {
    const a = Number(h[1]);
    const b = Number(h[2]);
    // Round HSS: diameter x wall (HSS6.625X.280) - one size and a thin wall.
    if (!h[3] && b < 1) return { kind: 'round', d: a, b: a };
    if (Math.abs(a - b) < 1e-6) return { kind: 'hss-square', d: a, b: a };
    return { kind: 'hss-rect', d: Math.max(a, b), b: Math.min(a, b) };
  }
  return { kind: 'unknown' };
}

/** The slice of a measurement read here. */
export interface ColumnLike {
  type: string;
  auto?: { cat?: string; des?: string } | null;
  customFields?: Record<string, unknown> | null;
  annotation?: string;
  label?: string;
  group?: string;
}

const COLUMN_SUBJECT_RE = /\b(column|post|col)\b/i;

/** The profile a column markup carries: the size set on it, else what Auto
 *  Takeoff read. */
export function columnProfileOf(m: ColumnLike): string {
  const mat = m.customFields?.Material;
  if (typeof mat === 'string' && mat.trim()) return mat.trim();
  if (m.auto?.des) return m.auto.des;
  return (m.annotation || m.label || '').trim();
}

/** A column placed by hand: a count markup whose Subject says column / post,
 *  or whose profile is a column section (W, HSS, pipe). */
export function isManualColumn(m: ColumnLike): boolean {
  if (m.type !== 'count' || m.auto) return false;
  const subj = m.customFields?.Subject;
  if (typeof subj === 'string' && COLUMN_SUBJECT_RE.test(subj)) return true;
  if (m.group && COLUMN_SUBJECT_RE.test(m.group)) return true;
  return columnShape(columnProfileOf(m)).kind !== 'unknown';
}

/** Any column markup: found by Auto Takeoff or placed by hand. */
export function isColumnMarkup(m: ColumnLike): boolean {
  return m.auto?.cat === 'columns' || isManualColumn(m);
}

/** Normalised profile used to group "same profile" columns. */
export function profileKey(profile: string): string {
  return profile.toUpperCase().replace(/\s+/g, '').replace(/^COL(UMN)?$/, 'COLUMN');
}

/**
 * Draw a column symbol centred at (x, y) on a canvas (screen pixels).
 * ``size`` is the symbol's long side and ``short`` its short side in pixels,
 * ``angle`` the long side's direction in radians.
 */
export function drawColumnSymbol(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  shape: ColumnShape,
  size: number,
  short: number,
  angle: number,
  colour: string,
  lineWidth: number,
): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.strokeStyle = colour;
  ctx.lineWidth = lineWidth;
  const L = size / 2;
  const S = short / 2;
  ctx.beginPath();
  switch (shape.kind) {
    case 'round':
      ctx.arc(0, 0, L, 0, Math.PI * 2);
      break;
    case 'hss-square':
      ctx.rect(-L, -L, 2 * L, 2 * L);
      // Inner wall line: a tube, not a solid bar.
      ctx.rect(-L * 0.72, -L * 0.72, 1.44 * L, 1.44 * L);
      break;
    case 'hss-rect': {
      const s = Math.max(S, L * 0.35);
      ctx.rect(-L, -s, 2 * L, 2 * s);
      ctx.rect(-L + s * 0.28, -s * 0.72, 2 * L - s * 0.56, 1.44 * s);
      break;
    }
    case 'wide-flange': {
      // Web along the long side (x), flanges across it at both ends.
      const bf = Math.max(S, L * 0.5);
      const tf = Math.max(lineWidth, L * 0.16);
      ctx.moveTo(-L, -bf);
      ctx.lineTo(-L, bf);
      ctx.moveTo(L, -bf);
      ctx.lineTo(L, bf);
      ctx.moveTo(-L, 0);
      ctx.lineTo(L, 0);
      ctx.stroke();
      // Flanges drawn as filled bars so the I reads at any zoom.
      ctx.fillStyle = colour;
      ctx.fillRect(-L - tf / 2, -bf, tf, 2 * bf);
      ctx.fillRect(L - tf / 2, -bf, tf, 2 * bf);
      ctx.restore();
      return;
    }
    default:
      // Size not known: the old ring with a cross.
      ctx.arc(0, 0, L, 0, Math.PI * 2);
      ctx.moveTo(-L * 0.7, -L * 0.7);
      ctx.lineTo(L * 0.7, L * 0.7);
      ctx.moveTo(L * 0.7, -L * 0.7);
      ctx.lineTo(-L * 0.7, L * 0.7);
  }
  ctx.stroke();
  ctx.restore();
}
