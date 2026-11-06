#!/usr/bin/env python3
"""
Cold-Formed Steel estimation — Excel → TypeScript data extractor.

Reads the estimator's .xlsm workbook and regenerates the data files used by
the CFS estimation engine in the ERP:

    frontend/src/features/estimation/cfs/data/ruleTable.ts
    frontend/src/features/estimation/cfs/data/materials.ts
    frontend/src/features/estimation/cfs/data/fasteners.ts
    frontend/src/features/estimation/cfs/data/scheduleDefaults.ts

Usage:
    python3 extract_cfs_data.py /path/to/workbook.xlsm [repo-root]

The script is idempotent: re-running it after the estimator updates the
workbook (new materials, new prices, new truss types, new schedule rows)
regenerates the files. The calc engine (engine/*.ts) does NOT need to change
unless the *formulas themselves* change — it reads these data files.

Requires: openpyxl  (pip install openpyxl)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")


HEADER = """// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * GENERATED FILE — do not edit by hand.
 *
 * Produced by tools/cfs-extract/extract_cfs_data.py from the estimator's
 * Cold-Formed Steel .xlsm workbook. To refresh after the workbook changes,
 * re-run the script (see frontend/src/features/estimation/cfs/README.md).
 */
"""


def ts_str(s: object) -> str:
    if s is None:
        return "null"
    return json.dumps(str(s), ensure_ascii=False)


def ts_num(v: object) -> str:
    if v is None or v == "":
        return "null"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "null"
    return repr(f)


def parse_price(v: object) -> str:
    """Prices may be stored as '$ 0.25' strings."""
    if v is None or v == "":
        return "null"
    if isinstance(v, (int, float)):
        return repr(float(v))
    m = re.search(r"[\d.]+", str(v))
    return repr(float(m.group())) if m else "null"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: extract_cfs_data.py /path/to/workbook.xlsm [repo-root]")
    xlsm = Path(sys.argv[1])
    repo = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[2]
    out_dir = repo / "frontend" / "src" / "features" / "estimation" / "cfs" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.load_workbook(xlsm, data_only=True)

    # ---------------------------------------------------------------- Rule Table
    rt = wb["Rule Table"]
    rules: list[str] = []
    for r in range(4, rt.max_row + 1):
        name = rt.cell(r, 1).value
        if not name or str(name).strip() == "":
            continue
        vals = [str(rt.cell(r, c).value or "").strip() for c in range(1, 15)]
        rules.append(
            "  {\n"
            f"    type: {ts_str(vals[0])},\n"
            f"    category: {ts_str(vals[1])},\n"
            f"    geometry: {ts_str(vals[2])},\n"
            f"    spanMode: {ts_str(vals[3])},\n"
            f"    symmetric: {ts_str(vals[4])},\n"
            f"    bottomChord: {ts_str(vals[5])},\n"
            f"    generatesPanels: {ts_str(vals[6])},\n"
            f"    useAtticOpening: {ts_str(vals[7])},\n"
            f"    hasVertical: {ts_str(vals[8])},\n"
            f"    hasDiagonal: {ts_str(vals[9])},\n"
            f"    useBcSlope: {ts_str(vals[10])},\n"
            f"    useFlatLength: {ts_str(vals[11])},\n"
            f"    useFascia: {ts_str(vals[12])},\n"
            f"    notes: {ts_str(vals[13])},\n"
            "  },"
        )
    (out_dir / "ruleTable.ts").write_text(
        HEADER
        + "/** Truss/member type → geometry flags (from the workbook's Rule Table). */\n"
        + "export interface TrussRule {\n"
        + "  type: string; category: string; geometry: string; spanMode: string;\n"
        + "  symmetric: string; bottomChord: string; generatesPanels: string;\n"
        + "  useAtticOpening: string; hasVertical: string; hasDiagonal: string;\n"
        + "  useBcSlope: string; useFlatLength: string; useFascia: string; notes: string;\n"
        + "}\n\n"
        + "export const TRUSS_RULES: TrussRule[] = [\n"
        + "\n".join(rules)
        + "\n];\n",
        encoding="utf-8",
    )
    print(f"ruleTable.ts: {len(rules)} rules")

    # ---------------------------------------------------------------- Reference Sheet
    ref = wb["Reference Sheet"]

    def table(rows: list[tuple[int, int]], cols: dict[str, int], price_cols: dict[str, int]) -> list[str]:
        out: list[str] = []
        r0, r1 = rows
        for r in range(r0, r1 + 1):
            name = ref.cell(r, cols["name"]).value
            if name is None or str(name).strip() == "":
                continue
            parts = [f"    name: {ts_str(str(name).strip())}"]
            if "gauge" in cols:
                parts.append(f"gauge: {ts_num(ref.cell(r, cols['gauge']).value)}")
            if "weight" in cols:
                parts.append(f"weightLbFt: {ts_num(ref.cell(r, cols['weight']).value)}")
            for key, c in price_cols.items():
                parts.append(f"{key}: {parse_price(ref.cell(r, c).value)}")
            out.append("  { " + ", ".join(parts) + " },")
        return out

    truss_rows = table((3, 500), {"name": 1, "gauge": 2, "weight": 3}, {"trussPrice": 4, "joistPrice": 5})
    stud_rows = table((3, 500), {"name": 9, "gauge": 10, "weight": 11}, {"precutPrice": 12, "panelizedPrice": 13})
    track_rows = table((3, 240), {"name": 17, "gauge": 18, "weight": 19}, {"price": 20})
    strap_rows = table((244, 400), {"name": 17, "gauge": 18, "weight": 19}, {"price": 20})
    # Tbl_Strap X2:AB14 — Description, Material, Gauge, Weight, Price
    strap_table: list[str] = []
    for r in range(3, 15):
        desc = ref.cell(r, 24).value
        if desc is None or str(desc).strip() == "":
            continue
        strap_table.append(
            "  { "
            f"description: {ts_str(str(desc).strip())}, "
            f"material: {ts_str(ref.cell(r, 25).value)}, "
            f"gauge: {ts_num(ref.cell(r, 26).value)}, "
            f"weightLbFt: {ts_num(ref.cell(r, 27).value)}, "
            f"price: {parse_price(ref.cell(r, 28).value)}"
            " },"
        )

    (out_dir / "materials.ts").write_text(
        HEADER
        + "export interface CfsMaterial {\n"
        + "  name: string; gauge: number | null; weightLbFt: number | null;\n"
        + "  trussPrice?: number | null; joistPrice?: number | null;\n"
        + "  precutPrice?: number | null; panelizedPrice?: number | null;\n"
        + "  price?: number | null;\n"
        + "}\n\n"
        + "/** Truss/joist/rafter materials — Reference Sheet cols A:E (price = $/ft where filled). */\n"
        + "export const TRUSS_MATERIALS: CfsMaterial[] = [\n" + "\n".join(truss_rows) + "\n];\n\n"
        + "/** Wall stud materials — Reference Sheet cols I:M. */\n"
        + "export const STUD_MATERIALS: CfsMaterial[] = [\n" + "\n".join(stud_rows) + "\n];\n\n"
        + "/** Track materials — Reference Sheet cols Q:T. */\n"
        + "export const TRACK_MATERIALS: CfsMaterial[] = [\n" + "\n".join(track_rows) + "\n];\n\n"
        + "/** Flat-strap / bridging materials — Reference Sheet cols Q:T (lower block). */\n"
        + "export const STRAP_MATERIALS: CfsMaterial[] = [\n" + "\n".join(strap_rows) + "\n];\n\n"
        + "export interface StrapEntry {\n"
        + "  description: string; material: string | null; gauge: number | null;\n"
        + "  weightLbFt: number | null; price: number | null;\n"
        + "}\n"
        + "/** Tbl_Strap — Reference Sheet cols X:AB. */\n"
        + "export const STRAP_TABLE: StrapEntry[] = [\n" + "\n".join(strap_table) + "\n];\n",
        encoding="utf-8",
    )
    print(f"materials.ts: {len(truss_rows)} truss, {len(stud_rows)} stud, {len(track_rows)} track, "
          f"{len(strap_rows)} strap, {len(strap_table)} strap-table rows")

    # ---------------------------------------------------------------- Fasteners
    fast: list[str] = []
    for r in range(3, 9):
        gauge = rt.cell(r, 21).value
        if gauge in (None, ""):
            continue
        fast.append(
            "  { "
            f"gauge: {ts_num(gauge)}, "
            f"minScrew: {ts_str(rt.cell(r, 22).value)}, "
            f"screwType: {ts_str(str(rt.cell(r, 23).value or '').strip())}, "
            f"length: {ts_str(rt.cell(r, 24).value if rt.cell(r, 24).value is not None else '')}"
            # NOTE: Length is intentionally NOT stripped — the workbook stores
            # ' 3/4"' with a leading space and the screw formula concatenates it raw.
            " },"
        )
    (out_dir / "fasteners.ts").write_text(
        HEADER
        + "export interface FastenerSpec {\n"
        + "  gauge: number; minScrew: string | null; screwType: string | null; length: string | null;\n"
        + "}\n\n"
        + "/** Steel gauge → screw spec (Rule Table, Tbl_fasteners). */\n"
        + "export const FASTENERS: FastenerSpec[] = [\n" + "\n".join(fast) + "\n];\n",
        encoding="utf-8",
    )
    print(f"fasteners.ts: {len(fast)} gauges")

    # ---------------------------------------------------------------- Door/Window schedule defaults
    dw = wb["Door Window Schedule"]
    sched: list[str] = []
    for r in range(8, dw.max_row + 1):
        sid = dw.cell(r, 1).value
        if sid is None or str(sid).strip() == "":
            continue
        sched.append(
            "  {\n"
            f"    id: {ts_str(str(sid).strip())},\n"
            f"    openingType: {ts_str(dw.cell(r, 2).value)},\n"
            f"    label: {ts_str(dw.cell(r, 3).value)},\n"
            f"    cls: {ts_str(dw.cell(r, 4).value)},\n"
            f"    headerMaterial: {ts_str(dw.cell(r, 5).value)},\n"
            f"    roWidthIn: {ts_num(dw.cell(r, 6).value)},\n"
            f"    roHeightIn: {ts_num(dw.cell(r, 7).value)},\n"
            f"    notes: {ts_str(dw.cell(r, 15).value)},\n"
            "  },"
        )
    (out_dir / "scheduleDefaults.ts").write_text(
        HEADER
        + "export interface ScheduleRowInput {\n"
        + "  id: string; openingType: string | null; label: string | null; cls: string | null;\n"
        + "  headerMaterial: string | null; roWidthIn: number | null; roHeightIn: number | null;\n"
        + "  notes: string | null;\n"
        + "}\n\n"
        + "/** Default Door & Window Schedule rows (from the workbook). */\n"
        + "export const SCHEDULE_DEFAULTS: ScheduleRowInput[] = [\n"
        + "\n".join(sched)
        + "\n];\n",
        encoding="utf-8",
    )
    print(f"scheduleDefaults.ts: {len(sched)} rows")
    print("done →", out_dir)


if __name__ == "__main__":
    main()
