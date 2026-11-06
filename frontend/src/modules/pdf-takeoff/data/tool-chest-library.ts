// OE-DELIVERY: 2026-10-29-standards-library-v1
/**
 * Tool Chest material library — hierarchical folders with editable materials.
 *
 * Main folders:
 *   - CFS Trusses, CFS Joist, CFS Load Bearing Walls, CFS Non-load Bearing Walls (SSMA)
 *   - Decking (Vulcraft)
 *   - W, WT, HSS, L (AISC)
 *
 * Data: designations, descriptions, specs and weights are generated from the
 * Standards Library seed tables (AISC Shapes Database v16.0, SSMA Technical
 * Guide) - the same tables behind GET /api/v1/standards-library/. Regenerate
 * from the seed package instead of hand-editing weights here.
 *
 * Each material has: name, designation, and specs. Users can edit/add/remove
 * materials via the Tool Chest UI; custom materials are stored in localStorage.
 */

export interface ChestMaterial {
  id: string;
  /** Display name, e.g. "362S162-43" */
  designation: string;
  /** Human description, e.g. '3-5/8" stud, 1-5/8" flange, 43 mil' */
  description: string;
  /** Extra specs shown in the picker */
  specs?: string;
  /** Published weight from the Standards Library tables (lb/ft), when known */
  weightLbFt?: number;
}

export interface ChestFolder {
  id: string;
  /** Main folder name, e.g. "CFS Trusses" */
  name: string;
  /** Material source standard */
  standard: 'SSMA' | 'AISC' | 'Vulcraft' | 'Custom';
  /** Default measurement tool for materials in this folder */
  defaultTool: 'distance' | 'polyline' | 'area';
  /** Default color for markups from this folder */
  color: string;
  materials: ChestMaterial[];
}

