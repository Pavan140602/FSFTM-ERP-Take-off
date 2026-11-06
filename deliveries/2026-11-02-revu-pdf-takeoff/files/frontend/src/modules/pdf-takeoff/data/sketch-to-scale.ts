// OE-DELIVERY: 2026-11-02-revu-viewports-sketch
/**
 * Bluebeam-style "Sketch to Scale" and viewport value reconciliation.
 *
 * Sketch to Scale: while a length / area tool has a point down, the estimator
 * types the next segment's true length (optionally with an angle) instead of
 * clicking, and the vertex lands exactly that far away at the page's (or
 * viewport's) scale. Input forms:
 *
 *   12.5            length in the reader's system (m, or decimal ft)
 *   12.5<90         length at an absolute angle, degrees CCW from east
 *   12.5@90         same, CAD style
 *   3500mm  250cm  12ft  6in  2.4m      explicit unit
 *   12'6"  12'-6"  12' 6 1/2"           feet + inches (+ fraction)
 *
 * With no angle the segment follows the cursor direction (or the Shift/ortho
 * lock the caller already applied to the cursor).
 *
 * Pure and React-free so it unit-tests without the viewer.
 */

import type { MeasurementSystem } from '@/stores/usePreferencesStore';
import type { ScaleConfig } from './scale-helpers';
import type { PageScales } from './page-scales';
import { scaleForMeasurement, hasAnyViewport, viewportsForPage } from './page-scales';

/** Tools that place vertices one click at a time, so a typed length can
 *  stand in for the next click. */
export const SKETCH_TOOLS: ReadonlySet<string> = new Set([
  'distance',
  'polyline',
  'area',
  'volume',
  'perimeter',
  'polygonCutout',
  'line',
  'polygon',
  'arrow',
  'cloud',
]);

const METRES_PER_FOOT = 0.3048;
const METRES_PER_INCH = 0.0254;

const UNIT_M: Record<string, number> = {
  m: 1,
  mm: 0.001,
  cm: 0.01,
  ft: METRES_PER_FOOT,
  "'": METRES_PER_FOOT,
  in: METRES_PER_INCH,
  '"': METRES_PER_INCH,
};

/** Parse "6", "6.5", "6 1/2", "1/2" into a number (inches part of ft-in). */
function parseMixedNumber(s: string): number | null {
  const t = s.trim();
  if (!t) return 0;
  const m = /^(\d+(?:\.\d+)?)?(?:\s*(\d+)\/(\d+))?$/.exec(t);
  if (!m || (!m[1] && !m[2])) return null;
  const whole = m[1] ? Number(m[1]) : 0;
  const frac = m[2] && m[3] && Number(m[3]) > 0 ? Number(m[2]) / Number(m[3]) : 0;
  return whole + frac;
}

