// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * CFS estimation engine — shared types.
 *
 * Every calc is a pure function: inputs in, numbers out. An `errors` array
 * carries the same "missing input" conditions the workbook expresses as
 * #DIV/0! / #VALUE! — the UI renders those as "—" with an inline hint
 * instead of Excel's error codes.
 */

export interface CalcResult<T> {
  value: T;
  /** Missing/invalid inputs, in workbook terms (e.g. "Span is required"). */
  errors: string[];
}

export function ok<T>(value: T): CalcResult<T> {
  return { value, errors: [] };
}

export function err<T>(value: T, ...errors: string[]): CalcResult<T> {
  return { value, errors };
}

/** A computed table cell: number, text, or empty when inputs are missing. */
export type Cell = number | string | null;

export interface TrussRowInput {
  id: string;
  /** Free-text description shown in the Description column (editable, not used by calcs). */
  description?: string | null;
  memberType: string;
  material: string;
  lengthFt: number | null; // D — span / truss length
  qty: number | null; // E
  slope: number | null; // F — slope ratio :12
  fasciaFt: number | null; // G — fascia / toe / depth
  panelSpacingFt: number | null; // H
  bcSlope: number | null; // I — Roof sheet only
  atticWidthFt: number | null; // J — Roof sheet only
  atticHeightFt: number | null; // K — Roof sheet only
  flatLengthFt: number | null; // L — Roof sheet only
  stiffTC: number | null; // M
  stiffBC: number | null; // N
  stiffWeb: number | null; // O
  screwType?: string | null; // manual override column (VBA-free sheets)
  connectorType?: string | null;
  connectorQty?: number | null;
  pricePerFt?: number | null; // editable — defaults from Reference Sheet
  connectorCost?: number | null; // editable
  /** Set when the row was imported from the PDF takeoff ledger. Re-exports
   *  replace rows carrying this flag; manually added rows never have it. */
  takeoffImport?: boolean;
}

export interface TrussRowComputed {
  rule: string | null;
  ruleError: string | null;
  panels: Cell;
  tcLnft: Cell;
  bcLnft: Cell;
  vertLnft: Cell;
  diagLnft: Cell;
  memberLnft: Cell; // per truss
  totalLnft: Cell; // × qty
  weightLb: Cell;
  screwSpec: string | null;
  screwQty: Cell;
  materialCost: Cell;
  totalCost: Cell;
  errors: string[];
}

export interface WallRowInput {
  id: string;
  /** Free-text description shown in the Description column (editable, not used by calcs). */
  description?: string | null;
  supplyType: string;
  studMaterial: string;
  trackMaterial: string;
  bridgingMaterial: string;
  wallLengthFt: number | null;
  wallHeightFt: number | null;
  studSpacingIn: number | null;
  bridgingRows: number | null;
  bracedBays: number | null;
  pricePerLb?: number | null; // editable
  connectorCost?: number | null; // editable
  /** Set when the row was imported from the PDF takeoff ledger. Re-exports
   *  replace rows carrying this flag; manually added rows never have it. */
  takeoffImport?: boolean;
}

export interface WallRowComputed {
  studCount: Cell;
  trackCount: Cell;
  panelCount: Cell;
  studLnft: Cell;
  trackFt: Cell;
  bridgingLnft: Cell;
  weightLb: Cell;
  materialCost: Cell;
  totalCost: Cell;
  errors: string[];
}

export interface ScheduleRowComputed {
  roWidthFt: Cell;
  kingStuds: Cell;
  jambStuds: Cell;
  headerLenFt: Cell;
  headerDepthIn: Cell;
  sillYN: string | null;
  sillLenFt: Cell;
}

export interface OpeningRowInput {
  id: string;
  level: string;
  wallType: string;
  loadBearing: string; // "Load Bearing" | "Non-Load Bearing"
  studSpacingIn: number | null;
  wallHeightFt: number | null;
  scheduleRef: string;
  materialCost?: number | null; // editable
  connectorCost?: number | null; // editable
}

export interface OpeningRowComputed {
  description: string | null;
  openingType: string | null;
  roWidthFt: Cell;
  roHeightFt: Cell;
  headerMaterial: string | null;
  kingStuds: Cell;
  kingStudLnft: Cell;
  jambStuds: Cell;
  jambStudLnft: Cell;
  crippleQty: Cell;
  crippleLnft: Cell;
  headerLnft: Cell;
  sillLnft: Cell | string;
  totalCost: Cell;
  errors: string[];
  scheduleError: string | null;
}
