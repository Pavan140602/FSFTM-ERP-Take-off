# 2026-11-03: PDF Takeoff wrap-up (Revu parity)

This builds on `deliveries/2026-11-02-revu-pdf-takeoff/`; restore that one first, then this one. The code changes are marked `OE-DELIVERY 2026-11-03-...`.

## Changes

### Auto Takeoff panel would not open
- **Cause:** Tools > Auto Takeoff… and Window > Auto Takeoff only switched the panel's tab. If the left panel was closed or showing another tab, nothing appeared.
- **Fix:** all Tools/Window menu entries for Auto Takeoff, AI Assistant and Tool Chest now open the panel (`showRevuPanel`).

### Tool Chest
- **Material Library removed.** It is replaced by structural tool sets, one per member family:
  - CFS Trusses, CFS Joist, CFS Load Bearing Walls, CFS Non-load Bearing Walls
  - Decking
  - W, WT, HSS and L Shapes
- **Source of the sets:** built from the SSMA / AISC / Vulcraft tables. They are added once; each set can be deleted. The library button in the Tool Chest header brings them back.
- **Tool tiles show the member type.** Each tile draws the member's cross-section with a badge:

  | Family | Drawing | Badge |
  |---|---|---|
  | W beam | I | W |
  | WT | T | WT |
  | HSS (rectangular) | tube | HSS |
  | HSS (round) / pipe | ring | HSS |
  | Angle | L | L |
  | Channel | C | C |
  | CFS stud | lipped C | CFS |
  | CFS track | U | TRK |
  | Deck | flutes | DECK |
  | Joist / truss | zig-zag | JST |

  The family is read from the designation (W12X26, WT9X25, HSS6X6X1/4, 600S162-43, 362T125-43, 1.5B-18, ...).
- **New tool button in every set (My Tools included).** You choose:
  - type
  - Subject
  - Label
  - name
  - colour, width and line style

  The form shows what the tool will display as (e.g. "Shows as: WT").
- **ZenTek:** the ZenTek Revu Tools store page was used only as the idea for family-based structural sets. None of its content is copied; ZenTek's own tool chests are a paid product.

### Scale
- The Scale tab shows the drawing scale (e.g. `1/8" = 1'-0"`) with its ratio, instead of `1px = 0.0339 m`.

### Left icon rail
- Every icon has a caption so each one reads at a glance: Thumbs, Index, Measure, Tools, Scale, AI, Auto, Search.
- New icons:
  - Thumbnails: a stack of pages
  - Bookmarks: a bookmarked book
  - AI: a chat bot
- **Removed:** Markups List. The bottom list still opens with Alt+L and the Window menu.

### Top toolbar
- One wrapping row instead of two fixed rows, so the buttons arrange themselves at any window width, full screen included.
- Pages, Legend, Show/Hide, Names, Values, Panel, AI Assistant, Fullscreen, Recognize, Count similar and the rest flow together.

### Active Group
- Removed from the side panels, including Auto Takeoff and the Tool Chest. Markups take their group from the tool, Auto Takeoff or the Tool Chest tool.

## Files

- `files/`: final copy of every file changed on 2026-11-03.
- `patch_scripts/`: the scripts used.
- `restore.py`: run it to put these files back; `--dry-run` shows what would change.

## State

- Typecheck: no new errors (112, all older).
- Unit tests in the takeoff areas: 658 pass. 6 fail, all of them older: wheelZoomStep ×2, ledger value sort ×3, MeasurementLedger sort ×1.
- Browser check: no page errors.
