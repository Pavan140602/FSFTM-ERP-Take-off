// OE-DELIVERY: 2026-10-29-textsearch-rotated-runs-fix2 (was 2026-10-29-textsearch-rotated-runs)
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Pure helpers for "find on sheet" text search in the PDF takeoff viewer.
 *
 * Split out from `TakeoffViewerModule` so the one genuinely tricky bit - the
 * pdf.js text-layer coordinate conversion - is isolated and unit tested. The
 * rest of the search (per-page caching, the debounced fan-out, the result
 * list, jump-to-match) lives in the module; this file only turns a pdf.js
 * `TextContent` into placed text items and finds query hits with a bounding
 * box per hit, in the SAME coordinate space the overlay already draws in.
 *
 * COORDINATE CONTRACT (the high-risk part):
 *   pdf.js text-item `transform` maps the run's local space to PDF *user*
 *   space, whose origin is BOTTOM-LEFT with y growing UP. The takeoff overlay
 *   draws in the space produced by `page.getViewport({ scale: 1 })`, whose
 *   origin is TOP-LEFT with y growing DOWN (a stored measurement point at
 *   `{x, y}` is painted at `x * zoom * dpr`). For an unrotated page of height
 *   `H` PDF units, that viewport transform is `[1, 0, 0, -1, 0, H]`, so a
 *   PDF-user point `(ux, uy)` maps to top-left `(ux, H - uy)`.
 *
 *   A text run's `transform[4], transform[5]` (= e, f) is its baseline origin
 *   in PDF user space. The run advances `width` to the right and rises
 *   `height` above the baseline (cap height), both in PDF user units. So in
 *   top-left space the run box is:
 *       minX = e,              maxX = e + width
 *       maxY = H - f           (the baseline, lowest on screen)
 *       minY = (H - f) - height (the cap, highest on screen)
 *   which is exactly the `{ minX, minY, maxX, maxY }` space
 *   `boundingBoxOfPoints` / `computeZoomToBox` consume, so jump-to-match
 *   reuses the existing zoom-to-selection machinery unchanged.
 *
 *   v1 handles the rotation-0 case precisely (takeoff sheets render
 *   unrotated, consistent with how measurement points are stored). Rotated
 *   sheets would skew the box; that is a documented follow-up, not a v1 goal.
 *
 *   Run-level rotation IS handled (2026-10-29): CAD sheets carry vertical
 *   callouts whose runs are rotated 90/180 degrees on an unrotated page.
 *   placeTextItem builds the box from the run's advance direction
 *   (transform[0], transform[1]) and rise direction (transform[2],
 *   transform[3]) instead of assuming width always extends to the right;
 *   for unrotated runs the result is identical to the formula above.
 *
 *   Page-level rotation IS handled too (2026-10-29, fix2): the run's
 *   user-space corners are mapped through the page viewport transform
 *   (`page.getViewport({ scale: 1 }).transform`) into display space.
 *   The earlier code flipped user-space y against the viewport HEIGHT,
 *   which is only correct when rotation is 0 (display height == user
 *   height). A sideways sheet (rotation 90/270 - common for extracted
 *   drawing sets) misplaced every box by the height difference, e.g.
 *   864 units on a 1584x2448 sheet rotated to 2448x1584. Passing just
 *   a height (the legacy call form) still works and means rotation 0.
 */

import type { BoundingBox } from './takeoff-viewport';

/** A placed text run on a page, in top-left PDF-unit overlay space. */
export interface TextItem {
  /** The run's text (verbatim from pdf.js, including trailing spaces). */
  str: string;
  /** Bounding box of the run in top-left PDF-unit space. */
  box: BoundingBox;
}

/** A single search hit. `index` is the running match ordinal across the whole
 *  document (assigned by the caller as it concatenates pages); `box` frames
 *  the matched run(s) for highlight + zoom; `snippet` is a short context
 *  string for the result row. */
