# 2026-11-06 pdf-roundtrip

Apply after `2026-11-12-revu-ui`: `python deliveries/2026-11-06-pdf-roundtrip/restore.py` (add `--dry-run` to preview), then reload the page.
- This change is frontend only, so the backend does not need a restart.
- Code is marked `OE-DELIVERY: 2026-11-06-pdf-roundtrip`.

## What the user reported
1. **Download PDF looked different from the ERP:**
   - the length was written sideways, across the line;
   - the name ("Polyline 7", "W12x22") was missing.
2. **Re-uploading a downloaded PDF:** the previous markups could not be edited reliably.

## Causes
1. **Sideways labels on rotated sheets.**
   - The sheets are stored with `/Rotate 270`.
   - The export wrote its text in the page's unrotated direction, so every label turned 90° and sat across its line.
   - It also wrote only the dimension, never the name or material line the ERP draws.
2. **Every markup saved twice.**
   - Ctrl+S, the 3 s auto-save, the close-tab save and the restore of a re-uploaded PDF could each start a save while another was still running.
   - Each one then created the same new markups on the server, so every markup existed twice.
   - The viewer showed one copy. An edit, move or delete changed only that copy, and the stale copy came back on reload.
   - The user's downloaded file already held one markup twice under the same id.
   - Duplicates also double the quantities.

## Fixes
1. **Download PDF draws captions exactly like the ERP** (`pdf-pages.ts`, `TakeoffViewerModule.tsx` `exportCaption`):
   - **Text:** name, material and dimension stacked above the line and turned with it, in the markup colour and caption sizes.
   - **Auto Takeoff lines:** profile above the line, length below it.
   - **Areas:** name above the value at the centroid.
   - **Rotated sheets:** all text, including text boxes and callouts, is laid out in the page's displayed orientation, so it reads upright on any page rotation.
   - **Lines:** widths match the ERP, and polylines get their vertex dots.
2. **One save at a time** (`useMeasurementPersistence.ts`):
   - a save asked for while another runs waits and then runs once;
   - a markup the server already created is stamped with its id, never created again;
   - the same id is never sent twice in one save.
3. **Clean-up of existing duplicates on load:**
   - When a drawing has several server copies of one markup, the most recently updated copy is kept and the stale copies are deleted on the next sync.
4. **Restore from a downloaded PDF** (`takeoff-export.ts` `snapshotToMeasurements`):
   - each markup id is restored once;
   - a different markup sharing an id gets its own id.

## Checks
- **Narrow tsc:** 96, the baseline.
- **vitest** (pdf-takeoff and features/takeoff): 722 pass. The 6 known old failures remain (ledger value sort ×4, wheel zoom ×2). `exports.test.ts` failed once in the full parallel run and passes 16/16 on its own; it is not related to this change.
- **Browser** (`e2e/e2e_roundtrip.cjs`, temporary project, 2-page test PDF rotated 270°), run before and after the fix:
  - **Before:** in one run the re-uploaded drawing had 6 server rows for 3 markups.
  - **After:**
    - five rapid Ctrl+S right after re-upload sent one create (3 rows);
    - a drag on a restored markup saved (PATCH);
    - a reload showed 3 rows.
  - **Picture:** `e2e/erp-vs-download.png`: ERP view on the left, downloaded PDF on the right, labels upright and matching.
- **Duplicate clean-up** (`e2e/e2e_dupclean.cjs`): a seeded stale copy (4 rows, one markup twice) went down to 3 after opening the drawing.
- **Test data:** the temporary test projects were deleted.

## Note
- The yellow "AutoCAD SHX Text" box in the user's download was not an ERP markup. All ERP annotations on that page were polylines and their labels. It comes from the original AutoCAD drawing, which carries hidden SHX-text comments that some PDF viewers show.
