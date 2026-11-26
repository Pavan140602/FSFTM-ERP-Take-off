// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * In-canvas measurement editing geometry (issue #194 Feature 1).
 *
 * Pure, dependency-free hit-testing + live-recompute helpers for the PDF
 * takeoff viewer. Everything here operates in PDF user units (the same
 * space stored measurement points live in): the viewer inverts a pointer
 * to PDF units with `(clientX - rect.left) / zoom` and never divides by
 * `dpr`, so a screen-constant grab radius is just `GRAB_PX / zoom`.
 *
 * Geometry is shared with the rest of the takeoff stack rather than
 * re-derived: the segment / polygon / self-intersection primitives come
 * from `features/dwg-takeoff/lib/measurement.ts`, and the scale-aware
 * real-world conversions from `data/scale-helpers.ts`. That keeps
 * create-time math (in `TakeoffViewerModule`) and reshape-time math
 * (here) from drifting, which matters because the label strings this
 * module emits are read back by the ledger / CSV / Excel export.
 */

import {
  pointInPolygon,
  pointToSegmentDistance,
  isSelfIntersecting,
} from '@/features/dwg-takeoff/lib/measurement';
import {
  pixelDistance,
  toRealDistance,
  toRealArea,
  polygonAreaPixels,
  polygonPerimeterPixels,
  formatMeasurement,
  type ScaleConfig,
} from './scale-helpers';
// OE-DELIVERY: 2026-10-30-fsftm-markup-tools
import { arcLengthPx, hitFSFTMBody } from './fsftm-markups';

export interface Point {
  x: number;
  y: number;
}

/** Measurement types the editor understands. Mirrors the viewer's union
 *  without importing the (heavy) module so this stays pure + testable. */
export type EditableMeasurementType =
  | 'distance'
  | 'polyline'
  | 'area'
  | 'volume'
  | 'count'
  | 'cloud'
  | 'arrow'
  | 'text'
  | 'rectangle'
  | 'highlight'
  | 'perimeter'
  | 'diameter'
  | 'radiusCenter'
  | 'radius3Point'
  | 'angle'
  | 'polygonCutout'
  | 'ellipseCutout'
  | 'dynamicFill'
  | 'legend'
  // FSFTM markup + arc tools (OE-DELIVERY 2026-10-30-fsftm-markup-tools).
  | 'line'
  | 'polygon'
  | 'ellipse'
  | 'pen'
  | 'callout'
  | 'stamp'
  | 'arc';

/** Minimal measurement shape the geometry helpers need. The viewer's
 *  full `Measurement` is structurally assignable to this. */
export interface EditableMeasurement {
  type: EditableMeasurementType;
  points: Point[];
  depth?: number;
  unit?: string;
  /** Stored box size for text annotations (PDF units). */
  width?: number;
  height?: number;
  /** Cut-out holes of an area / volume (PDF units). The fill leaves them
   *  open and the value excludes them (OE-DELIVERY 2026-11-26-fsftm-pdf). */
  holes?: Point[][];
}

/** Total pixel area of the valid holes (3+ points). */
export function holesAreaPixels(holes: Point[][] | undefined): number {
  let total = 0;
  for (const h of holes ?? []) if (h.length >= 3) total += polygonAreaPixels(h);
  return total;
}

/** Holes that follow a shape edit: a pure move (every point shifted by the
 *  same amount) carries the holes along; any reshape keeps them in place. */
export function carryHoles(m: { points: Point[]; holes?: Point[][] }, next: Point[]): Point[][] | undefined {
  const holes = m.holes;
  if (!holes || holes.length === 0) return holes;
  const prev = m.points;
  if (prev.length === 0 || prev.length !== next.length) return holes;
  const dx = next[0]!.x - prev[0]!.x;
  const dy = next[0]!.y - prev[0]!.y;
  if (dx === 0 && dy === 0) return holes;
  for (let i = 1; i < prev.length; i++) {
    if (Math.abs(next[i]!.x - prev[i]!.x - dx) > 1e-6 || Math.abs(next[i]!.y - prev[i]!.y - dy) > 1e-6) return holes;
  }
  return holes.map((h) => h.map((p) => ({ x: p.x + dx, y: p.y + dy })));
}

