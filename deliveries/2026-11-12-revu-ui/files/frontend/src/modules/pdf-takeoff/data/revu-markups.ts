// OE-DELIVERY: 2026-10-30-revu-markup-tools
/**
 * Bluebeam Revu markup + arc tools for PDF Measurements.
 *
 * Revu's Markup toolbar (Line, Polygon, Ellipse, Pen, Callout, Stamp)
 * and the Measure > Arc tool, kept out of TakeoffViewerModule so the
 * viewer only wires them in. Everything here is pure geometry or a
 * canvas draw routine; points are PDF user units, and the draw helpers
 * take the viewer's `dpr * zoom` factor so they paint in device px like
 * the rest of the overlay.
 *
 * Stored shapes:
 *  - line     [a, b]
 *  - polygon  [p0..pn]           closed outline, light fill
 *  - ellipse  [cornerA, cornerB] inscribed in the two-corner box
 *  - pen      [p0..pn]           freehand stroke (simplified on release)
 *  - callout  [tip, boxAnchor]   leader + arrowhead, text box at boxAnchor
 *                                (top-left), size in width/height
 *  - stamp    [anchor]           top-left of the stamp box, text in `text`
 *                                (first line = stamp, rest = date / user)
 *  - arc      [start, onArc, end] measured arc length
 */

import type { Point } from './hit-test';

export type RevuMarkupType = 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp';

/** Markup-only types (no quantity, excluded from totals). */
export const REVU_MARKUP_TYPES: ReadonlySet<string> = new Set<RevuMarkupType>([
  'line',
  'polygon',
  'ellipse',
  'pen',
  'callout',
  'stamp',
]);

export function isRevuMarkupType(type: string): type is RevuMarkupType {
  return REVU_MARKUP_TYPES.has(type);
}

/* ── Stamps ──────────────────────────────────────────────────────────── */

export interface StampPreset {
  id: string;
  text: string;
  color: string;
}

/** Revu's standard review stamps. */
export const STAMP_PRESETS: StampPreset[] = [
  { id: 'approved', text: 'APPROVED', color: '#16A34A' },
  { id: 'approved_as_noted', text: 'APPROVED AS NOTED', color: '#65A30D' },
  { id: 'reviewed', text: 'REVIEWED', color: '#2563EB' },
  { id: 'revise_resubmit', text: 'REVISE AND RESUBMIT', color: '#EA580C' },
  { id: 'rejected', text: 'REJECTED', color: '#DC2626' },
  { id: 'for_construction', text: 'FOR CONSTRUCTION', color: '#0D9488' },
  { id: 'not_for_construction', text: 'NOT FOR CONSTRUCTION', color: '#B91C1C' },
  { id: 'preliminary', text: 'PRELIMINARY', color: '#7C3AED' },
  { id: 'as_built', text: 'AS-BUILT', color: '#0369A1' },
  { id: 'draft', text: 'DRAFT', color: '#6B7280' },
  { id: 'void', text: 'VOID', color: '#374151' },
];

/** Stamp title font size and padding, PDF units. */
export const STAMP_TITLE_PX = 18;
export const STAMP_SUB_PX = 9;
export const STAMP_PAD = 8;

/** Callout text box metrics, PDF units. */
export const CALLOUT_FONT_PX = 12;
export const CALLOUT_LINE_H = 16;
export const CALLOUT_PAD = 6;

let measureCtx: CanvasRenderingContext2D | null | undefined;
function textWidth(text: string, font: string): number {
  if (measureCtx === undefined) {
    try { measureCtx = document.createElement('canvas').getContext('2d'); }
    catch { measureCtx = null; }
  }
  if (!measureCtx) return text.length * 0.6 * parseFloat(font.replace(/[^\d.]/g, '') || '12');
  measureCtx.font = font;
  return measureCtx.measureText(text).width;
}

/** Text shown on a stamp: title, then "date · user" when known. */
export function buildStampText(title: string, author?: string, date = new Date()): string {
  const d = date.toISOString().slice(0, 10);
  return author ? `${title}\n${d} · ${author}` : `${title}\n${d}`;
}

