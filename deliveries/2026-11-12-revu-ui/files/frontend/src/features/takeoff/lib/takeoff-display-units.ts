// OE-DELIVERY: 2026-10-09-area-pdf-label
// DDC-CWICR-OE: DataDrivenConstruction - OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Takeoff display-unit conversion.
 *
 * Takeoff measurements are stored metric-canonical (D-TKC-016: every
 * stored `unitLabel` is "m" and the value is metres / m2 / m3), regardless
 * of how the estimator calibrated the drawing. This module is the single
 * seam that converts those canonical metric quantities into the user's
 * preferred measurement system *at the display / export boundary only* -
 * storage is never touched.
 *
 * It is a thin wrapper over the shared `convertUnit` / `getDisplayUnit`
 * helpers (the same mechanism `QuantityDisplay` uses) so the rounding and
 * unit labels stay consistent across the whole app:
 *   - `metric`   : value + unit are returned unchanged (so a metric user
 *                  sees byte-identical output to before this seam existed).
 *   - `imperial` : m -> ft, m2/m² -> ft², m3/m³ -> ft³.
 *
 * The conversion is done here; the *formatting* (precision rules) is left
 * to each caller's existing formatter so that the metric path is provably
 * unchanged - we only feed a converted number + converted label through the
 * formatter that was already in place.
 */

import type { MeasurementSystem } from '@/stores/usePreferencesStore';
import { convertUnit, getDisplayUnit } from '@/shared/lib/unitConversion';
import type { Measurement } from './takeoff-types';
import { METRES_PER, SQM_PER, type AreaDispUnit, type CaptionKey, type DispUnit } from './takeoff-revu-props';
import { formatQuantity as formatPlainQuantity } from './measurement-format';
import { effectiveQuantity, effectiveUnit, isWallMeasurement, quantityFactor, wallGrossArea } from './takeoff-quantity';
import {
  type ScaleConfig,
  formatFeetInches,
  formatMeasurement,
  polygonPerimeterPixels,
  toRealDistance,
} from '@/modules/pdf-takeoff/data/scale-helpers';

export interface DisplayQuantity {
  /** Numeric value in the target system (unchanged when metric). */
  value: number;
  /** Display-friendly unit label in the target system. */
  unit: string;
}

/**
 * Convert a metric-canonical quantity into the target measurement system.
 *
 * For `metric` the value passes through untouched and the unit is only
 * normalised to its display form (e.g. "m2" -> "m²"). For `imperial` the
 * value is scaled and the unit relabelled (m -> ft, m² -> ft², m³ -> ft³).
 * Units with no imperial mapping (pcs, lsum, ...) pass through unchanged in
 * both systems, which is the correct behaviour for countable / lump items.
 */
export function convertQuantity(
  value: number,
  metricUnit: string,
  system: MeasurementSystem,
): DisplayQuantity {
  if (system !== 'imperial') {
    // Metric: never scale; keep the value bit-for-bit and only tidy the
    // unit label so "m2"/"m3" render as "m²"/"m³" like the rest of the UI.
    return { value, unit: getDisplayUnit(metricUnit) };
  }
  const result = convertUnit(value, metricUnit, 'imperial');
  return { value: result.value, unit: result.displayUnit };
}

/**
 * The display unit label a metric unit resolves to in the target system,
 * without needing a value. Used where only the unit column / suffix is
 * rendered (e.g. a calibration depth-input suffix or a ledger unit cell).
 */
export function displayUnitFor(
  metricUnit: string,
  system: MeasurementSystem,
): string {
  return convertQuantity(0, metricUnit, system).unit;
}

/**
 * Convert only the value of a metric quantity to the target system,
 * discarding the label. Handy for export sheets that store a raw numeric
 * cell + a separate unit string.
 */
export function convertValue(
  value: number,
  metricUnit: string,
  system: MeasurementSystem,
): number {
  return convertQuantity(value, metricUnit, system).value;
}

/**
 * Format a single converted quantity the way the on-canvas / readout labels
 * do (via `formatMeasurement`), in the target system. For `metric` this is
 * exactly `formatMeasurement(value, getDisplayUnit(metricUnit))`.
 */
