// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
/**
 * Snap-to-PDF-content: extract vector geometry from a PDF page so measurement
 * tools can snap to the drawing's own lines (endpoints, midpoints), Bluebeam-style.
 *
 * Approach: `page.getOperatorList()` yields the raw PDF drawing operators.
 * We walk them tracking the CTM (current transform matrix) through save/restore,
 * collecting line segments from moveTo/lineTo/rectangle (curves flattened).
 * Segments are stored in PDF-top-left space (y flipped via page height) to
 * match the viewer's measurement coordinate system.
 *
 * Performance: extraction runs once per page and is cached by the caller.
 * A uniform grid index makes nearest-segment lookup O(candidates).
 */

import { OPS } from 'pdfjs-dist';
import type { PDFPageProxy } from 'pdfjs-dist';

export interface Point {
  x: number;
  y: number;
}

export interface Segment {
  a: Point;
  b: Point;
}

/** Snap result: the snapped point and what was hit. */
export interface ContentSnap {
  point: Point;
  kind: 'endpoint' | 'midpoint' | 'edge' | 'intersection';
  /** The drawing line, for an edge snap (straight-onto-line, update 15). */
  seg?: Segment;
}

type Matrix = [number, number, number, number, number, number]; // a,b,c,d,e,f

const IDENTITY: Matrix = [1, 0, 0, 1, 0, 0];

function mulMat(m1: Matrix, m2: Matrix): Matrix {
  const [a1, b1, c1, d1, e1, f1] = m1;
  const [a2, b2, c2, d2, e2, f2] = m2;
  return [
    a1 * a2 + c1 * b2,
    b1 * a2 + d1 * b2,
    a1 * c2 + c1 * d2,
    b1 * c2 + d1 * d2,
    a1 * e2 + c1 * f2 + e1,
    b1 * e2 + d1 * f2 + f1,
  ];
}

function xformPt(m: Matrix, x: number, y: number): Point {
  return { x: m[0] * x + m[2] * y + m[4], y: m[1] * x + m[3] * y + m[5] };
}

/** Flatten a cubic bezier into line segments. */
function flattenCubic(
  p0: Point,
  p1: Point,
  p2: Point,
  p3: Point,
  out: Segment[],
  steps = 8,
): void {
  let prev = p0;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const mt = 1 - t;
    const x =
      mt * mt * mt * p0.x + 3 * mt * mt * t * p1.x + 3 * mt * t * t * p2.x + t * t * t * p3.x;
    const y =
      mt * mt * mt * p0.y + 3 * mt * mt * t * p1.y + 3 * mt * t * t * p2.y + t * t * t * p3.y;
    const cur = { x, y };
    out.push({ a: prev, b: cur });
    prev = cur;
  }
}

const MAX_SEGMENTS = 50000;

/**
 * Extract vector line segments from a PDF page.
 * Returns segments in PDF-top-left coordinates (y down), matching the viewer.
 */
