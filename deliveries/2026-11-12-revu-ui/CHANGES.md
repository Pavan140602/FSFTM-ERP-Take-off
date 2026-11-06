# 2026-11-12 revu-ui

Restore after 2026-11-11-div5-rules: `python deliveries/2026-11-12-revu-ui/restore.py`, then reload the page.
- This round is frontend only, so no backend restart is needed.
- `patch_scripts/` has the scripts that made the changes. The final files are in `files/`.

## What the user asked
1. Legend in PDF Measurements: Revu style and behaviour.
2. Markups list: right-click on 3–4 selected rows showed the browser's "Inspect" menu. Replace it with the Revu menu.
3. Every colour choice uses the colour picklist.
4. Cloud tool: dragging should draw a rectangular cloud.
5. Every tool exits by itself once its markup is done.
6. Revu-style tool icons.

## What changed
1. **Legend**
   - New "Revu" layout, the default. One row per Subject and look (type + colour), showing:
     - the symbol in its colour;
     - Qty;
     - Description (the Subject, else the label);
     - the total Length / Area, and the Unit.
   - The placed legend box on the sheet uses the same columns. Example: Home2 S-3.01 has 23 rows instead of 101.
   - The earlier per-length legend with every list column is the "Detailed" layout, one click away in the legend panel header. The choice is saved in `takeoff.legendStyle`.
2. **Markups list right-click**
   - Opens the markup menu for the selection:
     - "n markups selected";
     - Go to markup;
     - Properties;
     - Set Status (None / Accepted / Rejected / Cancelled / Completed);
     - Colour (picklist);
     - Lock / Unlock;
     - Hide / Show;
     - Select All (this page).
   - The existing items follow: select same profile, duplicate, multiply, offset, RFI, legend, rotate / flip / align, group, delete. Delete removes every selected markup.
   - A row outside the selection becomes the selection; a row inside keeps the whole selection, as in Revu.
   - Ctrl+click after a plain click keeps the first row selected.
   - The menu moves up so it never runs off the screen.
3. **Colour picklist** everywhere a colour is chosen in PDF Measurements:
   - markup colour, label text and background colours;
   - per-label text colours, legend text and background colours;
   - the Properties panel's custom colour and the top bar's text colour;
   - the Tool Chest tool colour and the tool style colour fields.
4. **Cloud**: press, drag and release draws a rectangular cloud with a dashed preview. Rectangle, Highlight and Ellipse also draw by dragging. Click-by-click still works.
5. **Tools exit after one markup** and go back to Select, like Revu.
   - Count keeps counting until Esc.
   - Double-click a tool button to lock it on for repeated use (lock badge shown). Picking another tool unlocks it.
6. **Icons**: a new original icon set (`components/revu-icons.tsx`) in Revu's style. Measure tools are line diagrams with blue dimension accents; markup tools are red / orange. It is used in the tool strip, its "more" menu and the Tool Chest. Bluebeam's own icon artwork is copyrighted, so it is not copied.

## Checks
- Browser, QA account, Home2 S-3.01 with 159 auto markups (`e2e/e2e_revu_ui.cjs`):
  - list right-click with 3 rows gives "3 markups selected";
  - status set to Accepted; colour picklist opened;
  - cloud drag made "Cloud 1" and the tool returned to Select;
  - a locked rectangle drew 2 and stayed on;
  - the legend is Revu style, and placed on the sheet.
  - Screenshots `e2e/r1`–`r8`.
- Type check (narrow tsc): 102, the baseline.
- vitest pdf-takeoff + features/takeoff: 687 pass. The same 6 old failures as before (ledger value sort, wheel zoom step), unrelated.

## Update: Legend Setup (user follow-up)
- **The user's request:** select hand-drawn markups, right-click, Legend, then a window to choose the columns to keep and the table lines (vertical and horizontal, only vertical, or only horizontal) with the title on top. The legend must update as markups are drawn, and resizing it must scale all of it, smaller or bigger, as in Revu.
- **Right-click → Legend → Create New Legend** opens **Legend Setup** (`components/LegendSetupDialog.tsx`):
  - Title, and "Show the title row on top";
  - Columns: tick, and order with up / down;
  - Table lines: Grid / Horizontal / Vertical / Outline / None, with previews;
  - "Keep it live".
  - Then click the sheet to place the legend.
- **Each legend keeps its own setup** (`Measurement.legendSetup`), saved with the markup on the server (`metadata.legend_setup`).
  - Right-click a placed legend → **Legend Setup…** to change it.
  - A legend with no setup still follows the panel settings.
- **Live:** markups drawn later on the page with the same Subject and colour as the picked ones join the legend. Example: 3 Lengths picked, a 4th drawn, and the legend shows "×4 Distance 7.40 m".
- **Revu grouping:** a markup with no Subject groups by its tool name ("Distance", "Area"), not by its running label ("Distance 1", "Distance 2").
- **Resizing scales the whole legend** with one factor: title, headers, rows and symbols, both smaller and bigger (0.25× to 4×). Clicking and dragging on the legend use the same size as the drawing.
- **Count column** is named "Count"; Description is the Subject.
- **Checks:** browser, QA account, Home2 S-3.01 (`e2e/e2e_legend_setup.cjs`, screenshots `e2e/l1`–`l6`):
  - setup → place → live (×4) → shrink → edit (vertical lines, no title);
  - tools exit after one markup (Length, Rectangle).
  - tsc 101 (one fewer than the baseline of 102); vitest 687 pass, the same 6 old failures.

## Update 2: Legend Properties (Revu)
- **Right-click on selected markups → Legend ▸** opens a child menu:
  - **None**: the selected markups are taken out of every legend on this sheet (kept out of live legends too).
  - **Create Legend (this sheet)**: click anywhere to place it. It lists that sheet's markups only.