export interface TextMatch {
  page: number;
  index: number;
  box: BoundingBox;
  snippet: string;
}

/** Minimal shape of a pdf.js text-content item this module reads. pdf.js
 *  emits `{ str, transform, width, height, ... }` for text runs and marked-
 *  content markers `{ type: 'beginMarkedContent', ... }` with no `transform`;
 *  the latter are skipped. Kept structural (not importing pdfjs types) so the
 *  helper stays pure and trivially testable with hand-built fixtures. */
export interface RawTextContentItem {
  str?: string;
  /** 6-element text matrix `[a, b, c, d, e, f]`. */
  transform?: number[];
  /** Run advance width in PDF user units (unrotated). */
  width?: number;
  /** Run height (cap) in PDF user units (unrotated). */
  height?: number;
}

/** Max characters of context shown around a hit in the result list. */
const SNIPPET_RADIUS = 32;

/**
 * Convert a pdf.js text run to a placed `TextItem` in top-left PDF-unit
 * (display) space. `space` is either the page height `H` in PDF units
 * (legacy form, rotation-0 pages only) or the page viewport transform
 * from `page.getViewport({ scale: 1 }).transform`, which also handles
 * rotated pages. Returns `null` for non-text markers (no usable
 * `transform`) or empty runs so callers can filter them.
 *
 * See the file header for the derivation of the box.
 */
export function placeTextItem(
  item: RawTextContentItem,
  space: number | readonly number[],
): TextItem | null {
  const str = item.str;
  const t = item.transform;
  if (typeof str !== 'string' || str.length === 0) return null;
  if (!Array.isArray(t) || t.length < 6) return null;

  const a = t[0]!;
  const b = t[1]!;
  const c = t[2]!;
  const d = t[3]!;
  const e = t[4]!;
  const f = t[5]!;
  if (![a, b, c, d, e, f].every(Number.isFinite)) return null;

  const width = Number.isFinite(item.width) ? (item.width as number) : 0;
  // pdf.js sometimes reports height 0 for whitespace-only runs; fall back to
  // the matrix vertical scale (|d|) so the box still has a sensible height.
  const rawH = Number.isFinite(item.height) ? (item.height as number) : 0;
  const height = rawH > 0 ? rawH : Math.abs(d) || Math.abs(a) || 0;

  // Build the box from the run's own directions instead of assuming the
  // text runs to the right: the run advances along (a, b) for `width`
  // user units and its glyphs rise along (c, d) for `height`. The four
  // corners in bottom-up user space give the axis-aligned bounds; for
  // unrotated runs this reduces to minX = e, maxX = e + width,
  // baseline maxY = H - f, cap minY = (H - f) - height, exactly as
  // before. Rotated runs (the vertical callouts all over CAD sheets)
  // previously got a flat box extending right from the baseline origin
  // - nowhere near the actual text.
  const advLen = Math.hypot(a, b);
  const riseLen = Math.hypot(c, d);
  if (advLen === 0 || riseLen === 0) return null;
  const advX = (a / advLen) * Math.max(0, width);
  const advY = (b / advLen) * Math.max(0, width);
  const riseX = (c / riseLen) * height;
  const riseY = (d / riseLen) * height;
  const xs = [e, e + advX, e + advX + riseX, e + riseX];
  const ys = [f, f + advY, f + advY + riseY, f + riseY];

  // Map the user-space corners into display (top-left) space through
  // the page viewport transform [va, vb, vc, vd, ve, vf]:
  //   X = va*x + vc*y + ve,  Y = vb*x + vd*y + vf.
  // A bare height means the rotation-0 transform [1, 0, 0, -1, 0, H],
  // under which X = x and Y = H - y - the original formula exactly.
  const vt: readonly number[] = typeof space === 'number' ? [1, 0, 0, -1, 0, space] : space;
  const va = vt[0] ?? 1;
  const vb = vt[1] ?? 0;
  const vc = vt[2] ?? 0;
  const vd = vt[3] ?? -1;
  const ve = vt[4] ?? 0;
  const vf = vt[5] ?? 0;
  const dxs = xs.map((x, i) => va * x + vc * ys[i]! + ve);
  const dys = xs.map((x, i) => vb * x + vd * ys[i]! + vf);
  return {
    str,
    box: {
      minX: Math.min(...dxs),
      maxX: Math.max(...dxs),
      minY: Math.min(...dys),
      maxY: Math.max(...dys),
    },
  };
}

