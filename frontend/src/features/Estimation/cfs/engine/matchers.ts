// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Fuzzy matchers — the TypeScript port of the workbook's lookup behaviour.
 *
 * The workbook matches user input two ways:
 *  - Cell formulas:  SEARCH(normalised input, normalised rule name), first hit
 *    in table order (INDEX/MATCH).
 *  - VBA validation:  shortest rule name that *contains* the normalised input.
 *
 * Both normalise with UPPER + space removal. This module implements one
 * consistent rule: exact normalised hit wins; otherwise the shortest rule
 * name containing the input (the VBA behaviour, which is the friendlier of
 * the two — e.g. "flat truss" still matches "Flat Truss").
 */

import { TRUSS_RULES, type TrussRule } from '../data/ruleTable';
import {
  STRAP_MATERIALS,
  STUD_MATERIALS,
  TRACK_MATERIALS,
  TRUSS_MATERIALS,
  type CfsMaterial,
} from '../data/materials';

export function norm(s: string | null | undefined): string {
  return (s ?? '').toUpperCase().replace(/[\s.\-]/g, '');
}

/** Match a truss/member type against the Rule Table. */
export function matchTrussType(input: string | null | undefined): TrussRule | null {
  const n = norm(input);
  if (!n) return null;
  const exact = TRUSS_RULES.find((r) => norm(r.type) === n);
  if (exact) return exact;
  let best: TrussRule | null = null;
  for (const r of TRUSS_RULES) {
    if (norm(r.type).includes(n)) {
      if (!best || r.type.length < best.type.length) best = r;
    }
  }
  return best;
}

function matchMaterialIn(input: string | null | undefined, list: CfsMaterial[]): CfsMaterial | null {
  const n = norm(input);
  if (!n) return null;
  const exact = list.find((m) => norm(m.name) === n);
  if (exact) return exact;
  let best: CfsMaterial | null = null;
  for (const m of list) {
    if (norm(m.name).includes(n)) {
      if (!best || m.name.length < best.name.length) best = m;
    }
  }
  return best;
}

export function matchTrussMaterial(input: string | null | undefined): CfsMaterial | null {
  return matchMaterialIn(input, TRUSS_MATERIALS);
}

export function matchStudMaterial(input: string | null | undefined): CfsMaterial | null {
  return matchMaterialIn(input, STUD_MATERIALS);
}

export function matchTrackMaterial(input: string | null | undefined): CfsMaterial | null {
  return matchMaterialIn(input, TRACK_MATERIALS);
}

export function matchStrapMaterial(input: string | null | undefined): CfsMaterial | null {
  return matchMaterialIn(input, STRAP_MATERIALS);
}

/** "362S162-33" → 33 (mil thickness after the dash). */
export function milThickness(material: string | null | undefined): number | null {
  if (!material) return null;
  const dash = material.indexOf('-');
  if (dash < 0) return null;
  const v = Number(material.slice(dash + 1).replace(/[^0-9]/g, ''));
  return Number.isFinite(v) && v > 0 ? v : null;
}

/** Workbook IFS: mil → steel gauge. */
export function gaugeFromMil(mil: number | null): number | null {
  if (mil == null) return null;
  if (mil <= 33) return 20;
  if (mil === 43) return 18;
  if (mil === 54) return 16;
  if (mil === 68) return 14;
  if (mil >= 97) return 12;
  return null;
}
