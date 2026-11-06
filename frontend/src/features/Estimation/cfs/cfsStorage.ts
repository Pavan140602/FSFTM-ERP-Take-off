// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * CFS estimation store — the estimator's workbook, persisted in the browser.
 *
 * Shape mirrors the workbook tabs: floor/roof truss rows, wall rows,
 * opening rows and the door/window schedule. Plain JSON in localStorage
 * (key oe.cfs.v2) so a future backend sync can adopt it as-is.
 */

import type { ScheduleRowInput } from './data/scheduleDefaults';
import type { OpeningRowInput, TrussRowInput, WallRowInput } from './engine/types';

export interface CfsState {
  version: 1;
  floorTrusses: TrussRowInput[];
  roofTrusses: TrussRowInput[];
  walls: WallRowInput[];
  openings: OpeningRowInput[];
  schedule: ScheduleRowInput[];
  quotation: { project: string; client: string; date: string; notes: string };
}

const STORAGE_KEY = 'oe.cfs.v2';

let seq = 0;
export function newId(prefix: string): string {
  seq += 1;
  return `${prefix}_${Date.now().toString(36)}_${seq}`;
}

function blankTruss(): TrussRowInput {
  return {
    id: newId('tr'), description: '', memberType: '', material: '', lengthFt: null, qty: 1,
    slope: null, fasciaFt: null, panelSpacingFt: null, bcSlope: null,
    atticWidthFt: null, atticHeightFt: null, flatLengthFt: null,
    stiffTC: null, stiffBC: null, stiffWeb: null,
    connectorType: '', connectorQty: null, pricePerFt: null, connectorCost: null,
  };
}

/** Fresh workbook: every tab starts empty. The estimator adds rows manually
 *  or via the PDF takeoff "Export to CFS Estimation" flow. */
function defaultState(): CfsState {
  return {
    version: 1,
    floorTrusses: [],
    roofTrusses: [],
    walls: [],
    openings: [],
    schedule: [],
    quotation: { project: '', client: '', date: new Date().toISOString().slice(0, 10), notes: '' },
  };
}

export function loadCfs(): CfsState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw) as Partial<CfsState>;
    const d = defaultState();
    return {
      version: 1,
      floorTrusses: Array.isArray(parsed.floorTrusses) ? parsed.floorTrusses : d.floorTrusses,
      roofTrusses: Array.isArray(parsed.roofTrusses) ? parsed.roofTrusses : d.roofTrusses,
      walls: Array.isArray(parsed.walls) ? parsed.walls : d.walls,
      openings: Array.isArray(parsed.openings) ? parsed.openings : d.openings,
      schedule: Array.isArray(parsed.schedule) ? parsed.schedule : d.schedule,
      quotation: { ...d.quotation, ...(parsed.quotation ?? {}) },
    };
  } catch {
    return defaultState();
  }
}

export function saveCfs(state: CfsState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

export function blankTrussRow(): TrussRowInput {
  return blankTruss();
}

export function blankWallRow(): WallRowInput {
  return {
    id: newId('wl'), description: '', supplyType: '', studMaterial: '', trackMaterial: '',
    bridgingMaterial: '', wallLengthFt: null, wallHeightFt: null,
    studSpacingIn: 16, bridgingRows: null, bracedBays: null,
    pricePerLb: null, connectorCost: null,
  };
}

export function blankOpeningRow(): OpeningRowInput {
  return {
    id: newId('op'), level: '', wallType: '', loadBearing: 'Load Bearing',
    studSpacingIn: 16, wallHeightFt: null, scheduleRef: '',
    materialCost: null, connectorCost: null,
  };
}

export function blankScheduleRow(): ScheduleRowInput {
  return {
    id: '', openingType: 'Door', label: '', cls: '', headerMaterial: '',
    roWidthIn: null, roHeightIn: null, notes: '',
  };
}

/** CFS tab targeted by a ledger multi-select export. */
export type CfsImportTarget = 'roofTrusses' | 'floorTrusses' | 'walls';

/**
 * Replace rows imported from the PDF takeoff ledger in a CFS tab.
 * Used by the ledger's "Export to CFS Estimation" flow: the estimator picks
 * measurements in takeoff, chooses a target (Roof/Floor Trusses,
 * Load/Non-Load Bearing Walls), and the mapped rows land here.
 *
 * Replace semantics (not append): rows previously imported from takeoff
 * (carrying `takeoffImport`) are removed from the target tab first, then the
 * new rows are added. Rows the estimator added or completed manually are
 * left untouched, so re-exporting never creates duplicates.
 */
export function replaceCfsRows(
  target: CfsImportTarget,
  rows: TrussRowInput[] | WallRowInput[],
): void {
  const state = loadCfs();
  if (target === 'roofTrusses') {
    state.roofTrusses = [
      ...state.roofTrusses.filter((r) => !r.takeoffImport),
      ...(rows as TrussRowInput[]).map((r) => ({ ...r, takeoffImport: true })),
    ];
  } else if (target === 'floorTrusses') {
    state.floorTrusses = [
      ...state.floorTrusses.filter((r) => !r.takeoffImport),
      ...(rows as TrussRowInput[]).map((r) => ({ ...r, takeoffImport: true })),
    ];
  } else {
    state.walls = [
      ...state.walls.filter((r) => !r.takeoffImport),
      ...(rows as WallRowInput[]).map((r) => ({ ...r, takeoffImport: true })),
    ];
  }
  saveCfs(state);
}
