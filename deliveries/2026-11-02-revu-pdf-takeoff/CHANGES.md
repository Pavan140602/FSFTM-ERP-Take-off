# 2026-11-02 — PDF Takeoff: Bluebeam Revu parity + Auto Takeoff

Everything delivered on 2026-11-02 for the ERP's PDF Measurements viewer
(`/takeoff?tab=measurements`). Every code change is marked in the source with
an `OE-DELIVERY 2026-11-02-<name>` comment. Grep for it to find each one:

```
grep -rn "OE-DELIVERY:\? \?2026-11-02" frontend/src backend/app backend/tests
```

## What is in this folder

| Path | What it is |
|---|---|
| `files/` | The final copy of every file changed today, at its real path in the project. |
| `patch_scripts/` | The patch scripts that made the changes, in the order they were written. They are already applied; the copy is kept as history. |
| `e2e/` | The browser checks used to verify the work (Playwright, headless Chrome). |
| `restore.py` | Copies `files/` back into the project, first backing up whatever is there. |

To restore today's state after a reinstall or an overwrite:

```
python deliveries/2026-11-02-revu-pdf-takeoff/restore.py
```

## Features delivered

### Auto Takeoff (rules + optional AI with your own key)
- Detects beams, columns, joist series, areas, CFS walls (by wall tag), trusses, joists and other members. The AI step uses the key in Settings > AI and is optional.
- Re-runs never duplicate. User edits, deletions (kept on the server) and profile changes survive.
- Detected-markups list with single delete, profile names (editable), column height (saved), and two-way highlight between the sheet and the list.
- C1/C2 column marks are resolved through schedule tables.
- Profile text is highlighted Revu-style; no column markers are drawn on the sheet.
- All auto markups are in the bottom Markups list.
- The old Detect tab was removed.
- Tags: `auto-takeoff`, `auto-takeoff-columns`, `auto-takeoff-list`, `auto-takeoff-profile-edit`, `remove-detect`.

### Revu workspace
- File / Edit / View / Document / Measure / Markup / Tools / Window / Help menu bar, and a full-window workspace (`revu-workspace`).
- Status bar: SNAP, scale picker, units, SYNC, zoom, sheet size, cursor X/Y (`revu-statusbar`, `revu-units`).
- Deep zoom, wheel zoom anchored at the cursor, and serialized renders (`revu-zoom`, `revu-zoom-anchor`, `render-serialize`).
- Viewports with their own scale, and Sketch to Scale (`revu-viewports-sketch`).
- Line type, fill, label mode, show/hide by type, and Revu captions (`revu-properties`, `revu-labels`).
- PDF export parity (`revu-export`).

### Left side (Revu tab order)
- Icon rail: Thumbnails, Bookmarks/Page Index, Measurements, Tool Chest, Scale | AI, Auto Takeoff | Markups List, Search. Clicking an open tab closes it. Panels can be resized by dragging.
- Thumbnails are sharp and labelled with the sheet number read from the title block (e.g. S1.00). The labels can be edited. Large files open the first page first (`revu-left-panel`, `revu-left-panel-v2`, `revu-dock`).
- Measurements tab: the measure tools with their Revu keys, plus this page's totals.
- Scale tab: Scale, Calibrate, calibration status, Viewports, and the scale presets (Imperial / Civil / Precision).
- Tool Chest tab (see below). Layers, Settings and Colours were removed from the rail.

### Right side
- A vertical tool strip with all 27 measure and markup tools. When the window is short, the rest go under a "more" button (`revu-tool-strip`).

### Split view + Sync
- SYNC puts both panes on the same page; zoom and pan follow both ways (`revu-dock`).

### Properties bar (top, only while markups are selected)
- A Revu tab showing the markup type, plus Subject and Label.
- Colour, line type, width, fill, opacity %.
- Units: in, ft, ft-in, mm, cm, m, km. Area units: sq in, sq ft, sq cm, sq m, sq mm.
- Wall Height, and a caption pick list (Label, Length, Area, Perimeter, Wall Area, Depth, Volume, Count).
- Font, size, text colour, Bold / Italic / Underline, selection totals, and "Add to Tool Chest".
- Only the fields that fit the selected markup type are shown.
- Saved per markup in the metadata key `label_style` (`revu-properties-bar`).

