import { describe, expect, it } from 'vitest';

import { findStackedMarkups, stackHaloColor } from './overlap-stacks';

const line = (id: string, x0: number, y0: number, x1: number, y1: number, type = 'distance') => ({
  id,
  type,
  points: [{ x: x0, y: y0 }, { x: x1, y: y1 }],
});

describe('findStackedMarkups', () => {
  it('flags a pasted copy sitting on the original line', () => {
    const res = findStackedMarkups([line('a', 0, 0, 100, 0), line('b', 0, 1, 100, 1), line('c', 0, 200, 100, 200)]);
    expect(res.get('a')).toEqual({ stackId: 'a', size: 2, index: 0 });
    expect(res.get('b')).toEqual({ stackId: 'a', size: 2, index: 1 });
    expect(res.has('c')).toBe(false);
  });

  it('chains three stacked lines into one stack', () => {
    const res = findStackedMarkups([line('a', 0, 0, 100, 0), line('b', 10, 0, 110, 0), line('c', 20, 0, 120, 0, 'polyline')]);
    expect(res.get('c')?.size).toBe(3);
    expect(res.get('c')?.index).toBe(2);
  });

  it('does not flag crossing or offset lines', () => {
    const res = findStackedMarkups([line('a', 0, 0, 100, 0), line('b', 50, -50, 50, 50), line('c', 0, 20, 100, 20)]);
    expect(res.size).toBe(0);
  });

  it('only compares markups of the same kind', () => {
    const area = { id: 'r', type: 'area', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }] };
    const res = findStackedMarkups([area, line('a', 0, 0, 100, 0)]);
    expect(res.size).toBe(0);
  });

  it('flags stacked areas and stacked count points', () => {
    const sq = (id: string, d: number) => ({ id, type: 'area', points: [{ x: d, y: d }, { x: 100 + d, y: d }, { x: 100 + d, y: 100 + d }, { x: d, y: 100 + d }] });
    const cnt = (id: string, x: number) => ({ id, type: 'count', points: [{ x, y: 5 }] });
    const res = findStackedMarkups([sq('s1', 0), sq('s2', 2), cnt('c1', 500), cnt('c2', 501)]);
    expect(res.get('s2')?.size).toBe(2);
    expect(res.get('c2')?.size).toBe(2);
  });

  it('ignores annotation types and empty markups', () => {
    const res = findStackedMarkups([
      { id: 't1', type: 'text', points: [{ x: 0, y: 0 }] },
      { id: 't2', type: 'text', points: [{ x: 0, y: 0 }] },
      { id: 'e', type: 'distance', points: [] },
    ]);
    expect(res.size).toBe(0);
  });

  it('gives each stack member a distinct halo colour', () => {
    expect(stackHaloColor(0)).not.toBe(stackHaloColor(1));
  });
});
