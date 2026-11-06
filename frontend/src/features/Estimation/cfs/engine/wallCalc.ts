// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Exterior Wall Studs engine — port of the Exterior Wall Studs sheet.
 *
 * Column letters below refer to that sheet:
 *  K Stud Count  = FLOOR(F/10)*(CEILING(10/(H/12))+3) + remainder panel
 *  L Track Count = CEILING(F/10)*2
 *  M Panels      = CEILING(F/10)
 *  N Stud LNFT   = K*G
 *  O Track (ft)  = F*2
 *  P Bridging    = F*4 (G<=10) else F*6
 *  Q Weight      = N*wStud + O*wTrack + P*wStrap  (Reference Sheet lookups)
 *  R..W (screws/connectors/costs) are blank in the workbook — the app
 *  prices them via editable rate inputs instead.
 */

import { matchStrapMaterial, matchStudMaterial, matchTrackMaterial } from './matchers';
import type { Cell, WallRowComputed, WallRowInput } from './types';

function num(v: number | null | undefined): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

export function calcWallRow(r: WallRowInput): WallRowComputed {
  const errors: string[] = [];
  const F = num(r.wallLengthFt);
  const G = num(r.wallHeightFt);
  const H = num(r.studSpacingIn);

  let studCount: Cell = null;
  let trackCount: Cell = null;
  let panelCount: Cell = null;
  let studLnft: Cell = null;
  let trackFt: Cell = null;
  let bridgingLnft: Cell = null;

  if (F == null || F <= 0) {
    errors.push('Wall length is required');
  } else {
    const spacingFt = H != null && H > 0 ? H / 12 : null;
    if (spacingFt == null) {
      errors.push('Stud spacing is required');
    } else {
      const fullPanels = Math.floor(F / 10);
      const rem = F % 10;
      studCount =
        fullPanels * (Math.ceil(10 / spacingFt) + 3) +
        (rem > 0 ? Math.ceil(rem / spacingFt) : 0);
      trackCount = Math.ceil(F / 10) * 2;
      panelCount = Math.ceil(F / 10);
      if (G != null && G > 0) {
        studLnft = (studCount as number) * G;
        bridgingLnft = G <= 10 ? F * 4 : F * 6;
      } else {
        errors.push('Wall height is required');
      }
      trackFt = F * 2;
    }
  }

  let weightLb: Cell = null;
  if (typeof studLnft === 'number' && typeof trackFt === 'number' && typeof bridgingLnft === 'number') {
    const sm = r.studMaterial?.trim() ? matchStudMaterial(r.studMaterial) : null;
    const tm = r.trackMaterial?.trim() ? matchTrackMaterial(r.trackMaterial) : null;
    const bm = r.bridgingMaterial?.trim() ? matchStrapMaterial(r.bridgingMaterial) : null;
    const wS = sm?.weightLbFt;
    const wT = tm?.weightLbFt;
    const wB = bm?.weightLbFt;
    if (wS == null) errors.push(`Stud material '${r.studMaterial || '—'}' not found in Reference Sheet`);
    if (wT == null) errors.push(`Track material '${r.trackMaterial || '—'}' not found in Reference Sheet`);
    if (wB == null) errors.push(`Bridging material '${r.bridgingMaterial || '—'}' not found in Reference Sheet`);
    if (wS != null && wT != null && wB != null) {
      weightLb = studLnft * wS + trackFt * wT + bridgingLnft * wB;
    }
  }

  const pricePerLb = num(r.pricePerLb) ?? 0;
  const materialCost: Cell = typeof weightLb === 'number' ? weightLb * pricePerLb : null;
  const connectorCost = num(r.connectorCost) ?? 0;
  const totalCost: Cell = typeof materialCost === 'number' ? materialCost + connectorCost : null;

  return {
    studCount, trackCount, panelCount, studLnft, trackFt, bridgingLnft,
    weightLb, materialCost, totalCost,
    errors: [...new Set(errors)],
  };
}
