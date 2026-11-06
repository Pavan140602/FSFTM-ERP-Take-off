# 2026-11-05 (part 3): Auto Takeoff accuracy + blank workspace fix

Apply after `2026-11-05-upload-progress`. Restore with `python deliveries/2026-11-05-takeoff-accuracy/restore.py` (try `--dry-run` first), then **restart the backend**. The backend in use when this was written started at 19:33, before these changes, so it runs the older code until restarted.

## Shear wall plans: measured like an estimator in Revu

- **Wall types W1–W4:** each wall runs from the centre of the intersecting wall on one side to the one on the other. Examples: a bay's exterior wall between two party walls (13'-0"), or a party wall from the exterior wall to the corridor wall.
  - Window and door gaps are bridged; a corridor is never crossed.
  - Two tags at one junction no longer count the same wall twice.
  - Dimension lines are never taken for walls.
- **Shear and strap-braced walls (SW / BR):**
  - **Length:** the hatched panel at the tag, set to the dimension drawn with it. A dimension is used only when its ticks are centred on its ends and it is within 15% of the hatch length.
  - **Hatching:** only the panel's own hatching is followed (same pen and weight as the starting stroke). A thin general wall pattern no longer stretches panels, and hatching that turns a corner into the next panel is ignored.
- **Stacked tags** such as "BR-1 W1": the W1 stud wall is measured wall to wall on the panel's own wall.
- **Schedule data:** a rounding mismatch dropped the schedule row for a few tags (5 walls on S208 had no profile). Fixed: every wall on S205–S208 now carries its framing, spacing, height and level.
- **Headers:** stay as counts with their schedule size, jacks and kings. These plans don't draw openings as gaps, so a length would be a guess. The opening finder (`opening_at`) is kept for plans that do draw them.

### Result on the StudioRes set (S205–S208; every value equals the dimension on the plan)

| Wall type | Lengths found |
|---|---|
| SW-1 | 14 × 7'-0", 2 × 9'-0" |
| BR-1 | all 24'-0" (20 on S205, 24 on S206–S208) |
| BR-2 | 24'-0" and 12'-0" |
| BR-3 | all 10 × 16'-0" |

- **Holdowns:** 108 on S205 and 120 on each of S206–S208. These equal the "HD" tags on each sheet; the one extra "HD" word per sheet is the legend line.

## Framing plans

- **CFS beam B-1:** takes the heavy beam line under its tag, 14'-0" on S202–S204. It was 2 ft before.

## Blank page in PDF Measurements (frontend)

- **Before:** the full-window workspace (on by default) covered the browser even with no drawing open, showing a white screen instead of "Current & recent drawings".
- **Now:** it covers the window only while a drawing is open.

## Checks

- **Backend tests:** 25 pass (8 framing-rules tests, 2 new: walls never counted twice, dimension tick detection; 17 existing Auto Takeoff tests).
- **Typecheck:** no new errors; the same 112 older errors remain.
- **Frontend tests:** 665 pass; the 6 failures are older (wheelZoomStep ×2, ledger value sort ×4).
- **Browser upload test:** the 8.6 MB PDF was uploaded to the local QA project at about 1.5 MB/s. The card showed "29% · 2.5 / 8.6 MB · 5 s left" → "65% · 5.6 / 8.6 MB · 3 s left" → "Uploaded · reading drawing…", then the drawing opened.