export async function extractPageSegments(page: PDFPageProxy): Promise<Segment[]> {
  const opList = await page.getOperatorList();
  const { fnArray, argsArray } = opList;
  // Use the viewport's transform (handles rotation, crop boxes) to map
  // PDF user space -> display space, matching exactly how PDF.js renders.
  const viewport = page.getViewport({ scale: 1 });
  const vt = viewport.transform as unknown as Matrix;

  const segments: Segment[] = [];
  const stack: Matrix[] = [];
  let ctm: Matrix = [...IDENTITY] as Matrix;
  let cur: Point | null = null;
  let subpathStart: Point | null = null;

  // Map a user-space point through CTM then viewport transform.
  const toDisplay = (p: Point): Point => {
    const q = xformPt(ctm, p.x, p.y);
    return xformPt(vt, q.x, q.y);
  };

  const pushSeg = (a: Point, b: Point) => {
    if (segments.length >= MAX_SEGMENTS) return;
    const da = toDisplay(a);
    const db = toDisplay(b);
    // Skip degenerate segments
    if (Math.abs(da.x - db.x) < 1e-6 && Math.abs(da.y - db.y) < 1e-6) return;
    segments.push({ a: da, b: db });
  };

  for (let i = 0; i < fnArray.length; i++) {
    const fn = fnArray[i];
    const args = argsArray[i] as number[];
    switch (fn) {
      case OPS.save:
        stack.push([...ctm] as Matrix);
        break;
      case OPS.restore:
        if (stack.length > 0) ctm = stack.pop()!;
        break;
      case OPS.transform: {
        const m = args as unknown as Matrix;
        const m0 = m[0] ?? 1, m1 = m[1] ?? 0, m2 = m[2] ?? 0, m3 = m[3] ?? 1, m4 = m[4] ?? 0, m5 = m[5] ?? 0;
        ctm = mulMat(ctm, [m0, m1, m2, m3, m4, m5]);
        break;
      }
      case OPS.moveTo: {
        const p = { x: args[0] ?? 0, y: args[1] ?? 0 };
        cur = p;
        subpathStart = p;
        break;
      }
      case OPS.lineTo: {
        const p = { x: args[0] ?? 0, y: args[1] ?? 0 };
        if (cur) pushSeg(cur, p);
        cur = p;
        break;
      }
      case OPS.curveTo: {
        const p1 = { x: args[0] ?? 0, y: args[1] ?? 0 };
        const p2 = { x: args[2] ?? 0, y: args[3] ?? 0 };
        const p3 = { x: args[4] ?? 0, y: args[5] ?? 0 };
        if (cur) {
          const tmp: Segment[] = [];
          flattenCubic(cur, p1, p2, p3, tmp);
          for (const s of tmp) pushSeg(s.a, s.b);
        }
        cur = p3;
        break;
      }
      case OPS.curveTo2: {
        const p2 = { x: args[0] ?? 0, y: args[1] ?? 0 };
        const p3 = { x: args[2] ?? 0, y: args[3] ?? 0 };
        if (cur) {
          const tmp: Segment[] = [];
          flattenCubic(cur, cur, p2, p3, tmp);
          for (const s of tmp) pushSeg(s.a, s.b);
        }
        cur = p3;
        break;
      }
      case OPS.curveTo3: {
        const p1 = { x: args[0] ?? 0, y: args[1] ?? 0 };
        const p3 = { x: args[2] ?? 0, y: args[3] ?? 0 };
        if (cur) {
          const tmp: Segment[] = [];
          flattenCubic(cur, p1, p3, p3, tmp);
          for (const s of tmp) pushSeg(s.a, s.b);
        }
        cur = p3;
        break;
      }
      case OPS.rectangle: {
        const [x, y, w, h] = args;
        const rx = x ?? 0, ry = y ?? 0, rw = w ?? 0, rh = h ?? 0;
        const p0 = { x: rx, y: ry };
        const p1 = { x: rx + rw, y: ry };
        const p2 = { x: rx + rw, y: ry + rh };
        const p3 = { x: rx, y: ry + rh };
        pushSeg(p0, p1);
        pushSeg(p1, p2);
        pushSeg(p2, p3);
        pushSeg(p3, p0);
        cur = p0;
        subpathStart = p0;
        break;
      }
      case OPS.closePath: {
        if (cur && subpathStart) pushSeg(cur, subpathStart);
        cur = subpathStart;
        break;
      }
      case OPS.constructPath: {
        // pdf.js 4+ packs each path into one constructPath op instead of
        // separate moveTo / lineTo ops, so without this nothing was read and
        // content snap never had any lines (OE-DELIVERY 2026-11-12-revu-ui u12).
        const raw = argsArray[i] as unknown as unknown[];
        // New form: [drawOp, [Float32Array of DrawOPS-coded data], minMax].
        const packed = Array.isArray(raw?.[1]) ? (raw[1] as unknown[])[0] : null;
        if (packed && typeof (packed as ArrayLike<number>).length === 'number' && !Array.isArray(raw[0])) {
          const d = packed as ArrayLike<number>;
          for (let k = 0; k < d.length; ) {
            const code = d[k++];
            if (code === 0) {
              const p = { x: d[k++]!, y: d[k++]! };
              cur = p;
              subpathStart = p;
            } else if (code === 1) {
              const p = { x: d[k++]!, y: d[k++]! };
              if (cur) pushSeg(cur, p);
              cur = p;
            } else if (code === 2) {
              const p1 = { x: d[k++]!, y: d[k++]! };
              const p2 = { x: d[k++]!, y: d[k++]! };
              const p3 = { x: d[k++]!, y: d[k++]! };
              if (cur) {
                const tmp: Segment[] = [];
                flattenCubic(cur, p1, p2, p3, tmp);
                for (const s of tmp) pushSeg(s.a, s.b);
              }
              cur = p3;
            } else if (code === 3) {
              const q1 = { x: d[k++]!, y: d[k++]! };
              const p3 = { x: d[k++]!, y: d[k++]! };
              if (cur) {
                const c1 = { x: cur.x + (2 / 3) * (q1.x - cur.x), y: cur.y + (2 / 3) * (q1.y - cur.y) };
                const c2 = { x: p3.x + (2 / 3) * (q1.x - p3.x), y: p3.y + (2 / 3) * (q1.y - p3.y) };
                const tmp: Segment[] = [];
                flattenCubic(cur, c1, c2, p3, tmp);
                for (const s of tmp) pushSeg(s.a, s.b);
              }
              cur = p3;
            } else if (code === 4) {
              if (cur && subpathStart) pushSeg(cur, subpathStart);
              cur = subpathStart;
            } else {
              break;
            }
            if (segments.length >= MAX_SEGMENTS) break;
          }
          break;
        }
        // Old form (pdf.js 2/3): [ops[], coords[], minMax].
        if (Array.isArray(raw?.[0]) && Array.isArray(raw?.[1])) {
          const ops = raw[0] as number[];
          const c = raw[1] as number[];
          let k = 0;
          for (const o of ops) {
            if (o === OPS.moveTo) {
              const p = { x: c[k++]!, y: c[k++]! };
              cur = p;
              subpathStart = p;
            } else if (o === OPS.lineTo) {
              const p = { x: c[k++]!, y: c[k++]! };
              if (cur) pushSeg(cur, p);
              cur = p;
            } else if (o === OPS.curveTo) {
              const p1 = { x: c[k++]!, y: c[k++]! };
              const p2 = { x: c[k++]!, y: c[k++]! };
              const p3 = { x: c[k++]!, y: c[k++]! };
              if (cur) {
                const tmp: Segment[] = [];
                flattenCubic(cur, p1, p2, p3, tmp);
                for (const s of tmp) pushSeg(s.a, s.b);
              }
              cur = p3;
            } else if (o === OPS.curveTo2 || o === OPS.curveTo3) {
              k += 2;
              const p3 = { x: c[k++]!, y: c[k++]! };
              if (cur) pushSeg(cur, p3);
              cur = p3;
            } else if (o === OPS.rectangle) {
              const rx = c[k++]!, ry = c[k++]!, rw = c[k++]!, rh = c[k++]!;
              const q0 = { x: rx, y: ry }, q1 = { x: rx + rw, y: ry }, q2 = { x: rx + rw, y: ry + rh }, q3 = { x: rx, y: ry + rh };
              pushSeg(q0, q1); pushSeg(q1, q2); pushSeg(q2, q3); pushSeg(q3, q0);
              cur = q0;
              subpathStart = q0;
            } else if (o === OPS.closePath) {
              if (cur && subpathStart) pushSeg(cur, subpathStart);
              cur = subpathStart;
            }
          }
        }
        break;
      }
      default:
        break;
    }
    if (segments.length >= MAX_SEGMENTS) break;
  }
  return segments;
}

