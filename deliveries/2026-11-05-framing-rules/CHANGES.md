# 2026-11-05: House framing rules for Auto Takeoff (+ fast upload)

Apply after `2026-11-04-page-flip-snap`. Code is marked `OE-DELIVERY 2026-11-05-framing-rules` and `2026-11-04-fast-upload`.
Restore with `python deliveries/2026-11-05-framing-rules/restore.py` (use `--dry-run` first), then restart the backend.

## The rules (same for every project)

Auto Takeoff reads each sheet's title-block title to decide what it is, and takes off only what that sheet is for. "House framing rules" in the Auto Takeoff panel is on by default.

| Sheet | Taken off | Not taken off |
|---|---|---|
| Floor framing plan (2nd, 3rd, 4th) | Every joist and truss framed one by one at the schedule spacing (T / RT from the truss schedule, J / RJ from the joist schedule), steel beams, CFS beams (B-x), deck (D1 from the diaphragm schedule) | Walls, headers, holdowns |
| Roof framing plan | Roof trusses and joists, CFS beams, deck | Walls |
| Shear wall plan of floor N | Walls W1–W4 with the schedule row **N TO N+1** (1st floor plan = "1ST TO 2ND"): stud size, spacing and height. Also headers H1–H4 for that level, shear walls SW-x, strap-braced walls BR-x, holdowns (HD, counts) and steel braces (BRACE-X) | Trusses, joists, steel beams |
| Foundation plan | Columns (at each size label's leader) and base plates (BP-x, counted at the column) | Footings, slabs |
| Details, sections, notes | Read for schedules only | Everything |

- **Schedules:** read once per drawing set, cached, and warmed when the Auto Takeoff panel opens. These kinds are read: wall framing, shear wall, brace wall, header, CFMF truss, CFMF joist, CFMF beam, base plate and diaphragm.
- **Trusses and joists:**
  - The tag's leader is followed to where the distribution arrow crosses the span line.
  - The span line is the one closest to the schedule length.
  - Both arrows are followed to their arrowhead tips (stopping at walls), so members run wall to wall onto their bearing walls.
  - One member is placed per spacing across the bay: a 13 ft bay at 24" gets 7.
- **Shear and strap-braced walls:**
  - **Length:** the hatched panel at the tag, set to the dimension drawn with the tag when there is one (e.g. 7'-0").
  - **Stacked tags:** a tag like "BR-1 W1" also counts the W1 stud wall on the same line.
- **Walls never bridge a gap:** wall lines stop at corridors and openings and keep to one line weight.
- **Corridor beams:** a beam's end piece stops at the last column, found from small column squares on the line.
- **Markups:**
  - **Subject:** the member role (Load Bearing Wall, Strap Braced Wall, Holdown, Base Plate, Steel Brace, CFS Beam and so on).
  - **Profile:** the schedule framing.
  - **Wall height:** taken from the schedule (drives Wall Area).
  - **Level:** stored in a `Level` custom field (add a "Level" column to the Markups list to see it).
- **New member types:** Base plates, Steel braces, Strap braced walls, Holdowns and CFS beams. They are turned on automatically for saved Auto Takeoff choices.
- **Result line:** after a run, the panel shows the sheets recognised (e.g. "p.8 1st floor shear walls") and the schedules read.

## Checked on "Pages from 01) StudioRes PCB - Building Drawings.pdf" (23 sheets)

- **Sheet kinds:** all 9 plan sheets are recognised with the right level; the 14 detail and notes sheets are skipped. S502, the dumpster enclosure foundation, is not taken for the building foundation.
- **S200 (foundation):** 20 / 20 HSS6X6 columns sit on their symbols. Base plates count BP-1 ×14 and BP-2 ×6, matching the base plate schedule.
- **S201 (2nd floor framing):**
  - Every bay is framed.
  - T-1 measures 12.5–13.0 ft against 13'-0" on the schedule.
  - Corridor W12X26 beams measure 13'-0" between columns, where they ran about 145 ft before.
- **S204 (roof):**
  - 7 trusses per 13 ft bay.
  - RT-1 measures 28.3–28.8 ft against 29'-0"; RT-2 30.3–30.8 ft against 31'-0".
  - RJ-1 roof joists measure 6'-0".
- **S205 (1st floor shear walls):**
  - W1 has 600S200-68 @ 24", 12'-7 1/4" high (1ST TO 2ND).
  - SW-1: 14 at 7'-0" and 2 at 9'-0".
  - BR-1 measures 23.4–24 ft against the 24'-0" dimensions; BR-3 15.3–16 ft against 16'-0".
  - 108 holdowns, headers H1–H4.
- **S206 (2nd floor shear walls):** takes the 2ND TO 3RD rows.
- **Whole set:** 53 s including the 11 s schedule read on the first run; a single page takes a few seconds once the schedules are cached.

## Fast upload (from 2026-11-04, not delivered before)

An upload answers after a quick text-only read. Table extraction runs in the background, and "Extract tables" runs it on demand if it hasn't finished. Measured: 75 s → 3.75 s.

## Checks

- **Backend tests:** 23 pass: 6 new for the framing rules and 17 existing Auto Takeoff tests.
- **Typecheck:** no new errors; the same 112 older errors remain.
- **Frontend tests:** 661 pass; the 6 failures are older (wheelZoomStep ×2, ledger value sort ×4).
- **Not done:** the backend was not restarted in this session. Restart it after restoring and before running Auto Takeoff.