export function formatQuantity(
  value: number,
  metricUnit: string,
  system: MeasurementSystem,
): string {
  const d = convertQuantity(value, metricUnit, system);
  // A LINEAR dimension in the imperial system is written the way it is written
  // on a drawing: 12'-6 3/4", not 41.01 ft. Only the linear case. Nobody
  // dimensions a slab as four hundred square feet and three quarters, so area
  // and volume keep decimal ft² / ft³ and fall through to the shared
  // formatter. `d.unit` is the seam that tells the two apart, because it is
  // already the result of the metric-to-imperial mapping.
  //
  // `value` rather than `d.value` is passed on purpose: formatFeetInches takes
  // metres and does its own conversion, in integer sixteenths. Handing it the
  // already-converted decimal feet would convert twice and reintroduce exactly
  // the float rounding the integer path exists to avoid.
  if (system === 'imperial' && d.unit === 'ft') {
    return formatFeetInches(value);
  }
  return formatMeasurement(d.value, d.unit);
}

/**
 * Format a metric-canonical quantity in the scale's calibration display
 * unit. When the estimator calibrated in feet, a line reads "12 ft";
 * in ft+in it reads 12'-0"; in mm it reads "120 mm" — whatever unit they
 * measured in, not the reader's system preference. Without a displayUnit
 * (preset scales, old documents) this falls back to `formatQuantity`
 * (previous behaviour).
 */
/** Dimension display unit chosen by the user for every label, the legend
 *  and the exports (OE-DELIVERY 2026-11-02-revu-units): 'auto' follows each
 *  page's calibration unit (previous behaviour). Set by the viewer. */
export type DisplayUnitPref = 'auto' | 'ftin' | 'ft' | 'in' | 'mm' | 'cm' | 'm';
let globalDisplayUnit: DisplayUnitPref = 'auto';
export function setGlobalDisplayUnit(u: DisplayUnitPref): void {
  globalDisplayUnit = u;
}
export function getGlobalDisplayUnit(): DisplayUnitPref {
  return globalDisplayUnit;
}

function formatWithDisplayUnit(
  metricValue: number,
  metricUnit: string,
  scale: ScaleConfig,
  system: MeasurementSystem,
  markupUnit?: DispUnit,
  markupAreaUnit?: AreaDispUnit,
): string {
  const isArea = metricUnit.includes('²') || metricUnit === 'm2';
  const isVol = metricUnit.includes('³') || metricUnit === 'm3';
  // Revu Properties toolbar (OE-DELIVERY 2026-11-02-revu-properties-bar): the
  // markup's own area / length unit wins over the global choice.
  if (isArea && markupAreaUnit) {
    return `${formatPlainQuantity(metricValue / SQM_PER[markupAreaUnit])} ${markupAreaUnit}`;
  }
  if (markupUnit) {
    if (markupUnit === 'ftin') {
      if (!isArea && !isVol) return formatFeetInches(metricValue);
      return formatQuantity(metricValue, metricUnit, 'imperial');
    }
    const per = METRES_PER[markupUnit];
    const exp = isArea ? 2 : isVol ? 3 : 1;
    const u = isArea ? `${markupUnit}²` : isVol ? `${markupUnit}³` : markupUnit;
    return formatMeasurement(metricValue / per ** exp, u);
  }
  const forced = globalDisplayUnit !== 'auto' ? globalDisplayUnit : null;
  if (forced === 'm') {
    return formatMeasurement(metricValue, isArea ? 'm²' : isVol ? 'm³' : 'm');
  }
  if (forced === 'cm') {
    const exp = isArea ? 2 : isVol ? 3 : 1;
    return formatMeasurement(metricValue * 100 ** exp, isArea ? 'cm²' : isVol ? 'cm³' : 'cm');
  }
  const du = forced ?? scale.displayUnit;
  if (!du || du === 'm') return formatQuantity(metricValue, metricUnit, system);
  if (du === 'ftin') {
    // Architectural feet+inches only reads for linear dimensions; area
    // and volume fall back to decimal ft² / ft³.
    if (!isArea && !isVol) return formatFeetInches(metricValue);
    return formatQuantity(metricValue, metricUnit, 'imperial');
  }
  const perMetre = du === 'mm' ? 1000 : du === 'ft' ? 1 / 0.3048 : 1 / 0.0254;
  const exp = isArea ? 2 : isVol ? 3 : 1;
  const unit = isArea ? `${du}²` : isVol ? `${du}³` : du;
  return formatMeasurement(metricValue * perMetre ** exp, unit);
}

/**
 * Recompute the on-canvas value label for a measurement in the target
 * measurement system.
 *
 * Takeoff stores quantities in metres (D-TKC-016) and this recomputes
 * the label from `value` + geometry through the same `formatMeasurement`
 * rules used at create time. Since K-12 the digits render in the READER's
 * app language, so the recomputed string equals a string the author saw
 * only when their locales agree - which is why quantity labels are no
 * longer persisted into `annotation` (K-13, see
 * `useMeasurementPersistence.annotationForWire`): display is always
 * recomputed, never read back from a stored render. For `imperial` the
 * label is rebuilt with converted numbers + ft / ft² / ft³ units. Counts
 * and annotation markups carry no convertible quantity, so their stored
 * label / annotation is returned untouched.
 *
 * The compound area / volume breakdowns mirror the create-time formats:
 *   area   -> "{area} u² (P: {perimeter} u)"
 *   volume -> "V = {vol} u³ (A: {base} u² x D: {depth} u)"
 * Perimeter is recomputed from the polygon points + `scale` (it is not a
 * stored field); base area + depth come from the stored measurement.
 */