/* ── Spatial index (uniform grid) ─────────────────────────────── */

export interface SnapIndex {
  segments: Segment[];
  cell: number;
  grid: Map<string, number[]>;
  minX: number;
  minY: number;
}

export function buildSnapIndex(segments: Segment[]): SnapIndex {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const s of segments) {
    minX = Math.min(minX, s.a.x, s.b.x);
    minY = Math.min(minY, s.a.y, s.b.y);
    maxX = Math.max(maxX, s.a.x, s.b.x);
    maxY = Math.max(maxY, s.a.y, s.b.y);
  }
  if (!isFinite(minX)) {
    return { segments, cell: 100, grid: new Map(), minX: 0, minY: 0 };
  }
  // Target ~20x20 grid
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const cell = Math.max(spanX, spanY) / 20;
  const grid = new Map<string, number[]>();
  segments.forEach((s, idx) => {
    const x0 = Math.floor((Math.min(s.a.x, s.b.x) - minX) / cell);
    const x1 = Math.floor((Math.max(s.a.x, s.b.x) - minX) / cell);
    const y0 = Math.floor((Math.min(s.a.y, s.b.y) - minY) / cell);
    const y1 = Math.floor((Math.max(s.a.y, s.b.y) - minY) / cell);
    for (let gx = x0; gx <= x1; gx++) {
      for (let gy = y0; gy <= y1; gy++) {
        const key = `${gx},${gy}`;
        let arr = grid.get(key);
        if (!arr) {
          arr = [];
          grid.set(key, arr);
        }
        arr.push(idx);
      }
    }
  });
  return { segments, cell, grid, minX, minY };
}