/** Box size (PDF units) of a stamp holding `text`. */
export function stampBoxSize(text: string): { width: number; height: number } {
  const [title = '', ...rest] = text.split('\n');
  let w = textWidth(title, `bold ${STAMP_TITLE_PX}px sans-serif`);
  for (const line of rest) w = Math.max(w, textWidth(line, `${STAMP_SUB_PX}px sans-serif`));
  const h = STAMP_TITLE_PX + rest.length * (STAMP_SUB_PX + 3) + STAMP_PAD * 2;
  return { width: Math.ceil(w + STAMP_PAD * 2 + 6), height: Math.ceil(h + 4) };
}

/** Box size (PDF units) of a callout holding `text` (manual line breaks only). */
export function calloutBoxSize(text: string): { width: number; height: number } {
  const lines = (text || ' ').split('\n');
  let w = 0;
  for (const line of lines) w = Math.max(w, textWidth(line, `${CALLOUT_FONT_PX}px sans-serif`));
  return {
    width: Math.ceil(Math.max(40, w) + CALLOUT_PAD * 2),
    height: Math.ceil(lines.length * CALLOUT_LINE_H + CALLOUT_PAD * 2),
  };
}

/* ── Arc geometry ────────────────────────────────────────────────────── */

export interface ArcGeom {
  cx: number;
  cy: number;
  r: number;
  start: number;
  /** Signed sweep in radians (positive = increasing canvas angle). */
  sweep: number;
}

const TAU = Math.PI * 2;
const norm = (a: number): number => ((a % TAU) + TAU) % TAU;

/** Arc through start -> onArc -> end, or null when the points are collinear. */
export function arcFrom3Points(p0: Point, p1: Point, p2: Point): ArcGeom | null {
  const d = 2 * (p0.x * (p1.y - p2.y) + p1.x * (p2.y - p0.y) + p2.x * (p0.y - p1.y));
  if (Math.abs(d) < 1e-9) return null;
  const s0 = p0.x * p0.x + p0.y * p0.y;
  const s1 = p1.x * p1.x + p1.y * p1.y;
  const s2 = p2.x * p2.x + p2.y * p2.y;
  const cx = (s0 * (p1.y - p2.y) + s1 * (p2.y - p0.y) + s2 * (p0.y - p1.y)) / d;
  const cy = (s0 * (p2.x - p1.x) + s1 * (p0.x - p2.x) + s2 * (p1.x - p0.x)) / d;
  const r = Math.hypot(p0.x - cx, p0.y - cy);
  const a0 = Math.atan2(p0.y - cy, p0.x - cx);
  const a1 = Math.atan2(p1.y - cy, p1.x - cx);
  const a2 = Math.atan2(p2.y - cy, p2.x - cx);
  const toMid = norm(a1 - a0);
  const toEnd = norm(a2 - a0);
  // Sweep the way that passes through the middle point.
  const sweep = toMid <= toEnd ? toEnd : -(TAU - toEnd);
  return { cx, cy, r, start: a0, sweep };
}

/** Arc length in PDF units (straight chord when collinear). */
export function arcLengthPx(points: Point[]): number {
  const [p0, p1, p2] = points;
  if (!p0 || !p1) return 0;
  if (!p2) return Math.hypot(p1.x - p0.x, p1.y - p0.y);
  const g = arcFrom3Points(p0, p1, p2);
  if (!g) return Math.hypot(p2.x - p0.x, p2.y - p0.y);
  return g.r * Math.abs(g.sweep);
}

/** Points sampled along the arc, for hit-testing and export. */
export function arcSamplePoints(points: Point[], segments = 32): Point[] {
  const [p0, p1, p2] = points;
  if (!p0 || !p1 || !p2) return points.slice();
  const g = arcFrom3Points(p0, p1, p2);
  if (!g) return [p0, p2];
  const out: Point[] = [];
  for (let i = 0; i <= segments; i++) {
    const a = g.start + (g.sweep * i) / segments;
    out.push({ x: g.cx + g.r * Math.cos(a), y: g.cy + g.r * Math.sin(a) });
  }
  return out;
}

/* ── Pen stroke simplification ───────────────────────────────────────── */

/** Ramer-Douglas-Peucker simplification (tolerance in PDF units), capped
 *  so a long scribble stays under the server's per-measurement point limit. */
