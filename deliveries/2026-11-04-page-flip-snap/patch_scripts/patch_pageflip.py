# OE-DELIVERY 2026-11-04-page-flip: Up = next page, Down = previous; Ctrl + wheel notch up =
# next page, down = previous (pinch still zooms); zoomed page flips are instant from a page
# cache with the neighbours rendered ahead in the background.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:160])
        sys.exit(1)
    s = s.replace(old, new)


# ── keyboard: Up / Down page through the set when nothing is selected ──
rep("""        if (targetIds.size > 0) {
          e.preventDefault();
          const step = e.shiftKey ? 10 : 1;
          const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
          const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
          nudgeMeasurements(targetIds, dx, dy);
          return;
        }""", """        if (targetIds.size > 0) {
          e.preventDefault();
          const step = e.shiftKey ? 10 : 1;
          const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
          const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
          nudgeMeasurements(targetIds, dx, dy);
          return;
        }
        // Nothing selected: Up = next page, Down = previous page
        // (OE-DELIVERY 2026-11-04-page-flip).
        if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && !e.shiftKey) {
          e.preventDefault();
          flipPageRef.current(e.key === 'ArrowUp' ? 1 : -1);
          return;
        }""")

# ── wheel: Ctrl + mouse-wheel notch flips pages; pinch (small ctrl deltas) zooms ──
rep("""    const handleWheel = (e: WheelEvent) => {
      // Single-page mode: the wheel always zooms (there is nothing to""", """    const handleWheel = (e: WheelEvent) => {
      // Ctrl + mouse wheel: notch up = next page, notch down = previous page
      // (OE-DELIVERY 2026-11-04-page-flip). A trackpad pinch also reports
      // ctrlKey but with small pixel deltas - that keeps zooming.
      if ((e.ctrlKey || e.metaKey) && isWheelNotch(e)) {
        e.preventDefault();
        e.stopPropagation();
        flipPageRef.current(e.deltaY < 0 ? 1 : -1, true);
        return;
      }
      // Single-page mode: the wheel always zooms (there is nothing to""")
rep("""    const handleRootWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      const container = containerRef.current;
      if (!container) return;
      e.preventDefault();""", """    const handleRootWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      const container = containerRef.current;
      if (!container) return;
      e.preventDefault();
      if (isWheelNotch(e)) {
        flipPageRef.current(e.deltaY < 0 ? 1 : -1, true);
        return;
      }""")
rep("""  /* ── Page navigation ─────────────────────────────────────────────── */

  /** Mirror of totalPages for callbacks that must not re-subscribe. */""", """  /* ── Page navigation ─────────────────────────────────────────────── */

  /** Next / previous page from the keyboard or Ctrl + wheel; wheel flips are
   *  spaced so one notch = one page (OE-DELIVERY 2026-11-04-page-flip). */
  const lastFlipRef = useRef(0);
  const flipPageRef = useRef<(dir: 1 | -1, fromWheel?: boolean) => void>(() => {});
  flipPageRef.current = (dir, fromWheel = false) => {
    const now = Date.now();
    if (fromWheel && now - lastFlipRef.current < 220) return;
    lastFlipRef.current = now;
    const tp = totalPagesRef.current || 1;
    const cp = currentPageRef.current || 1;
    const next = Math.max(1, Math.min(tp, cp + dir));
    if (next !== cp) goToPage(next);
  };

  /** Mirror of totalPages for callbacks that must not re-subscribe. */""")

# helper (module scope)
rep("""function downscaleCanvas(src: HTMLCanvasElement, targetW: number): HTMLCanvasElement {""",
    """/** A mouse-wheel notch (not a trackpad pinch / glide) - OE-DELIVERY 2026-11-04-page-flip. */
function isWheelNotch(e: WheelEvent): boolean {
  return e.deltaMode !== 0 || Math.abs(e.deltaY) >= 50;
}

function downscaleCanvas(src: HTMLCanvasElement, targetW: number): HTMLCanvasElement {""")