function distToSegmentSq(p: Point, s: Segment): { d2: number; t: number } {
  const dx = s.b.x - s.a.x;
  const dy = s.b.y - s.a.y;
  const len2 = dx * dx + dy * dy;
  if (len2 < 1e-12) {
    const ddx = p.x - s.a.x;
    const ddy = p.y - s.a.y;
    return { d2: ddx * ddx + ddy * ddy, t: 0 };
  }
  let t = ((p.x - s.a.x) * dx + (p.y - s.a.y) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const px = s.a.x + t * dx;
  const py = s.a.y + t * dy;
  const ddx = p.x - px;
  const ddy = p.y - py;
  return { d2: ddx * ddx + ddy * ddy, t };
}

/**
 * Snap a point (PDF-top-left coords) to nearby PDF content geometry.
 * Priority: endpoint > midpoint > edge projection.
 * `tolerancePx` is in screen pixels; `zoom` converts to PDF units.
 */
export function snapToContent(
  p: Point,
  index: SnapIndex,
  zoom: number,
  tolerancePx: number,
): ContentSnap | null {
  // Magnet reach (Revu-like): a little wider than the markup-vertex snap.
  const tol = (tolerancePx * 1.6) / Math.max(zoom, 0.01);
  const tol2 = tol * tol;
  const { segments, cell, grid, minX, minY } = index;
  if (segments.length === 0) return null;

  const gx = Math.floor((p.x - minX) / cell);
  const gy = Math.floor((p.y - minY) / cell);
  const seen = new Set<number>();
  const near: number[] = [];
  let best: ContentSnap | null = null;
  let bestD2 = tol2;

  // Check 3x3 neighborhood of cells
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const arr = grid.get(`${gx + dx},${gy + dy}`);
      if (!arr) continue;
      for (const idx of arr) {
        if (seen.has(idx)) continue;
        seen.add(idx);
        const s = segments[idx]!;
        if (near.length < 80 && distToSegmentSq(p, s).d2 < tol2 * 4) near.push(idx);
        // Endpoints first
        for (const ep of [s.a, s.b]) {
          const ddx = p.x - ep.x;
          const ddy = p.y - ep.y;
          const d2 = ddx * ddx + ddy * ddy;
          if (d2 < bestD2) {
            bestD2 = d2;
            best = { point: { x: ep.x, y: ep.y }, kind: 'endpoint' };
          }
        }
        // Midpoint
        const mx = (s.a.x + s.b.x) / 2;
        const my = (s.a.y + s.b.y) / 2;
        {
          const ddx = p.x - mx;
          const ddy = p.y - my;
          const d2 = ddx * ddx + ddy * ddy;
          // Midpoints get slightly lower priority than endpoints: require strictly closer
          if (d2 < bestD2 * 0.8) {
            bestD2 = d2;
            best = { point: { x: mx, y: my }, kind: 'midpoint' };
          }
        }
        // Edge projection (only if no endpoint/midpoint won yet for this segment)
        if (!best || best.kind === 'edge') {
          const { d2, t } = distToSegmentSq(p, s);
          if (d2 < bestD2) {
            bestD2 = d2;
            best = {
              point: { x: s.a.x + t * (s.b.x - s.a.x), y: s.a.y + t * (s.b.y - s.a.y) },
              kind: 'edge',
              seg: s,
            };
          }
        }
      }
    }
  }
  // Line crossings (grid lines, wall corners, framing): win over a plain
  // edge or midpoint, like an endpoint (update 12).
  for (let i = 0; i < near.length; i++) {
    const s1 = segments[near[i]!]!;
    for (let j = i + 1; j < near.length; j++) {
      const s2 = segments[near[j]!]!;
      const d1x = s1.b.x - s1.a.x;
      const d1y = s1.b.y - s1.a.y;
      const d2x = s2.b.x - s2.a.x;
      const d2y = s2.b.y - s2.a.y;
      const den = d1x * d2y - d1y * d2x;
      if (Math.abs(den) < 1e-9) continue;
      const ux = s2.a.x - s1.a.x;
      const uy = s2.a.y - s1.a.y;
      const ta = (ux * d2y - uy * d2x) / den;
      const tb = (ux * d1y - uy * d1x) / den;
      if (ta < -0.001 || ta > 1.001 || tb < -0.001 || tb > 1.001) continue;
      const ix = s1.a.x + ta * d1x;
      const iy = s1.a.y + ta * d1y;
      const d2 = (p.x - ix) ** 2 + (p.y - iy) ** 2;
      if (d2 >= tol2) continue;
      if (!best || best.kind === 'edge' || best.kind === 'midpoint' || d2 < bestD2) {
        bestD2 = d2;
        best = { point: { x: ix, y: iy }, kind: 'intersection' };
      }
    }
  }
  return best;
}