export function simplifyStroke(points: Point[], tolerance: number, maxPoints = 4000): Point[] {
  if (points.length <= 2) return points.slice();
  const keep = new Uint8Array(points.length);
  keep[0] = 1;
  keep[points.length - 1] = 1;
  const stack: Array<[number, number]> = [[0, points.length - 1]];
  while (stack.length > 0) {
    const [s, e] = stack.pop()!;
    const a = points[s]!;
    const b = points[e]!;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy) || 1;
    let maxD = -1;
    let idx = -1;
    for (let i = s + 1; i < e; i++) {
      const p = points[i]!;
      const dist = Math.abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / len;
      if (dist > maxD) { maxD = dist; idx = i; }
    }
    if (idx > 0 && maxD > tolerance) {
      keep[idx] = 1;
      stack.push([s, idx], [idx, e]);
    }
  }
  const out = points.filter((_, i) => keep[i] === 1);
  if (out.length <= maxPoints) return out;
  const step = out.length / maxPoints;
  const thinned: Point[] = [];
  for (let i = 0; i < maxPoints - 1; i++) thinned.push(out[Math.floor(i * step)]!);
  thinned.push(out[out.length - 1]!);
  return thinned;
}

/* ── Callout geometry ────────────────────────────────────────────────── */

/** Point on the callout box border nearest to the leader tip. */
export function calloutLeaderEnd(tip: Point, box: { x: number; y: number; w: number; h: number }): Point {
  const cx = Math.min(Math.max(tip.x, box.x), box.x + box.w);
  const cy = Math.min(Math.max(tip.y, box.y), box.y + box.h);
  // Tip inside the box: leave from the box centre's nearest edge.
  if (cx === tip.x && cy === tip.y) return { x: box.x, y: box.y + box.h / 2 };
  return { x: cx, y: cy };
}

/* ── Hit-testing ─────────────────────────────────────────────────────── */

function distToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

/** Body hit for the shapes the generic edge/polygon test cannot cover
 *  (ellipse, stamp, callout box, arc curve). `tol` is PDF units.
 *  Returns true on a hit, false on a miss, null when not handled here. */
export function hitRevuBody(
  pt: Point,
  m: { type: string; points: Point[]; width?: number; height?: number },
  tol: number,
): boolean | null {
  const pts = m.points;
  switch (m.type) {
    case 'ellipse': {
      const [a, b] = pts;
      if (!a || !b) return false;
      const rx = Math.abs(b.x - a.x) / 2 + tol;
      const ry = Math.abs(b.y - a.y) / 2 + tol;
      const cx = (a.x + b.x) / 2;
      const cy = (a.y + b.y) / 2;
      return ((pt.x - cx) / rx) ** 2 + ((pt.y - cy) / ry) ** 2 <= 1;
    }
    case 'stamp': {
      const a = pts[0];
      if (!a) return false;
      const w = m.width ?? 0;
      const h = m.height ?? 0;
      return pt.x >= a.x - tol && pt.x <= a.x + w + tol && pt.y >= a.y - tol && pt.y <= a.y + h + tol;
    }
    case 'callout': {
      const [tip, anchor] = pts;
      if (!tip || !anchor) return false;
      const w = m.width ?? 0;
      const h = m.height ?? 0;
      if (pt.x >= anchor.x - tol && pt.x <= anchor.x + w + tol && pt.y >= anchor.y - tol && pt.y <= anchor.y + h + tol) {
        return true;
      }
      const end = calloutLeaderEnd(tip, { x: anchor.x, y: anchor.y, w, h });
      return distToSegment(pt, tip, end) <= tol;
    }
    case 'arc': {
      const s = arcSamplePoints(pts);
      for (let i = 0; i < s.length - 1; i++) {
        if (distToSegment(pt, s[i]!, s[i + 1]!) <= tol) return true;
      }
      return false;
    }
    default:
      return null;
  }
}

/* ── Canvas drawing ──────────────────────────────────────────────────── */

export interface DrawOpts {
  /** dpr * zoom: PDF units -> device px. */
  k: number;
  /** Device pixel ratio, for screen-constant widths. */
  dpr: number;
  color: string;
  /** Stroke width in CSS px (defaults to 2). */
  strokeWidth?: number;
  fillAlpha?: number;
  strokeAlpha?: number;
}

function drawArrowHead(ctx: CanvasRenderingContext2D, from: Point, to: Point, size: number): void {
  const ang = Math.atan2(to.y - from.y, to.x - from.x);
  ctx.beginPath();
  ctx.moveTo(to.x, to.y);
  ctx.lineTo(to.x - size * Math.cos(ang - Math.PI / 7), to.y - size * Math.sin(ang - Math.PI / 7));
  ctx.lineTo(to.x - size * Math.cos(ang + Math.PI / 7), to.y - size * Math.sin(ang + Math.PI / 7));
  ctx.closePath();
  ctx.fill();
}

