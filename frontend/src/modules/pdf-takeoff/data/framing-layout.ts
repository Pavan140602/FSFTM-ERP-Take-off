// OE-DELIVERY: 2026-11-04-framing-layout
/**
 * Lay out framing that is not drawn: members (trusses, joists, hat
 * channels ...) across an outline at a set spacing and direction, clipped to
 * the outline. E.g. a gable roof: draw the roof outline, pick "perpendicular
 * to the ridge", 24" O.C. -> one truss line per 24" across the roof.
 */

export interface Pt {
  x: number;
  y: number;
}

export type StartAt = 'edge' | 'half' | 'full';

/**
 * Member lines across ``poly`` running at ``angleRad`` (0 = horizontal on the
 * sheet), ``spacing`` apart (PDF units), clipped to the polygon (concave
 * outlines give several pieces per line).
 */
export function layoutMembers(poly: Pt[], angleRad: number, spacing: number, startAt: StartAt = 'edge', includeEnd = true): [Pt, Pt][] {
  if (poly.length < 3 || !(spacing > 0)) return [];
  const ux = Math.cos(angleRad);
  const uy = Math.sin(angleRad);
  const nx = -uy;
  const ny = ux;
  const ts = poly.map((p) => p.x * nx + p.y * ny);
  const tMin = Math.min(...ts);
  const tMax = Math.max(...ts);
  const eps = Math.min(spacing * 0.01, 0.05);
  const first = tMin + (startAt === 'half' ? spacing / 2 : startAt === 'full' ? spacing : eps);
  const offsets: number[] = [];
  for (let t = first; t < tMax - eps; t += spacing) offsets.push(t);
  if (includeEnd && (offsets.length === 0 || tMax - eps - offsets[offsets.length - 1]! > spacing * 0.25)) offsets.push(tMax - eps);
  const out: [Pt, Pt][] = [];
  for (const t of offsets) {
    const hits: number[] = [];
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i]!;
      const b = poly[(i + 1) % poly.length]!;
      const ta = a.x * nx + a.y * ny - t;
      const tb = b.x * nx + b.y * ny - t;
      if ((ta > 0 && tb > 0) || (ta < 0 && tb < 0) || ta === tb) continue;
      const k = ta / (ta - tb);
      const x = a.x + (b.x - a.x) * k;
      const y = a.y + (b.y - a.y) * k;
      hits.push(x * ux + y * uy);
    }
    hits.sort((p, q) => p - q);
    for (let i = 0; i + 1 < hits.length; i += 2) {
      const s0 = hits[i]!;
      const s1 = hits[i + 1]!;
      if (s1 - s0 < spacing * 0.05) continue;
      out.push([
        { x: s0 * ux + t * nx, y: s0 * uy + t * ny },
        { x: s1 * ux + t * nx, y: s1 * uy + t * ny },
      ]);
    }
  }
  return out;
}

/** "24", 24\", 2'-0\", 2', 600mm, 0.6m -> metres (bare numbers are inches). */
export function parseSpacing(text: string): number | null {
  const t = text.trim().toLowerCase().replace(/[″”]/g, '"').replace(/[′’]/g, "'");
  if (!t) return null;
  let m = t.match(/^(\d+(?:\.\d+)?)\s*(mm|cm|m)$/);
  if (m) return Number(m[1]) * ({ mm: 0.001, cm: 0.01, m: 1 } as Record<string, number>)[m[2]!]!;
  m = t.match(/^(\d+(?:\.\d+)?)\s*'\s*-?\s*(\d+(?:\.\d+)?)?\s*"?$/);
  if (m) return (Number(m[1]) * 12 + Number(m[2] ?? 0)) * 0.0254;
  m = t.match(/^(\d+(?:\.\d+)?)\s*(?:"|in)?\s*(?:o\.?\s*c\.?)?$/);
  if (m) return Number(m[1]) * 0.0254;
  return null;
}
