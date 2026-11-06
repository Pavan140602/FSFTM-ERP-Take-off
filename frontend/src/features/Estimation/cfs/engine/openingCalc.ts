// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Door & Window Schedule + Wall Openings engine.
 *
 * Schedule (auto columns H..N of the Door Window Schedule sheet):
 *  RO W (ft)   = ROUND(F/12,3)
 *  King/Jamb   = 2
 *  Hdr Len     = ROUND(F/12+0.25,2)
 *  Hdr Depth   = 4/6/8/10/12/16 in by RO width thresholds 36/48/72/96/144
 *  Sill Y/N    = Door ? "N" : "Y";  Sill L = Y ? ROUND(F/12,2) : blank
 *
 * Wall Openings (cols H..T pull from the schedule by Sched. ID):
 *  King LNFT   = M*F,  Jamb LNFT = O*K
 *  Cripple Qty = Door ? FLOOR(J/(E/12)) : x2
 *  Cripple LNFT, Header LNFT (=J*4 load-bearing else J*2),
 *  Sill LNFT (Door → "—")
 * Screw/connector/cost columns are blank in the workbook — editable here.
 */

import type { ScheduleRowInput } from '../data/scheduleDefaults';
import { norm } from './matchers';
import type { Cell, OpeningRowComputed, OpeningRowInput, ScheduleRowComputed } from './types';

function num(v: number | null | undefined): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function headerDepthIn(roWidthIn: number): number {
  if (roWidthIn <= 36) return 4;
  if (roWidthIn <= 48) return 6;
  if (roWidthIn <= 72) return 8;
  if (roWidthIn <= 96) return 10;
  if (roWidthIn <= 144) return 12;
  return 16;
}

/** Opening framing depth used inside the Wall Openings sheet (no 144 branch). */
function openingHeaderDepthIn(roWidthIn: number): number {
  if (roWidthIn <= 36) return 4;
  if (roWidthIn <= 48) return 6;
  if (roWidthIn <= 72) return 8;
  if (roWidthIn <= 96) return 10;
  return 12;
}

export function calcScheduleRow(r: ScheduleRowInput): ScheduleRowComputed {
  const wIn = num(r.roWidthIn);
  const isDoor = (r.openingType ?? '').trim().toLowerCase() === 'door';
  if (wIn == null || wIn <= 0) {
    return {
      roWidthFt: null, kingStuds: null, jambStuds: null, headerLenFt: null,
      headerDepthIn: null, sillYN: isDoor ? 'N' : 'Y', sillLenFt: null,
    };
  }
  const sillYN = isDoor ? 'N' : 'Y';
  return {
    roWidthFt: Math.round((wIn / 12) * 1000) / 1000,
    kingStuds: 2,
    jambStuds: 2,
    headerLenFt: Math.round((wIn / 12 + 0.25) * 100) / 100,
    headerDepthIn: headerDepthIn(wIn),
    sillYN,
    sillLenFt: sillYN === 'Y' ? Math.round((wIn / 12) * 100) / 100 : null,
  };
}

export function calcOpeningRow(
  r: OpeningRowInput,
  schedule: ScheduleRowInput[],
): OpeningRowComputed {
  const errors: string[] = [];
  let scheduleError: string | null = null;

  const ref = norm(r.scheduleRef);
  const sched = schedule.find((s) => norm(s.id) === ref) ?? null;
  if (!ref) {
    return {
      description: null, openingType: null, roWidthFt: null, roHeightFt: null,
      headerMaterial: null, kingStuds: null, kingStudLnft: null, jambStuds: null,
      jambStudLnft: null, crippleQty: null, crippleLnft: null, headerLnft: null,
      sillLnft: null, totalCost: null, errors, scheduleError,
    };
  }
  if (!sched) {
    scheduleError = `ID '${r.scheduleRef}' not found in the Door & Window Schedule`;
  }
  const sc = sched ? calcScheduleRow(sched) : null;

  const description = sched?.label ?? null;
  const openingType = sched?.openingType ?? null;
  const roWidthFt: Cell = typeof sc?.roWidthFt === 'number' ? sc.roWidthFt : null;
  const roHeightFt: Cell = (() => {
    const hIn = num(sched?.roHeightIn);
    return hIn != null && hIn > 0 ? Math.round((hIn / 12) * 1000) / 1000 : null;
  })();
  const headerMaterial = sched?.headerMaterial ?? null;
  const kingStuds: Cell = typeof sc?.kingStuds === 'number' ? sc.kingStuds : null;
  const jambStuds: Cell = typeof sc?.jambStuds === 'number' ? sc.jambStuds : null;

  const F = num(r.wallHeightFt);
  const E = num(r.studSpacingIn);
  const isDoor = (openingType ?? '').toLowerCase() === 'door';
  const loadBearing = r.loadBearing.trim().toLowerCase() === 'load bearing';

  if (F == null || F <= 0) errors.push('Wall height is required');
  if (E == null || E <= 0) errors.push('Stud spacing is required');

  const kingStudLnft: Cell = typeof kingStuds === 'number' && F != null ? kingStuds * F : null;
  const jambStudLnft: Cell = typeof jambStuds === 'number' && typeof roHeightFt === 'number' ? jambStuds * roHeightFt : null;

  let crippleQty: Cell = null;
  let crippleLnft: Cell = null;
  if (typeof roWidthFt === 'number' && E != null && E > 0 && typeof jambStuds === 'number' && typeof roHeightFt === 'number' && F != null) {
    const base = Math.floor(roWidthFt / (E / 12));
    crippleQty = isDoor ? base : base * 2;
    const hdrD = openingHeaderDepthIn(roWidthFt * 12);
    crippleLnft = isDoor
      ? (jambStuds + 1) * (F - roHeightFt - hdrD / 12)
      : (jambStuds / 2 + 1) * (F - roHeightFt - hdrD / 12) + (jambStuds / 2 + 1) * roHeightFt;
  }

  const headerLnft: Cell = typeof roWidthFt === 'number' ? roWidthFt * (loadBearing ? 4 : 2) : null;
  const sillLnft: Cell | string = isDoor ? '—' : typeof roWidthFt === 'number' ? roWidthFt * (loadBearing ? 4 : 2) : null;

  const materialCost = num(r.materialCost) ?? 0;
  const connectorCost = num(r.connectorCost) ?? 0;
  const totalCost: Cell = materialCost + connectorCost;

  return {
    description, openingType, roWidthFt, roHeightFt, headerMaterial,
    kingStuds, kingStudLnft, jambStuds, jambStudLnft,
    crippleQty, crippleLnft, headerLnft, sillLnft,
    totalCost, errors: [...new Set(errors)], scheduleError,
  };
}
