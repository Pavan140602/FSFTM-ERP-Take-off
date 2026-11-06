// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * GENERATED FILE — do not edit by hand.
 *
 * Produced by tools/cfs-extract/extract_cfs_data.py from the estimator's
 * Cold-Formed Steel .xlsm workbook. To refresh after the workbook changes,
 * re-run the script (see frontend/src/features/estimation/cfs/README.md).
 */
export interface FastenerSpec {
  gauge: number; minScrew: string | null; screwType: string | null; length: string | null;
}

/** Steel gauge → screw spec (Rule Table, Tbl_fasteners). */
export const FASTENERS: FastenerSpec[] = [
  { gauge: 20.0, minScrew: "#8", screwType: "SDS or TEK", length: " 3/4\"" },
  { gauge: 18.0, minScrew: "#10", screwType: "SDS or TEK", length: " 3/4\"" },
  { gauge: 16.0, minScrew: "#10", screwType: "SDS or TEK", length: " 3/4\"" },
  { gauge: 14.0, minScrew: "#12", screwType: "SDS or TEK", length: " 3/4\"" },
  { gauge: 12.0, minScrew: "#12", screwType: "SDS or TEK", length: " 3/4\"" },
  { gauge: 10.0, minScrew: "#12", screwType: "SDS or TEK", length: " 3/4\"" },
];
