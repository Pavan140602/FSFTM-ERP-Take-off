// OE-DELIVERY: 2026-11-02-revu-zoom
/**
 * Revu-style deep zoom for the PDF takeoff viewer.
 *
 * A browser canvas cannot hold a whole E-size sheet at 1000%+ (side and
 * pixel-count limits, and seconds per pdf.js render). Revu renders only what
 * is on screen; we do the same:
 *
 *  - the page bitmap is rendered at most at {@link bitmapZoomCap} and CSS
 *    scaled above it (an instant, slightly soft backdrop);
 *  - a "detail" canvas re-renders just the visible region at the true zoom;
 *  - the measurement layer draws into a visible-region canvas the same way,
 *    so markups stay sharp at any zoom.
 *
 * Below the cap nothing changes: the viewer keeps its full-page canvases.
 * Pure helpers only, so they unit-test without a DOM.
 */

/** Hard ceilings for one canvas bitmap (well under every browser's limits). */
// 10 MP keeps a full-page re-render after a zoom quick; above it the
// visible-region tile keeps the drawing sharp (OE-DELIVERY 2026-11-04-perf-rerun).
export const MAX_BITMAP_SIDE = 6144;
export const MAX_BITMAP_PIXELS = 10_000_000;

/** Revu-like zoom range: 10% - 6400%. */
export const DEEP_ZOOM_MIN = 0.1;
export const DEEP_ZOOM_MAX = 64;

/** Largest zoom at which a full-page bitmap of ``pageW x pageH`` PDF units
 *  stays inside the canvas limits at device-pixel ratio ``dpr``. */
export function bitmapZoomCap(pageW: number, pageH: number, dpr: number): number {
  if (!(pageW > 0) || !(pageH > 0) || !(dpr > 0)) return 1;
  return Math.min(
    MAX_BITMAP_SIDE / (pageW * dpr),
    MAX_BITMAP_SIDE / (pageH * dpr),
    Math.sqrt(MAX_BITMAP_PIXELS / (pageW * pageH * dpr * dpr)),
  );
}

/** True when a full-page bitmap at ``zoom`` would exceed the limits. */
export function needsRegionRendering(pageW: number, pageH: number, zoom: number, dpr: number): boolean {
  return zoom > bitmapZoomCap(pageW, pageH, dpr) + 1e-9;
}

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** A rect in the page element's own CSS px (0,0 = the page's top-left). */
export interface Region {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * The part of the page element (``page``, a client rect) visible inside the
 * scroll viewport (``view``, a client rect), in page-local CSS px, snapped
 * outward to whole pixels. Null when nothing is visible.
 */
export function visibleRegion(view: Box, page: Box): Region | null {
  const l = Math.max(view.left, page.left);
  const t = Math.max(view.top, page.top);
  const r = Math.min(view.left + view.width, page.left + page.width);
  const b = Math.min(view.top + view.height, page.top + page.height);
  if (r - l < 1 || b - t < 1) return null;
  const x = Math.floor(l - page.left);
  const y = Math.floor(t - page.top);
  return {
    x,
    y,
    w: Math.min(Math.ceil(r - page.left), Math.ceil(page.width)) - x,
    h: Math.min(Math.ceil(b - page.top), Math.ceil(page.height)) - y,
  };
}

/** Same region? (re-render guard while scrolling by sub-pixel amounts). */
export function sameRegion(a: Region | null, b: Region | null): boolean {
  if (!a || !b) return a === b;
  return a.x === b.x && a.y === b.y && a.w === b.w && a.h === b.h;
}

/**
 * Zoom-to-box: the zoom that fits the PDF-unit rectangle ``r`` into a
 * ``viewW x viewH`` viewport (with a small margin, like Revu), and the PDF
 * point that must land at the viewport centre.
 */
export function zoomToBox(
  r: { x0: number; y0: number; x1: number; y1: number },
  viewW: number,
  viewH: number,
  maxZoom = DEEP_ZOOM_MAX,
  minZoom = DEEP_ZOOM_MIN,
): { zoom: number; cx: number; cy: number } | null {
  const w = Math.abs(r.x1 - r.x0);
  const h = Math.abs(r.y1 - r.y0);
  if (!(w > 0) || !(h > 0) || !(viewW > 0) || !(viewH > 0)) return null;
  const fit = Math.min(viewW / w, viewH / h) * 0.95;
  return {
    zoom: Math.min(maxZoom, Math.max(minZoom, fit)),
    cx: (r.x0 + r.x1) / 2,
    cy: (r.y0 + r.y1) / 2,
  };
}

/**
 * Scroll offsets that put PDF point (cx, cy) at the viewport centre, given
 * where the page element currently sits relative to the scroll content
 * (``pageOffsetLeft/Top`` = page client rect minus container client rect plus
 * the container's current scroll). Clamped at 0; the browser clamps the max.
 */
export function centreScroll(
  cx: number,
  cy: number,
  zoom: number,
  pageOffsetLeft: number,
  pageOffsetTop: number,
  viewW: number,
  viewH: number,
): { left: number; top: number } {
  return {
    left: Math.max(0, pageOffsetLeft + cx * zoom - viewW / 2),
    top: Math.max(0, pageOffsetTop + cy * zoom - viewH / 2),
  };
}

/** One Revu Zoom-tool click step. */
export const ZOOM_TOOL_STEP = 2;
