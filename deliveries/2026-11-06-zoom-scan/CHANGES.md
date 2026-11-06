# 2026-11-06: Detailed (zoomed) scan for columns and beams

Apply after `2026-11-05-detail-scan`. Restore with `python deliveries/2026-11-06-zoom-scan/restore.py` (add `--dry-run` to preview), then **restart the backend**.

House framing rules are unchanged: the StudioRes set gives exactly the same takeoff on S200–S208.

## Part 3 (same day): every column label must have its column (Home2 S-1.00)

The user reported many missed columns on Home2 Suites sheet 3 (S-1.00 foundation plan).

**Why the ERP showed so many misses:** the backend on :8000 started at 11:09 and was still running an in-between version of this delivery. It needs a restart.

**Real misses in the engine** (all fixed):
- HSS10X10X5/8 columns drawn as thin bars inside walls, with the size written on a diagonal leader line whose end touches the symbol.
- 10 grid bubbles counted as columns.
- 9 diagonal leader lines of column labels read as short "beams".

**New checks (no AI; geometry and text rules only):**
- `detail_scan.label_columns`: every column-size label (square HSS, W on column sheets, pipe) must have its column.
  - It follows the line the text is written on first, then the label's leaders, to the small square or round symbol at the end.
  - If a found column is already there, the label names it, and that label is no longer read as a beam.
  - If no symbol is found, the label is listed under "Not taken off".
  - W sizes count as columns only where square-tube sizes outnumber W sizes on the sheet. On framing plans they are beams.
  - Off on foundation plans read by the house rules, where the leader method already gives every column.
- `detail_scan.leader_beams`: a first-pass "beam" on a thin, short line ending at a column, with no heavy beam-pen line alongside (checked along its length, for dashed beams), is a leader and is removed.
- Leaders are followed through the full-detail line pieces even without house rules (`_detail_leader_ends`).
- Columns found by the zoomed check are named by a column mark only when the mark is right beside them. Deck cut marks (C2, C17) no longer name columns.

**Results, Home2 S-1.00:** before, 84 "columns" (10 of them grid bubbles) and 12 "beams". Now 78 columns:
- 45 HSS6X6X1/2, 16 HSS8X8X1/2, 8 HSS8X8X5/8, 2 HSS10X10X5/8, 2 W18X158, 2 W18X192, 1 W18X143;
- 2 still unnamed;
- 1 HSS10X10X5/8 (drawn only as part of a wall) listed to check.

StudioRes S200 without house rules now finds 19 of 20 columns (was 0). With house rules it is unchanged at 20.

**Sheet titles:**
- `framing_rules.title_block_small_title` reads titles printed small under a status line ("New Construction"), as on Home2 and AC Retreat.
- It is NOT yet used to switch those sets to the house rules. Tested: Home2 roof joists would drop 286 → 0 and the AC Retreat overall foundation plan 47 → 0 columns, because those sets write members differently. Left for the user's decision.

**Checks:** 38 backend tests pass; frontend 23 of 23; StudioRes (house rules) identical with the zoomed check on and off.

## Part 2 (same day): split into parts, zoom in, check one by one

As the user asked, each sheet's drawing area (title block left out) is split into parts. The part count follows how busy the sheet is: 4, 6, 9, 12 or 16, or set "Zoom in by parts" in the Auto Takeoff panel. Parts overlap by about 2 ft. Each part is checked zoomed in, one by one, for:

- **Columns**: as below. First-pass columns are checked again: grid bubbles (a grid letter at the centre) and deck arrows are removed. On Home2 S-1.00 and S-6.02, 10 grid bubbles per sheet had been counted as columns.
- **Beams**: as below, processed part by part.
- **Joists / trusses**: a callout that framed nothing is read zoomed in, across the callout and at its leader's end. Member lines at the callout's spacing are read from the callout outwards until the spacing breaks. Tested on StudioRes S201/S202/S204 as if nothing had been found: 89–99% of its lines sat exactly on the first pass's joists. A safety net only; it adds nothing where the first pass framed the callout.
- **Deck**:
  - Deck tags keyed to a DECK LEGEND (AD / BD / CD) mark their bay, bounded by the beams taken off, curved and zoom-found ones included.
  - The legend's own lines are never taken off or listed.
  - Designation "AD - COMPOSITE DECK", with the legend text as the spec.
- **Still not taken off**: on every sheet (not only with house rules), any beam, joist or deck callout with no markup of its size within 4 ft is listed. Legend boxes and sheet titles are skipped.
- **Panel**:
  - "Zoom in by parts" choice.
  - "Zoomed check" summary line.
  - "Part by part" list per sheet; click a part to zoom to it.
- **API**: body `zoom_parts` (0 = auto). The response gives `zoom_scan.parts`, `grid` and `log` per page.

