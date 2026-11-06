// OE-DELIVERY: 2026-11-02-revu-zoom
import { describe, expect, it } from 'vitest';
import {
  MAX_BITMAP_PIXELS,
  MAX_BITMAP_SIDE,
  bitmapZoomCap,
  needsRegionRendering,
  sameRegion,
  visibleRegion,
  zoomToBox,
} from './deep-zoom';

// ARCH E1 sheet: 30" x 42" = 2160 x 3024 PDF points.
const W = 3024;
const H = 2160;

describe('bitmapZoomCap', () => {
  it('keeps a full-page bitmap inside the side and pixel limits', () => {
    for (const dpr of [1, 1.25, 2]) {
      const z = bitmapZoomCap(W, H, dpr);
      expect(W * z * dpr).toBeLessThanOrEqual(MAX_BITMAP_SIDE + 1e-6);
      expect(W * H * z * z * dpr * dpr).toBeLessThanOrEqual(MAX_BITMAP_PIXELS + 1);
    }
  });

  it('switches to region rendering only above the cap', () => {
    expect(needsRegionRendering(W, H, 1, 1)).toBe(false);
    expect(needsRegionRendering(W, H, 8, 1)).toBe(true);
    // A letter page at 200% stays on the classic path.
    expect(needsRegionRendering(612, 792, 2, 2)).toBe(false);
  });
});

describe('visibleRegion', () => {
  it('clips the page to the viewport in page-local px', () => {
    const r = visibleRegion({ left: 100, top: 50, width: 800, height: 600 }, { left: -5000, top: -3000, width: 20000, height: 15000 });
    expect(r).toEqual({ x: 5100, y: 3050, w: 800, h: 600 });
  });

  it('handles a page smaller than the viewport and an off-screen page', () => {
    expect(visibleRegion({ left: 0, top: 0, width: 800, height: 600 }, { left: 100, top: 100, width: 200, height: 100 })).toEqual({
      x: 0,
      y: 0,
      w: 200,
      h: 100,
    });
    expect(visibleRegion({ left: 0, top: 0, width: 800, height: 600 }, { left: 900, top: 0, width: 100, height: 100 })).toBeNull();
  });

  it('compares regions', () => {
    expect(sameRegion(null, null)).toBe(true);
    expect(sameRegion({ x: 1, y: 2, w: 3, h: 4 }, { x: 1, y: 2, w: 3, h: 4 })).toBe(true);
    expect(sameRegion({ x: 1, y: 2, w: 3, h: 4 }, null)).toBe(false);
  });
});

describe('zoomToBox', () => {
  it('fits the box with a small margin and returns its centre', () => {
    const z = zoomToBox({ x0: 100, y0: 100, x1: 300, y1: 200 }, 800, 600)!;
    expect(z.zoom).toBeCloseTo(Math.min(800 / 200, 600 / 100) * 0.95);
    expect(z.cx).toBe(200);
    expect(z.cy).toBe(150);
  });

  it('clamps to the deep-zoom range and rejects empty boxes', () => {
    expect(zoomToBox({ x0: 0, y0: 0, x1: 0.5, y1: 0.5 }, 800, 600)!.zoom).toBe(64);
    expect(zoomToBox({ x0: 1, y0: 1, x1: 1, y1: 5 }, 800, 600)).toBeNull();
  });
});