/** SSMA cold-formed steel studs (designation: depth + style + flange + mils). */
const CFS_STUDS: ChestMaterial[] = [
  { id: 'cfs-362s125-33', designation: '362S125-33', description: '3-5/8" stud, 1-1/4" flange, 33 mil (20 ga)', specs: 'W = 0.73 lb/ft, A = 0.215 in², Ix = 0.421 in⁴', weightLbFt: 0.73 },
  { id: 'cfs-362s162-43', designation: '362S162-43', description: '3-5/8" stud, 1-5/8" flange, 43 mil (18 ga)', specs: 'W = 1.16 lb/ft, A = 0.34 in², Ix = 0.71 in⁴', weightLbFt: 1.16 },
  { id: 'cfs-362s200-54', designation: '362S200-54', description: '3-5/8" stud, 2" flange, 54 mil (16 ga)', specs: 'W = 1.63 lb/ft, A = 0.479 in², Ix = 1.03 in⁴', weightLbFt: 1.63 },
  { id: 'cfs-362s250-68', designation: '362S250-68', description: '3-5/8" stud, 2-1/2" flange, 68 mil (14 ga)', specs: 'W = 2.27 lb/ft, A = 0.666 in², Ix = 1.49 in⁴', weightLbFt: 2.27 },
  { id: 'cfs-400s162-43', designation: '400S162-43', description: '4" stud, 1-5/8" flange, 43 mil (18 ga)', specs: 'W = 1.21 lb/ft, A = 0.357 in², Ix = 0.892 in⁴', weightLbFt: 1.21 },
  { id: 'cfs-400s200-54', designation: '400S200-54', description: '4" stud, 2" flange, 54 mil (16 ga)', specs: 'W = 1.7 lb/ft, A = 0.5 in², Ix = 1.292 in⁴', weightLbFt: 1.7 },
  { id: 'cfs-600s125-33', designation: '600S125-33', description: '6" stud, 1-1/4" flange, 33 mil (20 ga)', specs: 'W = 1.01 lb/ft, A = 0.297 in², Ix = 1.409 in⁴', weightLbFt: 1.01 },
  { id: 'cfs-600s162-43', designation: '600S162-43', description: '6" stud, 1-5/8" flange, 43 mil (18 ga)', specs: 'W = 1.52 lb/ft, A = 0.447 in², Ix = 2.316 in⁴', weightLbFt: 1.52 },
  { id: 'cfs-600s200-54', designation: '600S200-54', description: '6" stud, 2" flange, 54 mil (16 ga)', specs: 'W = 2.09 lb/ft, A = 0.613 in², Ix = 3.319 in⁴', weightLbFt: 2.09 },
  { id: 'cfs-600s250-68', designation: '600S250-68', description: '6" stud, 2-1/2" flange, 68 mil (14 ga)', specs: 'W = 2.84 lb/ft, A = 0.836 in², Ix = 4.727 in⁴', weightLbFt: 2.84 },
  { id: 'cfs-600s250-97', designation: '600S250-97', description: '6" stud, 2-1/2" flange, 97 mil (12 ga)', specs: 'W = 3.98 lb/ft, A = 1.169 in², Ix = 6.496 in⁴', weightLbFt: 3.98 },
  { id: 'cfs-800s200-54', designation: '800S200-54', description: '8" stud, 2" flange, 54 mil (16 ga)', specs: 'W = 2.47 lb/ft, A = 0.726 in², Ix = 6.573 in⁴', weightLbFt: 2.47 },
  { id: 'cfs-800s250-68', designation: '800S250-68', description: '8" stud, 2-1/2" flange, 68 mil (14 ga)', specs: 'W = 3.33 lb/ft, A = 0.978 in², Ix = 9.261 in⁴', weightLbFt: 3.33 },
  { id: 'cfs-800s250-97', designation: '800S250-97', description: '8" stud, 2-1/2" flange, 97 mil (12 ga)', specs: 'W = 4.67 lb/ft, A = 1.372 in², Ix = 12.789 in⁴', weightLbFt: 4.67 },
  { id: 'cfs-1000s250-68', designation: '1000S250-68', description: '10" stud, 2-1/2" flange, 68 mil (14 ga)', specs: 'W = 3.81 lb/ft, A = 1.121 in², Ix = 15.751 in⁴', weightLbFt: 3.81 },
  { id: 'cfs-1000s250-97', designation: '1000S250-97', description: '10" stud, 2-1/2" flange, 97 mil (12 ga)', specs: 'W = 5.36 lb/ft, A = 1.576 in², Ix = 21.827 in⁴', weightLbFt: 5.36 },
  { id: 'cfs-1200s250-97', designation: '1200S250-97', description: '12" joist, 2-1/2" flange, 97 mil', specs: 'W = 6.05 lb/ft, A = 1.779 in², Ix = 34.016 in⁴', weightLbFt: 6.05 },
];

/** SSMA track (T) — matches stud depths. */
const CFS_TRACK: ChestMaterial[] = [
  { id: 'cfs-362t125-33', designation: '362T125-33', description: '3-5/8" track, 1-1/4" leg, 33 mil', specs: 'W = 0.72 lb/ft, A = 0.212 in², Ix = 0.438 in⁴', weightLbFt: 0.72 },
  { id: 'cfs-362t125-43', designation: '362T125-43', description: '3-5/8" track, 1-1/4" leg, 43 mil', specs: 'W = 0.94 lb/ft, A = 0.276 in², Ix = 0.571 in⁴', weightLbFt: 0.94 },
  { id: 'cfs-400t125-43', designation: '400T125-43', description: '4" track, 1-1/4" leg, 43 mil', specs: 'W = 1 lb/ft, A = 0.293 in², Ix = 0.716 in⁴', weightLbFt: 1 },
  { id: 'cfs-600t125-33', designation: '600T125-33', description: '6" track, 1-1/4" leg, 33 mil', specs: 'W = 1 lb/ft, A = 0.294 in², Ix = 1.428 in⁴', weightLbFt: 1 },
  { id: 'cfs-600t125-54', designation: '600T125-54', description: '6" track, 1-1/4" leg, 54 mil', specs: 'W = 1.63 lb/ft, A = 0.48 in², Ix = 2.344 in⁴', weightLbFt: 1.63 },
  { id: 'cfs-800t125-54', designation: '800T125-54', description: '8" track, 1-1/4" leg, 54 mil', specs: 'W = 2.02 lb/ft, A = 0.594 in², Ix = 4.745 in⁴', weightLbFt: 2.02 },
  { id: 'cfs-1000t125-68', designation: '1000T125-68', description: '10" track, 1-1/4" leg, 68 mil', specs: 'W = 3.03 lb/ft, A = 0.89 in², Ix = 10.522 in⁴', weightLbFt: 3.03 },
];