/** A hole vertex under the pointer: [hole index, vertex index]. */
export function hitHoleVertex(pt: Point, holes: Point[][] | undefined, zoom: number): [number, number] | null {
  const tol = VERTEX_GRAB_PX / (zoom > 0 ? zoom : 1);
  let best: [number, number] | null = null;
  let bestD = Infinity;
  (holes ?? []).forEach((h, hi) =>
    h.forEach((p, vi) => {
      const d = pixelDistance(pt.x, pt.y, p.x, p.y);
      if (d < tol && d < bestD) {
        bestD = d;
        best = [hi, vi];
      }
    }),
  );
  return best;
}

/* ── Tolerances (screen pixels; divide by zoom for PDF-unit space) ───── */

/** Grab radius for an edge / midpoint / interior body, in screen pixels. */
export const GRAB_PX = 8;
/** Grab radius for a vertex handle, in screen pixels (slightly larger so a
 *  vertex always wins over the edge it sits on). */
export const VERTEX_GRAB_PX = 10;

/* ── Text box metrics (FSFTM-style text annotations) ───────────────────
 * Shared by the viewer's canvas draw, its editor overlay and the
 * hit-test below so all three agree on the box geometry. All values are
 * PDF units; the font renders at TEXT_FONT_PX × zoom on screen. */
export const TEXT_FONT_PX = 14;
export const TEXT_LINE_HEIGHT_PX = 19;
export const TEXT_PAD_X = 5;
export const TEXT_PAD_Y = 3;
/** Default width of a freshly placed text box (PDF units). */
export const TEXT_BOX_DEFAULT_W = 240;
/** Narrowest a text box can be resized to (PDF units). */
export const TEXT_BOX_MIN_W = 60;

/** Circle through 3 points (for the 3-point radius tool). Returns null if the
 *  points are collinear. */
export function circleFrom3Points(p1: Point, p2: Point, p3: Point): { c: Point; r: number } | null {
  const d = 2 * (p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y));
  if (Math.abs(d) < 1e-9) return null;
  const s1 = p1.x * p1.x + p1.y * p1.y;
  const s2 = p2.x * p2.x + p2.y * p2.y;
  const s3 = p3.x * p3.x + p3.y * p3.y;
  const cx = (s1 * (p2.y - p3.y) + s2 * (p3.y - p1.y) + s3 * (p1.y - p2.y)) / d;
  const cy = (s1 * (p3.x - p2.x) + s2 * (p1.x - p3.x) + s3 * (p2.x - p1.x)) / d;
  const r = Math.hypot(p1.x - cx, p1.y - cy);
  return { c: { x: cx, y: cy }, r };
}

/* ── Per-type capability matrix ──────────────────────────────────────── */

/** Closed polygon types (the wrap edge participates in hit-testing). */
const CLOSED_TYPES: ReadonlySet<EditableMeasurementType> = new Set([
  'area',
  'volume',
  'cloud',
  'perimeter',
  'polygonCutout',
  'dynamicFill',
  'polygon',
]);

/** Open multi-segment types. */
const OPEN_LINE_TYPES: ReadonlySet<EditableMeasurementType> = new Set([
  'distance',
  'polyline',
  'arrow',
  'line',
  'pen',
]);

/** Whether a measurement type supports adding / removing vertices. */
export function supportsVariableVertices(type: EditableMeasurementType): boolean {
  return (
    type === 'polyline' ||
    type === 'area' ||
    type === 'volume' ||
    type === 'cloud' ||
    type === 'polygon' ||
    type === 'perimeter' ||
    type === 'polygonCutout'
  );
}

/** Minimum vertex count a type must keep to stay valid. Dropping below
 *  this should delete the whole measurement instead. */
export function minVertices(type: EditableMeasurementType): number {
  if (CLOSED_TYPES.has(type)) return 3;
  if (type === 'polyline') return 2;
  if (type === 'count' || type === 'stamp') return 1;
  if (type === 'arc') return 3;
  return 2;
}

/* ── Hit-testing ─────────────────────────────────────────────────────── */

export type HitKind = 'vertex' | 'edge' | 'body' | 'legend-resize' | 'text-resize';

export interface HitResult {
  kind: HitKind;
  /** For `vertex`: the vertex index. For `edge`: the index of the edge's
   *  first vertex (insert the new vertex at `index + 1`). For `body`: the
   *  nearest edge / dot index (informational). */
  index: number;
}

/** Number of edges to test for a measurement (closes the wrap edge for
 *  polygon types). */