# ── page bitmap cache + neighbour pre-render ──
rep("""  /** The main canvas's in-flight render, so the next one waits for it. */
  const mainRenderTaskRef = useRef<Promise<void> | null>(null);""", """  /** The main canvas's in-flight render, so the next one waits for it. */
  const mainRenderTaskRef = useRef<Promise<void> | null>(null);
  /* Page bitmap cache (OE-DELIVERY 2026-11-04-page-flip): the last few page
   * bitmaps, so flipping pages while zoomed in shows the drawing at once; the
   * next and previous pages are rendered ahead while the user is idle. */
  const pageCacheRef = useRef<Map<number, { bz: number; lw: boolean; canvas: HTMLCanvasElement }>>(new Map());
  const PAGE_CACHE_MAX = 4;
  const cachePut = (n: number, entry: { bz: number; lw: boolean; canvas: HTMLCanvasElement }) => {
    const m = pageCacheRef.current;
    m.delete(n);
    m.set(n, entry);
    while (m.size > PAGE_CACHE_MAX) {
      const oldest = m.keys().next().value as number;
      if (oldest === currentPageRef.current) {
        const e = m.get(oldest)!;
        m.delete(oldest);
        m.set(oldest, e);
        if (m.size <= PAGE_CACHE_MAX) break;
        continue;
      }
      m.delete(oldest);
    }
  };
  useEffect(() => {
    pageCacheRef.current = new Map();
  }, [pdfDoc]);
  const prefetchTokenRef = useRef(0);
  const prefetchNeighbours = (doc: PDFDocumentProxy, page: number, zoomWanted: number, lw: boolean) => {
    const token = ++prefetchTokenRef.current;
    const tp = totalPagesRef.current || 1;
    const order = [page + 1, page - 1].filter((n) => n >= 1 && n <= tp);
    (async () => {
      for (const n of order) {
        // Wait for a quiet moment: never compete with zooming / panning / drawing.
        for (let w = 0; w < 100 && Date.now() - lastInteractRef.current < 900; w++) {
          await new Promise<void>((r) => setTimeout(r, 150));
          if (token !== prefetchTokenRef.current) return;
        }
        await new Promise<void>((r) => {
          const ric = (window as unknown as { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number }).requestIdleCallback;
          if (ric) ric(() => r(), { timeout: 800 });
          else setTimeout(r, 80);
        });
        if (token !== prefetchTokenRef.current || pdfDocRef.current !== doc) return;
        try {
          const pg = await doc.getPage(n);
          const dpr = window.devicePixelRatio || 1;
          const u = pg.getViewport({ scale: 1 });
          const bz = Math.min(zoomWanted, bitmapZoomCap(u.width, u.height, dpr));
          const have = pageCacheRef.current.get(n);
          if (have && have.bz >= bz - 1e-6 && have.lw === lw) continue;
          const vp = pg.getViewport({ scale: bz * dpr });
          const off = document.createElement('canvas');
          off.width = Math.round(vp.width);
          off.height = Math.round(vp.height);
          await pg.render({ canvas: hairlineCanvas(off, bz * dpr), viewport: vp }).promise;
          if (token !== prefetchTokenRef.current || pdfDocRef.current !== doc) return;
          cachePut(n, { bz, lw, canvas: off });
        } catch {
          /* a bad page or a superseded prefetch: skip it */
        }
      }
    })();
  };""")

rep("""        const task = page.render({ canvas: hairlineCanvas(canvas, bz * dpr), viewport });
        activeTask = task;
        mainRenderTaskRef.current = task.promise.then(() => undefined, () => undefined);
        await task.promise;
        if (cancelled) return;
        // The overlay is sized by its own effect; bump a nonce so the draw""", """        // Page cache (OE-DELIVERY 2026-11-04-page-flip): paint the cached bitmap
        // straight away (scaled if it was rendered at another zoom), then
        // render sharp off-screen only when the cache is not good enough.
        const ctxMain = canvas.getContext('2d');
        const cached = pageCacheRef.current.get(currentPage);
        if (cached && ctxMain) {
          ctxMain.drawImage(cached.canvas, 0, 0, canvas.width, canvas.height);
          mainRenderedPageRef.current = currentPage;
        }
        if (!cached || cached.bz < bz - 1e-6 || cached.lw !== lineWeightsOff) {
          const off = document.createElement('canvas');
          off.width = canvas.width;
          off.height = canvas.height;
          const task = page.render({ canvas: hairlineCanvas(off, bz * dpr), viewport });
          activeTask = task;
          mainRenderTaskRef.current = task.promise.then(() => undefined, () => undefined);
          await task.promise;
          if (cancelled) return;
          if (ctxMain) {
            ctxMain.clearRect(0, 0, canvas.width, canvas.height);
            ctxMain.drawImage(off, 0, 0);
          }
          cachePut(currentPage, { bz, lw: lineWeightsOff, canvas: off });
        } else {
          cachePut(currentPage, cached);
        }
        canvas.dataset.renderedPage = String(currentPage);
        prefetchNeighbours(pdfDoc, currentPage, rz, lineWeightsOff);
        // The overlay is sized by its own effect; bump a nonce so the draw""")
P.write_text(s, encoding='utf-8')
print('ok')