/** Parse a typed length into canonical metres; null when unreadable or <= 0. */
export function parseSketchLength(text: string, system: MeasurementSystem): number | null {
  const t = text.trim().replace(',', '.').replace(/[″”]/g, '"').replace(/[′’]/g, "'");
  if (!t) return null;
  // Feet + inches: 12'6", 12'-6", 12' 6 1/2", 12'
  const fi = /^(\d+(?:\.\d+)?)\s*'\s*-?\s*([\d./\s]*)"?$/.exec(t);
  if (fi) {
    const inches = parseMixedNumber(fi[2] ?? '');
    if (inches == null) return null;
    const m = Number(fi[1]) * METRES_PER_FOOT + inches * METRES_PER_INCH;
    return m > 0 ? m : null;
  }
  // Number with optional unit suffix
  const nu = /^(\d+(?:\.\d+)?|\.\d+)\s*(mm|cm|m|ft|in|"|')?$/i.exec(t);
  if (!nu) return null;
  const n = Number(nu[1]);
  if (!Number.isFinite(n) || n <= 0) return null;
  const unit = nu[2]?.toLowerCase();
  if (unit) return n * UNIT_M[unit]!;
  return system === 'imperial' ? n * METRES_PER_FOOT : n;
}

export interface SketchInput {
  /** True length in metres. */
  meters: number;
  /** Absolute angle in degrees CCW from east, or null = follow the cursor. */
  angleDeg: number | null;
}

/** Parse the full Sketch-to-Scale entry ("length" or "length<angle"). */
export function parseSketchInput(text: string, system: MeasurementSystem): SketchInput | null {
  const parts = text.split(/[<@]/);
  if (parts.length > 2) return null;
  const meters = parseSketchLength(parts[0] ?? '', system);
  if (meters == null) return null;
  if (parts.length === 1) return { meters, angleDeg: null };
  const a = Number((parts[1] ?? '').trim().replace(',', '.').replace(/°$/, ''));
  if (!Number.isFinite(a)) return null;
  return { meters, angleDeg: a };
}

/**
 * The exact next vertex: ``meters`` away from ``from`` at ``scale``, along the
 * typed angle or, without one, toward ``cursor``. Page coordinates are y-down,
 * so a CCW-from-east angle maps to (cos, -sin). Null for an unusable scale.
 */
export function sketchPoint(
  from: { x: number; y: number },
  cursor: { x: number; y: number } | null,
  input: SketchInput,
  scale: ScaleConfig,
): { x: number; y: number } | null {
  if (!(scale.pixelsPerUnit > 0)) return null;
  const px = input.meters * scale.pixelsPerUnit;
  let ux: number;
  let uy: number;
  if (input.angleDeg != null) {
    const r = (input.angleDeg * Math.PI) / 180;
    ux = Math.cos(r);
    uy = -Math.sin(r);
  } else {
    const dx = cursor ? cursor.x - from.x : 0;
    const dy = cursor ? cursor.y - from.y : 0;
    const d = Math.hypot(dx, dy);
    if (d < 1e-9) {
      ux = 1;
      uy = 0;
    } else {
      ux = dx / d;
      uy = dy / d;
    }
  }
  return { x: from.x + ux * px, y: from.y + uy * px };
}

/* ── Viewport value reconciliation ────────────────────────────────────── */

/** Measurement types whose value depends on the drawing scale. */
export const SCALE_DEPENDENT_TYPES: ReadonlySet<string> = new Set([
  'distance',
  'polyline',
  'area',
  'volume',
  'perimeter',
  'diameter',
  'radiusCenter',
  'radius3Point',
  'polygonCutout',
  'ellipseCutout',
  'dynamicFill',
  'arc',
]);

interface ReconcilableMeasurement {
  type: string;
  page: number;
  points: { x: number; y: number }[];
  value: number;
}

/**
 * Re-derive the value of every scale-dependent measurement on a page that has
 * viewports, against the scale it actually sits in (viewport or page). The
 * many create paths in the viewer compute against the page scale; this pass
 * corrects them in one place. Pages without viewports are never touched, so a
 * document that does not use viewports behaves exactly as before.
 *
 * ``recompute`` is the viewer's {@link recomputeMeasurement}; injected to keep
 * this module free of the hit-test dependency graph. Returns the input array
 * itself when nothing changed, so a React state update can be skipped.
 */
export function reconcileViewportValues<M extends ReconcilableMeasurement>(
  ms: M[],
  ps: PageScales,
  recompute: (m: M, points: M['points'], scale: ScaleConfig) => Partial<M> & { value?: number },
): M[] {
  if (!hasAnyViewport(ps)) return ms;
  let changed = false;
  const out = ms.map((m) => {
    if (!SCALE_DEPENDENT_TYPES.has(m.type) || !m.points?.length) return m;
    if (viewportsForPage(ps, m.page).length === 0) return m;
    return reconcileOne(m, ps, recompute, () => {
      changed = true;
    });
  });
  return changed ? out : ms;
}

/**
 * Recompute measurements on ``page`` against the scale they sit in, without
 * the "page has viewports" guard. Used after a page's LAST viewport is
 * removed, so rows that were inside it fall back to the page scale.
 */
export function reconcilePageValues<M extends ReconcilableMeasurement>(
  ms: M[],
  ps: PageScales,
  page: number,
  recompute: (m: M, points: M['points'], scale: ScaleConfig) => Partial<M> & { value?: number },
): M[] {
  let changed = false;
  const out = ms.map((m) =>
    m.page === page && SCALE_DEPENDENT_TYPES.has(m.type) && m.points?.length
      ? reconcileOne(m, ps, recompute, () => {
          changed = true;
        })
      : m,
  );
  return changed ? out : ms;
}

function reconcileOne<M extends ReconcilableMeasurement>(
  m: M,
  ps: PageScales,
  recompute: (m: M, points: M['points'], scale: ScaleConfig) => Partial<M> & { value?: number },
  onChange: () => void,
): M {
  const target = scaleForMeasurement(ps, m.page, m.points);
  if (!(target.pixelsPerUnit > 0)) return m;
  const patch = recompute(m, m.points, target);
  if (typeof patch.value !== 'number' || !Number.isFinite(patch.value)) return m;
  const tol = 1e-9 * Math.max(1, Math.abs(m.value));
  if (Math.abs(patch.value - m.value) <= tol) return m;
  onChange();
  return { ...m, ...patch };
}