/** Format an area value in a specific unit (e.g. "sf", "sq m") from the
 *  area tool popup's pick list. */
function formatAreaWithUnit(value: number, fromUnit: string, toLabel: string): string {
  const toM2: Record<string, number> = {
    'mm\u00B2': 1e-6, 'mm2': 1e-6, 'cm\u00B2': 1e-4, 'cm2': 1e-4, 'm\u00B2': 1, 'm2': 1,
    'km\u00B2': 1e6, 'km2': 1e6, 'in\u00B2': 0.00064516, 'in2': 0.00064516,
    'ft\u00B2': 0.092903, 'ft2': 0.092903, 'yd\u00B2': 0.836127, 'yd2': 0.836127,
    'mi\u00B2': 2589988, 'mi2': 2589988,
  };
  const fromM2: Record<string, [number, string]> = {
    'sq in': [0.00064516, 'sq in'], 'sf': [0.092903, 'sf'], 'sq yd': [0.836127, 'sq yd'],
    'sq mi': [2589988, 'sq mi'], 'sq mm': [1e-6, 'sq mm'], 'sq cm': [1e-4, 'sq cm'],
    'sq m': [1, 'sq m'], 'sq km': [1e6, 'sq km'], 'ac': [4046.86, 'ac'],
    'ha': [10000, 'ha'], 'tsubo (\u5733)': [3.30579, 'tsubo'],
  };
  const m2 = value * (toM2[fromUnit.trim()] ?? 1);
  const [factor, short] = fromM2[toLabel] ?? [0.092903, 'sf'];
  const v = m2 / factor;
  return `${formatPlainQuantity(v)} ${short}`;
}

export function measurementLabel(
  m: Measurement,
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  if (m.captions && m.captions.length > 0) return captionValueText(m, scale, system, areaUnitOverride);
  const fmt = (v: number, u: string) => formatWithDisplayUnit(v, u, scale, system, m.dispUnit, m.dispAreaUnit);
  switch (m.type) {
    case 'distance':
    case 'polyline': {
      // Stored unit is "m"; value is metres. Reads in the calibration
      // display unit when the estimator calibrated in one.
      const lengthStr = fmt(m.value, m.unit || 'm');
      if (!isWallMeasurement(m)) return lengthStr;
      // A wall reads as its sum, "12.5 m × 2.8 m = 35 m²", and when openings,
      // wastage or a multiplier move the reported figure, "→ 31.2 m²" after it,
      // so the drawing shows the same number the ledger and the bill carry.
      const areaUnit = effectiveUnit(m);
      const heightStr = fmt(m.wallHeight ?? 0, m.unit || 'm');
      const gross = wallGrossArea(m);
      const reported = Math.abs(effectiveQuantity(m));
      const head = `${lengthStr} × ${heightStr} = ${fmt(gross, areaUnit)}`;
      return Math.abs(reported - gross) > 1e-9
        ? `${head} → ${fmt(reported, areaUnit)}`
        : head;
    }

    case 'area': {
      // Use the slope-adjusted true area so the PDF label matches the ledger's
      // Area column (both reflect Depth/Slope from the area popup).
      const trueArea = (m.value || 0) * quantityFactor(m);
      const areaStr = areaUnitOverride && !m.dispAreaUnit
        ? formatAreaWithUnit(trueArea, m.unit || 'm²', areaUnitOverride)
        : fmt(trueArea, m.unit || 'm²');
      // Area only on the sheet (user rule, OE-DELIVERY 2026-11-12-revu-ui u25);
      // the perimeter is still there through the Caption option (P).
      return areaStr;
    }

    case 'volume': {
      const volStr = fmt(m.value, m.unit || 'm³');
      const baseArea = m.area ?? 0;
      const baseStr = fmt(baseArea, 'm²');
      const depthStr = fmt(m.depth ?? 0, 'm');
      return `V = ${volStr} (A: ${baseStr} × D: ${depthStr})`;
    }

    case 'count':
      // Counts render as the annotation plus a live tally of placed points,
      // mirroring the on-canvas and PDF / Excel export renderers. The tally
      // lives in m.points.length (kept in sync with m.value); the stored label
      // is the static group label and would show no tally (issue #300).
      return `${m.annotation} (${m.points.length})`;

    default:
      // Annotation markups (cloud / arrow / text / rectangle / highlight): no
      // convertible quantity - keep the stored label.
      return m.label;
  }
}

