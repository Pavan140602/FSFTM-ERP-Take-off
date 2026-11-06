// OE-DELIVERY: 2026-10-30-revu-markup-tools
import { describe, expect, it } from 'vitest';
import {
  arcFrom3Points,
  arcLengthPx,
  buildStampText,
  calloutLeaderEnd,
  hitRevuBody,
  isRevuMarkupType,
  simplifyStroke,
} from './revu-markups';
import { hitTest, minVertices, recomputeMeasurement } from './hit-test';

describe('arc geometry', () => {
  it('measures a half circle through its top point', () => {
    // Radius 10 centred at (10, 0): start (0,0), through (10,-10), end (20,0).
    const len = arcLengthPx([{ x: 0, y: 0 }, { x: 10, y: -10 }, { x: 20, y: 0 }]);
    expect(len).toBeCloseTo(Math.PI * 10, 6);
  });

  it('takes the long way round when the middle point says so', () => {
    // Same circle; the arc passes through (10, 10) below, still a half circle,
    // but a quarter arc start->(10,-10) must not be confused with 3/4.
    const quarter = arcLengthPx([{ x: 0, y: 0 }, { x: 2.93, y: -7.07 }, { x: 10, y: -10 }]);
    expect(quarter).toBeCloseTo((Math.PI * 10) / 2, 1);
    const threeQuarter = arcLengthPx([{ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 10, y: -10 }]);
    expect(threeQuarter).toBeCloseTo((3 * Math.PI * 10) / 2, 6);
  });

  it('falls back to the chord for collinear points', () => {
    expect(arcFrom3Points({ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 })).toBeNull();
    expect(arcLengthPx([{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }])).toBeCloseTo(10);
  });

  it('recomputes the arc measurement in real units', () => {
    const scale = { pixelsPerUnit: 10, unitLabel: 'm' } as Parameters<typeof recomputeMeasurement>[2];
    const patch = recomputeMeasurement(
      { type: 'arc', points: [] },
      [{ x: 0, y: 0 }, { x: 10, y: -10 }, { x: 20, y: 0 }],
      scale,
    );
    expect(patch.value).toBeCloseTo(Math.PI, 4);
    expect(patch.unit).toBe('m');
  });
});

describe('pen simplification', () => {
  it('drops collinear samples and keeps the corners', () => {
    const pts = [
      ...Array.from({ length: 50 }, (_, i) => ({ x: i, y: 0 })),
      ...Array.from({ length: 50 }, (_, i) => ({ x: 49, y: i + 1 })),
    ];
    const out = simplifyStroke(pts, 0.5);
    expect(out).toEqual([{ x: 0, y: 0 }, { x: 49, y: 0 }, { x: 49, y: 50 }]);
  });

  it('caps the point count', () => {
    const zigzag = Array.from({ length: 10000 }, (_, i) => ({ x: i, y: i % 2 ? 5 : 0 }));
    expect(simplifyStroke(zigzag, 0.1, 500).length).toBeLessThanOrEqual(500);
  });
});

describe('hit-testing', () => {
  it('hits inside an ellipse but not its box corner', () => {
    const m = { type: 'ellipse', points: [{ x: 0, y: 0 }, { x: 100, y: 50 }] };
    expect(hitRevuBody({ x: 50, y: 25 }, m, 1)).toBe(true);
    expect(hitRevuBody({ x: 3, y: 3 }, m, 1)).toBe(false);
  });

  it('hits a stamp box and a callout leader', () => {
    expect(hitRevuBody({ x: 20, y: 10 }, { type: 'stamp', points: [{ x: 0, y: 0 }], width: 100, height: 40 }, 1)).toBe(true);
    const callout = { type: 'callout', points: [{ x: 0, y: 0 }, { x: 100, y: 100 }], width: 50, height: 20 };
    expect(hitRevuBody({ x: 50, y: 50 }, callout, 2)).toBe(true);
    expect(hitRevuBody({ x: 0, y: 80 }, callout, 2)).toBe(false);
  });

  it('routes line / pen / polygon through the generic edge test', () => {
    expect(hitTest({ x: 5, y: 0.2 }, { type: 'line', points: [{ x: 0, y: 0 }, { x: 10, y: 0 }] }, 1, false)).not.toBeNull();
    const poly = { type: 'polygon' as const, points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }] };
    expect(hitTest({ x: 50, y: 50 }, poly, 1, false)).toEqual({ kind: 'body', index: 0 });
    expect(minVertices('polygon')).toBe(3);
    expect(minVertices('stamp')).toBe(1);
  });
});

describe('misc', () => {
  it('builds stamp text with date and author', () => {
    const text = buildStampText('APPROVED', 'Pavan K', new Date('2026-10-30T12:00:00Z'));
    expect(text).toBe('APPROVED\n2026-10-30 · Pavan K');
  });

  it('leaves the callout box from the edge nearest the tip', () => {
    expect(calloutLeaderEnd({ x: 0, y: 5 }, { x: 10, y: 0, w: 20, h: 10 })).toEqual({ x: 10, y: 5 });
  });

  it('classifies markup types', () => {
    expect(isRevuMarkupType('stamp')).toBe(true);
    expect(isRevuMarkupType('arc')).toBe(false);
    expect(isRevuMarkupType('area')).toBe(false);
  });
});
