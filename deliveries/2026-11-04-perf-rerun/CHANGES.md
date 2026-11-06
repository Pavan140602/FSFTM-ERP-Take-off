# 2026-11-04 (part 2): Re-running after deleting, opening speed, zoom speed

Apply after `2026-11-04-members-labels-workarea`. The code changes are marked `OE-DELIVERY 2026-11-04-perf-rerun`.

## Delete all beams, re-run, nothing came back

- **Cause:** deleting several markups at once recorded each one as "deleted by you". Re-runs never put back a markup you deleted, a rule meant for removing a single wrong detection.
- **Fix:**
  - Deleting several at once now clears them, and a re-run places them again.
  - Deleting one markup on its own still keeps that one away.
  - When a re-run skips markups you deleted before, the result says so, with a "Bring them back and re-run" button.
- **New:** a "Select all" button on each category in Detected markups (e.g. all beams on the sheet).
- **Browser check:** Select all beams → 58 selected → Delete → 0 → Re-run → 58 placed again → Select all → 58 selected.

## Opening a drawing (61-page set, 8 MB)

- **Thumbnails:**
  - Rendered straight at their final size and stored as JPEG. Before, they were drawn at 3× size, then shrunk and saved as PNG.
  - Only thumbnails on or near the screen are rendered.
  - They render only when the browser is idle, and pause while you zoom, pan or draw.
- **Main-thread freezes during opening:** about 10.2 s before, about 7.8 s now. Most of what remains is pdf.js shrinking the large raster images embedded in this set.
- **Note on measured times:** these come from the development server, which loads the app as many small files. A production build opens noticeably faster.

## Zooming

- **Bitmap cap:** the full-page bitmap is now capped at 10 megapixels (was 16). The visible-area tile keeps it sharp above that.
- **Re-render after zoom:** about 0.2 s before, 0.01–0.14 s now.
- **Sharp tile at deep zoom (~750%):** appears in about 0.1 s.
- **Freezes during zoom:** about 5 s before, about 0.15 s now.

## Checks

- Typecheck: no new errors.
- Frontend tests: 741 pass; the 6 failures are older.
