# 2026-11-04 (part 3): Page keys, fast zoomed page changes, precise member ends

Apply after `2026-11-04-perf-rerun`. The code changes are marked `OE-DELIVERY 2026-11-04-page-flip` and `2026-11-04-snap-ends`.

## Changing pages

- **Up arrow:** next page. **Down arrow:** previous page. These apply when nothing is selected; with markups selected, the arrows still nudge them.
- **Ctrl + mouse wheel:** wheel up goes to the next page, wheel down to the previous one, one page per notch. A trackpad pinch (also reported as Ctrl + wheel, but with small steps) still zooms.
- **Ctrl + wheel over the toolbar and panels** pages through the set too, instead of zooming the browser.

## Changing pages while zoomed in

- **Page cache:** the last 4 page bitmaps are kept. A page you have already seen comes back instantly, sharp at the current zoom.
- **Background pre-render:** the next and previous pages are rendered ahead when the browser is idle. This pauses while you zoom, pan or draw.
- **No duplicate render:** a page change waits for a render already in progress instead of starting a second one.
- **Instant preview:** a page that isn't ready shows its thumbnail straight away, then sharpens.
- **Measured** on the 61-page set at 300%, development server:

  | Situation | Time to sharp page |
  |---|---|
  | Before | 6–8.6 s |
  | Next page rendered ahead | 0.15 s |
  | Other pages | about 0.9 s |
  | Next page not rendered ahead yet (no idle time) | about 2.9 s |

## Auto Takeoff: precise member ends

- Each beam, joist or truss end is moved, along its own line only, onto the exact column center or the framing line it stops at. Lengths now read center to center and the line stays straight.
- **Limits:** a column must sit on the member's line within 4.5 units and within 16 of the end; a framing line must be within 10 of the end. Nearly parallel lines are ignored. A member is never shortened below half its length. Generated series lines are left alone.
- **QA sheet:** 16 beam ends now sit exactly on column centers; the rest end exactly on the girders they frame into.

## Checks

- Typecheck: no new errors.
- Frontend tests: 661 pass; the 6 failures are older.
- Backend Auto Takeoff tests: 17 pass (new: end snapping).
- Browser: Up / Down and Ctrl + wheel up / down go to the next and previous pages, and zoomed page changes were timed as above.
