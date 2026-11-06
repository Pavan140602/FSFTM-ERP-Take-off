# 2026-11-07: Revu-style Text Box

Apply after `2026-11-07-column-shapes`. Restore with `python deliveries/2026-11-07-text-box/restore.py` (add `--dry-run` to preview), then reload the browser. This change is frontend only; no backend restart is needed for it.

## How it works (like Bluebeam Revu's Text Box)

**Draw**
- Text Box tool (**T**): **press and drag** to draw the box. A dashed outline shows the size as you drag.
- A plain click still opens a box of the default width.

**Type**
- The editor sits on the box and looks exactly like the finished box: same font, size, colours, fill, border and alignment.
- **Enter** starts a new line.
- **Ctrl+Enter**, **Esc** or a click outside finishes the box.
- **Ctrl+B / Ctrl+I / Ctrl+U** toggle bold, italic and underline.

**Text Box properties bar** (floats above the box while typing and when it is selected):
- **Font**: Arial, Helvetica, Calibri, Verdana, Tahoma, Times New Roman, Georgia, Courier New, Consolas.
- **Size**: in pt, typed or picked (6–72).
- **Style**: bold, italic, underline, strike-through.
- **Alignment**: left, centre, right.
- **Text colour**.
- **Fill**: colour or none, with fill opacity.
- **Border**: colour or none, width 0.5–6 pt, style solid, dashed, dotted or **cloud**.
- **Opacity** of the whole box.

**Edit and restyle**
- Double-click a box with the Select tool to edit its text.
- Select one or more text boxes (Ctrl+click / Shift+click) and use the bar to restyle them all.
- The corner handle resizes width and height. The height never goes below what the text needs.

**Defaults**
- With the Text Box tool active and nothing selected, the bar sets the look of **new** boxes ("New text boxes:").
- The last look you set is remembered as the tool default, like Revu.
- Text boxes made before this delivery keep their old bold-14 look until you restyle them.

**Saving and export**
- The look is saved with the markup on the server (`metadata.text_style`).
- A restyle or resize now re-saves. Before, a text box's size was not part of the change check.
- **Export PDF with markups** draws text boxes exactly as on screen: wrapped, with fill, border and font. Before, it wrote one line in bold 14.
- The top Properties bar no longer shows caption Font/Size/B/I/U for text boxes. Those controls set measurement captions; a text box is styled from its own bar.

## Files
- `frontend/src/modules/pdf-takeoff/data/text-box.ts` (new): style, wrapping, layout, drawing. Tests are in `text-box.test.ts`.
- `frontend/src/modules/pdf-takeoff/components/TextFormatBar.tsx` (new): the properties bar.
- `frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx`:
  - drag to draw;
  - editor styled like the box;
  - bar for the tool default, editing and selection;
  - styled canvas draw;
  - width and height resize;
  - Ctrl+B/I/U, Enter and Esc behaviour;
  - hint text.
- `frontend/src/modules/pdf-takeoff/useMeasurementPersistence.ts`: `text_style` saved and loaded; style and size in the change check.
- `frontend/src/features/takeoff/lib/takeoff-types.ts`: `textStyle` field.
- `frontend/src/features/takeoff/lib/takeoff-export.ts`: PDF export of styled boxes.
- `frontend/src/modules/pdf-takeoff/components/RevuPropertiesBar.tsx`: caption font controls hidden for text boxes.

## Checks
- **Unit tests:** text-box 5 pass. The takeoff suites run 574 pass and 6 fail; those 6 are the same old failures (value sort, wheel zoom) and are unrelated.
- **Narrow tsc:** no new errors.
- **In the running app** (Vite dev server, QA project "Auto Takeoff QA", sheet S4.01a), scripts in `e2e/`:
  - Pressing T showed the "New text boxes" bar.
  - Dragging a box showed the dashed outline and opened a 300 px editor.
  - Typed two lines, then set bold, centre and a yellow fill from the bar while typing; the editor kept focus.
  - Ctrl+Enter placed the box.
  - Selecting the box showed the bar; choosing "Cloud" redrew the border as a cloud.
  - After the auto-save, reopening with the browser storage cleared loaded the box back from the server with the same look. Screenshots: `t2-editing.png`, `t4-selected-cloud.png`, `r1-reloaded.png`.
- The QA drawing now has one test text box ("Revu text box test"). Delete it if you like.
