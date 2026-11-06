// OE-DELIVERY: 2026-11-08-stud-walls
import { describe, expect, it } from 'vitest';
import { studCount, studPositions } from './stud-wall';

// 1/8" = 1'-0": 9 units per foot, 24" o.c. = 18 units.
const ft = (f: number) => f * 9;

describe('studs in a wall run', () => {
  it('a stud at the start, one every spacing, one at the end', () => {
    const tag = { ww: 4.5, sd: ft(2), ss: 24, seg: 'wall' };
    expect(studCount([{ x: 0, y: 0 }, { x: ft(10), y: 0 }], tag)).toBe(6); // 0,2,4,6,8,10
    expect(studCount([{ x: 0, y: 0 }, { x: ft(9), y: 0 }], tag)).toBe(6); // 0,2,4,6,8 + end at 9
    expect(studCount([{ x: 0, y: 0 }, { x: 0, y: ft(1) }], tag)).toBe(2);
  });
  it('positions match the count and end on the run end', () => {
    const pts = studPositions({ x: 0, y: 0 }, { x: ft(9), y: 0 }, ft(2));
    expect(pts.length).toBe(6);
    expect(pts[pts.length - 1]).toEqual({ x: ft(9), y: 0 });
  });
  it('header areas and runs without a spacing carry no studs', () => {
    expect(studCount([{ x: 0, y: 0 }, { x: ft(6), y: 0 }], { ww: 4.5, sd: ft(2), seg: 'header' })).toBe(0);
    expect(studCount([{ x: 0, y: 0 }, { x: ft(6), y: 0 }], { ww: 4.5 })).toBe(0);
  });
});
