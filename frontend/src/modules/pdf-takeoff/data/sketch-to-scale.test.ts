// OE-DELIVERY: 2026-11-02-revu-viewports-sketch
import { describe, expect, it } from 'vitest';
import {
  parseSketchInput,
  parseSketchLength,
  reconcilePageValues,
  reconcileViewportValues,
  sketchPoint,
} from './sketch-to-scale';
import {
  emptyPageScales,
  hydratePageScales,
  pageScalesHaveCalibration,
  reconcilePageScales,
  removeViewport,
  scaleForMeasurement,
  setPageScale,
  upsertViewport,
  viewportAt,
  type Viewport,
} from './page-scales';
import { recomputeMeasurement } from './hit-test';

const vp = (id: string, x: number, y: number, w: number, h: number, ppu: number): Viewport => ({
  id,
  name: id,
  rect: { x, y, w, h },
  scale: { pixelsPerUnit: ppu, unitLabel: 'm' },
});

describe('parseSketchLength', () => {
  it('reads plain numbers in the reader system', () => {
    expect(parseSketchLength('2.5', 'metric')).toBeCloseTo(2.5);
    expect(parseSketchLength('2,5', 'metric')).toBeCloseTo(2.5);
    expect(parseSketchLength('10', 'imperial')).toBeCloseTo(3.048);
  });

  it('honours explicit units', () => {
    expect(parseSketchLength('3500mm', 'imperial')).toBeCloseTo(3.5);
    expect(parseSketchLength('250 cm', 'metric')).toBeCloseTo(2.5);
    expect(parseSketchLength('12ft', 'metric')).toBeCloseTo(3.6576);
    expect(parseSketchLength('6in', 'metric')).toBeCloseTo(0.1524);
  });

  it('reads feet and inches with fractions', () => {
    expect(parseSketchLength(`12'6"`, 'metric')).toBeCloseTo(3.81);
    expect(parseSketchLength(`12'-6"`, 'metric')).toBeCloseTo(3.81);
    expect(parseSketchLength(`1' 6 1/2"`, 'metric')).toBeCloseTo(0.3048 + 6.5 * 0.0254);
    expect(parseSketchLength(`5'`, 'metric')).toBeCloseTo(1.524);
  });

  it('rejects junk, zero and negatives', () => {
    expect(parseSketchLength('', 'metric')).toBeNull();
    expect(parseSketchLength('abc', 'metric')).toBeNull();
    expect(parseSketchLength('0', 'metric')).toBeNull();
    expect(parseSketchLength('-3', 'metric')).toBeNull();
  });
});

describe('parseSketchInput + sketchPoint', () => {
  const scale = { pixelsPerUnit: 10, unitLabel: 'm' };

  it('follows the cursor direction without an angle', () => {
    const inp = parseSketchInput('5', 'metric')!;
    expect(inp.angleDeg).toBeNull();
    const p = sketchPoint({ x: 0, y: 0 }, { x: 3, y: 4 }, inp, scale)!;
    expect(p.x).toBeCloseTo(30);
    expect(p.y).toBeCloseTo(40);
  });

  it('uses an absolute CCW angle, y-down page space', () => {
    const up = sketchPoint({ x: 100, y: 100 }, null, parseSketchInput('2<90', 'metric')!, scale)!;
    expect(up.x).toBeCloseTo(100);
    expect(up.y).toBeCloseTo(80);
    const left = sketchPoint({ x: 100, y: 100 }, { x: 999, y: 0 }, parseSketchInput('1@180', 'metric')!, scale)!;
    expect(left.x).toBeCloseTo(90);
    expect(left.y).toBeCloseTo(100);
  });

  it('defaults east with no cursor and refuses an unusable scale', () => {
    const p = sketchPoint({ x: 0, y: 0 }, null, { meters: 1, angleDeg: null }, scale)!;
    expect(p).toEqual({ x: 10, y: 0 });
    expect(sketchPoint({ x: 0, y: 0 }, null, { meters: 1, angleDeg: null }, { pixelsPerUnit: 0, unitLabel: 'm' })).toBeNull();
    expect(parseSketchInput('1<2<3', 'metric')).toBeNull();
    expect(parseSketchInput('1<x', 'metric')).toBeNull();
  });
});