/**
 * Caption text built from the markup's caption pick list (Revu Properties
 * toolbar, OE-DELIVERY 2026-11-02-revu-properties-bar). 'label' is the name
 * line and is drawn by the viewer, so it is skipped here; every other pick
 * adds one figure in the markup's own units.
 */
export function captionValueText(
  m: Measurement,
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  const fmt = (v: number, u: string) => formatWithDisplayUnit(v, u, scale, system, m.dispUnit, m.dispAreaUnit);
  const fmtArea = (v: number) =>
    areaUnitOverride && !m.dispAreaUnit ? formatAreaWithUnit(v, 'm²', areaUnitOverride) : fmt(v, 'm²');
  const caps = (m.captions ?? []) as CaptionKey[];
  const out: string[] = [];
  const linear = m.type !== 'area' && m.type !== 'volume' && m.type !== 'count';
  const trueArea = m.type === 'area' ? (m.value || 0) * quantityFactor(m) : m.type === 'volume' ? m.area ?? 0 : 0;
  for (const c of caps) {
    switch (c) {
      case 'length':
        if (linear) out.push(fmt(m.value || 0, 'm'));
        break;
      case 'area':
        if (m.type === 'area' || m.type === 'volume') out.push(`A: ${fmtArea(trueArea)}`);
        break;
      case 'perimeter':
        if ((m.type === 'area' || m.type === 'volume') && m.points.length > 2) {
          out.push(`P: ${fmt(toRealDistance(polygonPerimeterPixels(m.points), scale), 'm')}`);
        }
        break;
      case 'wallArea':
        if (isWallMeasurement(m)) out.push(`WA: ${fmtArea(Math.abs(effectiveQuantity(m)))}`);
        break;
      case 'depth': {
        const d = m.type === 'volume' || m.type === 'area' ? m.depth : m.wallHeight;
        if (d && d > 0) out.push(`D: ${fmt(d, 'm')}`);
        break;
      }
      case 'volume': {
        const vol = m.type === 'volume' ? m.value : m.type === 'area' && m.depth ? trueArea * m.depth : 0;
        if (vol) out.push(`V: ${fmt(vol, 'm³')}`);
        break;
      }
      case 'count':
        if (m.type === 'count') out.push(String(m.points.length));
        break;
      default:
        break;
    }
  }
  return out.join('  ');
}

/** Format a metric quantity in a markup's own units (Revu Properties
 *  toolbar totals, OE-DELIVERY 2026-11-02-revu-properties-bar). */
export function formatInUnits(
  value: number,
  metricUnit: string,
  scale: ScaleConfig,
  system: MeasurementSystem,
  dispUnit?: DispUnit,
  dispAreaUnit?: AreaDispUnit,
): string {
  return formatWithDisplayUnit(value, metricUnit, scale, system, dispUnit, dispAreaUnit);
}

/** A markup quantity formatted exactly as its sheet caption shows it: the
 *  markup's own units, else the area-popup area unit, else the chosen display
 *  unit, else the page calibration (OE-DELIVERY 2026-11-02-revu-markups-units). */
export function formatMarkupQuantity(
  m: Pick<Measurement, 'dispUnit' | 'dispAreaUnit'>,
  metricValue: number,
  kind: 'length' | 'area' | 'volume',
  scale: ScaleConfig,
  system: MeasurementSystem,
  areaUnitOverride?: string,
): string {
  if (kind === 'area') {
    if (areaUnitOverride && !m.dispAreaUnit) return formatAreaWithUnit(metricValue, 'm²', areaUnitOverride);
    return formatWithDisplayUnit(metricValue, 'm²', scale, system, m.dispUnit, m.dispAreaUnit);
  }
  return formatWithDisplayUnit(metricValue, kind === 'length' ? 'm' : 'm³', scale, system, m.dispUnit, m.dispAreaUnit);
}

/** Split "3,757.2 mm" / "12.5 sq ft" / 12'-3 1/2" into number and unit. */
export function splitQuantityText(text: string): { num: string; unit: string } {
  const t = text.trim();
  if (/['"]/.test(t)) return { num: t, unit: 'ft-in' };
  const m = t.match(/^(-?[\d.,\s  ']*\d)\s+(.+)$/);
  return m ? { num: m[1]!.trim(), unit: m[2]!.trim() } : { num: t, unit: '' };
}