Final takeoff report: `report/zoomed-takeoff-check.html`, built by `e2e/make_report.py` + `e2e/build_html.py`. It covers six sheets with the parts grid, markups and quantities.

Checks:
- Backend: 37 tests pass (9 zoom scan, 28 existing).
- Frontend: auto-takeoff.test.ts 23 of 23 pass; narrow tsc shows no errors in the changed files.
- StudioRes (house rules): identical takeoff with the zoomed check on and off.

## What it does

After the normal pass, every sheet is read again at full detail and walked in tiles of about 3 in of paper, like an estimator zooming in area by area.

### Columns
Every small closed shape is checked, however it is drawn:
- one rectangle, four loose lines in any order, or a double outline;
- rotated along a curved wall;
- rounded corners;
- an unusual size that appears only once or twice.

A shape counts as a column when framing members run into it, or when it looks the same as a column already confirmed on the sheet.

It never counts:
- deck-span arrows or other filled symbol parts; first-pass "columns" on arrows are removed;
- section-marker heads (next to S6.11, S501 and so on);
- grid bubbles, tag boxes, or white text masks;
- piles, unless a confirmed column looks the same;
- crossed boxes (shaft openings);
- pieces of double-line walls;
- one-off rectangles made only by separate lines crossing.

On foundation plans with house rules on, only shapes that look like a column already found from its label are added.

### Beams
- **Labelled beams with no line:** the heavy line under or beside the size label is followed from column to column, through curves (curved beams come as polylines with their real arc length) and across small drafting breaks (about 1'-3").
- **Unlabelled beams:** heavy lines drawn with the same pen as the sheet's beams, running between columns, are added as **"BEAM (no size on plan)"** at lower confidence. Rename them with ✏️ in the Detected list. Not used when house rules are on.

### Panel
A **"Detailed scan"** line in the results shows:
- how many areas were checked;
- the columns added;
- the false columns removed;
- the beams added, and how many need a size.

API body field `detail_scan` (default `true`) turns the scan off.

## Results (engine run on the PDFs in Downloads)

| Sheet | Before | Now |
|---|---|---|
| AC Retreat S2.01b (2nd floor framing, part B) | 35 columns, 6 of them deck arrows; 40 beams; curved bay empty | 5 missed columns added (grid 17 and the rotated ones on the curved wall); 6 arrows removed; 54 beams. All curved and radial beams in the curved bay are taken off; 8 have no size on the plan |
| AC Retreat S4.01a (4th floor framing, part A) | 24 columns, 58 beams | 32 columns; 73 beams (the short W12X26 beams between rows A and B, the W24X76 (4) bay, the end bays) |
| AC Retreat S3.01a | 27 columns, 32 beams | 29 columns, 38 beams |
| AC Retreat S4.03a (decking plan) | 8 columns | 29 columns (the column rows at A0 and B) |
| Home2 Suites (pages 3, 4, 6, 16, 21) | | after tuning: no additions on S-1.00 (p.3) or S-6.02 (p.16); 2 bold squares in walls added on p.4 and on p.21 |
| StudioRes S200–S208 (house rules) | | identical |

Speed: about half a second more per sheet.

## Known limits
- Columns drawn only as part of a wall (no symbol of their own) are still not added.
- On a plain foundation sheet without house rules, a labelled column whose square is drawn as separate crossing lines can still be missed (Home2 S-1.00, HSS10 at F2). Use house rules there: the leader method finds it.
- Unlabelled beams are added only between columns, or from a column to a beam, and only in the beam pen.

## Files
- `backend/app/modules/takeoff/detail_scan.py` (new): sheet reading, column scan, beam trace.
- `backend/app/modules/takeoff/auto_takeoff.py`:
  - reads the drawings once;
  - `PageModel.detail`;
  - `_column_named` helper;
  - scan wired into `take_off_page`;
  - `detail_scan` passed through `run_models` and `run_auto_takeoff`.
- `backend/app/modules/takeoff/auto_takeoff_ai.py` and `router.py`: `detail_scan` option.
- `frontend/.../TakeoffViewerModule.tsx`: line items with more than 2 points become polyline markups.
- `frontend/.../data/auto-takeoff.ts`: re-run duplicate check covers every piece of a polyline.
- `frontend/.../AutoTakeoffPanel.tsx`: "Detailed scan" summary.
- `backend/tests/unit/test_takeoff_detail_scan.py`: 6 tests (rotated column, loose-piece outline, deck arrow, text mask, curved beam, line break).

## Checks run
- Backend: the 6 new tests pass, and the 28 existing Auto Takeoff and framing-rules tests pass.
- Frontend:
  - `auto-takeoff.test.ts`: 23 of 23 pass.
  - Narrow tsc: no errors in the changed files.
- Not browser-tested: the backend needs a restart first.