/** Paint a stored Revu markup. Returns false when the shape is incomplete. */
export function drawRevuMarkup(
  ctx: CanvasRenderingContext2D,
  m: { type: string; points: Point[]; text?: string; annotation?: string; width?: number; height?: number },
  o: DrawOpts,
): boolean {
  const k = o.k;
  const P = (p: Point): Point => ({ x: p.x * k, y: p.y * k });
  const pts = m.points;
  ctx.save();
  ctx.strokeStyle = o.color;
  ctx.fillStyle = o.color;
  ctx.lineWidth = (o.strokeWidth ?? 2) * o.dpr;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.globalAlpha = o.strokeAlpha ?? 1;
  let ok = true;

  switch (m.type) {
    case 'line': {
      // Two points = Line; more = Polyline (OE-DELIVERY 2026-11-12-revu-ui).
      if (pts.length < 2) { ok = false; break; }
      ctx.beginPath();
      pts.forEach((pt, i) => { const q = P(pt); if (i === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y); });
      ctx.stroke();
      break;
    }
    case 'polygon': {
      if (pts.length < 3) { ok = false; break; }
      ctx.beginPath();
      pts.forEach((p, i) => { const q = P(p); if (i === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y); });
      ctx.closePath();
      ctx.globalAlpha = o.fillAlpha ?? 0.08;
      ctx.fill();
      ctx.globalAlpha = o.strokeAlpha ?? 1;
      ctx.stroke();
      break;
    }
    case 'ellipse': {
      const [a, b] = pts;
      if (!a || !b) { ok = false; break; }
      const A = P(a); const B = P(b);
      ctx.beginPath();
      ctx.ellipse((A.x + B.x) / 2, (A.y + B.y) / 2, Math.abs(B.x - A.x) / 2, Math.abs(B.y - A.y) / 2, 0, 0, Math.PI * 2);
      ctx.globalAlpha = o.fillAlpha ?? 0.06;
      ctx.fill();
      ctx.globalAlpha = o.strokeAlpha ?? 1;
      ctx.stroke();
      break;
    }
    case 'pen': {
      if (pts.length < 2) { ok = false; break; }
      // Smooth through the midpoints so the simplified stroke stays fluid.
      const q = pts.map(P);
      ctx.beginPath();
      ctx.moveTo(q[0]!.x, q[0]!.y);
      for (let i = 1; i < q.length - 1; i++) {
        const c = q[i]!; const n = q[i + 1]!;
        ctx.quadraticCurveTo(c.x, c.y, (c.x + n.x) / 2, (c.y + n.y) / 2);
      }
      const last = q[q.length - 1]!;
      ctx.lineTo(last.x, last.y);
      ctx.stroke();
      break;
    }
    case 'callout': {
      const [tip, anchor] = pts;
      if (!tip || !anchor) { ok = false; break; }
      const w = m.width ?? 0;
      const h = m.height ?? 0;
      const end = calloutLeaderEnd(tip, { x: anchor.x, y: anchor.y, w, h });
      const T = P(tip); const E = P(end);
      ctx.beginPath(); ctx.moveTo(E.x, E.y); ctx.lineTo(T.x, T.y); ctx.stroke();
      drawArrowHead(ctx, E, T, 10 * o.dpr);
      const bx = anchor.x * k; const by = anchor.y * k;
      ctx.globalAlpha = 0.92;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(bx, by, w * k, h * k);
      ctx.globalAlpha = o.strokeAlpha ?? 1;
      ctx.strokeRect(bx, by, w * k, h * k);
      ctx.fillStyle = o.color;
      ctx.font = `${CALLOUT_FONT_PX * k}px sans-serif`;
      ctx.textBaseline = 'top';
      // A centred align left over from other drawing put the text off the box.
      ctx.textAlign = 'left';
      // An empty comment stays empty (Cloud+ filled in later, update 12).
      const lines = (m.text ?? m.annotation ?? '').split('\n');
      lines.forEach((line, i) => {
        ctx.fillText(line, bx + CALLOUT_PAD * k, by + (CALLOUT_PAD + i * CALLOUT_LINE_H + 2) * k);
      });
      break;
    }
    case 'stamp': {
      const a = pts[0];
      if (!a) { ok = false; break; }
      const w = (m.width ?? 0) * k;
      const h = (m.height ?? 0) * k;
      const x = a.x * k; const y = a.y * k;
      const [title = '', ...rest] = (m.text || m.annotation || '').split('\n');
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 2.5 * o.dpr;
      ctx.beginPath(); ctx.roundRect(x, y, w, h, 6 * k); ctx.stroke();
      ctx.lineWidth = 1 * o.dpr;
      ctx.beginPath(); ctx.roundRect(x + 3 * k, y + 3 * k, w - 6 * k, h - 6 * k, 4 * k); ctx.stroke();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.font = `bold ${STAMP_TITLE_PX * k}px sans-serif`;
      ctx.fillText(title, x + w / 2, y + STAMP_PAD * k + 2 * k);
      ctx.font = `${STAMP_SUB_PX * k}px sans-serif`;
      rest.forEach((line, i) => {
        ctx.fillText(line, x + w / 2, y + (STAMP_PAD + STAMP_TITLE_PX + 3 + i * (STAMP_SUB_PX + 3)) * k);
      });
      break;
    }
    case 'arc': {
      const [p0, p1, p2] = pts;
      if (!p0 || !p1 || !p2) { ok = false; break; }
      const g = arcFrom3Points(p0, p1, p2);
      ctx.beginPath();
      if (g) {
        ctx.arc(g.cx * k, g.cy * k, g.r * k, g.start, g.start + g.sweep, g.sweep < 0);
      } else {
        ctx.moveTo(p0.x * k, p0.y * k); ctx.lineTo(p2.x * k, p2.y * k);
      }
      ctx.stroke();
      for (const p of [p0, p2]) {
        ctx.beginPath(); ctx.arc(p.x * k, p.y * k, 3 * o.dpr, 0, Math.PI * 2); ctx.fill();
      }
      break;
    }
    default:
      ok = false;
  }
  ctx.restore();
  return ok;
}