- **Select a placed legend** (or right-click it → Legend Properties…) and the **Legend Properties** panel opens (`components/LegendPropertiesPanel.tsx`). Items with ▸ open a child pop-up beside the panel:
  - Font (Arial, Calibri, Times New Roman…) and Colour (text).
  - **Title ▸**: title text, show on top, font size − / +, style B / I / U, colour.
  - **Columns ▸**: "In the legend" (order up / down, remove), beside it "Markup list columns" as the Edit Columns picklist.
  - **Cells ▸**: font size − / +, style B / I / U, colour.
  - Opacity (whole legend) and Line colour.
  - **Legend style ▸**: grid / horizontal / vertical / outline / none, with previews.
  - Line width (− / + in 0.5 pt steps), Fill (colour or none), Fill opacity, and Live.
- **Every setting is drawn on the sheet**, and the legend's size follows its fonts. The legend text now also grows with zoom.
- **The setup is saved per legend** with the markup on the server.
- **Fixes:**
  - The legend keeps the markups picked for Create Legend even though the placing click clears the selection.
  - An "everything" legend lists its own sheet only, less the ones taken out with None.
- **Checks:** browser, QA account (`e2e/e2e_legend_props.cjs`, `e2e/p1`–`p5`):
  - placed; panel opened;
  - title "Wall Legend" +2 pt, italic, underlined; Label column added; cells 12 pt bold;
  - Times New Roman, horizontal style, 2 pt lines, fill opacity 40%;
  - Legend ▸ None on Distance 1 changed the legend to ×2 (Distance 2, 3).
  - tsc 100 (two fewer than the old baseline of 102); vitest 687 pass, the same 6 old failures.

## Update 3: Legend side window, top-bar Legend button, properties in the top bar
- **Right-click → Legend:** the side window with **None** and **Create New Legend (this sheet)** opens on hover (or click).
  - It now floats above the menu, which had clipped it.
  - The menu remembers every selected markup when it opens. Right-clicking one of 3 selected markups on the PDF shows "3 markups selected", and None / Create New Legend / Delete act on all 3.
- **Create New Legend:** the next click on the PDF places it.
  - It keeps the markups picked, even when another legend already lists them, as Revu allows.
- **Top-bar Legend button:** with markups selected, it starts Create New Legend for them; click the PDF to place it. With nothing selected it opens the legend panel as before.
- **Click a placed legend:** its properties sit horizontally in the top Properties bar (`LegendPropertiesPanel layout="bar"`):
  - Legend | Font | Colour | Title ▸ | Columns ▸ | Cells ▸ | Opacity | Line | Style ▸ | Width − / + | Fill | Fill opacity | Live.
  - The ▸ items drop down their child pop-up under the item.
  - The floating panel is gone.
- **Checks:** browser (`e2e/e2e_legend_bar.cjs`, `e2e/b1`–`b5`):
  - side window visible with both items; "3 markups selected";
  - legend placed; properties shown in the top bar;
  - Title ▸ size + italic applied; Style ▸ opened;
  - navbar Legend with 2 selected placed a second legend.
  - tsc 100; vitest 687 pass, the same 6 old failures.

## Update 4: markups list, Polyline / Polylength, tool strip, Set Scale, Recent Tools
- **Markups list shows every sheet:** new "This sheet | All sheets" switch in the list header. It defaults to All sheets (`takeoff.ledgerScope`), sorted by page. Clicking a row on another sheet goes to that sheet.
- **Shift+click** selects the whole run from the last row clicked (checked: 3 rows over 2 sheets).
- **Polyline / Polylength (Revu):**
  - The measuring tool keeps Revu's name **Polylength**.
  - New **Polyline** markup tool (Markup menu and tool strip): click points, then double-click or right-click to finish. No measurement. It is saved as a multi-point Line markup, and Line markups now draw through all their points.
  - Legend / type labels: Polylength for the measure, Polyline for the markup.
