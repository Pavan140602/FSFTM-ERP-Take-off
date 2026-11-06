// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Per-page (per-sheet) scale model for the PDF takeoff viewer.
 *
 * A multi-sheet drawing set has a DIFFERENT scale per sheet: the floor
 * plan on page 1 may be 1:50 while the site plan on page 3 is 1:500.
 * Storing a single document-wide scale made every measurement on a page
 * whose scale differed from the calibrated one wrong. This module keeps a
 * scale per 1-indexed page, with a single ``defaultScale`` applied to any
 * page that has not been calibrated yet.
 *
 * The shape is pure data so it round-trips through localStorage and is
 * unit-testable without mounting the viewer. It deliberately mirrors the
 * DWG side (``features/dwg-takeoff/lib/calibration-store``), which already
 * keeps an independent scale per paper-space layout.
 */

import type { ScaleConfig } from './scale-helpers';

/** Page-keyed scale map. Keys are 1-indexed page numbers as numbers. */
export interface PageScales {
  /** Scale used for any page without its own calibration. */
  defaultScale: ScaleConfig;
  /** Per-page overrides. A page present here was calibrated on that page. */
  byPage: Record<number, ScaleConfig>;
  /** Bluebeam-style viewports: rectangles on a page that carry their own
   *  scale (a 1:20 detail on a 1:100 sheet). A measurement whose first point
   *  falls inside one reads that viewport's scale instead of the page's.
   *  Optional so every pre-viewport payload stays valid.
   *  OE-DELIVERY: 2026-11-02-revu-viewports-sketch */
  viewports?: Record<number, Viewport[]>;
}

/** A scaled region of a page, in PDF user units (OE-DELIVERY 2026-11-02-revu-viewports-sketch). */
export interface Viewport {
  id: string;
  name: string;
  rect: { x: number; y: number; w: number; h: number };
  scale: ScaleConfig;
  /** Display label of the scale (preset label or "1:N"), for the badge. */
  scaleLabel?: string;
}

/** The factory default scale used before any calibration (1px ~ 0.01 m).
 *  Matches the viewer's historical initial ``{ pixelsPerUnit: 100 }``. */
export function defaultScaleConfig(): ScaleConfig {
  return { pixelsPerUnit: 100, unitLabel: 'm' };
}

/** Build an empty page-scale model with the factory default. */
export function emptyPageScales(): PageScales {
  return { defaultScale: defaultScaleConfig(), byPage: {} };
}

/**
 * Resolve the effective scale for a page: its own calibration when it has
 * one, otherwise the document default. This is the single accessor every
 * measurement-conversion path should use so a page never silently borrows
 * a neighbouring sheet's scale.
 */
export function scaleForPage(ps: PageScales, page: number): ScaleConfig {
  const own = ps.byPage[page];
  return own ?? ps.defaultScale;
}

/** True when the given page has its own calibration (vs. the default). */
export function pageIsCalibrated(ps: PageScales, page: number): boolean {
  return Object.prototype.hasOwnProperty.call(ps.byPage, page);
}

/**
 * Return a NEW model with ``page`` calibrated to ``scale``. The default is
 * left untouched so other uncalibrated pages keep falling back to it. We do
 * NOT mutate the input (React state must stay immutable).
 */
export function setPageScale(
  ps: PageScales,
  page: number,
  scale: ScaleConfig,
): PageScales {
  return {
    ...ps,
    defaultScale: ps.defaultScale,
    byPage: { ...ps.byPage, [page]: scale },
  };
}

/* ── Viewports (OE-DELIVERY 2026-11-02-revu-viewports-sketch) ─────────── */

/** Upper bound per page, mirrored by the backend size guard. */
export const MAX_VIEWPORTS_PER_PAGE = 50;

/** The viewports of one page, in creation order (later ones sit on top). */
export function viewportsForPage(ps: PageScales, page: number): Viewport[] {
  return ps.viewports?.[page] ?? [];
}

/** True when the document has at least one viewport on any page. */
export function hasAnyViewport(ps: PageScales): boolean {
  return !!ps.viewports && Object.values(ps.viewports).some((v) => v.length > 0);
}

