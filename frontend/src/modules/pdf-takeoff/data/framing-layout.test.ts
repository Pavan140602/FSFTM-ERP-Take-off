import { describe, expect, it } from 'vitest';
import { layoutMembers, parseSpacing } from './framing-layout';

const rect = [
  { x: 0, y: 0 },
  { x: 100, y: 0 },
  { x: 100, y: 50 },
  { x: 0, y: 50 },
];

describe('framing layout', () => {
  it('lays vertical members across a rectangle at the spacing', () => {
    const lines = layoutMembers(rect, Math.PI / 2, 10);
    expect(lines.length).toBe(11);
    for (const [a, b] of lines) {
      expect(Math.abs(a.x - b.x)).toBeLessThan(1e-6);
      expect(Math.abs(Math.abs(b.y - a.y) - 50)).toBeLessThan(1e-6);
    }
  });
  it('clips to an L-shaped outline', () => {
    const L = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 40 },
      { x: 40, y: 40 },
      { x: 40, y: 100 },
      { x: 0, y: 100 },
    ];
    const lines = layoutMembers(L, 0, 20, 'half', false);
    const lens = lines.map(([a, b]) => Math.round(Math.hypot(b.x - a.x, b.y - a.y)));
    expect(lens).toEqual([100, 100, 40, 40, 40]);
  });
  it('reads spacings', () => {
    expect(parseSpacing('24')).toBeCloseTo(0.6096);
    expect(parseSpacing('24" O.C.')).toBeCloseTo(0.6096);
    expect(parseSpacing("2'-0\"")).toBeCloseTo(0.6096);
    expect(parseSpacing('600mm')).toBeCloseTo(0.6);
    expect(parseSpacing('abc')).toBeNull();
  });
});
