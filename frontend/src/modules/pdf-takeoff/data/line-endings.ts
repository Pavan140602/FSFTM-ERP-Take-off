// FSFTM line endings (OE-DELIVERY 2026-11-25-fsftm-pdf): the Start / End
// arrowhead styles for lines, polylines, lengths and arrows, picked from the
// properties bar like in snap-style PDF markup tools.

export type LineEnding =
  | 'none'
  | 'openArrow'
  | 'closedArrow'
  | 'circle'
  | 'filledCircle'
  | 'square'
  | 'filledSquare'
  | 'diamond'
  | 'butt'
  | 'slash';

export const LINE_ENDINGS: { value: LineEnding; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'openArrow', label: 'Open arrow' },
  { value: 'closedArrow', label: 'Closed arrow' },
  { value: 'circle', label: 'Circle' },
  { value: 'filledCircle', label: 'Filled circle' },
  { value: 'square', label: 'Square' },
  { value: 'filledSquare', label: 'Filled square' },
  { value: 'diamond', label: 'Diamond' },
  { value: 'butt', label: 'Bar' },
  { value: 'slash', label: 'Slash' },
];

const VALID = new Set<string>(LINE_ENDINGS.map((e) => e.value));

export function isLineEnding(v: unknown): v is LineEnding {
  return typeof v === 'string' && VALID.has(v);
}

/** Markup types that can carry line endings. */
export const LINE_ENDING_TYPES = new Set(['line', 'distance', 'polyline', 'arrow', 'polylineMarkup']);

interface Pt {
  x: number;
  y: number;
}

/**
 * Draw one line ending at `tip`, oriented along the segment `from -> tip`.
 * `size` is in canvas pixels; stroke / fill use the context's current colours.
 */
export function drawLineEnding(ctx: CanvasRenderingContext2D, tip: Pt, from: Pt, style: LineEnding | undefined, size: number): void {
  if (!style || style === 'none') return;
  const ang = Math.atan2(tip.y - from.y, tip.x - from.x);
  const cos = Math.cos(ang);
  const sin = Math.sin(ang);
  // Local frame: +u along the line towards the tip, +v perpendicular.
  const at = (u: number, v: number): [number, number] => [tip.x + u * cos - v * sin, tip.y + u * sin + v * cos];
  ctx.save();
  ctx.setLineDash([]);
  ctx.lineJoin = 'miter';
  ctx.beginPath();
  switch (style) {
    case 'openArrow': {
      ctx.moveTo(...at(-size, -size * 0.5));
      ctx.lineTo(...at(0, 0));
      ctx.lineTo(...at(-size, size * 0.5));
      ctx.stroke();
      break;
    }
    case 'closedArrow': {
      ctx.moveTo(...at(0, 0));
      ctx.lineTo(...at(-size, -size * 0.45));
      ctx.lineTo(...at(-size, size * 0.45));
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'circle':
    case 'filledCircle': {
      ctx.arc(tip.x, tip.y, size * 0.4, 0, Math.PI * 2);
      if (style === 'filledCircle') ctx.fill();
      else {
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.stroke();
      }
      break;
    }
    case 'square':
    case 'filledSquare': {
      const h = size * 0.38;
      ctx.moveTo(...at(-h, -h));
      ctx.lineTo(...at(h, -h));
      ctx.lineTo(...at(h, h));
      ctx.lineTo(...at(-h, h));
      ctx.closePath();
      if (style === 'filledSquare') ctx.fill();
      else {
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.stroke();
      }
      break;
    }
    case 'diamond': {
      const h = size * 0.5;
      ctx.moveTo(...at(h, 0));
      ctx.lineTo(...at(0, -h * 0.7));
      ctx.lineTo(...at(-h, 0));
      ctx.lineTo(...at(0, h * 0.7));
      ctx.closePath();
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.stroke();
      break;
    }
    case 'butt': {
      ctx.moveTo(...at(0, -size * 0.5));
      ctx.lineTo(...at(0, size * 0.5));
      ctx.stroke();
      break;
    }
    case 'slash': {
      ctx.moveTo(...at(-size * 0.35, size * 0.5));
      ctx.lineTo(...at(size * 0.35, -size * 0.5));
      ctx.stroke();
      break;
    }
    default:
      break;
  }
  ctx.restore();
}

/**
 * Draw a markup's Start / End endings: Start at the first point (pointing
 * backwards out of the line), End at the last point.
 */
export function drawMarkupEndings(
  ctx: CanvasRenderingContext2D,
  pts: Pt[],
  start: LineEnding | undefined,
  end: LineEnding | undefined,
  size: number,
): void {
  if (pts.length < 2) return;
  if (start && start !== 'none') drawLineEnding(ctx, pts[0]!, pts[1]!, start, size);
  if (end && end !== 'none') drawLineEnding(ctx, pts[pts.length - 1]!, pts[pts.length - 2]!, end, size);
}
