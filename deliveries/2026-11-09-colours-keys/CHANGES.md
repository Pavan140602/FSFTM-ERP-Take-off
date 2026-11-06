# 2026-11-09 colours-keys

Restore after 2026-11-08-stud-walls: `python deliveries/2026-11-09-colours-keys/restore.py`,
then restart the backend (port 8000) and reload the frontend.

## Colours (picklist, one per parameter set)
- `data/auto-colours.ts` (new): every Auto Takeoff markup takes a Revu picklist colour.
  - Header areas and header tags get warm colours.
  - Walls get cool colours.
  - Other members get the rest of the palette.
- Any difference in role, material/profile, stud spacing, wall width, height, or header vs wall gives a different colour.
- The same parameters always get the same colour. The colours are kept per drawing (localStorage `takeoff.autoColours.v1.<doc>`).
- A colour the user picks from a group's picklist is kept on re-runs (`auto.uc`).

## Header areas filter
- The Walls chips now include **Header areas**. It shows only the header (opening) pieces in the list and on the sheet.
- **Select all** on the CFS Walls row then selects every one (browser check: 41 selected on S205).

## Cover the whole drawn wall (backend)
- `detail_scan.uncovered_walls`: finds double-line wall stretches in the wall-face pen, at a wall width learned from the tagged walls, that no tag reached. Each stretch is at least 2 ft.
- `wall_geometry` now also returns `face_widths`.
- `auto_takeoff._fill_uncovered_walls` adds each stretch:
  - as the tagged wall it continues (same line, within 4 ft), with the same material and spacing;
  - otherwise as `WALL` "(no tag on the plan)" with a 24" o.c. default and low confidence, so it can be checked.
- It runs only when 3 or more tagged walls with a measured width exist, so framing and foundation sheets are unchanged (Home2 S-1.00 still finds 78 columns).
- StudioRes S205: the sweep adds 18 pieces / 59 LF (stair walls, elevator core, wall ends). Picture: `e2e/s205u.png`, sweep pieces in green.

## Keys and moving
- Page Up / Page Down: previous / next page, always.
- Up / Down with nothing selected: next / previous page (unchanged).
- Arrow keys with markups selected: move them (Shift = 10x), as before.
- Mouse: dragging one of several selected markups moves all of them together, with one undo step each. It was type-checked only, not tested in the browser.

## Tests
- Backend:
  - detail-scan tests: 14/14 pass, including the new `test_uncovered_double_line_wall_is_found`;
  - auto-takeoff and framing-rules tests: 28/28 pass.
- Frontend:
  - pdf-takeoff vitest: 239/239 pass, including the new `auto-colours.test.ts`;
  - narrow tsc: 102 errors (baseline).
- Browser (`e2e/e2e_colkeys.cjs`, engine output mocked, saves blocked):
  - colours distinct per wall type, headers warm;
  - Header areas then Select all = 41;
  - PageDown 1→2, PageUp 2→1, Up 1→2, Down 2→1;
  - no page errors.