/** The topmost viewport containing ``pt`` on ``page``, or null. */
export function viewportAt(
  ps: PageScales,
  page: number,
  pt: { x: number; y: number } | undefined | null,
): Viewport | null {
  if (!pt) return null;
  const list = viewportsForPage(ps, page);
  for (let i = list.length - 1; i >= 0; i--) {
    const r = list[i]!.rect;
    if (pt.x >= r.x && pt.x <= r.x + r.w && pt.y >= r.y && pt.y <= r.y + r.h) return list[i]!;
  }
  return null;
}

/**
 * The scale a measurement reads: the viewport holding its FIRST point (as in
 * Revu, where a measurement belongs to the viewport it starts in), else the
 * page scale. Every per-measurement conversion should go through this.
 */
export function scaleForMeasurement(
  ps: PageScales,
  page: number,
  points: readonly { x: number; y: number }[] | undefined,
): ScaleConfig {
  const vp = viewportAt(ps, page, points?.[0]);
  return vp ? vp.scale : scaleForPage(ps, page);
}

/** Normalise a rect so w/h are positive (drawn corner to corner either way). */
export function normalizeRect(
  a: { x: number; y: number },
  b: { x: number; y: number },
): Viewport['rect'] {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    w: Math.abs(b.x - a.x),
    h: Math.abs(b.y - a.y),
  };
}

/** Return a NEW model with ``vp`` added to (or replacing the same id on) ``page``. */
export function upsertViewport(ps: PageScales, page: number, vp: Viewport): PageScales {
  const list = viewportsForPage(ps, page);
  const idx = list.findIndex((v) => v.id === vp.id);
  const next =
    idx >= 0
      ? list.map((v, i) => (i === idx ? vp : v))
      : [...list, vp].slice(-MAX_VIEWPORTS_PER_PAGE);
  return { ...ps, viewports: { ...(ps.viewports ?? {}), [page]: next } };
}

/** Return a NEW model without viewport ``id`` on ``page``. */
export function removeViewport(ps: PageScales, page: number, id: string): PageScales {
  const next = viewportsForPage(ps, page).filter((v) => v.id !== id);
  const viewports = { ...(ps.viewports ?? {}) };
  if (next.length) viewports[page] = next;
  else delete viewports[page];
  return { ...ps, viewports };
}

function sanitizeViewports(raw: unknown): Record<number, Viewport[]> | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const out: Record<number, Viewport[]> = {};
  for (const [k, list] of Object.entries(raw as Record<string, unknown>)) {
    const page = Number(k);
    if (!Number.isInteger(page) || page < 1 || !Array.isArray(list)) continue;
    const clean: Viewport[] = [];
    for (const item of list.slice(0, MAX_VIEWPORTS_PER_PAGE)) {
      if (!item || typeof item !== 'object') continue;
      const o = item as Record<string, unknown>;
      const r = o.rect as Record<string, unknown> | undefined;
      const nums = r ? [r.x, r.y, r.w, r.h] : [];
      if (
        typeof o.id !== 'string' ||
        !isFiniteScale(o.scale) ||
        !(o.scale.pixelsPerUnit > 0) ||
        nums.length !== 4 ||
        !nums.every((n) => typeof n === 'number' && Number.isFinite(n))
      ) {
        continue;
      }
      clean.push({
        id: o.id,
        name: typeof o.name === 'string' ? o.name : 'Viewport',
        rect: { x: r!.x as number, y: r!.y as number, w: Math.abs(r!.w as number), h: Math.abs(r!.h as number) },
        scale: { pixelsPerUnit: o.scale.pixelsPerUnit, unitLabel: o.scale.unitLabel, ...(o.scale.displayUnit ? { displayUnit: o.scale.displayUnit } : {}) },
        ...(typeof o.scaleLabel === 'string' ? { scaleLabel: o.scaleLabel } : {}),
      });
    }
    if (clean.length) out[page] = clean;
  }
  return Object.keys(out).length ? out : undefined;
}

/* ── localStorage (de)serialisation with graceful migration ──────────── */

function isFiniteScale(v: unknown): v is ScaleConfig {
  if (!v || typeof v !== 'object') return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.pixelsPerUnit === 'number' &&
    Number.isFinite(o.pixelsPerUnit) &&
    typeof o.unitLabel === 'string'
  );
}

