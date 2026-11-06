# 2026-11-10 legend-walls

Restore after 2026-11-09-colours-keys: `python deliveries/2026-11-10-legend-walls/restore.py`.
Then restart the backend (port 8000) and reload the page. `files/` holds the final files. `patch_scripts/` has only the first patch; later fixes were made directly in the files.

## Why
- Home2 Suites (2026-10-22) page 7: walls with no tag were not drawn, and some "walls" were drawn on grid lines and leaders.
- CFS Standards "Structural Approval Drawings REV-014": nothing came out at all.
  - It prints no scale.
  - Its walls have no tags: a colour legend says what each wall is.
- The user asked for common-sense rules that work on drawings in any style, not one fix per drawing.

## General rules added (backend)
1. **Scale from the dimensions** (`detail_scan.dimension_scale`, used in `build_page_model`).
   - Used when no scale is printed.
   - Every feet-inch dimension string is checked against the line it sits on. The ratio most of them agree on (within 3%) is the scale.
   - It is named when it matches a standard scale. Otherwise it reads "x" = 1'-0" (as printed)".
   - The dimensions that agree also mark out the plan area.
2. **Scale from a sheet of the same size** (`_borrow_scales`).
   - Used when a sheet has no scale and no dimensions.
   - The scale text says which sheet the scale came from.
3. **Walls from the legend** (`detail_scan.tick_runs`, `legend_wall_types`, `legend_walls`, `auto_takeoff.legend_wall_items`).
   - A legend entry is either text in a wall's own colour, or text naming a wall (a stud size or a kind of wall) with a sample pattern next to it.
   - Every row of the same pattern on the plan is taken off as that wall type:
     - full width, measured from the pattern;
     - header areas at gaps of 2–16 ft;
     - studs at the legend's spacing, else 24" o.c.;
     - profile = the stud size in the legend;
     - role from the text: shear / bearing / non-bearing / CMU.
   - Notes, titles and the legend's own elevation drawings are left out.
   - Faint marks along each face of a wall are part of that wall, not walls of their own.
4. **A wall must be drawn as a wall** (`stud_walls` + `detail_scan.drawn_cover`).
   - A tagged run is dropped when nothing of real line weight runs along it. This covers runs traced along a dashed grid line, a leader or a hairline.
   - Thresholds: under 30% drawn, or under 45% drawn with more than 20 ft of nothing (openings are shorter).
   - Where another wall runs along the same line, that stretch counts as drawn.
   - A whole tag chain with no faces at all and only a thin line under it is dropped too.
5. **Untagged double-line walls at any normal width** (`_fill_uncovered_walls`).
   - The sweep now also accepts 2½"–12" wall widths, up to the widest wall measured on the sheet, in the wall pen.
   - A bug that let one stretch swallow another stretch elsewhere on the same line was fixed.

## Results

| Sheet | Before | After |
|---|---|---|
| CFS REV-014 p3 | nothing (no scale) | scale ≈1.73"/ft read from the dimensions; 1,128 LF in 4 colour wall types + header areas |
| CFS REV-014 p4–p7 | nothing | 69–93 wall pieces each |
| Home2 p7 | false walls on the grid line at D/E and on HDU leaders | those removed |
| Home2 p7 untagged walls | — | now drawn: corridor walls, T-ends, the short SW-3 stub; 83 untagged pieces, 583 LF |
| StudioRes S205–S208 | — | unchanged: 233 / 270 / 270 / 272 walls; S205 2,695 LF, 1,045 studs |
| Home2 S-1.00 | — | still 78 columns |
| StudioRes framing sheets | — | unchanged |

- CFS REV-014 p24 (wall sections layout) now borrows the scale from p14. Its diamond wall-type tags (1A–5) are not read yet.
- Pictures: `e2e/cfs_p3_walls.png`, `e2e/home2_p7_walls.png`, `e2e/studiores_s205_walls.png`.

## Tests
- Backend:
  - detail-scan: 18/18 pass. New tests: dimension strings, scale from dimensions, legend-coloured wall, dashed grid line is not a wall.
  - auto-takeoff + framing-rules: 28/28 pass.
- Frontend: vitest pdf-takeoff 239/239 pass; narrow tsc 102 (baseline). The only frontend change is the `source` type, which now includes `zoom` and `legend`.
