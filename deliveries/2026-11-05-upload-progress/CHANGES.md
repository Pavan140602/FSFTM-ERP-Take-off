# 2026-11-05 (part 2): Upload progress bar

Apply after `2026-11-05-framing-rules`. Code is marked `OE-DELIVERY 2026-11-05-upload-progress`. Restore with `python deliveries/2026-11-05-upload-progress/restore.py` (try `--dry-run` first). Frontend only, so no backend restart is needed.

## What changed

- **Progress bar on uploads:** while a drawing uploads, its card in "Current & recent drawings" (and in the Documents tab) shows a progress bar, e.g. `42% · 12.4 / 30.1 MB · 9 s left`.
- **Time left:** worked out from the average speed so far. It shows "estimating time…" for the first moment and updates every second.
- **Reading phase:** once every byte is sent, the bar pulses with "Uploaded · reading drawing…" while the server opens the PDF. The card then turns into the normal drawing card.
- **How:** the upload now goes through XMLHttpRequest, because `fetch` cannot report upload progress.
- **Unchanged:** server error messages (e.g. "This PDF is password-protected") still show as before, and the project the drawing is saved under is the same.

## Files

- `frontend/src/features/takeoff/lib/upload-progress.ts` (new): `xhrUpload`, `uploadStats`, `formatTimeLeft`.
- `frontend/src/features/takeoff/components/UploadProgressBar.tsx` (new).
- `frontend/src/features/takeoff/TakeoffPage.tsx`: the upload mutation and both document cards.
- `frontend/src/features/takeoff/__tests__/upload-progress.test.ts` (new).

## Checks

- **Typecheck:** no new errors; the same 112 older errors remain.
- **Frontend tests:** 665 pass, including the 4 new upload-progress tests. The 6 failures are older (wheelZoomStep ×2, ledger value sort ×4).
- **Not done:** the backend was not running, so the browser upload test was not run.
