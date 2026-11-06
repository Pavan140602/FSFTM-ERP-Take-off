# 2026-11-11 div5-rules

Restore after 2026-11-10-legend-walls: `python deliveries/2026-11-11-div5-rules/restore.py`.
Then restart the backend (port 8000) and reload the page. The changes were made directly in the files; `files/` holds the final copies.

## Why
- CFS REV-014 p24–26 (wall sections layouts): the walls carry wall-type codes in diamonds (1A, 2A, 5) and nothing came out.
- The user's rule: when the plan does not say whether a wall bears, read the floor framing above it, as an estimator does.
- The user asked for general rules that read Division 05 and CFS drawings the way an estimator, owner or professional takeoff person reads them, with no per-drawing teaching.

## Rules added (backend)

1. **Wall-type codes in symbols** (`auto_takeoff.symbol_wall_tags`)
   - A code such as 1A, 2B or 5 inside a diamond, hexagon or box, with a leader to a wall, is read as a wall tag when:
     - the sheet is about walls (a wall layout or wall-type title, or wall types captioned with the same codes); and
     - the codes repeat across the plan.
   - Numbers used once each are keynotes or detail marks and are ignored.
   - The spec is the caption, e.g. "1A (2 HOURS FIRE RATED WALL, UL# U425)", plus the sheet's stud note, e.g. "SINGLE STUD 600S162-54".
2. **Sheets drawn all in hairlines** (`detail_scan.hairline_sheet`)
   - Line weight cannot tell a wall from a leader on these sheets, so the wall's own face lines set the threshold.
   - This applies only on all-hairline sheets; other sets are unchanged.
3. **Common sense for walls with no tag** (`_sane_untagged`)
   - They must lie on the plan, within the extent of the tagged walls. The border, title block and wall-type details are left out.
   - A row of three or more equal short pairs is stairs or casework, not walls.
   - A short piece that touches no other wall is furniture.
4. **Each foot of wall once** (`_once_per_foot`, chain grouping)
   - Two tags traced on either face of one wall no longer count it twice. CFS p24 had about 180 LF double counted.
5. **Joists or trusses drawn as a field of lines** (`detail_scan.joist_fields`, `plan_joist_fields`, `auto_takeoff.field_joist_items`)
   - A field is 6 or more parallel lines at 12", 16", 19.2" or 24" o.c. (±4%).
   - It is named from, in order:
     1. the zone mark in the field, e.g. "JOIST 2", and the legend entry with that mark, e.g. "2x800S162-54 … JOIST 2 @16" O.C" (profile 2x800S162-54);
     2. the same pen as a named field;
     3. a callout across any field of that pen and spacing, e.g. "ROOF TRUSS @ 2'-0" OC";
     4. the legend sample drawn in that pen.
   - An unnamed field is taken off only on a sheet titled as framing.
   - Members are cut where they cross a heavier supporting line (truss, beam).
   - Tables (text running between the rows) are skipped, as are stair treads next to UP/DN text.
6. **Load bearing or not, from the framing above** (`bearing_walls.py`)
   - The framing sheets of the set are read, even when not taken off.
   - The plan is lined up with the wall sheet in feet, shifted until the joist ends land on walls. The floor above is preferred: "FOR 2ND FLOOR" framing goes over "FIRST FLOOR" walls.
   - Joists landing on a wall: Load Bearing. Joists running alongside: Non-Load Bearing.
   - The reason is written in the spec, e.g. "Load bearing: 15 joists of the floor above (sheet 12) land on it".
   - What the drawings say outright, house-rules sheets, shear and CMU walls, and legend roles are never changed.
7. **Miscellaneous steel: stairs** (`detail_scan.stair_flights`, `auto_takeoff.stair_items`)
   - Five or more treads 9–13" apart, 2'-6"–8' wide, with UP/DN/STAIR text, make one flight.
   - Each flight is an area markup with its treads, risers, width, going and an approximate stringer LF.
8. **Division 05 vocabulary** (`detect.py`, `classify`)
   - SJI joist girders (44G8N9.5K, BG, VG) are read as beams, role "Joist Girder".
   - KCS and SLH joists.
   - Round HSS (HSS6.625X0.280) and PIPE 4 STD.
   - A bare "1B" or "3A" is no longer read as a deck type.

## Frontend
- New member types:
  - "Joist girders (SJI G / BG / VG)";
  - "Walls with no tag / CMU (check type)": the roles Wall and CMU Wall were filtered out of results before;
  - "Stairs" under a new group, "Miscellaneous steel".
- These types are switched on once for saved settings (`prefs.div5Types`).

## Results (CFS REV-014)

| Sheet | Before | After |
|---|---|---|
| p24 first floor wall sections | nothing | 1A/1B/2A/3A/4A/5 walls with fire-rating spec; 1,060 LF load bearing, 837 LF non-load bearing (from p12 joists); 289 LF untagged; 1 stair |
| p25, p26 (upper floors) | 0–5 pieces | 3,400–3,600 LF of walls, bearing split |
| p12 2nd floor frame | nothing | 700 joist pieces, 9,200 LF: JOIST 1 800S162-54, JOIST 2 2x800S162-54, JOIST 3 4x800S162-54, all at 16" o.c. |
| p13 3rd–5th floor frame | nothing | 196 pieces, 8,762 LF |
| p14 roof frame | nothing | 291 pieces, 8,862 LF |