function edgeCount(type: EditableMeasurementType, n: number): number {
  if (n < 2) return 0;
  return CLOSED_TYPES.has(type) ? n : n - 1;
}

/**
 * Hit-test a pointer (in PDF units) against one measurement.
 *
 * Priority high to low: vertex, then (only when `selected`) an edge
 * midpoint for add-vertex, then the edge / line body, then the interior.
 * Returns `null` when nothing is within grab tolerance.
 *
 * `zoom` is the current canvas zoom so the grab radius stays constant in
 * screen pixels at any zoom level (no `dpr` ever enters this space).
 */
export function hitTest(
  pt: Point,
  m: EditableMeasurement,
  zoom: number,
  selected: boolean,
): HitResult | null {
  const z = zoom > 0 ? zoom : 1;
  const pts = m.points;
  const n = pts.length;
  if (n === 0) return null;

  const vertexTol = VERTEX_GRAB_PX / z;
  const edgeTol = GRAB_PX / z;

  // 1) Vertex - nearest within the vertex grab radius.
  let bestVertex = -1;
  let bestVertexDist = Infinity;
  for (let i = 0; i < n; i++) {
    const p = pts[i]!;
    const d = pixelDistance(pt.x, pt.y, p.x, p.y);
    if (d < vertexTol && d < bestVertexDist) {
      bestVertexDist = d;
      bestVertex = i;
    }
  }
  if (bestVertex >= 0) return { kind: 'vertex', index: bestVertex };

  // Count markers have no edges / interior - a dot miss is a full miss.
  if (m.type === 'count') return null;

  // Text box: the body is the stored box (anchor = top-left corner);
  // the bottom-right corner is the width-resize handle when selected.
  // Legacy pins (no stored width) keep anchor-vertex-only behaviour.
  if (m.type === 'text') {
    const w = m.width && m.width > 0 ? m.width : 0;
    if (w <= 0) return null;
    const anchor = pts[0]!;
    const h = m.height && m.height > 0 ? m.height : TEXT_LINE_HEIGHT_PX + TEXT_PAD_Y * 2;
    if (selected) {
      const tol = VERTEX_GRAB_PX / z;
      if (Math.abs(pt.x - (anchor.x + w)) <= tol && Math.abs(pt.y - (anchor.y + h)) <= tol) {
        return { kind: 'text-resize', index: 2 };
      }
    }
    if (pt.x >= anchor.x && pt.x <= anchor.x + w && pt.y >= anchor.y && pt.y <= anchor.y + h) {
      return { kind: 'body', index: 0 };
    }
    return null;
  }

  // Legends are hit-tested by the viewer with live row-count geometry
  // (the box height depends on the current measurement set); the generic
  // path here cannot know the row count, so it defers.
  if (m.type === 'legend') return null;

  // FSFTM ellipse / stamp / callout / arc bodies (vertices tested above).
  const fsftmHit = hitFSFTMBody(pt, m, edgeTol);
  if (fsftmHit !== null) return fsftmHit ? { kind: 'body', index: 0 } : null;

  // Rectangle / highlight: two-corner bbox. The corners were already
  // tested as vertices; the body is the filled bbox.
  if ((m.type === 'rectangle' || m.type === 'highlight') && n === 2) {
    const a = pts[0]!;
    const b = pts[1]!;
    const minX = Math.min(a.x, b.x) - edgeTol;
    const maxX = Math.max(a.x, b.x) + edgeTol;
    const minY = Math.min(a.y, b.y) - edgeTol;
    const maxY = Math.max(a.y, b.y) + edgeTol;
    if (pt.x >= minX && pt.x <= maxX && pt.y >= minY && pt.y <= maxY) {
      return { kind: 'body', index: 0 };
    }
    return null;
  }

  const edges = edgeCount(m.type, n);

  // 2) Edge midpoint (add-vertex) - only on an already-selected,
  //    variable-vertex measurement.
  if (selected && supportsVariableVertices(m.type)) {
    for (let i = 0; i < edges; i++) {
      const a = pts[i]!;
      const b = pts[(i + 1) % n]!;
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      if (pixelDistance(pt.x, pt.y, mid.x, mid.y) < edgeTol) {
        return { kind: 'edge', index: i };
      }
    }
  }

  // 3) Edge / line body.
  if (OPEN_LINE_TYPES.has(m.type) || CLOSED_TYPES.has(m.type)) {
    let bestEdge = -1;
    let bestEdgeDist = Infinity;
    for (let i = 0; i < edges; i++) {
      const a = pts[i]!;
      const b = pts[(i + 1) % n]!;
      const d = pointToSegmentDistance(pt, a, b);
      if (d < edgeTol && d < bestEdgeDist) {
        bestEdgeDist = d;
        bestEdge = i;
      }
    }
    if (bestEdge >= 0) return { kind: 'body', index: bestEdge };
  }

  // 3b) Edges of cut-out holes belong to the area too.
  for (const h of m.holes ?? []) {
    for (let i = 0; i < h.length; i++) {
      if (pointToSegmentDistance(pt, h[i]!, h[(i + 1) % h.length]!) < edgeTol) return { kind: 'body', index: 0 };
    }
  }

  // 4) Interior - closed polygon fill (a cut-out hole is open, not part of it).
  if (
    CLOSED_TYPES.has(m.type) &&
    n >= 3 &&
    pointInPolygon(pt, pts) &&
    !(m.holes ?? []).some((h) => h.length >= 3 && pointInPolygon(pt, h))
  ) {
    return { kind: 'body', index: 0 };
  }

  return null;
}