/** Midpoint of a stored shape in PDF units, for the label stack. */
export function revuLabelAnchor(m: { type: string; points: Point[] }): Point | null {
  if (m.type === 'arc') {
    const s = arcSamplePoints(m.points, 2);
    return s[1] ?? null;
  }
  const pts = m.points;
  if (pts.length === 0) return null;
  return {
    x: pts.reduce((s, p) => s + p.x, 0) / pts.length,
    y: pts.reduce((s, p) => s + p.y, 0) / pts.length,
  };
}

/** In-progress preview for the click-built Revu tools. `cursor` is the
 *  live (snapped) pointer, or null when the pointer is off the canvas. */
export function drawRevuPreview(
  ctx: CanvasRenderingContext2D,
  tool: string,
  placed: Point[],
  cursor: Point | null,
  o: DrawOpts,
): void {
  if (placed.length === 0) return;
  const k = o.k;
  const all = cursor ? [...placed, cursor] : placed;
  ctx.save();
  ctx.strokeStyle = o.color;
  ctx.fillStyle = o.color;
  ctx.lineWidth = 1.5 * o.dpr;
  ctx.setLineDash([5 * o.dpr, 4 * o.dpr]);
  switch (tool) {
    case 'line':
    case 'callout':
    case 'polygon': {
      ctx.beginPath();
      all.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x * k, p.y * k); else ctx.lineTo(p.x * k, p.y * k); });
      if (tool === 'polygon' && all.length >= 3) ctx.closePath();
      ctx.stroke();
      break;
    }
    case 'pen': {
      ctx.setLineDash([]);
      ctx.lineWidth = 2 * o.dpr;
      ctx.beginPath();
      placed.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x * k, p.y * k); else ctx.lineTo(p.x * k, p.y * k); });
      ctx.stroke();
      break;
    }
    case 'arc': {
      if (all.length >= 3) {
        const g = arcFrom3Points(all[0]!, all[1]!, all[2]!);
        ctx.beginPath();
        if (g) ctx.arc(g.cx * k, g.cy * k, g.r * k, g.start, g.start + g.sweep, g.sweep < 0);
        ctx.stroke();
      } else {
        ctx.beginPath();
        all.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x * k, p.y * k); else ctx.lineTo(p.x * k, p.y * k); });
        ctx.stroke();
      }
      break;
    }
    default:
      break;
  }
  ctx.restore();
}
