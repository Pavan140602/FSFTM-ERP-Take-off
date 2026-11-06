/**
 * Stud walls drawn the way an estimator marks them (OE-DELIVERY 2026-11-08-stud-walls):
 * the wall at its full width as a see-through band (the drawing shows
 * through), a stud across the band at every spacing (one at each end), and
 * the header area over an opening as its own hatched band with no studs.
 */

export interface WallTagLike {
  /** Full wall width, PDF units. */
  ww?: number;
  /** Stud spacing, PDF units and inches. */
  sd?: number;
  ss?: number;
  /** 'wall' | 'header'. */
  seg?: string;
}

export interface Pt {
  x: number;
  y: number;
}

function runLength(pts: Pt[]): number {
  let L = 0;
  for (let i = 0; i + 1 < pts.length; i++) L += Math.hypot(pts[i + 1]!.x - pts[i]!.x, pts[i + 1]!.y - pts[i]!.y);
  return L;
}

/** Studs in a run: one at the start, one at every spacing, one at the end -
 *  ceil(L / s) + 1. Header areas carry none (header, jacks and kings are
 *  counted with the header). */
export function studCount(pts: Pt[], tag: WallTagLike | undefined): number {
  if (!tag || tag.seg === 'header' || !tag.sd || tag.sd <= 0) return 0;
  const L = runLength(pts);
  if (L <= 0) return 0;
  return Math.ceil(L / tag.sd - 1e-6) + 1;
}

/** Positions of the studs along a straight run (PDF units). */
export function studPositions(a: Pt, b: Pt, spacing: number): Pt[] {
  const L = Math.hypot(b.x - a.x, b.y - a.y);
  if (L <= 0 || spacing <= 0) return [];
  const ux = (b.x - a.x) / L;
  const uy = (b.y - a.y) / L;
  const out: Pt[] = [];
  // Every spacing from the start, then the end stud: ceil(L / s) + 1.
  for (let t = 0; t < L - 1e-6; t += spacing) out.push({ x: a.x + ux * t, y: a.y + uy * t });
  out.push({ ...b });
  return out;
}

/**
 * Draw a wall band with its studs. ``k`` is screen pixels per PDF unit.
 * The band is filled at ``alpha`` so the drawing stays readable through it.
 */
export function drawStudWall(
  ctx: CanvasRenderingContext2D,
  pts: Pt[],
  tag: WallTagLike,
  k: number,
  colour: string,
  alpha = 0.28,
  showStuds = true,
): void {
  const w = tag.ww ?? 0;
  if (w <= 0 || pts.length < 2) return;
  const header = tag.seg === 'header';
  ctx.save();
  ctx.setLineDash([]);
  for (let i = 0; i + 1 < pts.length; i++) {
    const a = pts[i]!;
    const b = pts[i + 1]!;
    const L = Math.hypot(b.x - a.x, b.y - a.y);
    if (L <= 0) continue;
    const nx = (-(b.y - a.y) / L) * (w / 2);
    const ny = ((b.x - a.x) / L) * (w / 2);
    const quad: Pt[] = [
      { x: a.x + nx, y: a.y + ny },
      { x: b.x + nx, y: b.y + ny },
      { x: b.x - nx, y: b.y - ny },
      { x: a.x - nx, y: a.y - ny },
    ];
    ctx.beginPath();
    quad.forEach((q, qi) => (qi === 0 ? ctx.moveTo(q.x * k, q.y * k) : ctx.lineTo(q.x * k, q.y * k)));
    ctx.closePath();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = colour;
    ctx.fill();
    ctx.globalAlpha = Math.min(1, alpha * 3);
    ctx.strokeStyle = colour;
    ctx.lineWidth = Math.max(1, 0.5 * k);
    if (header) ctx.setLineDash([Math.max(3, 3 * k), Math.max(2, 2 * k)]);
    ctx.stroke();
    ctx.setLineDash([]);
    if (header) {
      // Header area: diagonal hatch, no studs.
      ctx.save();
      ctx.clip();
      ctx.globalAlpha = Math.min(1, alpha * 2.2);
      ctx.lineWidth = Math.max(1, 0.4 * k);
      const step = Math.max(w, 3);
      const ux = (b.x - a.x) / L;
      const uy = (b.y - a.y) / L;
      for (let t = -w; t <= L + w; t += step) {
        const p = { x: a.x + ux * t, y: a.y + uy * t };
        ctx.beginPath();
        ctx.moveTo((p.x - nx - ux * w) * k, (p.y - ny - uy * w) * k);
        ctx.lineTo((p.x + nx + ux * w) * k, (p.y + ny + uy * w) * k);
        ctx.stroke();
      }
      ctx.restore();
    } else if (showStuds && tag.sd && tag.sd > 0) {
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = Math.max(1.2, 0.9 * k);
      for (const s of studPositions(a, b, tag.sd)) {
        ctx.beginPath();
        ctx.moveTo((s.x + nx) * k, (s.y + ny) * k);
        ctx.lineTo((s.x - nx) * k, (s.y - ny) * k);
        ctx.stroke();
      }
    }
  }
  ctx.restore();
}
