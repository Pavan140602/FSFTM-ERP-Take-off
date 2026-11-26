// FSFTM: stacked-markup detection (OE-DELIVERY 2026-11-25-fsftm-pdf).
//
// When a takeoff line is pasted or drawn on top of another one, the two read
// as a single line and the estimator cannot tell the quantity is counted
// twice. This finds markups on a page that sit on top of each other so the
// viewer can draw them with contrasting halos and a "xN" badge.

import { areasOverlap, linesOverlap } from './auto-takeoff';

export interface StackPoint {
  x: number;
  y: number;
}

export interface StackMarkup {
  id: string;
  type: string;
  points: StackPoint[];
}

export interface StackInfo {
  /** Stable id of the cluster (the id of its first member). */
  stackId: string;
  /** Number of markups in the cluster (always >= 2). */
  size: number;
  /** Position of this markup in the cluster, 0-based, in input order. */
  index: number;
}

const LINE_TYPES = new Set(['distance', 'polyline', 'perimeter', 'line', 'polylineMarkup', 'arrow', 'arc']);
const AREA_TYPES = new Set(['area', 'volume', 'rectangle', 'rectarea', 'rectArea', 'polygon', 'ellipse', 'cloud', 'cloudPlus']);

type Kind = 'line' | 'area' | 'count';

function kindOf(type: string): Kind | null {
  if (LINE_TYPES.has(type)) return 'line';
  if (AREA_TYPES.has(type)) return 'area';
  if (type === 'count') return 'count';
  return null;
}

function bboxOf(points: StackPoint[]): [number, number, number, number] {
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const p of points) {
    if (p.x < x0) x0 = p.x;
    if (p.y < y0) y0 = p.y;
    if (p.x > x1) x1 = p.x;
    if (p.y > y1) y1 = p.y;
  }
  return [x0, y0, x1, y1];
}

function boxesTouch(a: [number, number, number, number], b: [number, number, number, number], tol: number): boolean {
  return a[0] - tol <= b[2] && b[0] - tol <= a[2] && a[1] - tol <= b[3] && b[1] - tol <= a[3];
}

function overlaps(a: StackMarkup, b: StackMarkup, kind: Kind, tol: number): boolean {
  if (kind === 'count') {
    return a.points.some((p) => b.points.some((q) => Math.hypot(p.x - q.x, p.y - q.y) <= tol));
  }
  if (kind === 'area') {
    return a.points.length >= 2 && b.points.length >= 2 && areasOverlap(a.points, b.points);
  }
  for (let i = 0; i + 1 < a.points.length; i++) {
    const sa: [StackPoint, StackPoint] = [a.points[i]!, a.points[i + 1]!];
    for (let j = 0; j + 1 < b.points.length; j++) {
      if (linesOverlap(sa, [b.points[j]!, b.points[j + 1]!], tol)) return true;
    }
  }
  return false;
}

/**
 * Markups that lie on top of another markup of the same kind (line on line,
 * area on area, count point on count point). Returns an entry only for
 * markups that are part of a stack of two or more. `tol` is in the same units
 * as the points (PDF points), default 4.
 */
export function findStackedMarkups(markups: readonly StackMarkup[], tol = 4): Map<string, StackInfo> {
  const items = markups
    .map((m, order) => ({ m, order, kind: kindOf(m.type), box: bboxOf(m.points) }))
    .filter((x): x is typeof x & { kind: Kind } => x.kind !== null && x.m.points.length > 0);

  // Union-find over the items.
  const parent = items.map((_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]!]!;
      i = parent[i]!;
    }
    return i;
  };
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i]!;
      const b = items[j]!;
      if (a.kind !== b.kind || !boxesTouch(a.box, b.box, tol)) continue;
      if (find(i) === find(j)) continue;
      if (overlaps(a.m, b.m, a.kind, tol)) parent[find(j)] = find(i);
    }
  }

  const groups = new Map<number, number[]>();
  items.forEach((_, i) => {
    const r = find(i);
    const g = groups.get(r);
    if (g) g.push(i);
    else groups.set(r, [i]);
  });

  const out = new Map<string, StackInfo>();
  for (const members of groups.values()) {
    if (members.length < 2) continue;
    members.sort((a, b) => items[a]!.order - items[b]!.order);
    const stackId = items[members[0]!]!.m.id;
    members.forEach((idx, index) => {
      out.set(items[idx]!.m.id, { stackId, size: members.length, index });
    });
  }
  return out;
}

/** Contrasting halo colours for the members of a stack, by index. */
export const STACK_HALO_COLORS = ['#ffd400', '#ff2fd0', '#00e5ff', '#7cff00', '#ff7a00', '#ffffff'] as const;

export function stackHaloColor(index: number): string {
  return STACK_HALO_COLORS[index % STACK_HALO_COLORS.length]!;
}