Other sets:
- AC Retreat S6.05 high roof: 59 roof trusses at 2'-0" o.c., missed before.
- StudioRes, Home2 and AC Retreat are otherwise unchanged. The only changes are fewer false untagged pieces (title block, stairs, furniture); see `e2e/final_diff.txt`.

## Tests
- Backend:
  - new `test_takeoff_div5_rules.py`: 9/9 pass;
  - detail-scan 18/18, auto-takeoff 17/17, framing-rules 11/11 pass.
- Frontend: vitest pdf-takeoff 239/239 pass; narrow tsc 102 (baseline).
- Regression: `e2e/regress.py old|new` + `e2e/diff.py` over 4 full sets (150 sheets).

## Not done yet
- Bearing is only read where a framing sheet lines up with the wall sheet. Walls with no joists over them keep the profile-based guess (54 mil and heavier = bearing).
- Stairs drawn without UP/DN text are not found.
- Ladders, grating, lintels and embeds are not read from plans yet.
- Some joist fields broken by many crossing lines are partly missed (AC S6.05 has a few trusses not drawn).

## Update (same day): sheet 3 load bearing walls
- **What you reported:** CFS REV-014 sheet 3 gave no load bearing walls in the ERP.
- **Cause 1:** the legend lines say "… SINGLE STUD AT THE EDGES OF SHEAR WALLS, STRAP BRACING …". Every coloured wall was labelled "Shear Wall", and the bearing check leaves shear walls alone.
  - Now "shear" names the wall type only when the entry starts with it.
  - A stud spec that mentions shear walls or strap bracing in passing is a stud wall: its bearing comes from the framing above, else from the gauge (54 mil and heavier = bearing).
- **Cause 2:** the sheet's dimensions disagree with each other.
  - The 13'-0" panel dimensions say 10.40 units/ft. The overall 190'-6" / 64'-6" dimensions say 10.84.
  - The majority won, so the sheet read about 4% too big and could not be laid over the framing plan.
  - Now each dimension's vote counts by the length it measures, so overall building dimensions decide. Sheet 3 is now 1.81" = 1'-0", the building measures 190 ft, and the overlay with sheet 12 fits 56%.
- **The overlay** also slides in half-foot steps (±3 ft) to line the joist ends up on the walls.
- **Result, sheet 3:** 26 load bearing walls (450 LF), 28 non-load bearing (632 LF), 4 CMU. Sheets 4–7 are split the same way.
- **Regression:** StudioRes and AC Retreat unchanged. On Home2, only sheet 16's walls changed: unnamed → load bearing, by stud gauge.

## Update 2: walls when the drawings don't say (user rule)
- **The user's rule:** read the full sheet; take off only what is ticked. When the drawings don't say:
  - exterior walls and demising walls (hotel / apartment) are load bearing, 6" studs;
  - every other wall is non-load bearing, 3-5/8" typical.
- **What decides, in order:**
  1. what the drawings say (wall-type text, schedule, legend, house rules);
  2. the floor framing above (`bearing_walls.py`);
  3. these defaults (`auto_takeoff.default_wall_roles`).
- **Exterior wall:** one side open to the outside (rays from the wall meet nothing). It must also be the outermost wall there: no other wall of the building lies beyond it, so an undrawn corridor is not "outside".
- **Demising wall:**
  - the whole wall line, end to end (a shear panel plus W4 pieces count as one wall);
  - 10 ft or longer, starting at an exterior wall;
  - repeated: two or more like walls side by side, 8–60 ft apart.
- **Defaults:**
  - Load bearing gets 600S162-54; non-load bearing gets 362S125-18. The drawing's own stud size (e.g. "6" METAL STUD WALL") is kept.
  - The reason is written into the spec: "Bearing not stated on the drawings: …".
  - The framing above replaces it when the set has framing.
- **Wall-type text:**
  - CMU, masonry and concrete stay CMU walls.
  - "2-1/2" / 3-5/8" / 4" metal stud wall" is a partition.
  - "6" metal stud wall" is judged by where it sits. This replaces the old "any metal stud wall = partition" rule.
- **Wall detection with no tags at all** (`walls_without_tags`, `detail_scan.wall_pens`):
  - Every double line in the sheet's wall pen at 3"–10" apart is a wall.
  - Only on a sheet titled as a wall / floor plan or layout, never framing, foundation, truss, roof or detail sheets.
  - The walls must spread 30 ft or more each way.
- **Scale borrowing** (for sheets with no readable scale):
  - takes the most common scale among the nearest same-size sheets;
  - never takes a detail scale larger than 1/4" = 1'-0".
  - A sheet with none must be calibrated, e.g. arch sheets whose text is drawn as lines.
- **Regression:** only walls that nothing named changed role (StudioRes S205–S208, Home2 S-3.0x, AC wall sheets, CFS p15/19/20/24–26). No walls were added or lost on the four test sets.
- **Tests:** div5 10/10 (new: defaults for exterior, demising and partition walls); auto-takeoff 17/17 (wall-type test updated to the new rule); detail-scan 18/18; framing-rules 11/11.