### Markups list (bottom)
- Length / Area / Unit show exactly what the sheet caption shows: the markup's own unit, else the area unit, else the chosen display unit, else the page calibration. The legend uses the same rules.
- Separate Subject and Label columns, as in Revu (`revu-markups-list`, `revu-markups-units`).

### Tool Chest (Revu style)
- Tool sets: Recent Tools (automatic), My Tools, and your own sets.
- Each tool keeps its type, Subject, Label, group and all properties.
- Drawing mode or Properties mode per set; icon or detail view; drag between sets; double-click to rename.
- Saved in the browser (`localStorage` `takeoff.toolChest.v2`). Old saved tools are migrated into My Tools (`revu-tool-chest`).

### Revu keyboard shortcuts (Bluebeam defaults)
- Measure:
  - Shift+Alt+L Length, Shift+Alt+Q Polylength, Shift+Alt+A Area, Shift+Alt+P Perimeter, Shift+Alt+V Volume
  - Shift+Alt+C Count, Shift+Alt+D Diameter, Shift+Alt+G Angle, Shift+Alt+U Radius, J Dynamic Fill
- Markup: V, L, A, R, E, C, K, T, W, Q, N, H, P, S, Shift+P, Shift+C, Shift+L.
- View: Ctrl+9/0/8, Ctrl+Left/Right, Home/End, Ctrl+2/H/I, Ctrl+Shift+2, Ctrl+4/5, Shift+V, Z, +/-.
- Panels: Alt+T/B/L/X/U, Ctrl+F.
- Edit: Ctrl+Shift+L/M/J/[, Ctrl+G, Ctrl+Shift+G, Ctrl+Shift+F8.
- Help > Keyboard Shortcuts shows the full list (`revu-shortcuts`).

### Review fixes
- `review-fixes`: fixes found in review during the day.

## Files changed (43)

Backend:
- `backend/app/modules/takeoff/auto_takeoff.py`, `auto_takeoff_ai.py`, `router.py`, `schemas.py`
- `backend/tests/unit/test_takeoff_auto_takeoff.py`

Frontend: see `files/frontend/src/...`. The main ones:
- `modules/pdf-takeoff/TakeoffViewerModule.tsx`
- `modules/pdf-takeoff/components/RevuMenuBar.tsx`, `RevuPropertiesBar.tsx`, `RevuToolStrip.tsx`, `RevuToolChest.tsx`
- `modules/pdf-takeoff/data/auto-takeoff.ts`, `revu-shortcuts.ts`, `tool-chest-sets.ts`, `sheet-index.ts`, `revu-style.ts`
- `modules/pdf-takeoff/useMeasurementPersistence.ts`
- `features/takeoff/components/MeasurementLedger.tsx`
- `features/takeoff/lib/takeoff-display-units.ts`, `takeoff-revu-props.ts`, `takeoff-shortcuts.ts`, `takeoff-ledger.ts`, `takeoff-types.ts`

## State at the end of the day

- Typecheck: no new errors. The narrow takeoff check gives 112, all of them older.
- Unit tests (takeoff areas): 6 failing, all old (wheelZoomStep ×2, ledger value sort ×3, MeasurementLedger sort ×1). Everything added today passes.
- The backend must be restarted after backend changes; there is no hot reload. The frontend hot-reloads.

## Not done yet

- Tool Chest sets are saved per browser, not on the server.
- Sheet-number edits are saved per browser, not on the server.
- The saved PDF does not draw the caption font or underline.
- Revu Markup Polyline (Shift+N), Eraser, Snapshot, Image and Lasso have no tool here.
- Bookmarks and Search are simple: the page index and Find.

## Test data

- QA login: `revu-qa@example.com` (local only).
- Project: "Auto Takeoff QA" (`c36f0df4-3be0-4dee-a063-64212295c1c3`).
- Main test drawing: `8070446a-eec2-49fe-913d-8c576069a6b9`.
- Delete these when testing is finished.
