# 2026-11-07: Column shapes, select same profile, columns added by hand

Apply after `2026-11-06-zoom-scan`. Restore with `python deliveries/2026-11-07-column-shapes/restore.py` (add `--dry-run` to preview), then **restart the backend** and reload the browser.

## Part 2: Ctrl / Shift multi-select in the lists

The **Detected markups** list (Auto Takeoff tab) and the **Markups list** (ledger) now select the way the PDF does:
- **Click** a row: selects that one markup and zooms to it (as before).
- **Ctrl+click** (Cmd+click on Mac): adds that markup to the selection, or removes it. Repeat for markup 1, 3, 7 …
- **Shift+click**: selects every markup from the last row clicked to this one, in the order shown (markup 1 to markup 10 in one go).

On the PDF, Ctrl+click and Shift+click do the same, and right-click → "Select same profile" picks every column of that size.

Files:
- `frontend/src/modules/pdf-takeoff/AutoTakeoffList.tsx`
- `frontend/src/features/takeoff/components/MeasurementLedger.tsx`
- tests `AutoTakeoffList.multiselect.test.tsx` and `MeasurementLedger.multiselect.test.tsx` (4 tests, pass)

Checks:
- New and existing tests: 34 of 34 pass.
- The takeoff feature suite has 6 failures (ledger value sort, wheel zoom). They fail the same way with the original MeasurementLedger.tsx, so they are not from this change.
- Narrow tsc: no new errors.

## What changed

1. **Select many columns at once**
   - **Ctrl+click** (Cmd+click on Mac) adds or removes a markup from the selection, like Shift+click, without Shift+drag's copy.
   - **Right-click a markup → "Select same profile"** (this sheet) or **"Select same profile, all sheets"** selects every markup with that profile. For columns that means every column of that size, whether Auto Takeoff found it or you placed it. The same two items are under **Edit** in the menu bar.
   - The Detected list keeps its per-size "select all" buttons.

2. **Columns you add yourself are counted with the rest**
   - Place a count markup and give it a column profile (Material such as `HSS6X6X1/2`, `W18X158`, `PIPE6STD`) or the Subject "Column". It is then treated as a column.
   - It is drawn with the same column symbol as found columns, with its profile beside it.
   - It shows in the Detected list under Columns as "<profile> · added by you". "Select same profile" picks it up with the found ones.
   - With **Highlight all** on, every column taken off, found or added, gets a soft green disc, so what is covered shows at a glance and gaps stand out.

3. **Column symbols drawn by section shape**

   | Profile | Symbol |
   |---|---|
   | W / HP / S / M (wide flange) | an I, web along the symbol's long side, **turned the way it is drawn on the plan** |
   | Square HSS (HSS8X8X1/2) | a square tube |
   | Rectangular HSS (HSS8X4X1/4) | a rectangle, turned like the plan |
   | Round HSS (HSS6.625X.280) / pipe | a circle |
   | Unknown size | the old ring with a cross |

   - The backend now sends each found column's symbol size and turn from the sheet: `symbol: [long side, short side, angle]` (detail_scan.symbol_at). The viewer stores it on the markup as `auto.sy`. On Home2 S-1.00, the W18 columns read about 14.6 × 8.4 units, an I about 18" deep at 1/8".
   - Columns placed by hand use the section's own proportions.
   - Columns found before this delivery get their turn on the next Auto Takeoff run.

## Files
- `frontend/src/modules/pdf-takeoff/data/column-shape.ts` (new): profile → shape, hand-placed column detection, symbol drawing. Tests are in `column-shape.test.ts`.
- `frontend/.../TakeoffViewerModule.tsx`:
  - column symbols by shape for found and hand-placed columns;
  - coverage highlight;
  - Ctrl/Cmd+click;
  - "Select same profile" in Edit and the right-click menu;
  - hand-placed columns in the Detected list.
- `frontend/.../data/auto-takeoff.ts`: `AutoItem.symbol`, `AutoTag.sy`.
- `backend/app/modules/takeoff/detail_scan.py`: `symbol_at`.
- `backend/app/modules/takeoff/auto_takeoff.py`: `symbol` on column items.
- `backend/tests/unit/test_takeoff_detail_scan.py`: symbol size and turn test.

## Checks
- **Backend:** 39 tests pass. StudioRes takeoff is identical with the zoomed check on and off.
- **Frontend:**
  - Tests: column-shape 7 and auto-takeoff 23, all pass.
  - Narrow tsc: no new errors.
- **Symbols:** rendered in headless Chrome (`e2e/shot.png`).
- **Not tried in the ERP:** the backend must be restarted first.
