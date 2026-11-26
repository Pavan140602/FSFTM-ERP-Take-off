import { describe, expect, it } from 'vitest';
import { canSplit, layoutRects, leaf, leaves, removeLeaf, resizeAt, splitLeaf, type LayoutNode } from './split-layout';

const two: LayoutNode = { kind: 'split', dir: 'row', children: [leaf('main'), leaf('p2')], sizes: [0.5, 0.5] };

describe('split layout tree', () => {
  it('adds an equal sibling when splitting the same way', () => {
    const t = splitLeaf(two, 'p2', 'row', 'p3');
    expect(leaves(t)).toEqual(['main', 'p2', 'p3']);
    const r = layoutRects(t).panes;
    expect(r.main!.w).toBeCloseTo(0.5);
    expect(r.p2!.w).toBeCloseTo(0.25);
    expect(r.p3!.x).toBeCloseTo(0.75);
  });

  it('nests when splitting the other way (left column into 3 rows)', () => {
    let t = splitLeaf(two, 'main', 'col', 'p3');
    t = splitLeaf(t, 'p3', 'col', 'p4');
    const r = layoutRects(t).panes;
    expect(r.main!.h).toBeCloseTo(0.5);
    expect(r.p3!.y).toBeCloseTo(0.5);
    expect(r.p4!.y).toBeCloseTo(0.75);
    expect(r.p2!.x).toBeCloseTo(0.5);
    expect(r.p2!.h).toBeCloseTo(1);
  });

  it('closing a pane gives its space back and collapses one-child splits', () => {
    const t = removeLeaf(splitLeaf(two, 'main', 'col', 'p3'), 'p3')!;
    expect(t).toEqual(two);
    expect(removeLeaf(leaf('main'), 'main')).toBeNull();
  });

  it('dragging a divider resizes only its two neighbours', () => {
    const t = resizeAt(splitLeaf(two, 'p2', 'row', 'p3'), [], 0, 0.3);
    const r = layoutRects(t).panes;
    expect(r.main!.w).toBeCloseTo(0.3);
    expect(r.p2!.w).toBeCloseTo(0.45);
    expect(r.p3!.w).toBeCloseTo(0.25);
  });

  it('refuses a split that leaves panes too small', () => {
    expect(canSplit(1000, 600, 'row')).toBe(true);
    expect(canSplit(400, 600, 'row')).toBe(false);
    expect(canSplit(400, 300, 'col')).toBe(false);
  });
});