- **Right-side tool strip:** bigger icons (19 px) with the tool name under each; full name on hover.
- **Set Scale window** (`components/SetScaleDialog.tsx`, Revu's Measurements > Scale):
  - Pages: Current (n) / All pages (1-N) / Custom range ("1-3, 5").
  - Scale: ◉ Preset (architectural, engineering, metric) or ◉ Custom ([1] [in/mm/cm] = [10] [ft/in/m/mm/cm/yd]).
  - Precision: 1", 1/2" … 1/64".
  - Calibrate… / Apply Scale / Cancel.
  - Opens by itself when a measurement starts (Length, Polylength, Area, Volume, Perimeter, Diameter, Radius, Arc, cutouts, Dynamic Fill) on a sheet with no scale. Cancel keeps the default for that sheet for the session. Measure menu > Set Scale… opens it any time.
  - Calibrate… arms the two-click calibration; the known length then applies to every page picked in Pages.
- **Preview while drawing:** the dashed line from the first point with segment / total read-outs is there for the measuring tools; drag-drawn shapes show a dashed box.
- **Recent Tools bar** under the navbar (Revu's Recent Tools): the tools used last, with their colour and Subject. One click takes the tool again.
- **Checks:** browser (`e2e/e2e_scale_tools.cjs`, `e2e/s1`–`s6`):
  - Set Scale opened on S-3.01 with no scale; All pages + 1/8" = 1'-0" applied, so S-3.02 did not ask again.
  - Length and Polyline drawn and went back to Select.
  - The list showed S-3.01 and S-3.02; Shift+click checked all 3.
  - Recent Tools re-armed Length.
  - Calibrate from Set Scale onto several pages is wired but was not clicked through in the browser.
  - tsc 100; vitest 687 pass, the same 6 old failures.

## Update 5: draw first, then ask for the scale
- **Change:** on a sheet with no scale (not calibrated, no preset), a measurement is drawn as normal, and Set Scale opens once it is finished. The first click no longer opens it.
- **After Apply Scale:** the measurement just drawn is re-measured with the new scale.
- **Cancel:** keeps the default for that sheet; it doesn't ask again this session.
- **Check** (`e2e/e2e_draw_then_scale.cjs`, `a1`–`a2`):
  - no window on the first click; the window opened after the Length was drawn;
  - 1/8" = 1'-0" changed the Length from 2.00 m to 6.77 m (200 pt = 22.2 ft);
  - a second Length on the sheet did not ask again.
  - tsc 100; vitest 687 pass, the same 6 old failures.

## Update 6: scale asks every time, previews, Cloud+, Reuse, Multiply/Offset
- **Scale ask:** on a sheet with no scale, Set Scale opens after **every** measurement until a scale is set (Cancel no longer silences it).
- **Set Scale window:** Preset and Custom sit side by side. Custom takes any length form: `12`, `12.0`, `12.5`, `12'`, `12'-6"`, `12' 6"`, `12'-6 1/2"`, `12 ft 6 in`, `6"`, `1 1/2"`, `1/8"`, `300 mm`, `3.5 m` (new `data/length-input.ts`, 24 tests).
- **Preview while drawing:** Cloud (and Cloud+) draws the scalloped outline through the clicked points and the mouse, shaded once it has 3 points. Polyline follows the mouse too.
- **Cloud+ (Revu cloud with comment):** tool strip and Markup menu. Draw the cloud by click points or drag; a comment box opens, and the callout (box + leader to the cloud's top-right) is grouped with the cloud, which also gets the comment text.
- **REUSE button** in the bottom status bar beside SNAP: when on, every tool stays on after each markup (Esc / Select to stop). Remembered between sessions. Double-click on a tool still locks just that tool.
- **Multiply / Offset:** the distance box takes the same length forms (fractions too); the Offset preview label shows the real typed distance (it used to read only the first number). Multiply keeps Revu's Direction / Distance / Copies with the live preview.
- **Checks** (`e2e/e2e_update6.cjs`, `e2e/shots_u6`): asked after the 1st and 2nd Length; custom 1" = 12'-6" read as 150 in; no ask after; cloud preview follows the mouse; Cloud+ drag → comment → grouped callout; REUSE kept Length on for two in a row. tsc 100; vitest 711 pass, the same 6 old failures.

## Update 7: Revu "Apply Scale to Pages", unscaled markups removed on Cancel, icon-only strip, real drag previews
- **Scale window** now has Revu's layout ("Apply Scale to Pages"):
  - Pages: one box, with a ▾ menu for Current (n) / All Pages (1-N), or type pages (e.g. 3-5 or 1,5).
  - Scale: ◉ Preset ○ Custom on one line; under it, the preset list or `[1"] [in] = [12'-6"] [ft]`.
  - Precision, then Calibrate… / Apply Scale / Cancel.
  - Revu's "Separate Y Scale" is not included: measurements use one scale for X and Y.
- **Unscaled markup:**
  - a measurement drawn on a sheet with no scale is removed when the window is cancelled (or a calibration started from it is cancelled);
  - Apply keeps it and re-measures it;
  - the window still asks after every measurement until the sheet has a scale.
- **Tool strip:**
  - icons only, the name on hover;
  - Revu order: markups (Text Box, Highlight, Pen, Callout, Cloud, Cloud+, Stamp) | shapes (Line, Arrow, Polyline, Rectangle, Ellipse, Polygon) | measurements, with dotted separators.
- **Drag preview** shows the real shape:
  - solid rectangle or ellipse;
  - yellow highlight;
  - scalloped cloud;
  - Cloud+: scallops plus the comment leader from the top-left corner.
  - Fix: the drag box was drawn inside a block that only ran with the Select tool, so it never showed while drawing.
- **Cloud+ comment box** now sits up-left of the cloud, as in Revu.
- **Checks** (`e2e/e2e_update7.cjs`, `e2e/e2e_drag_probe.cjs`, `e2e/shots_u7`):
  - asked → 1 row while asking → 0 rows after Cancel;
  - asked again; All Pages from the menu; custom 1/8" = 1'-0" applied and kept the row;
  - drag previews seen for Rectangle, Cloud, Cloud+ and Ellipse.
  - tsc 100; vitest 711 pass, the same 6 old failures.

## Update 8: Area options docked at the top
- **Area tool:**
  - Picking Area (or Volume) shows the Revu properties bar at the top: Colour, Line, Width, Fill, Opacity, Units, Area, Caption, Font, Size, Bold/Italic/Underline.
  - Under it, the area options (Length / Area / Volume units, Depth, Slope) sit in one horizontal bar.
  - The old floating popup under the tool button is gone.
- **When it shows:**
  - When the area is finished (the tool goes back to Select), both bars close.
  - Clicking an area (on the sheet or in the Markups list) opens them again with its own values and totals.
  - ✕ hides the area options until another area is selected.
- **Leftover code:** removed the popup position state and effect.
- **Check** (`e2e/e2e_area_bar.cjs`, `e2e/shots_u8`):
  - the bar showed with the Area tool;
  - after the area was finished, the tool was Select and the bar was gone;
  - selecting the area brought it back.
  - tsc 100.

## Update 9: live tracing for all tools, rectangle Area, one-column strip
- **Recent Tools bar** removed from PDF Measurements.
- **Live tracing:** every tool placed by clicks now draws its shape following the mouse.
  - Already did: Length, Polylength, Area, Volume, Arc, Line, Polyline, Callout, Cloud, Cloud+, Rectangle, Ellipse, Polygon, Pen, Highlight.
  - Added:
    - Perimeter and Polygon Cutout: open outline, closing edge to the start, cutout shaded red;
    - Diameter: line and circle; Radius: centre to circle; Radius (3-point): circle through the points;
    - Angle: both arms; Arrow: solid line with head; Ellipse Cutout: ellipse.
  - Area / Volume / Polygon Cutout also shade the shape as it is traced.
  - Count, Stamp and Text are one click, so they have nothing to trace.
  - Cause: the cursor was only tracked for a fixed list of tools.
- **Rectangle area:**
  - Area, Volume, Perimeter and Polygon Cutout can be drawn by press-and-drag; a shaded dashed box shows while dragging.
  - The four corners finish like a double-click (area, perimeter and value worked out as usual).
  - A plain click still places vertices one by one.
- **Polylength icon:** redrawn as a measure (blue path with dimension end ticks and a ruler) so it no longer looks like the red Polyline markup.
- **Right tool strip:**
  - one column;
  - the tools that don't fit sit behind a ▾ at the bottom, which opens a list (icon + name + shortcut) beside it, above the chat button;
  - a tool picked from the list takes the last slot so it shows as active.
- **Checks** (`e2e/e2e_follow_audit2.cjs`, `e2e/shots_u9`):
  - 24 tools all followed the mouse;
  - no Recent Tools bar; strip 1 column with 6 tools under ▾;
  - a dragged rectangle made Area 1 = 321.5 sf.
  - tsc 100; vitest same as before.

## Update 10: Cloud+ and Callout drawn the Revu way, typed in place
- **Cloud+:**
  1. Draw the cloud (drag, or click points).
  2. The leader line stays attached to the cloud: its arrow end slides round the cloud outline to the point nearest the mouse, and the box end follows the mouse.
  3. One click drops the comment box there; type straight into it.
  - Enter places it, Shift+Enter adds a new line, Esc cancels (the cloud stays).
  - No "name" dialog any more. The comment box and cloud are grouped.
  - The tool no longer jumps back to Select between the cloud and the comment.
- **Callout:**
  - First click = the point you call out.
  - A live leader follows the mouse, with the arrow head on that first point and a dashed box at the mouse, on the side the box will grow.
  - Second click places the box; type straight into it.
- **Fix:** saved callout text was centred on the box's left edge (a text alignment left over from other drawing); it now sits inside the box.
- **Check** (`e2e/e2e_leaders.cjs`, `e2e/shots_u10`):
  - the Cloud+ leader moved from top-left to bottom-right round the cloud with the mouse;
  - the click opened the in-place box (no dialog), typed text was placed, and cloud + comment were saved;
  - the callout live arrow showed and was typed in place;
  - tool back to Select afterwards.
  - tsc 100; vitest 711 pass, the same 6 old failures.

## Update 11: Enter closes, ghost closing line, snap to drawing lines, properties for every tool, grey scrolling strip
- **Enter finishes** Cloud, Cloud+, Polygon, Perimeter, Polygon Cutout, Area and Volume (3+ points), and Polyline / Polylength (2+ points).
  - Cloud+ then goes straight on to its leader and comment.
- **Ghost closing line:** while a cloud is clicked out, the scallops follow the mouse, and a dashed straight line runs from the mouse back to the start, showing where Enter / double-click will close it.
- **Snap to the drawing (Revu):**
  - Calibration now snaps to the drawing's lines, ends and corners on both clicks, with the snap ring while hovering.
  - Before, it only snapped if the tool armed underneath happened to be on the snap list.
  - Perimeter, cutouts, Diameter, Radius, 3-point Radius, Angle, Rectangle Area, Cloud, Cloud+, Polyline and Arrow now snap too (Length, Polylength, Area, Volume, Line, Polygon, Callout and Arc already did).
  - Uses the SNAP toggle in the status bar (on by default).
- **Properties for every tool:**
  - the Revu properties bar (Colour picklist, Line style, Width, Opacity %, plus fill, units, caption and font where they apply) now shows for every armed tool, not only Area / Volume;
  - settings carry onto each new markup.
- **Right tool strip:**
  - grey icons on white like the left rail, blue when on, no names;
  - one column that scrolls; ▾ at the bottom / ▴ at the top scroll it; it stays clear of the chat button.
- **Polylength icon:** redrawn after the user's Revu picture (polyline with square vertex grips in violet corner brackets).
- **Fix:** Esc during a calibration started from the scale window now also removes the markup drawn without a scale (as Cancel does).
- **Check** (`e2e/e2e_u11.cjs`, `e2e/shots_u11`):
  - the calibration point locked onto a wall line;
  - Cloud+ with 3 clicks showed the ghost line, Enter closed it, and leader → click → typed comment was saved;
  - Polygon closed with Enter;
  - the bar showed Width and Opacity for the Cloud+ tool;
  - the strip scrolled to Dynamic Fill.
  - tsc 100; vitest 711 pass, the same 6 old failures.

## Update 12: status-bar scale window, straight track lines, empty Cloud+ comment, magnet snap fixed
- **Status-bar scale:** now a button showing the page's scale; it opens the Apply Scale to Pages window (Pages / Preset-Custom / Precision / Calibrate…).
- **Cloud and Cloud+ while drawing:**
  - clicked out: straight dashed track lines through the points and the mouse, plus a dashed ghost line back to the start;
  - dragged: a dashed box;
  - the scallops appear only once finished (Enter, double-click or release).
- **Cloud+ comment can be left empty:**
  - Enter or clicking away with no text keeps an empty comment box; Esc keeps it too for Cloud+;
  - double-click any callout box later to type or change its text in place (one undo step);
  - an empty box shows blank instead of the default name.
- **Properties bar always shown** (greyed when nothing is picked), so the drawing no longer jumps up and down by about 40 px when a tool is picked or finished.
- **Magnet snap to the drawing (Revu):**
  - Root cause 1: the page line index was built from fields that don't exist on what the reader returns (`.segments` / `.centers` on a plain list), so it threw and no page ever had snap lines. This was one of the known type errors.
  - Root cause 2: the PDF line reader didn't understand pdf.js 6's packed `constructPath` op, so it found 0 lines even after that fix. It now reads both the new and old forms; page 7 gives 16,047 lines.
  - Snapping now finds line crossings (grid lines, wall corners, framing), shown as an ✕, as well as ends, midpoints and edges; the reach is a little wider (16 px).
  - It works for Polylength, Length, Area, calibration and the other measure tools; the SNAP toggle in the status bar turns it off.
- Fix: Enter followed by the box losing focus no longer adds the callout twice.
- **Check** (`e2e/e2e_u12.cjs`, `e2e/e2e_magnet.cjs`, `e2e/shots_u12`):
  - the status-bar scale opened the window;
  - straight track lines showed, with scallops after Enter;
  - an empty Cloud+ comment was kept, then double-clicked and filled in;
  - magnet markers showed on a wall corner (ring), a wall/HDU crossing (✕) and a gridline.
  - tsc 97 (3 old errors fixed); vitest 711 pass, the same 6 old failures.

## Update 13: left Scale panel opens the same scale window
- In the left rail's Scale & Calibration panel, Scale, Calibrate and the Not calibrated / calibrated chip now open the same Apply Scale to Pages window as the status bar.
  - Calibrate… in that window does the two-click calibration for the pages picked.
  - The quick preset buttons in the panel still apply at once.
- **Check** (`e2e/e2e_u13.cjs`, `e2e/shots_u13`): the panel's Calibrate and the chip both opened the window; its Calibrate… armed the two-click pick ("Calibrate: click point A"). tsc 97.

## Update 14: scale and calibrate windows in Revu's layout
- **Custom row** (every scale window): `[value] [unit] = [value] [unit]`, with Revu's unit list on both sides: in, ft, ft' in", in", yd, mi, mm, cm, m, km.
  - A bare number is in the chosen unit (0.125 in, 1 ft' in" = 1'-0"); marks typed in the box (', ", mm, m ...) win.
  - A read-out under the row shows the scale as understood (e.g. 1/8" on paper = 1'-0").
- **Scale line:** ◉ Preset ○ Custom on the left; **Calibrate / Recalibrate** and **+ Add Preset** on the right.
  - + Add Preset saves the custom scale to the user's saved scales: shown under "Saved" in the Preset list and in the left Scale panel.
- **Calibrate:**
  - After the two clicks, the old calibration dialog is replaced by this same window titled "Calibrate", on Custom, with the measured paper length filled in (e.g. 2.777778 in).
  - Type the real length on the right (e.g. 12'-6") and Apply Scale.
  - Pages picked before calibrating are kept; Recalibrate picks the two points again; Cancel removes an unscaled markup as before.
- **Check** (`e2e/e2e_u14.cjs`, `e2e/shots_u14`):
  - the 10 units listed; 0.125 in = 1 ft' in" read as 1/8" = 1'-0" and was saved as a preset;
  - Recalibrate, two clicks 200 pt apart: Calibrate window with 2.777778 in; 12'-6" gave 1:54 (150 / 2.7778).
  - tsc 97; vitest 711 pass, the same 6 old failures.

## Update 15: straight lines, small magnet, tool names, Close/Save, tool popover, Revu thumbnails + page menu, vector Save PDF
**Needs `npm install` in frontend once:** new dependency `pdf-lib` (pure JS); package.json and package-lock.json are included.

- **Straight lines by default:**
  - every new segment snaps to 0 / 45 / 90°;
  - **Ctrl+Shift** while clicking places a free point; **Ctrl** (or Shift) forces straight;
  - the toolbar ortho button still turns it off (remembered).
  - **Drawing between two lines:** a straight segment that snaps onto a drawing line lands exactly where its 0/45/90° direction meets that line, so lines drawn between walls are square.
  - Vertex edits are only squared with Shift / Ctrl.
- **Magnet symbol:** one small ring (3.5 px) for every snap kind.
- **Right tool strip:** the tool name is back under every icon (still one scrolling column).
- **Save / Close:**
  - **Save** button and **Ctrl+S** (File > Save was not wired) save now and confirm;
  - **Close PDF** button and File > Close PDF save, then go back to the drawing list.
- **Tool popover (Revu):** the tool button at the left of the properties bar opens:
  - Subject, Label, Layer (group);
  - **Set as Default:** the look plus Subject / Label / Layer become the tool's defaults, remembered;
  - **Add to Tool Chest ▾** (choose the tool set).
  - It works for an armed tool (any measure or markup tool) and for selected markups.
- **Thumbnails:**
  - under each sheet label: page number · scale (or "Scale Not Set" in amber); click the scale to set it for that page;
  - Ctrl / Shift click selects several pages.
- **Thumbnail right-click menu** (Revu's list; works on the selected pages):
  - Page Setup (size / rotation), Set Scale…, Cut / Copy / Paste Pages, Copy Page to Snapshot (PNG to the clipboard), Apply Stamp…;
  - Insert Blank Page…, Insert Pages… (pick a PDF), Extract Pages… (download, markups kept), Replace Pages… (pick a PDF), Delete Pages… (confirm), Rotate Pages ▸ (90 / -90 / 180);
  - Number Pages… (prefix + start → page labels), Rename Page Label, Reset All Page Labels;
  - Export Pages ▸ (PDF / PNG), Email Pages… (downloads + opens an email), Print Pages…;
  - Repair PDF, Flatten… (picture PDF of the pages with markups), Markup Summary ▸ CSV.
  - Changes to the document (insert / delete / rotate / replace / paste / cut / repair) are made on the real vector file. A new copy "<name> (…).pdf" is uploaded to the project and opened; its markups and page scales are carried across, rotated with the page where needed, and the original stays as it was.
- **Save PDF (Revu way):**
  - keeps the original file and all pages (vector, not pictures);
  - writes every markup as a real PDF annotation (line / polyline / polygon or cloud / square / circle / ink / free text / count points) on a PDF layer "OE Markups", so Revu, Acrobat and browsers show them;
  - embeds the editable ERP copy (markups + page scales).
  - Re-saving replaces the earlier ERP annotations instead of stacking them.
  - Opening that file in the ERP again turns off only the OE Markups layer and restores the markups as editable, with their scales; the drawing's own annotations (e.g. earlier Revu markups) stay visible.
  - The old picture export is still in File > Export flattened PDF.
- **Fix:** a new copy's empty first server load no longer wipes the markups just restored from the file.
- **Checks** (`e2e/e2e_u15*.cjs`, `e2e/shots_u15`, `data/pdf-pages.test.ts` 6 tests):
  - Distance 1 drawn off-level came out straight; Distance 2 with Ctrl+Shift stayed free; the magnet ring is small;
  - the popover set Subject / Label and added to My Tools; Save toast shown;
  - thumbnails showed "1:100" / "Scale Not Set"; the menu opened;
  - Extract downloaded (397 KB); Save PDF gave 34 pages with OE annotations + snapshot;
  - Insert Blank Page uploaded and opened a 35-page copy with the 2 markups;
  - Close PDF closed; re-opening the saved file restored the markups once (not doubled), with page 7's 1:100 scale, and page 4's original Revu cloud still showing.
  - tsc 96; vitest 717 pass, the same 6 old failures.

## Update 16: thumbnails load fast
**Why they were slow** (measured on Home2, 34 sheets):
- **Strip images:** every sheet draws about 1,850 tiny image strips (a title-block logo split into 1-pixel rows). pdf.js turned each strip into its own ImageBitmap, so one 240 px thumbnail took about 2.5–3 s to draw, as long as the full page.
- **Serial queue:** thumbnails were drawn one at a time, with an idle pause (up to 0.6 s) and an "interaction" pause (0.9 s) between pages.
- **Late start:** they waited for the main page on every page change, so the first one appeared about 20 s after opening.
- **Shared worker:** they shared the main PDF worker with the page render, the title-block text reading and the snap-line reading.
- **Heavy sheets:** some sheets (19, 20) also carry ~60 large photos, about 4–8 s each.

**Fix:**
- **Faster image drawing:** the takeoff viewer opens PDFs with raw image data instead of per-strip bitmaps (`openPdf(..., { fastImages: true })`, i.e. pdf.js `isOffscreenCanvasSupported: false`). A thumbnail went from ~3 s to ~0.3 s; a full page from ~1.9 s to ~0.45 s. This is opt-in in `shared/lib/pdfjs.ts`, so other viewers are unchanged.
- **Own workers:** thumbnails render from copies of the PDF on their own workers (`openPdfSideWorker`); two lanes with one worker each when the CPU has 4+ cores. They start as soon as the first page is on screen, with no idle pauses (only a 350 ms hold while you pan / zoom).
- **Order:** thumbnails showing in the panel are drawn first; the rest follow nearest to the current page. A lane restarts whenever new pages are asked for, so a heavy sheet never holds the others up.
- **Background fill:** 2.5 s after opening, all other pages are queued quietly, so scrolling the thumbnails finds them ready.
- **Browser cache (IndexedDB, `data/thumb-cache.ts`):** reopening a drawing shows its thumbnails at once (capped at 3,000 thumbnails).

**Measured (headless Chrome, same drawing):**

| | Before | After |
|---|---|---|
| First 5 thumbnails | 26 s | under 0.1–0.8 s |
| 12 thumbnails | — | 1.6 s |
| Scroll to the middle of the set | 20 s for 4 new | 0.6 s (already drawn in the background) |
| Reopen | everything again | 5 thumbnails in about 0.6–0.9 s from cache |

- Still slow: sheets with many large photos (19, 20) are about 4–8 s each the first time; after that they come from the cache.
- Checks: `e2e/e2e_thumbtime*.cjs`, `e2e/pdfjs_bench.cjs`, `e2e/ops19.mjs`. The Update 15 browser test was re-run and passed. tsc 96; vitest 717 pass, the same 6 old failures.

## Update 17: an uploaded PDF opens in PDF Measurements by itself
- **Auto-open:** uploading a PDF in "Current & recent drawings" (or the drop zone) now opens it in PDF Measurements as soon as the upload finishes.
  - Before, it was only added to the list.
  - With several files at once, the first to finish opens; the rest just join the list.
- **Fix (address bar):** the viewer's page-number update could rewrite the address from a stale copy right after a document switch, which dropped `?doc=`, so a refresh lost the open drawing. It now always keeps the open drawing's id (and tab=measurements).
- **Check** (`e2e/e2e_autoopen.cjs`, `e2e/shots_auto`):
  - upload → the viewer opened the new drawing (URL `?tab=measurements&doc=<new id>`);
  - its embedded markups were restored;
  - after a refresh the same drawing reopened.

## Update 18: properties bar only while a tool is active; clearer thumbnail page numbers
- **Properties bar:**
  - shows only while a tool is active (or markups are selected, so they can still be edited); gone when idle;
  - floats over the top of the drawing, so the drawing never jumps;
  - the Area options bar floats with it;
  - the "Detected scale … Use this" suggestion moved above it, so it stays clickable;
  - the blue tool tip moves down below the bar while the bar is showing.
- **Thumbnails:**
  - the page number is a bold badge (dark; blue on the current page);
  - the scale text is larger and darker ("Scale Not Set" in amber).
- **Check** (`e2e/e2e_u18.cjs`, `e2e/shots_u18`): bar count 0 idle → 1 with Polylength → 0 after Select; the drawing's top stayed at 213 px; thumbnail badges readable. tsc 96.

## Update 19: thumbnail page labels, Revu Extract / Delete Pages windows, copy / paste markups between pages
- **Thumbnail labels** (e.g. A000, A001, A002):
  - **Fallback:** when the title block gives no sheet number, the thumbnail now shows the PDF's own page label. Before, it was ignored and showed "+ sheet (n)".
  - **Title-block reading:** numbers split into pieces ("A" + "000"), written with a space ("A 101"), or small in the title-block corner are now read too (3 new tests in `data/sheet-index.test.ts`).
  - **Look:** the label is bold, 12 px; click to edit it as before.
- **Extract Pages… (Revu window, `components/PageToolsDialogs.tsx`):**
  - Page Range, Pages: [Current (n) / Selected (7,8) / All Pages / typed 3-5 or 1,5] of N.
  - Options:
    - Delete pages after extracting: saves a copy of the drawing without them and opens it;
    - Extract pages as separate files, with Use page label to name files (e.g. S-3.01.pdf) and Overwrite existing files (replaces a project drawing of the same name);
    - Open files after extraction: adds them to the project's drawings and opens the first; off = download;
    - Update hyperlinks (links in the pages are kept).
  - The markups on the extracted pages go with them.
- **Delete Pages… (Revu window):** Pages: [Current / Selected / All / typed] of N, OK / Cancel. A new copy of the drawing is saved without those pages and opened; the original stays. A drawing must keep at least one page.
- **Ctrl+C / Ctrl+V markups:**
  - select markups (on the drawing or in the Markups list), Ctrl+C, go to any page, Ctrl+V: they paste on that page in the same position;
  - they are re-measured with that page's scale and selected; a cloud stays grouped with its comment; one undo step.
- **Fixes:**
  - pressing Enter in the page-number box now leaves the box;
  - pressing on the drawing takes the keyboard out of any field, so Ctrl+C / Ctrl+V and tool keys work right after typing a page number;
  - the "n selected" bar moves below the floating properties bar.
- **Check** (`e2e/e2e_u19.cjs`, `e2e/mk_labels.cjs`, `e2e/shots_u19`):
  - a 3-page PDF with only PDF page labels showed A000 / A001 / A002;
  - Ctrl+C on page 7 then Ctrl+V on page 8 added 2 markups on S-3.02 in the same place (7.06 m);
  - the Delete window showed "Current (8) of 34";
  - Extract with Selected (7,8) + separate files + page-label names downloaded S-3.01.pdf and S-3.02.pdf.
  - tsc 96; vitest 720 pass, the same 6 old failures.

## Update 20: copy / paste markups = Shift+Ctrl+C / Shift+Ctrl+V
- Copy markups is **Shift+Ctrl+C** and paste in place is **Shift+Ctrl+V** (Revu). Plain Ctrl+C / Ctrl+V no longer copy markups. The toast after copying names the new keys.
- **Check** (`e2e/e2e_u20.cjs`): Shift+Ctrl+C on page 7, then Shift+Ctrl+V on page 8, pasted 2 markups in the same place. tsc 96.
- **Data cleanup (database only, not part of the code package; done on the user's request, 2026-11-06):**
  - Deleted every project except Luthar (the project of the "martin" bid): "Auto Takeoff QA" with its drawings and markups.
  - Deleted every bid (CRM opportunity) except "martin": 203 removed.
  - CRM leads (82) were kept.
  - Script: `e2e/purge_user_request.py` (dry run unless `--apply`).
  - Full backup taken first: `C:\Users\ishat\Downloads\OE-db-backups\before-delete-2026-11-06.dump`. To restore: `pg_restore -c -h 127.0.0.1 -p <port> -U postgres -d postgres <file>`.

## Update 21: clear thumbnail labels, Ctrl+C / Ctrl+V, Custom pages, Combine, New PDF, text highlight, Select / Pan / Text Select
- **Thumbnail labels:** the page label (S-0.00, A000 …) is a dark pill with white text (light in dark mode), so it stands apart from the white thumbnail. The page number is a badge below it, then the scale.
- **Copy / paste markups:** **Ctrl+C / Ctrl+V** (Shift+Ctrl+C / Shift+Ctrl+V also work); paste lands in the same position on the page on screen.
- **Pages picker** (Extract, Delete): Selected, **Custom…** (clears the box and puts the cursor in it; type 3-5 or 1,5), Current, All Pages.
- **Combine** (toolbar "Combine", File > Combine Files…):
  - pick other drawings of the project and / or PDF files from the computer, order them (up / down / remove), name the result;
  - the open drawing's markups and page scales go with its pages;
  - the result is added to the project's drawings and opened (downloaded when no project is open).
- **New PDF** (toolbar "New", File > New PDF…):
  - Page size Preset (ANSI A–E, Legal, ARCH A–E1, ISO A4–A0) or Custom X × Y in in / mm;
  - Portrait / Landscape; number of pages (1–500); name;
  - creates blank pages, added to the drawings and opened (or downloaded).
- **Highlight on readable text:**
  - a drag over text snaps to the words it covers: one highlight per text line, like a text highlighter;
  - the words are kept in the markup's Text field;
  - on drawings (no text) it stays a rectangle.
- **Bottom bar tools** beside the page number:
  - **Select**;
  - **Pan** (drag moves the sheet);
  - **Text Select** (drag over text: the lines are marked in blue and the text is copied to the clipboard; "No text here" on drawn or scanned areas).
- New files: `components/PdfCreateDialogs.tsx`, `data/text-words.ts` (+ test). `data/pdf-pages.ts` gains `combinePdfs` and `createBlankPdf` (+ test).
- **Check** (`e2e/e2e_u21.cjs`, `e2e/shots_u21`; local Home2 copy, since the QA project was deleted on request):
  - labels clear;
  - Text Select copied 29 words over 4 lines;
  - a highlight drag over 3 text lines gave 3 line highlights;
  - Ctrl+C / Ctrl+V pasted 1;
  - the picker lists Selected / Custom… / Current / All;
  - New PDF custom 24×36 in landscape × 2 → 2 pages of 36"×24";
  - Combine Home2 (34) + a 3-page file → 37 pages.
  - tsc 96; vitest same 6 old failures only.

## Update 22: thumbnail scale pill, close tab top right, New PDF follows the drawing, dimensions in the saved PDF
- **Thumbnail scale:** a pill like the label: green with the scale, or orange "Scale Not Set". Click it to set the scale.
- **Close:** a Chrome-style tab with the drawing's name and a × at the top right of the menu bar. It saves first, then closes. The old "Close PDF" toolbar button was removed (File > Close PDF stays).
- **New PDF follows the open drawing:**
  - the default size is "Same as this drawing (W × H in)", with the orientation taken from it;
  - "Use this drawing's scale on the new pages (1/4" = 1'-0")" is ticked by default; the scale is stored in the new file and applied when it opens.
  - The ERP snapshot can now carry page scales without markups.
- **Dimensions missing in the saved PDF (fixed):**
  - Save PDF wrote Length / Polylength as bare PDF Line / PolyLine annotations with no drawn appearance and no dimension. Viewers that don't draw annotations themselves (Chrome / Edge) showed nothing, and none showed the dimension.
  - Every saved markup now carries its own drawn appearance (/AP: lines, polylines, polygons, clouds as scallops, boxes, ellipses, ink, count dots, callouts / text with arrows), so it looks the same in every viewer.
  - Each measurement gets a visible dimension label, formatted exactly like the sheet caption (e.g. 12'-6", 45.2 sf; Count → "n ea").
  - All of it sits on the "OE Markups" layer, as before.
- **Check** (`e2e/e2e_u22.cjs`, `e2e/shots_u22`):
  - scale pills green / orange; the tab with × closes;
  - New PDF defaulted to "Same as this drawing - 17 x 11 in" + its 1/4" scale, and the new PDF opened at 1/4" = 1'-0";
  - the saved PDF rendered with the Length and Polylength lines and their dimensions (5.08 m / 5.16 m).
  - tsc 96; vitest same 6 old failures.

## Update 23: a markup's own Caption wins (Polylength length not showing)
- **Bug:** a Polylength / Length with Caption "Label, Length" showed only its name. The length was drawn only when two global switches were also on: the toolbar **Values** button and the Colours-tab "dimension" option. With Values off, the length stayed hidden whatever the markup's caption said.
- **Fix:** the markup's own Caption choice wins, as in Revu.
  - Caption "Label, Length" shows the name and length even when Values is off.
  - Caption "Label" shows the name only.
  - Markups left on "Default" still follow the global Values / Names switches.
- **Check** (`e2e/e2e_cap2.cjs`, `e2e/shots_u23`): with Values off, Caption Label only gives "Polyline 1"; Label + Length gives "Polyline 1 / 5.16 m". tsc 96.

## Update 24: label and dimension shown by default on every measurement
- **Rule (user):** every measurement (Length, Polylength, Area, Perimeter, Volume, Count, Diameter, Radius, Angle, Arc, cutouts …) shows its label and dimension by default; the markup's Caption option is how to hide either.
- **Cause:** the toolbar Names / Values switches and the Colours-tab name / dimension switches were remembered in the browser. Once turned off, every later session hid them.
- **Fix:** those switches now start ON every session and only hide labels for that session. A markup's own Caption (update 23) is the lasting per-markup choice.
- **Check** (`e2e/e2e_u24.cjs`, `e2e/shots_u24`): with all four switches stored as "off", Length 3.46 m, Polylength 4.57 m, Area 86.42 sf (P: 11.51 m), Perimeter 9.28 m, Count (2) and Diameter Ø 2.54 m all showed their label and dimension. tsc 96.

## Update 25: area shows the area only, slope in the area, Download PDF button
- **Area caption:** shows only the area (e.g. "Area 1 / 166.7 sf"), on the sheet and in the hover tip. The perimeter is no longer added; it can still be shown per markup through Caption > Perimeter. The stored label format (used by the list and exports) is unchanged.
  - Tests in `takeoff-display-units.test.ts` updated to the new rule.
- **Slope** (Area bar: Pitch rise / run, Degree, or Grade %): already part of the area (plan area × slope factor). It applies to a selected area and to new areas drawn while a slope is set.
  - Checked: 166.7 sf + 30° → 192.5 sf (× 1.155); the list shows Slope 30.0°.
- **Download PDF:** the green toolbar button (formerly "Save PDF") is now called **Download PDF**, with a download icon. It downloads the whole marked-up PDF (markups with dimensions; opens editable again in the ERP). File > Download PDF (with markups) does the same. **Save** (Ctrl+S) keeps saving the work inside the ERP.
- **Check** (`e2e/e2e_u25.cjs`, `e2e/shots_u25`). tsc 96; vitest same 6 old failures.