/** Whether segment a-b crosses the axis-aligned box. */
function segmentTouchesBox(a: Point, b: Point, x0: number, y0: number, x1: number, y1: number): boolean {
  const inside = (p: Point) => p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1;
  if (inside(a) || inside(b)) return true;
  // Liang-Barsky clip: does any part of the segment fall inside the box?
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  let t0 = 0;
  let t1 = 1;
  const edges: [number, number][] = [
    [-dx, a.x - x0],
    [dx, x1 - a.x],
    [-dy, a.y - y0],
    [dy, y1 - a.y],
  ];
  for (const [pp, q] of edges) {
    if (pp === 0) {
      if (q < 0) return false;
      continue;
    }
    const r = q / pp;
    if (pp < 0) {
      if (r > t1) return false;
      if (r > t0) t0 = r;
    } else {
      if (r < t0) return false;
      if (r < t1) t1 = r;
    }
  }
  return t0 <= t1;
}

/**
 * Whether a markup is touched by a selection box (PDF units, any corner
 * order). Lines and polygons are tested on their real geometry, so a long
 * diagonal line or an L-shaped area is only picked when the box actually
 * touches it, not when the box merely overlaps its bounding box. A box
 * drawn entirely inside an area also selects that area. Other markup kinds
 * (text, stamps, ellipses, legends, ...) use their bounding box.
 */
export function measurementTouchesBox(
  m: EditableMeasurement,
  box: { x0: number; y0: number; x1: number; y1: number },
  tol = 0,
): boolean {
  const x0 = Math.min(box.x0, box.x1) - tol;
  const x1 = Math.max(box.x0, box.x1) + tol;
  const y0 = Math.min(box.y0, box.y1) - tol;
  const y1 = Math.max(box.y0, box.y1) + tol;
  const pts = m.points;
  const n = pts.length;
  if (n === 0) return false;
  if (OPEN_LINE_TYPES.has(m.type) || CLOSED_TYPES.has(m.type) || m.type === 'count') {
    if (n === 1 || m.type === 'count') return pts.some((p) => p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1);
    const edges = edgeCount(m.type, n);
    for (let i = 0; i < edges; i++) {
      if (segmentTouchesBox(pts[i]!, pts[(i + 1) % n]!, x0, y0, x1, y1)) return true;
    }
    return CLOSED_TYPES.has(m.type) && n >= 3 && pointInPolygon({ x: (x0 + x1) / 2, y: (y0 + y1) / 2 }, pts);
  }
  let bx0 = Infinity;
  let by0 = Infinity;
  let bx1 = -Infinity;
  let by1 = -Infinity;
  for (const p of pts) {
    if (p.x < bx0) bx0 = p.x;
    if (p.y < by0) by0 = p.y;
    if (p.x > bx1) bx1 = p.x;
    if (p.y > by1) by1 = p.y;
  }
  if (m.type === 'text' && m.width && m.width > 0) {
    bx1 = Math.max(bx1, pts[0]!.x + m.width);
    by1 = Math.max(by1, pts[0]!.y + (m.height && m.height > 0 ? m.height : TEXT_LINE_HEIGHT_PX + TEXT_PAD_Y * 2));
  }
  return bx0 <= x1 && bx1 >= x0 && by0 <= y1 && by1 >= y0;
}