/** SSMA joists — deeper sections for floor/roof framing. */
const CFS_JOISTS: ChestMaterial[] = [
  { id: 'cfs-800s200-33', designation: '800S200-33', description: '8" joist, 2" flange, 33 mil', specs: 'W = 1.52 lb/ft, A = 0.448 in², Ix = 4.096 in⁴', weightLbFt: 1.52 },
  { id: 'cfs-800s200-43', designation: '800S200-43', description: '8" joist, 2" flange, 43 mil', specs: 'W = 1.98 lb/ft, A = 0.582 in², Ix = 5.302 in⁴', weightLbFt: 1.98 },
  { id: 'cfs-1000s162-43', designation: '1000S162-43', description: '10" joist, 1-5/8" flange, 43 mil', specs: 'W = 2.13 lb/ft, A = 0.627 in², Ix = 8.025 in⁴', weightLbFt: 2.13 },
  { id: 'cfs-1000s200-54', designation: '1000S200-54', description: '10" joist, 2" flange, 54 mil', specs: 'W = 2.86 lb/ft, A = 0.839 in², Ix = 11.278 in⁴', weightLbFt: 2.86 },
  { id: 'cfs-1200s200-54', designation: '1200S200-54', description: '12" joist, 2" flange, 54 mil', specs: 'W = 3.24 lb/ft, A = 0.953 in², Ix = 17.662 in⁴', weightLbFt: 3.24 },
  { id: 'cfs-1200s250-68', designation: '1200S250-68', description: '12" joist, 2-1/2" flange, 68 mil', specs: 'W = 4.3 lb/ft, A = 1.263 in², Ix = 24.484 in⁴', weightLbFt: 4.3 },
  { id: 'cfs-1200s250-97', designation: '1200S250-97', description: '12" joist, 2-1/2" flange, 97 mil', specs: 'W = 6.05 lb/ft, A = 1.779 in², Ix = 34.016 in⁴', weightLbFt: 6.05 },
  { id: 'cfs-1400s250-97', designation: '1400S250-97', description: '14" joist, 2-1/2" flange, 97 mil', specs: 'W = 6.75 lb/ft, A = 1.983 in², Ix = 49.764 in⁴', weightLbFt: 6.75 },
];

