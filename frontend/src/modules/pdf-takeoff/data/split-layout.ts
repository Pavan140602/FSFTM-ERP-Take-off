/**
 * Split-pane layout tree (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * Any pane can be split again, side by side ('row') or stacked ('col'), as
 * many times as there is room for - like nested split views in a desktop
 * PDF tool. Leaves are pane keys ('main' is the main drawing's pane). Sizes
 * are fractions of the parent that add up to 1.
 */

export type SplitDir = 'row' | 'col';
export type LayoutNode =
  | { kind: 'leaf'; pane: string }
  | { kind: 'split'; dir: SplitDir; children: LayoutNode[]; sizes: number[] };

export type Rect = { x: number; y: number; w: number; h: number };
export type Divider = { path: number[]; index: number; dir: SplitDir; rect: Rect };

/** Smallest pane a split may leave, in screen pixels. */
export const MIN_PANE_W = 260;
export const MIN_PANE_H = 180;

export const leaf = (pane: string): LayoutNode => ({ kind: 'leaf', pane });

export function leaves(node: LayoutNode | null | undefined): string[] {
  if (!node) return [];
  if (node.kind === 'leaf') return [node.pane];
  return node.children.flatMap(leaves);
}

/** Split `target` in `dir`, putting `newPane` after it. A split in the same
 *  direction as the parent adds an equal sibling instead of nesting. */
export function splitLeaf(root: LayoutNode, target: string, dir: SplitDir, newPane: string): LayoutNode {
  const walk = (node: LayoutNode): LayoutNode => {
    if (node.kind === 'leaf') {
      if (node.pane !== target) return node;
      return { kind: 'split', dir, children: [node, leaf(newPane)], sizes: [0.5, 0.5] };
    }
    const i = node.children.findIndex((c) => c.kind === 'leaf' && c.pane === target);
    if (i >= 0 && node.dir === dir) {
      // Halve the target and give the other half to the new pane.
      const half = node.sizes[i]! / 2;
      const children = [...node.children.slice(0, i + 1), leaf(newPane), ...node.children.slice(i + 1)];
      const sizes = [...node.sizes.slice(0, i), half, half, ...node.sizes.slice(i + 1)];
      return { ...node, children, sizes };
    }
    return { ...node, children: node.children.map(walk) };
  };
  return walk(root);
}

/** Remove a pane; its space goes to its neighbours. Returns null when
 *  nothing is left. A split left with one child collapses into it. */
export function removeLeaf(root: LayoutNode, target: string): LayoutNode | null {
  const walk = (node: LayoutNode): LayoutNode | null => {
    if (node.kind === 'leaf') return node.pane === target ? null : node;
    const kept: LayoutNode[] = [];
    const sizes: number[] = [];
    node.children.forEach((c, i) => {
      const r = walk(c);
      if (r) {
        kept.push(r);
        sizes.push(node.sizes[i]!);
      }
    });
    if (kept.length === 0) return null;
    if (kept.length === 1) return kept[0]!;
    const total = sizes.reduce((a, b) => a + b, 0) || 1;
    return { ...node, children: kept, sizes: sizes.map((x) => x / total) };
  };
  return walk(root);
}

/** Pane rectangles and the dividers between them, as fractions (0..1) of
 *  the whole split area. */
export function layoutRects(root: LayoutNode): { panes: Record<string, Rect>; dividers: Divider[] } {
  const panes: Record<string, Rect> = {};
  const dividers: Divider[] = [];
  const walk = (node: LayoutNode, r: Rect, path: number[]) => {
    if (node.kind === 'leaf') {
      panes[node.pane] = r;
      return;
    }
    let at = 0;
    node.children.forEach((c, i) => {
      const f = node.sizes[i]!;
      const cr: Rect = node.dir === 'row'
        ? { x: r.x + at * r.w, y: r.y, w: f * r.w, h: r.h }
        : { x: r.x, y: r.y + at * r.h, w: r.w, h: f * r.h };
      walk(c, cr, [...path, i]);
      at += f;
      if (i < node.children.length - 1) {
        dividers.push({
          path,
          index: i,
          dir: node.dir,
          rect: node.dir === 'row' ? { x: r.x + at * r.w, y: r.y, w: 0, h: r.h } : { x: r.x, y: r.y + at * r.h, w: r.w, h: 0 },
        });
      }
    });
  };
  walk(root, { x: 0, y: 0, w: 1, h: 1 }, []);
  return { panes, dividers };
}

/** Move the divider after child `index` of the split at `path` so it sits
 *  at fraction `at` of that split (each side keeps at least `min`). */
export function resizeAt(root: LayoutNode, path: number[], index: number, at: number, min = 0.08): LayoutNode {
  const walk = (node: LayoutNode, depth: number): LayoutNode => {
    if (node.kind === 'leaf') return node;
    if (depth < path.length) {
      const k = path[depth]!;
      return { ...node, children: node.children.map((c, i) => (i === k ? walk(c, depth + 1) : c)) };
    }
    const before = node.sizes.slice(0, index).reduce((a, b) => a + b, 0);
    const pair = node.sizes[index]! + node.sizes[index + 1]!;
    const left = Math.min(pair - min, Math.max(min, at - before));
    const sizes = [...node.sizes];
    sizes[index] = left;
    sizes[index + 1] = pair - left;
    return { ...node, sizes };
  };
  return walk(root, 0);
}

/** The split node at `path` (for its on-screen box while dragging). */
export function nodeAt(root: LayoutNode, path: number[]): LayoutNode | null {
  let n: LayoutNode = root;
  for (const k of path) {
    if (n.kind !== 'split') return null;
    n = n.children[k]!;
  }
  return n;
}

/** Whether splitting a pane of `wPx` x `hPx` in `dir` leaves room for two. */
export function canSplit(wPx: number, hPx: number, dir: SplitDir): boolean {
  return dir === 'row' ? wPx / 2 >= MIN_PANE_W && hPx >= MIN_PANE_H : hPx / 2 >= MIN_PANE_H && wPx >= MIN_PANE_W;
}
