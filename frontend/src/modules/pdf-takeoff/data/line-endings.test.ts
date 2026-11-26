import { describe, expect, it } from 'vitest';

import { LINE_ENDINGS, drawMarkupEndings, isLineEnding } from './line-endings';

/** Minimal 2D-context stand-in that records path calls. */
function fakeCtx() {
  const calls: string[] = [];
  const rec = (name: string) => (..._a: unknown[]) => { calls.push(name); };
  const ctx = {
    calls,
    save: rec('save'), restore: rec('restore'), setLineDash: rec('setLineDash'),
    beginPath: rec('beginPath'), moveTo: rec('moveTo'), lineTo: rec('lineTo'),
    closePath: rec('closePath'), arc: rec('arc'), fill: rec('fill'), stroke: rec('stroke'),
    lineJoin: 'round', fillStyle: '#000',
  };
  return ctx as unknown as CanvasRenderingContext2D & { calls: string[] };
}

describe('line endings', () => {
  it('validates ending names', () => {
    expect(isLineEnding('closedArrow')).toBe(true);
    expect(isLineEnding('banana')).toBe(false);
    expect(LINE_ENDINGS[0]!.value).toBe('none');
  });

  it('draws nothing for none / missing endings', () => {
    const ctx = fakeCtx();
    drawMarkupEndings(ctx, [{ x: 0, y: 0 }, { x: 10, y: 0 }], 'none', undefined, 10);
    expect(ctx.calls).toEqual([]);
  });

  it('draws a filled arrow at the end and an open circle at the start', () => {
    const ctx = fakeCtx();
    drawMarkupEndings(ctx, [{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 100, y: 0 }], 'circle', 'closedArrow', 10);
    expect(ctx.calls.filter((c) => c === 'arc')).toHaveLength(1);
    expect(ctx.calls.filter((c) => c === 'fill')).toHaveLength(2); // circle background + arrow
    expect(ctx.calls.filter((c) => c === 'save')).toHaveLength(2);
  });

  it('needs two points', () => {
    const ctx = fakeCtx();
    drawMarkupEndings(ctx, [{ x: 0, y: 0 }], 'closedArrow', 'closedArrow', 10);
    expect(ctx.calls).toEqual([]);
  });
});
