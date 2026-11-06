# OE-DELIVERY 2026-11-04-perf-rerun:
#  - deleting many auto markups at once clears them (a re-run places them again); deleting
#    one on its own still keeps it away; one-click "bring back + re-run" in the run result.
#  - thumbnails rendered straight at their size, stored as JPEG (was 3x + downscale + PNG).
#  - full-page bitmap capped at 10 MP so zooming re-renders far less; the visible-region
#    tile keeps it sharp above that.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:140])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('TakeoffViewerModule.tsx', [
    ("""  const deleteMeasurement = useCallback((id: string) => {""",
     """  const deleteMeasurement = useCallback((id: string, opts?: { reject?: boolean }) => {"""),
    ("""      // A deleted auto markup stays deleted on re-runs (OE-DELIVERY 2026-11-02-auto-takeoff-list).
      if (target.auto) rememberRejectedRef.current([target]);""",
     """      // A deleted auto markup stays deleted on re-runs (OE-DELIVERY 2026-11-02-auto-takeoff-list)
      // - unless it went in a bulk delete, which clears rather than rejects
      // (OE-DELIVERY 2026-11-04-perf-rerun).
      if (target.auto && opts?.reject !== false) rememberRejectedRef.current([target]);"""),
    ("""    for (const id of ids) deleteMeasurement(id);
    setSelectedLedgerIds(new Set());""",
     """    // Deleting many at once ("select all beams, delete") is a clear-out, not
    // "this one is wrong": a re-run places them again. One on its own stays
    // rejected (OE-DELIVERY 2026-11-04-perf-rerun).
    for (const id of ids) deleteMeasurement(id, { reject: ids.length === 1 });
    setSelectedLedgerIds(new Set());"""),
    ("""  const forgetRejected = useCallback(() => {
    setAutoRejected([]);""", """  const forgetRejected = useCallback(() => {
    autoRejectedRef.current = [];
    setAutoRejected([]);"""),
    # thumbnails: render at the stored size, JPEG
    ("""      const scale = computeThumbScale(page.getViewport({ scale: 1 }).width, THUMB_MAX_WIDTH * 3);""",
     """      // Rendered straight at the stored size (2x the display width) - the 3x
      // supersample + downscale cost seconds on big sets (OE-DELIVERY 2026-11-04-perf-rerun).
      const scale = computeThumbScale(page.getViewport({ scale: 1 }).width, THUMB_MAX_WIDTH * 2);"""),
    ("""      const url = downscaleCanvas(off, THUMB_MAX_WIDTH * 2).toDataURL('image/png');""",
     """      const url = off.toDataURL('image/jpeg', 0.86);"""),
    ("""      const url = downscaleCanvas(main, Math.max(1, THUMB_MAX_WIDTH * 2)).toDataURL('image/png');""",
     """      const url = downscaleCanvas(main, Math.max(1, THUMB_MAX_WIDTH * 2)).toDataURL('image/jpeg', 0.86);"""),
])

patch('data/deep-zoom.ts', [
    ("""export const MAX_BITMAP_SIDE = 8192;
export const MAX_BITMAP_PIXELS = 16_000_000;""", """// 10 MP keeps a full-page re-render after a zoom quick; above it the
// visible-region tile keeps the drawing sharp (OE-DELIVERY 2026-11-04-perf-rerun).
export const MAX_BITMAP_SIDE = 6144;
export const MAX_BITMAP_PIXELS = 10_000_000;"""),
])

patch('AutoTakeoffPanel.tsx', [
    ("""          {last.res.read && (""", """          {last.summary.rejected > 0 && (
            <p className="text-content-secondary" data-testid="auto-rejected-note">
              {last.summary.rejected} were skipped because you deleted them earlier.{' '}
              <button
                type="button"
                className="font-semibold text-oe-blue underline"
                onClick={() => {
                  onForgetRejected();
                  void run();
                }}
                data-testid="auto-bring-back"
              >
                Bring them back and re-run
              </button>
            </p>
          )}
          {last.res.read && ("""),
])
print('ok')
