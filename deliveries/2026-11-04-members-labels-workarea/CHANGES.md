# 2026-11-04: Member types, on-line labels, framing layout, work area, accounts

Apply after the 2026-11-02 and 2026-11-03 deliveries. The code changes are marked `OE-DELIVERY 2026-11-0[34]-...`.

## Auto Takeoff: member types

"What to take off" now lists member types in two groups.

- **Structural steel**
  - Columns
  - Beams
  - Joists (SJI K / LH / DLH)
  - Deck areas: Type B / F / A roof deck, composite (VL / VLI / VLR), form deck, Type N, cellular. Each deck callout becomes an area covering the bay it sits in.
- **Cold-formed steel**
  - Load bearing walls, Load bearing headers, Load bearing jambs, Shear walls
  - Non-load bearing walls, Non-load bearing headers, Non-load bearing jambs
  - Trusses (roof / floor)
  - CFS joists
  - Hat channels (hat / furring / resilient channel callouts)
- **Other:** angles, track and bays.

How each member is identified:
- **Headers and jambs** take the wall they sit in: load bearing (or shear) vs non-load bearing. With no wall nearby, 54 mil and heavier counts as load bearing.
- **Shear walls** are their own type: SW tags or "SHEAR" in the schedule.
- **Re-runs** only touch the member types you ticked.

## Tool Chest

- **Names** show only the designation, AISC style: WT4x9, W12x26, HSS6x6x1/4, Pipe4Std. In detail view, the second line is the description.
- **New sets:**
  - SJI Steel Joists (24 sizes)
  - Metal Deck (13)
  - SSMA Shear Walls (9)
  - Load Bearing Headers and Non-Load Bearing Headers
  - Load Bearing Jambs and Non-Load Bearing Jambs
  - CFS Joists
  - Hat Channels (SSMA F furring 087F / 150F, RC-1)
- **Hat glyph:** hat channels get their own tile drawing.

## Reading the drawings

- **Text-layer sheets:** every word and line is read from the PDF's vector data at full precision, so nothing is missed at any zoom.
- **Scanned sheets (AI vision):** each sheet is read zoomed in, as four overlapping quarters (about 2000 px each). Lines are traced at 220 dpi.
- **Schedules and notes first:** wall, header and jamb schedules, column marks and notes are read from all sheets before anything is drawn.
- **Run report:** the result says what was read first, e.g. "Read first: 3 sheets of schedules and notes · 4 wall types · 2 column marks".

## Labels on auto markups

- **Layout:** the profile (e.g. W12x26) sits above the line and the length below it, centred on the line. They turn with it: horizontal, vertical, inclined or any angle.
- **Size:** labels match the callout on the sheet.
- **Existing auto markups** switch to these labels once per drawing. Choosing "None" in the panel afterwards sticks.

## Lay out framing (framing that is not drawn)

**Where to find it:** Tools > Lay out framing…, or "Lay out framing" on the Properties bar when an area is selected.

**How to use it:** draw the outline (e.g. a gable roof), select it, and optionally also select the ridge line. Then pick:
- the member, from the Tool Chest or your own Subject / Label
- the direction: vertical, horizontal, across or along the selected line, or a custom angle
- the spacing (24, 24", 2'-0", 600mm)
- where the first member goes

Every member is placed across the outline at that spacing and clipped to its shape, including L-shapes. One Undo removes them all.

## PDF Measurements work area

- **Compact bar:** the header (breadcrumb, info card, big tabs, videos bar) shrinks to one slim tab bar. The ▾ button brings the full header back.
- **More room for the drawing:** the Markups list opens shorter (drag it taller) and the bottom drawing strip is slimmer.
- **Drawing stays open:** the drawing you had open comes back when you return to PDF Measurements, from the sidebar or from /takeoff with no tab. It opens on the same page.
- **Drawings strip:** renamed "Current & recent drawings". The open one is tagged CURRENT, then the most recently opened.

## Accounts

- Users > **Create account** (admins only): name, email, a first password (12+ characters, with a letter and a digit) and a role. The account is active at once; no email or approval is needed.
- It uses the existing admin endpoint `POST /v1/users/`.
- This installation already has an administrator, which is why demo-admin sign-in is switched off. Sign in as that administrator to create accounts.

## Checks

- **Typecheck:** no new errors.
- **Frontend tests:** 741 pass; the 6 failures are older.
- **Backend Auto Takeoff tests:** 16 pass.
- **Browser:**
  - Compact page: no videos bar, Markups list 170 px tall.
  - Member-type picker; "Read first" report.
  - Labels on horizontal, vertical and inclined members.
  - Lay out framing: 36 members at 24" O.C., then one Undo.
  - The test outlines were removed afterwards.