/** AISC wide-flange beams. */
const AISC_W: ChestMaterial[] = [
  { id: 'aisc-w8x24', designation: 'W8x24', description: 'W8x24 wide-flange beam', specs: 'A = 7.08 in², d = 7.93", Ix = 82.7 in⁴, W = 24 lb/ft', weightLbFt: 24 },
  { id: 'aisc-w10x22', designation: 'W10x22', description: 'W10x22 wide-flange beam', specs: 'A = 6.49 in², d = 10.2", Ix = 118 in⁴, W = 22 lb/ft', weightLbFt: 22 },
  { id: 'aisc-w10x30', designation: 'W10x30', description: 'W10x30 wide-flange beam', specs: 'A = 8.84 in², d = 10.5", Ix = 170 in⁴, W = 30 lb/ft', weightLbFt: 30 },
  { id: 'aisc-w12x26', designation: 'W12x26', description: 'W12x26 wide-flange beam', specs: 'A = 7.65 in², d = 12.2", Ix = 204 in⁴, W = 26 lb/ft', weightLbFt: 26 },
  { id: 'aisc-w12x35', designation: 'W12x35', description: 'W12x35 wide-flange beam', specs: 'A = 10.3 in², d = 12.5", Ix = 285 in⁴, W = 35 lb/ft', weightLbFt: 35 },
  { id: 'aisc-w14x34', designation: 'W14x34', description: 'W14x34 wide-flange beam', specs: 'A = 10 in², d = 14", Ix = 340 in⁴, W = 34 lb/ft', weightLbFt: 34 },
  { id: 'aisc-w14x48', designation: 'W14x48', description: 'W14x48 wide-flange beam', specs: 'A = 14.1 in², d = 13.8", Ix = 484 in⁴, W = 48 lb/ft', weightLbFt: 48 },
  { id: 'aisc-w16x40', designation: 'W16x40', description: 'W16x40 wide-flange beam', specs: 'A = 11.8 in², d = 16", Ix = 518 in⁴, W = 40 lb/ft', weightLbFt: 40 },
  { id: 'aisc-w18x50', designation: 'W18x50', description: 'W18x50 wide-flange beam', specs: 'A = 14.7 in², d = 18", Ix = 800 in⁴, W = 50 lb/ft', weightLbFt: 50 },
  { id: 'aisc-w21x62', designation: 'W21x62', description: 'W21x62 wide-flange beam', specs: 'A = 18.3 in², d = 21", Ix = 1330 in⁴, W = 62 lb/ft', weightLbFt: 62 },
  { id: 'aisc-w24x76', designation: 'W24x76', description: 'W24x76 wide-flange beam', specs: 'A = 22.4 in², d = 23.9", Ix = 2100 in⁴, W = 76 lb/ft', weightLbFt: 76 },
];

/** AISC structural tees (cut from W shapes). */
const AISC_WT: ChestMaterial[] = [
  { id: 'aisc-wt4x9', designation: 'WT4x9', description: 'WT4x9 structural tee', specs: 'Cut from W8x18, W = 9 lb/ft, A = 2.63 in²', weightLbFt: 9 },
  { id: 'aisc-wt5x11', designation: 'WT5x11', description: 'WT5x11 structural tee', specs: 'Cut from W10x22, W = 11 lb/ft, A = 3.24 in²', weightLbFt: 11 },
  { id: 'aisc-wt6x13', designation: 'WT6x13', description: 'WT6x13 structural tee', specs: 'Cut from W12x26, W = 13 lb/ft, A = 3.82 in²', weightLbFt: 13 },
  { id: 'aisc-wt7x19', designation: 'WT7x19', description: 'WT7x19 structural tee', specs: 'Cut from W14x38, W = 19 lb/ft, A = 5.58 in²', weightLbFt: 19 },
  { id: 'aisc-wt8x18', designation: 'WT8x18', description: 'WT8x18 structural tee', specs: 'Cut from W16x36, W = 18 lb/ft, A = 5.29 in²', weightLbFt: 18 },
  { id: 'aisc-wt9x25', designation: 'WT9x25', description: 'WT9x25 structural tee', specs: 'Cut from W18x50, W = 25 lb/ft, A = 7.34 in²', weightLbFt: 25 },
  { id: 'aisc-wt10x22', designation: 'WT10x22', description: 'WT10x22 structural tee', specs: 'Cut from W21x44, W = 22 lb/ft, A = 6.49 in²', weightLbFt: 22 },
  { id: 'aisc-wt12x31', designation: 'WT12x31', description: 'WT12x31 structural tee', specs: 'Cut from W24x62, W = 31 lb/ft, A = 9.11 in²', weightLbFt: 31 },
];

