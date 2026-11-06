# CFS Estimation — Cold-Formed Steel workbook in the ERP

This section (`Estimating → Estimation → CFS Estimation`) is a native web
port of the estimator's Cold-Formed Steel `.xlsm` workbook. Every
auto-calculated column is produced by the engine in `engine/` — a 1:1 port
of the workbook's `LET` formulas plus its two VBA macros:

| Workbook piece | Ported to |
|---|---|
| Rule Table (20 truss/member types + geometry flags) | `data/ruleTable.ts` (generated) |
| Reference Sheet (materials, weights, prices) | `data/materials.ts` (generated) |
| Tbl_fasteners (gauge → screw) | `data/fasteners.ts` (generated) |
| Door & Window Schedule rows | `data/scheduleDefaults.ts` (generated) |
| LET formulas (panels, TC/BC, verticals, diagonals, LNFT, weight, screws, walls, openings) | `engine/trussCalc.ts`, `engine/wallCalc.ts`, `engine/openingCalc.ts` |
| VBA `Worksheet_Change` attic recalc | `calcAttic()` in `engine/trussCalc.ts` |
| VBA `Worksheet_Change` type/material validation | `matchTrussType()` / `match*Material()` in `engine/matchers.ts` (invalid input → red hint, same as the macro's red highlight) |
| VBA `ShowCalcDetail` popup | `trussCalcDetail()` + `components/CalcDetailModal.tsx` |

Two deliberate fixes vs the workbook (documented, not accidental):

1. **Attic flag**: the S/T formulas read Rule Table col 14 (*Notes*) for the
   attic flag, which never equals `"Yes"` — they compute *standard*
   verticals for an Attic Truss and rely on the macro overwriting the cells.
   The engine keys off the real `Use_Attic_Opening` flag (col 8), i.e. it
   always does what the macro intended.
2. **Costs**: the workbook's cost columns are blank (formulas never written).
   The app prices them: truss rows use an editable **$/ft** (defaulted from
   the Reference Sheet where the estimator filled prices), wall rows use an
   editable **$/lb**, connector cost is editable per row.

## Verification

`engine/` is verified against the workbook's own cached values
(`tools/cfs-extract` fixtures + `/tmp/cfs-verify.cjs` pattern):

- Roof Trusses sample (Howe Truss 35 ft): panels/TC/BC/vert/diag/member
  length/LNFT/weight/screw spec/screw qty — all match.
- Floor Trusses 10 sample rows — all match (incl. the lowercase
  `"flat truss"` fuzzy-match case).
- Wall Studs sample row: stud/track/panel counts, LNFTs, weight — match.
- Door & Window Schedule D01 + Wall Openings rows — match.
- Attic loop: 4 cases compared against an independent Python port of the
  VBA — exact match.

## Future updates — how to bring workbook changes in

**Case A — data changed** (new materials, new prices, new truss type in the
Rule Table, new schedule rows, renamed types): **no code changes needed.**

```bash
python3 tools/cfs-extract/extract_cfs_data.py /path/to/updated-workbook.xlsm .
```

This regenerates the four `data/*.ts` files. The engine reads them, so new
types/materials/prices work immediately — including the fuzzy matcher and
the validation.

**Case B — a formula changed** (e.g. a new geometry group, a different
screw-count rule): edit the corresponding function in `engine/`:

- truss geometry → `engine/trussCalc.ts` (`calcTC`, `calcBC`,
  `calcVertDiag`, `screwQtyFor`, …)
- walls → `engine/wallCalc.ts`
- openings/schedule → `engine/openingCalc.ts`
- matching rules → `engine/matchers.ts`

Each function mirrors one workbook formula — the column letters are noted
in comments. After changing, re-run the verification (compare against the
workbook's cached values for a sample row) before shipping.

**Case C — a new sheet** (e.g. the estimator adds "Interior Walls"): add a
`<New>Tab.tsx` under `components/`, a calc module under `engine/` if it has
formulas, wire it into `components/CfsEstimation.tsx` tabs and
`cfsStorage.ts` state.

## Files

```
cfs/
  README.md                 this file
  cfsStorage.ts             localStorage persistence (oe.cfs.v1) + sample rows
  data/                     GENERATED — see tools/cfs-extract
    ruleTable.ts            20 truss/member types + geometry flags
    materials.ts            ~1.2k materials (weight lb/ft, prices)
    fasteners.ts            gauge → screw spec
    scheduleDefaults.ts     68 default D&W schedule rows
  engine/
    types.ts                row input / computed types
    matchers.ts             fuzzy type/material matching, mil→gauge
    trussCalc.ts            truss geometry + screws + calc detail
    wallCalc.ts             wall stud/track/bridging counts + weight
    openingCalc.ts          D&W schedule + wall opening framing
  components/
    CfsEstimation.tsx       tab shell
    EditableGrid.tsx        spreadsheet-like editable table
    TrussTab.tsx            Floor/Roof Trusses (shared)
    WallTab.tsx             Exterior Wall Studs
    OpeningTab.tsx          Wall Openings
    ScheduleTab.tsx         Door & Window Schedule
    QuotationTab.tsx        roll-up totals + project header
    CalcDetailModal.tsx     per-member audit trail dialog
```