/**
 * Build placed text items from a pdf.js `TextContent.items` array and
 * the page height (rotation-0 pages) or viewport transform - see
 * placeTextItem. Skips markers / empty runs. Pure: no pdf.js calls.
 */
export function itemsFromTextContent(
  items: ReadonlyArray<RawTextContentItem>,
  space: number | readonly number[],
): TextItem[] {
  const out: TextItem[] = [];
  for (const it of items) {
    const placed = placeTextItem(it, space);
    if (placed) out.push(placed);
  }
  return out;
}

/** Union of two boxes (small local helper; `mergeBoundingBoxes` in
 *  takeoff-viewport takes an array - this avoids the array allocation in the
 *  hot per-item loop). */
function unionBox(a: BoundingBox, b: BoundingBox): BoundingBox {
  return {
    minX: Math.min(a.minX, b.minX),
    minY: Math.min(a.minY, b.minY),
    maxX: Math.max(a.maxX, b.maxX),
    maxY: Math.max(a.maxY, b.maxY),
  };
}

/**
 * Find all case-insensitive occurrences of `query` within a page's placed
 * text items.
 *
 * v1 matches PER ITEM: pdf.js splits text into runs, so a query that straddles
 * two runs ("fire rated" split as "fire " + "rated") is not found as a single
 * hit. This is the documented v1 limitation; per-item matching covers the
 * overwhelmingly common single-run case (room names, sheet numbers, "SCALE",
 * door tags) and never produces a wrong box. A run can contain the query more
 * than once; every occurrence is returned. The box for a hit is the whole
 * run's box (a sub-run glyph box would need per-glyph offsets pdf.js does not
 * cheaply expose); when several adjacent runs each contain the query they
 * stay separate hits.
 *
 * `startIndex` seeds the running `index` so a caller scanning many pages gets
 * globally-unique, in-order ordinals; the function returns nothing about the
 * next index (the caller advances by `matches.length`).
 */
export function findMatchesInPage(
  items: ReadonlyArray<TextItem>,
  query: string,
  page: number,
  startIndex: number = 0,
): TextMatch[] {
  const q = query.trim().toLowerCase();
  if (q.length === 0) return [];
  const matches: TextMatch[] = [];
  let idx = startIndex;
  for (const item of items) {
    const hay = item.str.toLowerCase();
    let from = 0;
    let pos = hay.indexOf(q, from);
    while (pos !== -1) {
      matches.push({
        page,
        index: idx++,
        box: item.box,
        snippet: buildSnippet(item.str, pos, q.length),
      });
      from = pos + q.length;
      pos = hay.indexOf(q, from);
    }
  }
  return matches;
}

/**
 * A short context snippet around a hit: up to `SNIPPET_RADIUS` chars either
 * side of the match, with an ellipsis where the run text was clipped, and
 * surrounding whitespace collapsed so the result row stays on one line.
 */
export function buildSnippet(runText: string, matchStart: number, matchLen: number): string {
  const start = Math.max(0, matchStart - SNIPPET_RADIUS);
  const end = Math.min(runText.length, matchStart + matchLen + SNIPPET_RADIUS);
  let s = runText.slice(start, end).replace(/\s+/g, ' ').trim();
  if (start > 0) s = `…${s}`;
  if (end < runText.length) s = `${s}…`;
  return s;
}

export type { BoundingBox };
export { unionBox };