/* ── Vertex add / delete ─────────────────────────────────────────────── */

/** Insert a vertex at `index + 1` on the segment from `index` to its
 *  successor, positioned at the segment midpoint. Returns a NEW array. */
export function insertVertexAt(points: Point[], edgeIndex: number): Point[] {
  const n = points.length;
  if (n < 2) return points;
  const a = points[edgeIndex]!;
  const b = points[(edgeIndex + 1) % n]!;
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  const next = points.slice();
  next.splice(edgeIndex + 1, 0, mid);
  return next;
}

/** Remove the vertex at `vertexIndex`. Returns a NEW array; callers must
 *  guard `points.length > minVertices(type)` before calling so the
 *  measurement never drops below a valid shape. */
export function deleteVertexAt(points: Point[], vertexIndex: number): Point[] {
  if (vertexIndex < 0 || vertexIndex >= points.length) return points;
  const next = points.slice();
  next.splice(vertexIndex, 1);
  return next;
}

/* ── Shape translation ───────────────────────────────────────────────── */

/** Translate every point of a shape by `(dx, dy)`. Returns a NEW array. */
export function translatePoints(points: Point[], dx: number, dy: number): Point[] {
  return points.map((p) => ({ x: p.x + dx, y: p.y + dy }));
}

/* ── Live recompute (the money path, mirrors create-time math) ──────── */

const SUP2 = '²';
const SUP3 = '³';
const TIMES = '×';

export interface RecomputePatch {
  value: number;
  label: string;
  unit?: string;
  area?: number;
  depth?: number;
  width?: number;
  height?: number;
  /** True when an area / volume polygon currently self-intersects (bowtie).
   *  The caller surfaces a non-blocking amber readout; the trace is still
   *  editable so the user can fix it (D-TKC-015). */
  selfIntersecting?: boolean;
}

/**
 * Recompute a measurement's value + label from a candidate set of points.
 *
 * This is the single source of truth for reshape-time numbers and is the
 * exact mirror of the create-time handlers in `TakeoffViewerModule`
 * (`handleCanvasDblClick`, `handleVolumeDepthConfirm`, distance / rectarea
 * paths). The label strings (`"(P: ...)"`, `"V = ..."`) are pinned because
 * the ledger and exports parse them.
 */