/**
 * Hydrate a {@link PageScales} from whatever a persisted document carried.
 *
 * Graceful migration is the whole point here: an existing document was
 * saved with a single ``scale`` (one global ``ScaleConfig``). We treat that
 * legacy scale as the document DEFAULT so every page keeps reading the same
 * number it always did until the user re-calibrates an individual sheet -
 * existing data never breaks. A document saved with the new ``pageScales``
 * shape is read back as-is.
 *
 * @param pageScales The new-format payload, if present.
 * @param legacyScale The old single-scale payload, if present.
 */
export function hydratePageScales(
  pageScales: unknown,
  legacyScale: unknown,
): PageScales {
  // New format wins when valid.
  if (pageScales && typeof pageScales === 'object') {
    const o = pageScales as Record<string, unknown>;
    const def = isFiniteScale(o.defaultScale)
      ? o.defaultScale
      : isFiniteScale(legacyScale)
        ? legacyScale
        : defaultScaleConfig();
    const byPage: Record<number, ScaleConfig> = {};
    if (o.byPage && typeof o.byPage === 'object') {
      for (const [k, v] of Object.entries(o.byPage as Record<string, unknown>)) {
        const page = Number(k);
        if (Number.isInteger(page) && page >= 1 && isFiniteScale(v)) {
          byPage[page] = v;
        }
      }
    }
    const viewports = sanitizeViewports(o.viewports);
    return viewports ? { defaultScale: def, byPage, viewports } : { defaultScale: def, byPage };
  }

  // Legacy single-scale document: promote it to the default for all pages.
  if (isFiniteScale(legacyScale)) {
    return { defaultScale: legacyScale, byPage: {} };
  }

  return emptyPageScales();
}

/* ── Load reconciliation (issue #334) ─────────────────────────────────── */

/**
 * True when a page-scale model carries an EXPLICIT calibration rather than
 * sitting on the factory default: either a per-page override exists, or the
 * document default was moved off the factory ratio.
 *
 * Used to reconcile a local (offline-cache) model against the server
 * (authoritative) one so a stale local DEFAULT can never override a real server
 * calibration, and to decide whether a restored calibration is worth persisting
 * back to the document.
 */
export function pageScalesHaveCalibration(ps: PageScales): boolean {
  if (Object.keys(ps.byPage).length > 0) return true;
  if (hasAnyViewport(ps)) return true;
  return ps.defaultScale.pixelsPerUnit !== defaultScaleConfig().pixelsPerUnit;
}

/**
 * Reconcile a local (localStorage offline cache) page-scale model against the
 * server (document-level, authoritative) one (issue #334).
 *
 * The failure this fixes: a device whose localStorage still held the factory
 * default used to WIN over a real server calibration, silently wiping it on
 * reload. The rule is "prefer an explicit calibration; never let a local
 * default override an explicit server one". We MERGE rather than pick a side so
 * a calibration made on another device (server) and one made here (local) both
 * survive: per-page overrides are unioned with the local copy winning a
 * conflict (it is the user's latest work on this device), and the document
 * default prefers an explicit (non-factory) value, local first.
 *
 * Returns ``null`` only when neither side exists so the caller keeps its own
 * state.
 */
export function reconcilePageScales(
  local: PageScales | null,
  server: PageScales | null,
): PageScales | null {
  if (!local && !server) return null;
  if (!local) return server;
  if (!server) return local;
  // Union of per-page overrides; the local copy wins a page both calibrated
  // (it is the user's latest work on this device). Every entry on either side
  // is an explicit per-page calibration, so a merge never resurrects a default.
  const byPage: Record<number, ScaleConfig> = { ...server.byPage, ...local.byPage };
  // The document default prefers whichever side moved it off the factory ratio;
  // a local factory default never overrides an explicit server default.
  const localDefaultExplicit =
    local.defaultScale.pixelsPerUnit !== defaultScaleConfig().pixelsPerUnit;
  const defaultScale = localDefaultExplicit ? local.defaultScale : server.defaultScale;
  // Viewports merge page by page the same way: the local list wins a page
  // both sides have (OE-DELIVERY 2026-11-02-revu-viewports-sketch).
  const viewports = { ...(server.viewports ?? {}), ...(local.viewports ?? {}) };
  return Object.keys(viewports).length ? { defaultScale, byPage, viewports } : { defaultScale, byPage };
}