/** AISC hollow structural sections (tube steel). */
const AISC_HSS: ChestMaterial[] = [
  { id: 'aisc-hss4x4x38', designation: 'HSS4x4x3/8', description: 'HSS 4x4x3/8 tube', specs: 'A = 4.78 in², W = 17.27 lb/ft', weightLbFt: 17.27 },
  { id: 'aisc-hss6x6x12', designation: 'HSS6x6x1/2', description: 'HSS 6x6x1/2 tube', specs: 'A = 9.74 in², W = 35.24 lb/ft', weightLbFt: 35.24 },
  { id: 'aisc-hss8x8x58', designation: 'HSS8x8x5/8', description: 'HSS 8x8x5/8 tube', specs: 'A = 16.4 in², W = 59.32 lb/ft', weightLbFt: 59.32 },
  { id: 'aisc-hss10x10x34', designation: 'HSS10x10x3/4', description: 'HSS 10x10x3/4 tube', specs: 'A = 24.7 in², W = 89.5 lb/ft', weightLbFt: 89.5 },
  { id: 'aisc-hss12x8x12', designation: 'HSS12x8x1/2', description: 'HSS 12x8x1/2 rectangular tube', specs: 'A = 17.2 in², W = 62.46 lb/ft', weightLbFt: 62.46 },
  { id: 'aisc-hss10x6x38', designation: 'HSS10x6x3/8', description: 'HSS 10x6x3/8 rectangular tube', specs: 'A = 10.4 in², W = 37.69 lb/ft', weightLbFt: 37.69 },
  { id: 'aisc-hss8x4x38', designation: 'HSS8x4x3/8', description: 'HSS 8x4x3/8 rectangular tube', specs: 'A = 7.58 in², W = 27.48 lb/ft', weightLbFt: 27.48 },
];

/** AISC angles. */
const AISC_L: ChestMaterial[] = [
  { id: 'aisc-l3x3x38', designation: 'L3x3x3/8', description: 'L3x3x3/8 angle', specs: 'A = 2.11 in², W = 7.2 lb/ft', weightLbFt: 7.2 },
  { id: 'aisc-l4x4x12', designation: 'L4x4x1/2', description: 'L4x4x1/2 angle', specs: 'A = 3.75 in², W = 12.8 lb/ft', weightLbFt: 12.8 },
  { id: 'aisc-l4x3x38', designation: 'L4x3x3/8', description: 'L4x3x3/8 unequal angle', specs: 'A = 2.49 in², W = 8.5 lb/ft', weightLbFt: 8.5 },
  { id: 'aisc-l5x5x58', designation: 'L5x5x5/8', description: 'L5x5x5/8 angle', specs: 'A = 5.9 in², W = 20 lb/ft', weightLbFt: 20 },
  { id: 'aisc-l6x6x34', designation: 'L6x6x3/4', description: 'L6x6x3/4 angle', specs: 'A = 8.46 in², W = 28.7 lb/ft', weightLbFt: 28.7 },
  { id: 'aisc-l6x4x12', designation: 'L6x4x1/2', description: 'L6x4x1/2 unequal angle', specs: 'A = 4.75 in², W = 16.2 lb/ft', weightLbFt: 16.2 },
  { id: 'aisc-l8x8x1', designation: 'L8x8x1', description: 'L8x8x1 angle', specs: 'A = 15.1 in², W = 51 lb/ft', weightLbFt: 51 },
];

/** Vulcraft steel deck. */
const VULCRAFT_DECK: ChestMaterial[] = [
  { id: 'vul-15b-20', designation: '1.5B-20', description: '1.5" B roof deck, 20 ga', specs: 'Vulcraft 1.5B' },
  { id: 'vul-15b-18', designation: '1.5B-18', description: '1.5" B roof deck, 18 ga', specs: 'Vulcraft 1.5B' },
  { id: 'vul-15f-20', designation: '1.5F-20', description: '1.5" F floor deck, 20 ga', specs: 'Vulcraft 1.5F' },
  { id: 'vul-20-18', designation: '2.0-18', description: '2" composite floor deck, 18 ga', specs: 'Vulcraft 2.0' },
  { id: 'vul-30-16', designation: '3.0-16', description: '3" composite floor deck, 16 ga', specs: 'Vulcraft 3.0' },
  { id: 'vul-30-18', designation: '3.0-18', description: '3" composite floor deck, 18 ga', specs: 'Vulcraft 3.0' },
];