export function recomputeMeasurement(
  m: EditableMeasurement,
  points: Point[],
  scale: ScaleConfig,
): RecomputePatch {
  const unitLabel = scale.unitLabel;

  switch (m.type) {
    case 'distance': {
      const a = points[0];
      const b = points[1];
      if (!a || !b) return { value: 0, label: '' };
      const value = toRealDistance(pixelDistance(a.x, a.y, b.x, b.y), scale);
      return { value, label: formatMeasurement(value, unitLabel), unit: unitLabel };
    }

    case 'polyline': {
      let totalPx = 0;
      for (let i = 0; i < points.length - 1; i++) {
        const pa = points[i]!;
        const pb = points[i + 1]!;
        totalPx += pixelDistance(pa.x, pa.y, pb.x, pb.y);
      }
      const value = toRealDistance(totalPx, scale);
      return { value, label: formatMeasurement(value, unitLabel), unit: unitLabel };
    }

    case 'area': {
      const value = toRealArea(Math.max(0, polygonAreaPixels(points) - holesAreaPixels(m.holes)), scale);
      const perim = toRealDistance(polygonPerimeterPixels(points), scale);
      const label = `${formatMeasurement(value, unitLabel + SUP2)} (P: ${formatMeasurement(perim, unitLabel)})`;
      return {
        value,
        label,
        unit: `${unitLabel}${SUP2}`,
        selfIntersecting: isSelfIntersecting(points),
      };
    }

    case 'volume': {
      const area = toRealArea(Math.max(0, polygonAreaPixels(points) - holesAreaPixels(m.holes)), scale);
      const depth = m.depth ?? 0;
      const value = area * depth;
      const label =
        `V = ${formatMeasurement(value, unitLabel + SUP3)} ` +
        `(A: ${formatMeasurement(area, unitLabel + SUP2)} ${TIMES} D: ${formatMeasurement(depth, unitLabel)})`;
      return {
        value,
        label,
        unit: `${unitLabel}${SUP3}`,
        area,
        depth,
        selfIntersecting: isSelfIntersecting(points),
      };
    }

    case 'count': {
      // Vertex drag repositions a dot; the count equals the dot count.
      return { value: points.length, label: String(points.length), unit: 'pcs' };
    }

    case 'rectangle':
    case 'highlight': {
      const a = points[0];
      const b = points[1];
      const width = a && b ? Math.abs(b.x - a.x) : 0;
      const height = a && b ? Math.abs(b.y - a.y) : 0;
      return { value: 0, label: '', width, height };
    }

    case 'cloud':
    case 'arrow':
    case 'text':
      return { value: 0, label: '' };

    case 'perimeter': {
      let totalPx = 0;
      for (let i = 0; i < points.length; i++) {
        const pa = points[i]!;
        const pb = points[(i + 1) % points.length]!;
        totalPx += pixelDistance(pa.x, pa.y, pb.x, pb.y);
      }
      const value = toRealDistance(totalPx, scale);
      return { value, label: formatMeasurement(value, unitLabel), unit: unitLabel };
    }

    case 'diameter': {
      const a = points[0];
      const b = points[1];
      if (!a || !b) return { value: 0, label: '' };
      const value = toRealDistance(pixelDistance(a.x, a.y, b.x, b.y), scale);
      return { value, label: `Ø ${formatMeasurement(value, unitLabel)}`, unit: unitLabel };
    }

    case 'radiusCenter': {
      const c = points[0];
      const e = points[1];
      if (!c || !e) return { value: 0, label: '' };
      const value = toRealDistance(pixelDistance(c.x, c.y, e.x, e.y), scale);
      return { value, label: `R ${formatMeasurement(value, unitLabel)}`, unit: unitLabel };
    }

    case 'radius3Point': {
      if (points.length < 3) return { value: 0, label: '' };
      const circ = circleFrom3Points(points[0]!, points[1]!, points[2]!);
      if (!circ) return { value: 0, label: '' };
      const value = toRealDistance(circ.r, scale);
      return { value, label: `R ${formatMeasurement(value, unitLabel)}`, unit: unitLabel };
    }

    case 'angle': {
      if (points.length < 3) return { value: 0, label: '', unit: '°' };
      const v = points[0]!;
      const p1 = points[1]!;
      const p2 = points[2]!;
      const a1 = Math.atan2(p1.y - v.y, p1.x - v.x);
      const a2 = Math.atan2(p2.y - v.y, p2.x - v.x);
      let deg = Math.abs((a2 - a1) * 180 / Math.PI);
      if (deg > 180) deg = 360 - deg;
      return { value: deg, label: `${deg.toFixed(1)}°`, unit: '°' };
    }

    case 'polygonCutout': {
      const value = toRealArea(polygonAreaPixels(points), scale);
      return { value, label: `-${formatMeasurement(value, unitLabel + SUP2)}`, unit: `${unitLabel}${SUP2}` };
    }

    case 'ellipseCutout': {
      if (points.length < 2) return { value: 0, label: '' };
      const cp = points[0]!;
      const ep = points[1]!;
      const rPx = (Math.abs(ep.x - cp.x) + Math.abs(ep.y - cp.y)) / 2;
      const value = toRealArea(Math.PI * rPx * rPx, scale);
      return { value, label: `-${formatMeasurement(value, unitLabel + SUP2)}`, unit: `${unitLabel}${SUP2}` };
    }

    case 'dynamicFill': {
      const value = toRealArea(polygonAreaPixels(points), scale);
      return { value, label: formatMeasurement(value, unitLabel + SUP2), unit: `${unitLabel}${SUP2}` };
    }

    case 'arc': {
      const value = toRealDistance(arcLengthPx(points), scale);
      return { value, label: `⌒ ${formatMeasurement(value, unitLabel)}`, unit: unitLabel };
    }

    case 'ellipse': {
      const a = points[0];
      const b = points[1];
      const width = a && b ? Math.abs(b.x - a.x) : 0;
      const height = a && b ? Math.abs(b.y - a.y) : 0;
      return { value: 0, label: '', width, height };
    }

    case 'line':
    case 'polygon':
    case 'pen':
    case 'callout':
    case 'stamp':
      return { value: 0, label: '' };

    default:
      return { value: 0, label: '' };
  }
}
