# 2026-11-03 (part 2): Structural Tool Chest + Auto Takeoff roles + column marks

Apply after `2026-11-02-revu-pdf-takeoff` and `2026-11-03-revu-wrapup`. The code changes are marked `OE-DELIVERY 2026-11-03-structural-tool-chest` and `2026-11-03-auto-takeoff-roles`.

## Tool Chest: profile by profile, by use

The sets follow the idea of ZenTek's structural Revu tool sets. Nothing was copied from ZenTek, whose chests are a paid product. The data is in `frontend/src/modules/pdf-takeoff/data/structural-tools.ts`.

**AISC, most commonly used shapes**
- W Beams (46)
- W Columns (32)
- WT (11)
- HSS Square & Rectangular (20)
- HSS Round & Pipe (10)
- Channels C / MC (8)
- Angles (10)

**SSMA cold-formed steel, by use**
- Load Bearing Walls (17)
- Non-Load Bearing Walls (11)
- Headers (10): box, back-to-back, L-headers, header track
- Jambs (8)
- Floor Joists (10), including rim track
- Track & Accessories (10): track, bridging, blocking, strap, clip

**CFS trusses**
- Floor Trusses (6)
- Roof Trusses (10): common, girder, hip, hip girder, jack, mono, scissor, gable end, valley, attic

**How the tools work**
- Each tool's Subject is the member role: Beam, Column, Load Bearing Wall, Header, Jamb, Floor Joist, Roof Truss and so on.
- Each tool has a role colour and the right takeoff tool:
  - walls use polyline
  - jambs and W columns use count
  - the rest use length
- Tiles draw the member's cross-section. New ones: Header (box) and Jamb (paired studs).
- The first structural sets (the old material-library ones) are replaced automatically.

## Auto Takeoff finds what each member is

The backend now returns `role` and `profile` for every item (`auto_takeoff.assign_roles`).

| Member | How the role is decided |
|---|---|
| Walls | Load Bearing / Non-Load Bearing from the wall schedule text (LOAD BEARING, SHEAR WALL, NON-LOAD, PARTITION, "metal stud wall" ...), then the tag prefix (EW/SW/BW vs IW/PW/NW), then the stud thickness (54 mil and up = load bearing). The stud profile is taken from the schedule (SW-4 → 600S162-54). |
| Trusses | Floor or Roof, from the callout, else the sheet title (ROOF FRAMING / FLOOR FRAMING ...). |
| Joists | Floor / Roof / Ceiling Joist, the same way. |
| Headers / Jambs | From callouts ("(2) 600S162-54 JAMB", "BOX HEADER", HDR) and from H1 / JB1 tags with a header / jamb schedule. A tag without a schedule row must repeat before it counts. |
| Beams / Columns / Angles / Track / Stud | From the profile. |

On the sheet:
- The markup's **Subject** is the role.
- **Material/Profile** is the profile found.
- The **colour** is the colour of the matching Tool Chest tool, else the role colour.
- A Subject you typed yourself is never overwritten on a re-run.

## Column marks

Every auto column shows a column symbol (a ring with a cross) on the sheet. Where the drawing prints a mark (C1, C2 ...), the mark is shown in a tag beside it and its printed text is highlighted like the profile text.

## Checks

- Typecheck: no new errors (112, all older).
- Frontend tests: 658 pass; the 6 failures are older.
- Backend Auto Takeoff tests: 15 pass (2 new: wall roles, header/jamb classification).
- Browser:
  - QA drawing: 59 beams → Subject Beam, 24 columns → Subject Column, column symbols drawn.
  - Full 61-page set: SW walls → Load Bearing Wall with stud profile; "6" metal stud wall" types → Non-Load Bearing Wall; HDR callouts → Header.
- The backend was restarted to load the new code.
