# 2026-11-08: Stud walls (full width, studs, header areas), materials, wall filter, Revu colour picklist

Apply after `2026-11-07-text-box`. Restore with `python deliveries/2026-11-08-stud-walls/restore.py` (add `--dry-run` to preview), then **restart the backend** and reload the browser.

## Stud walls
For every wall Auto Takeoff finds (house-rules wall plans and plain runs):

- **Full width, see-through.** The wall's two drawn faces are read zoomed in.
  - Their distance apart is the wall width; S205: about 6", matching the 600S studs. If the faces can't be read, the stud depth from the profile is used (600S… = 6").
  - The markup moves onto the true centre line between the faces.
  - In the viewer the wall is a band at that width, filled at 28 % so the drawing shows through.
- **Studs.**
  - Spacing comes from the plan or schedule ("600S200-68 @ 24\" O.C."). A screw / nail spacing in the same note ("#8 @ 4'' O.C.") is ignored, and **24" o.c. is used when the plan gives none**.
  - Count = ⌈length ÷ spacing⌉ + 1: one at the start, one every spacing, one at the end. A stud is drawn across the band at each.
  - The count follows the markup if you drag its ends.
- **Header areas kept apart.** Where the wall's faces stop at an opening (2–20 ft, only hairline window / door lines across), the run is cut.
  - The opening becomes its own piece: "W3 HEADER", hatched band, no studs.
  - It takes its header size from the nearest header tag (e.g. H1 TRUSS HEADER, H3 (2) 600S200-97 (50) BOXED), and the opening width goes in its notes.
  - Runs of the same wall tag in one line are read together, so an opening where two runs meet, or right beside a cross wall, is found too.
- **Shear / strap-braced walls with bearing walls.**
  - A shear (SW-1) or strap-braced (BR-) panel drawn on a bearing wall keeps its own markup on top of the wall, and the wall stays whole.
  - The panel counts no field studs of its own; they are counted in the wall, and its notes say which wall. This avoids double counting.
  - The panel's chord studs stay in its spec.

StudioRes results (house rules):

| Sheet | Wall pieces | Header areas | Wall LF | Header LF | Studs |
|---|---|---|---|---|---|
| S205 | 175 | 41 | 2,391 | 251 | 991 |
| S206 | 199 | 52 | 2,816 | 298 | 1,174 |
| S207 | 200 | 51 | 2,847 | 299 | 1,153 |
| S208 | 201 | 51 | 2,846 | 298 | 1,206 |

Framing, roof and foundation sheets are unchanged.

## Detected markups table
- **Material from the plan.**
  - Each size group shows its material chip: stud / header / joist size, e.g. 600S200-68 (50), 2-600S200-68 (50), TRUSS HEADER.
  - Each row shows it after its quantity. The Markups list Material column has it too.
- **Linear feet and studs.**
  - Wall groups show total length plus **"· N studs"**.
  - Each row shows "length × height = wall area · N studs @ 24\" o.c. · material". Header areas are tagged "header area".
- **Walls filter chips:** "All walls · Load Bearing Wall · Shear Wall · Strap Braced Wall".
  - Picking one shows only those walls, in the list and on the sheet.
  - "Shear Wall" on S205 shows SW-1 ×16 only.
- **Colour per size group** from the Revu-style colour picklist.

## Revu colour picklist
- New `ColorPicklist` includes:
  - 48 standard colours (8 hues × 5 tints plus greys);
  - the colours used lately;
  - "No colour" where it applies;
  - "More colours…".
- Used in:
  - the Detected list (colour of a whole size group);
  - the Text Box bar (text, fill, border);
  - the top Properties bar (Colour, Fill).

## Fixes found on the way
- Pieces of one split wall share their tag and label, and the viewer took them for one markup. Each piece now carries its number, so all of them are added and re-runs still match them.

## Files
- **Backend:**
  - `auto_takeoff.py`: `stud_walls`, `stud_spacing_in`, `DEFAULT_STUD_SPACING_IN`.
  - `detail_scan.py`: `wall_geometry`, `split_wall_at_openings`, `stud_count`, `stud_depth_in`.
  - Tests in `tests/unit/test_takeoff_detail_scan.py`.
- **Frontend:**
  - `data/stud-wall.ts` (new, with tests): stud count and positions, band drawing.
  - `components/ColorPicklist.tsx` (new).
  - `AutoTakeoffList.tsx`: material, studs, role chips, colour.
  - `data/auto-takeoff.ts`: wall fields on items and tags; walls of another tag on the same line are not duplicates.
  - `TakeoffViewerModule.tsx`: band and stud drawing, role filter, rows, recolour.
  - `TextFormatBar.tsx`, `RevuPropertiesBar.tsx`: picklist.

## Checks
- **Backend:** 41 unit tests pass, including the wall width and opening test and the spacing test.
- **Frontend:** 577 pass. The 6 failures are the same old ones (ledger value sort, wheel zoom).
- **Narrow tsc:** no new errors.
- **Real viewer** (QA project; the Auto Takeoff answer was the new engine's S205 result, and saves were blocked so the project is unchanged):
  - "375 added", CFS Walls 216, with role chips, materials and stud totals.
  - "Shear Wall" shows 16.
  - The picklist shows 48 colours and recolours a group.
  - Bands with studs and hatched header areas are drawn.
  - Screenshots in `e2e/`.