export const TOOL_CHEST_LIBRARY: ChestFolder[] = [
  {
    id: 'cfs-trusses',
    name: 'CFS Trusses',
    standard: 'SSMA',
    defaultTool: 'distance',
    color: '#2563EB',
    materials: [...CFS_JOISTS.slice(0, 4), ...CFS_STUDS.slice(8, 12)],
  },
  {
    id: 'cfs-joist',
    name: 'CFS Joist',
    standard: 'SSMA',
    defaultTool: 'distance',
    color: '#0891B2',
    materials: CFS_JOISTS,
  },
  {
    id: 'cfs-lb-walls',
    name: 'CFS Load Bearing Walls',
    standard: 'SSMA',
    defaultTool: 'distance',
    color: '#DC2626',
    materials: [...CFS_STUDS.filter((s) => s.designation.includes('-68') || s.designation.includes('-97')), ...CFS_TRACK],
  },
  {
    id: 'cfs-nlb-walls',
    name: 'CFS Non-load Bearing Walls',
    standard: 'SSMA',
    defaultTool: 'distance',
    color: '#EA580C',
    materials: [...CFS_STUDS.filter((s) => s.designation.includes('-33') || s.designation.includes('-43')), ...CFS_TRACK.slice(0, 3)],
  },
  {
    id: 'decking',
    name: 'Decking',
    standard: 'Vulcraft',
    defaultTool: 'area',
    color: '#7C3AED',
    materials: VULCRAFT_DECK,
  },
  {
    id: 'w-shapes',
    name: 'W Shapes',
    standard: 'AISC',
    defaultTool: 'distance',
    color: '#16A34A',
    materials: AISC_W,
  },
  {
    id: 'wt-shapes',
    name: 'WT Shapes',
    standard: 'AISC',
    defaultTool: 'distance',
    color: '#65A30D',
    materials: AISC_WT,
  },
  {
    id: 'hss-shapes',
    name: 'HSS Shapes',
    standard: 'AISC',
    defaultTool: 'distance',
    color: '#0D9488',
    materials: AISC_HSS,
  },
  {
    id: 'l-shapes',
    name: 'L Shapes',
    standard: 'AISC',
    defaultTool: 'distance',
    color: '#4F46E5',
    materials: AISC_L,
  },
];

/** localStorage key for user-customized tool chest (edits/additions). */
const CHEST_CUSTOM_KEY = 'takeoff.toolChest.library.v1';

export interface ChestCustomization {
  /** Material IDs the user deleted (hidden from the library). */
  deletedIds: string[];
  /** User-added materials, keyed by folder id. */
  added: Record<string, ChestMaterial[]>;
  /** User-edited materials (full replacement by id). */
  edited: Record<string, ChestMaterial>;
}

/** Load user customizations. */
export function loadChestCustomization(): ChestCustomization {
  try {
    const raw = localStorage.getItem(CHEST_CUSTOM_KEY);
    if (!raw) return { deletedIds: [], added: {}, edited: {} };
    const p = JSON.parse(raw);
    return {
      deletedIds: Array.isArray(p.deletedIds) ? p.deletedIds : [],
      added: p.added && typeof p.added === 'object' ? p.added : {},
      edited: p.edited && typeof p.edited === 'object' ? p.edited : {},
    };
  } catch {
    return { deletedIds: [], added: {}, edited: {} };
  }
}

/** Save user customizations. */
export function saveChestCustomization(c: ChestCustomization): void {
  try {
    localStorage.setItem(CHEST_CUSTOM_KEY, JSON.stringify(c));
  } catch {
    /* ignore */
  }
}

/** Get folders with user customizations applied. */
export function getCustomizedLibrary(): ChestFolder[] {
  const custom = loadChestCustomization();
  return TOOL_CHEST_LIBRARY.map((folder) => {
    const mats = folder.materials
      .filter((m) => !custom.deletedIds.includes(m.id))
      .map((m) => custom.edited[m.id] ?? m);
    const added = custom.added[folder.id] ?? [];
    return { ...folder, materials: [...mats, ...added] };
  });
}