describe('viewport model', () => {
  it('resolves the topmost viewport holding the first point', () => {
    let ps = setPageScale(emptyPageScales(), 1, { pixelsPerUnit: 50, unitLabel: 'm' });
    ps = upsertViewport(ps, 1, vp('a', 0, 0, 100, 100, 5));
    ps = upsertViewport(ps, 1, vp('b', 50, 50, 100, 100, 20));
    expect(viewportAt(ps, 1, { x: 10, y: 10 })?.id).toBe('a');
    expect(viewportAt(ps, 1, { x: 60, y: 60 })?.id).toBe('b');
    expect(viewportAt(ps, 2, { x: 10, y: 10 })).toBeNull();
    expect(scaleForMeasurement(ps, 1, [{ x: 500, y: 500 }]).pixelsPerUnit).toBe(50);
    expect(scaleForMeasurement(ps, 1, [{ x: 10, y: 10 }, { x: 500, y: 500 }]).pixelsPerUnit).toBe(5);
  });

  it('keeps viewports through a page recalibration and removes cleanly', () => {
    let ps = upsertViewport(emptyPageScales(), 3, vp('a', 0, 0, 10, 10, 5));
    ps = setPageScale(ps, 3, { pixelsPerUnit: 7, unitLabel: 'm' });
    expect(ps.viewports?.[3]).toHaveLength(1);
    expect(pageScalesHaveCalibration(upsertViewport(emptyPageScales(), 2, vp('x', 0, 0, 1, 1, 1)))).toBe(true);
    ps = removeViewport(ps, 3, 'a');
    expect(ps.viewports?.[3]).toBeUndefined();
  });

  it('round-trips through hydrate and drops malformed entries', () => {
    const raw = JSON.parse(
      JSON.stringify({
        defaultScale: { pixelsPerUnit: 100, unitLabel: 'm' },
        byPage: {},
        viewports: {
          '1': [vp('ok', 1, 2, 3, 4, 9), { id: 'bad', rect: { x: 'no' }, scale: { pixelsPerUnit: 1, unitLabel: 'm' } }],
          zero: [vp('z', 0, 0, 1, 1, 1)],
        },
      }),
    );
    const ps = hydratePageScales(raw, null);
    expect(ps.viewports?.[1]?.map((v) => v.id)).toEqual(['ok']);
    expect(Object.keys(ps.viewports ?? {})).toEqual(['1']);
    expect(hydratePageScales({ defaultScale: { pixelsPerUnit: 100, unitLabel: 'm' }, byPage: {} }, null).viewports).toBeUndefined();
  });

  it('merges viewports local-first in reconcile', () => {
    const server = upsertViewport(upsertViewport(emptyPageScales(), 1, vp('s1', 0, 0, 1, 1, 1)), 2, vp('s2', 0, 0, 1, 1, 1));
    const local = upsertViewport(emptyPageScales(), 1, vp('l1', 0, 0, 1, 1, 1));
    const merged = reconcilePageScales(local, server)!;
    expect(merged.viewports?.[1]?.[0]?.id).toBe('l1');
    expect(merged.viewports?.[2]?.[0]?.id).toBe('s2');
  });
});

describe('viewport value reconciliation', () => {
  const recompute = (m: Parameters<typeof recomputeMeasurement>[0], pts: { x: number; y: number }[], sc: Parameters<typeof recomputeMeasurement>[2]) =>
    recomputeMeasurement(m, pts, sc) as { value: number };
  const line = (id: string, x: number, page = 1) => ({
    id,
    type: 'distance',
    page,
    points: [{ x, y: 0 }, { x: x + 100, y: 0 }],
    value: 1, // computed at the page scale of 100 px/m
  });

  it('re-derives rows inside a viewport and leaves the rest alone', () => {
    const ps = upsertViewport(setPageScale(emptyPageScales(), 1, { pixelsPerUnit: 100, unitLabel: 'm' }), 1, vp('v', 0, -10, 50, 20, 10));
    const ms = [line('in', 0), line('out', 500), line('other-page', 0, 2)];
    const out = reconcileViewportValues(ms, ps, recompute);
    expect(out[0]!.value).toBeCloseTo(10);
    expect(out[1]).toBe(ms[1]);
    expect(out[2]).toBe(ms[2]);
    // Second pass settles: same array back.
    expect(reconcileViewportValues(out, ps, recompute)).toBe(out);
  });

  it('is a no-op without viewports and restores the page scale after delete', () => {
    const page = setPageScale(emptyPageScales(), 1, { pixelsPerUnit: 100, unitLabel: 'm' });
    const ms = [line('a', 0)];
    expect(reconcileViewportValues(ms, page, recompute)).toBe(ms);
    const inside = [{ ...ms[0]!, value: 10 }];
    const back = reconcilePageValues(inside, page, 1, recompute);
    expect(back[0]!.value).toBeCloseTo(1);
  });
});
