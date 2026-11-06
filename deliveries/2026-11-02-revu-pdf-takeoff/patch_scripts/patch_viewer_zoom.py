"""Revu-style zoom for TakeoffViewerModule (anchored, all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-zoom"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-zoom'
pairs = [
# ── imports ──────────────────────────────────────────────────────────
("""  clampZoom,
""", """  clampZoom,
  CONTINUOUS_ZOOM_MAX,
"""),
("""import {
  SKETCH_TOOLS,""", """// Deep zoom + Zoom tool (""" + TAG + """).
import {
  bitmapZoomCap,
  needsRegionRendering,
  visibleRegion,
  sameRegion,
  zoomToBox,
  ZOOM_TOOL_STEP,
  type Region,
} from './data/deep-zoom';
import {
  SKETCH_TOOLS,"""),

# ── refs ─────────────────────────────────────────────────────────────
("""  const zoomWrapRef = useRef<HTMLDivElement>(null);
""", """  const zoomWrapRef = useRef<HTMLDivElement>(null);
  /* Deep zoom (""" + TAG + """): page size in PDF units
   * (set by the page render, independent of the bitmap's capped zoom), the
   * zoom the page bitmap was actually rendered at, and the visible-region
   * canvases used above the full-page bitmap limit. */
  const pageSizePdfRef = useRef<{ page: number; w: number; h: number } | null>(null);
  const baseZoomRef = useRef(1);
  const deepModeRef = useRef(false);
  const deepRegionRef = useRef<Region | null>(null);
  const deepCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const detailCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const detailOffRef = useRef<HTMLCanvasElement | null>(null);
  const [regionNonce, setRegionNonce] = useState(0);
"""),
("""  const zoomAreaRef = useRef<{ start: Point; current: Point } | null>(null);
""", """  // ``out``: Alt/Shift press of the Zoom tool zooms out (""" + TAG + """).
  const zoomAreaRef = useRef<{ start: Point; current: Point; out?: boolean } | null>(null);
  const zoomAreaArmedRef = useRef(zoomAreaArmed);
  zoomAreaArmedRef.current = zoomAreaArmed;
"""),

# ── zoomTo: continuous mode keeps the old 400% ceiling ───────────────
("""    const target = clampZoom(nextZoom);""",
 """    // Continuous mode keeps one full canvas per page, so it stays at 400%;
    // single-page mode goes to 6400% via deep zoom (""" + TAG + """).
    const target = pageModeRef.current === 'continuous'
      ? Math.min(CONTINUOUS_ZOOM_MAX, clampZoom(nextZoom))
      : clampZoom(nextZoom);"""),

# ── main page render: capped bitmap ──────────────────────────────────
("""        const rz = renderZoomRef.current || zoom;
        // Bitmap renders at the settled (debounced) zoom for crispness;
        // the element CSS-scales with the LIVE zoom so the page tracks a
        // zoom gesture smoothly while the bitmap catches up.
        const viewport = page.getViewport({ scale: rz * dpr });
        const canvas = canvasRef.current!;

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const liveScale = rz > 0 ? zoom / rz : 1;""",
 """        const rz = renderZoomRef.current || zoom;
        // Bitmap renders at the settled (debounced) zoom for crispness;
        // the element CSS-scales with the LIVE zoom so the page tracks a
        // zoom gesture smoothly while the bitmap catches up.
        // Deep zoom (""" + TAG + """): the full-page bitmap
        // never exceeds the canvas limits; above that the detail canvas
        // renders the visible region sharp.
        const unitVp = page.getViewport({ scale: 1 });
        pageSizePdfRef.current = { page: currentPage, w: unitVp.width, h: unitVp.height };
        const bz = Math.min(rz, bitmapZoomCap(unitVp.width, unitVp.height, dpr));
        baseZoomRef.current = bz;
        const viewport = page.getViewport({ scale: bz * dpr });
        const canvas = canvasRef.current!;

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const liveScale = bz > 0 ? zoom / bz : 1;"""),
("""        const task = page.render({ canvas: hairlineCanvas(canvas, rz * dpr), viewport });""",
 """        const task = page.render({ canvas: hairlineCanvas(canvas, bz * dpr), viewport });"""),
("""        mainRenderedPageRef.current = currentPage;
        setRenderNonce((n) => n + 1);""", """        mainRenderedPageRef.current = currentPage;
        setRenderNonce((n) => n + 1);
        setRegionNonce((n) => n + 1);"""),
]

# The live-follow and overlay-sizing effects both derive the page size from
# the bitmap; with a capped bitmap that is wrong, so read the stored size.
OLD_SIZE = """    const rz = renderZoomRef.current || zoom;
    if (!(rz > 0) || canvas.width === 0) return;
    const pageW = canvas.width / (rz * dpr);
    const pageH = canvas.height / (rz * dpr);"""
NEW_SIZE = """    // Page size in PDF units from the render, not the (possibly capped)
    // bitmap (""" + TAG + """).
    const pageSz = pageSizePdfRef.current;
    if (!pageSz || pageSz.page !== currentPage || canvas.width === 0) return;
    const pageW = pageSz.w;
    const pageH = pageSz.h;"""

pairs += [
# overlay sizing: deep mode keeps a 1x1 bitmap, draws into the region canvas
("""    const w = Math.max(1, Math.round(pageW * zoom * dpr));
    const h = Math.max(1, Math.round(pageH * zoom * dpr));
    if (overlay.width !== w || overlay.height !== h) {
      overlay.width = w;
      overlay.height = h;
      setRenderNonce((n) => n + 1);
    }""", """    // Deep zoom (""" + TAG + """): above the bitmap limit the
    // full-size overlay keeps taking pointer events (so every pointer->PDF
    // mapping is unchanged) with a 1x1 bitmap; markups draw into the
    // visible-region canvas instead.
    const deep = needsRegionRendering(pageW, pageH, zoom, dpr);
    deepModeRef.current = deep;
    const w = deep ? 1 : Math.max(1, Math.round(pageW * zoom * dpr));
    const h = deep ? 1 : Math.max(1, Math.round(pageH * zoom * dpr));
    if (overlay.width !== w || overlay.height !== h) {
      overlay.width = w;
      overlay.height = h;
      setRenderNonce((n) => n + 1);
    }
    requestAnimationFrame(() => updateDeepRegionRef.current());"""),

# ── draw effect: pick the target canvas ──────────────────────────────
("""    if (!overlayRef.current) return;
    const ctx = overlayRef.current.getContext('2d')!;
    const dpr = window.devicePixelRatio;
    ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
""", """    if (!overlayRef.current) return;
    const dpr = window.devicePixelRatio;
    // Deep zoom (""" + TAG + """): draw into the visible-region
    // canvas, shifted so all the page-space maths below is unchanged.
    const deepRegion = deepModeRef.current ? deepRegionRef.current : null;
    const deepCanvas = deepCanvasRef.current;
    let ctx: CanvasRenderingContext2D;
    if (deepRegion && deepCanvas) {
      overlayRef.current.getContext('2d')!.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
      ctx = deepCanvas.getContext('2d')!;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, deepCanvas.width, deepCanvas.height);
      ctx.setTransform(1, 0, 0, 1, -deepRegion.x * dpr, -deepRegion.y * dpr);
    } else {
      ctx = overlayRef.current.getContext('2d')!;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
    }
"""),
# the zoom box was only drawn while a selection marquee existed
("""    if (activeTool === 'select' && (selectedLedgerIds.size > 0 || marqueeRect)) {""",
 """    // The zoom box draws in every tool, not only alongside a selection
    // marquee (""" + TAG + """).
    if ((activeTool === 'select' && (selectedLedgerIds.size > 0 || marqueeRect)) || zoomAreaRect) {"""),

# ── deep region tracking + PDF detail render (after the Esc-less helper) ─
("""  /** Zoom-to-area mouseup: fit the dragged rectangle to the viewport. */
  const finishZoomArea = useCallback(() => {
    const zr = zoomAreaRef.current;
    zoomAreaRef.current = null;
    setZoomAreaRect(null);
    setZoomAreaArmed(false);
    if (!zr) return;
    const x0 = Math.min(zr.start.x, zr.current.x);
    const x1 = Math.max(zr.start.x, zr.current.x);
    const y0 = Math.min(zr.start.y, zr.current.y);
    const y1 = Math.max(zr.start.y, zr.current.y);
    const rw = x1 - x0;
    const rh = y1 - y0;
    // Too small = accidental click, ignore.
    if (rw < 8 || rh < 8) return;
    const container = containerRef.current;
    if (!container) return;
    const vw = container.clientWidth;
    const vh = container.clientHeight;
    if (vw <= 0 || vh <= 0) return;
    const curZoom = zoomRef.current || 1;
    // Rect size in screen px at current zoom.
    const rwPx = rw * curZoom;
    const rhPx = rh * curZoom;
    const fit = Math.min(vw / rwPx, vh / rhPx);
    // Clamp the resulting zoom to sane limits.
    const nextZoom = Math.min(8, Math.max(0.25, curZoom * fit));
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    // Apply zoom, then center the rect on the next frame (after layout).
    zoomToRef.current(nextZoom);
    requestAnimationFrame(() => {
      const c = containerRef.current;
      if (!c) return;
      c.scrollLeft = Math.max(0, cx * nextZoom - c.clientWidth / 2);
      c.scrollTop = Math.max(0, cy * nextZoom - c.clientHeight / 2);
    });
  }, []);""", """  /** Revu Zoom tool release (""" + TAG + """):
   *  a click zooms in (Alt/Shift: out) by one step around the point; a drag
   *  fits the box to the viewport and centres it. The tool stays armed, as in
   *  Revu, until Z / Esc / another tool. The old version clamped to 800%,
   *  ignored the page's offset inside the scroll area (so it landed off
   *  target) and disarmed after one use. */
  const finishZoomArea = useCallback(() => {
    const zr = zoomAreaRef.current;
    zoomAreaRef.current = null;
    setZoomAreaRect(null);
    if (!zr) return;
    const container = containerRef.current;
    const ov = overlayRef.current;
    if (!container || !ov) return;
    const curZoom = zoomRef.current || 1;
    const x0 = Math.min(zr.start.x, zr.current.x);
    const x1 = Math.max(zr.start.x, zr.current.x);
    const y0 = Math.min(zr.start.y, zr.current.y);
    const y1 = Math.max(zr.start.y, zr.current.y);
    // A press that barely moved is a click: step zoom around that point.
    if ((x1 - x0) * curZoom < 6 && (y1 - y0) * curZoom < 6) {
      const r = ov.getBoundingClientRect();
      const factor = zr.out ? 1 / ZOOM_TOOL_STEP : ZOOM_TOOL_STEP;
      zoomToRef.current(curZoom * factor, {
        x: r.left + zr.start.x * curZoom,
        y: r.top + zr.start.y * curZoom,
      });
      return;
    }
    const fit = zoomToBox({ x0, y0, x1, y1 }, container.clientWidth, container.clientHeight);
    if (!fit) return;
    zoomToRef.current(fit.zoom);
    // Centre on the box once the new size is laid out, measuring where the
    // page element really is (flex centering + pan translate included).
    const centre = () => {
      const c = containerRef.current;
      const o = overlayRef.current;
      if (!c || !o) return;
      const z = zoomRef.current || 1;
      const cr = c.getBoundingClientRect();
      const orr = o.getBoundingClientRect();
      c.scrollLeft += orr.left + fit.cx * z - (cr.left + c.clientLeft + c.clientWidth / 2);
      c.scrollTop += orr.top + fit.cy * z - (cr.top + c.clientTop + c.clientHeight / 2);
    };
    requestAnimationFrame(() => requestAnimationFrame(() => {
      centre();
      // Once more after the crisp re-render settles the element size.
      window.setTimeout(centre, 220);
    }));
  }, []);

  /** Recompute the visible part of the page for deep zoom and resize the
   *  region canvas over it (""" + TAG + """). */
  const updateDeepRegion = useCallback(() => {
    const ov = overlayRef.current;
    const c = containerRef.current;
    const dc = deepCanvasRef.current;
    if (!ov || !c || !dc) return;
    const cr = c.getBoundingClientRect();
    const region = deepModeRef.current
      ? visibleRegion(
          { left: cr.left + c.clientLeft, top: cr.top + c.clientTop, width: c.clientWidth, height: c.clientHeight },
          ov.getBoundingClientRect(),
        )
      : null;
    if (sameRegion(region, deepRegionRef.current)) return;
    deepRegionRef.current = region;
    if (!region) {
      dc.style.display = 'none';
    } else {
      const dpr = window.devicePixelRatio || 1;
      dc.width = Math.max(1, Math.round(region.w * dpr));
      dc.height = Math.max(1, Math.round(region.h * dpr));
      dc.style.left = `${region.x}px`;
      dc.style.top = `${ov.offsetTop + region.y}px`;
      dc.style.width = `${region.w}px`;
      dc.style.height = `${region.h}px`;
      dc.style.display = 'block';
    }
    setRenderNonce((n) => n + 1);
    setRegionNonce((n) => n + 1);
  }, []);
  const updateDeepRegionRef = useRef(updateDeepRegion);
  updateDeepRegionRef.current = updateDeepRegion;

  // Scrolling / resizing changes what is visible.
  useEffect(() => {
    const c = containerRef.current;
    if (!c) return;
    let raf = 0;
    const onMove = () => {
      if (!deepModeRef.current && !deepRegionRef.current) return;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        updateDeepRegionRef.current();
      });
    };
    c.addEventListener('scroll', onMove, { passive: true });
    window.addEventListener('resize', onMove);
    return () => {
      c.removeEventListener('scroll', onMove);
      window.removeEventListener('resize', onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [pdfDoc]);
  useEffect(() => {
    // Continuous mode has no deep zoom (it caps at 400%).
    if (pageMode !== 'single') deepModeRef.current = false;
    requestAnimationFrame(() => updateDeepRegionRef.current());
  }, [panOffset, currentPage, pageMode]);

  /* Sharp PDF tile for the visible region when the page bitmap is capped
   * (""" + TAG + """). Rendered off-screen, then blitted,
   * so the old tile never flashes; hidden during a live zoom gesture. */
  useEffect(() => {
    const dc = detailCanvasRef.current;
    if (!dc) return;
    const rz = renderZoom;
    const region = deepRegionRef.current;
    if (
      !pdfDoc ||
      pageMode !== 'single' ||
      zoom !== rz ||
      !(rz > baseZoomRef.current + 1e-9) ||
      mainRenderedPageRef.current !== currentPage ||
      !region
    ) {
      dc.style.display = 'none';
      return;
    }
    let cancelled = false;
    let task: { cancel: () => void } | null = null;
    const timer = window.setTimeout(async () => {
      try {
        const page = await pdfDoc.getPage(currentPage);
        if (cancelled) return;
        const dpr = window.devicePixelRatio || 1;
        const vp = page.getViewport({ scale: rz * dpr });
        const off = detailOffRef.current ?? (detailOffRef.current = document.createElement('canvas'));
        off.width = Math.max(1, Math.round(region.w * dpr));
        off.height = Math.max(1, Math.round(region.h * dpr));
        const t2 = page.render({
          canvas: hairlineCanvas(off, rz * dpr),
          viewport: vp,
          transform: [1, 0, 0, 1, -region.x * dpr, -region.y * dpr],
        });
        task = t2;
        await t2.promise;
        if (cancelled) return;
        dc.width = off.width;
        dc.height = off.height;
        dc.getContext('2d')!.drawImage(off, 0, 0);
        dc.style.left = `${region.x}px`;
        dc.style.top = `${region.y}px`;
        dc.style.width = `${region.w}px`;
        dc.style.height = `${region.h}px`;
        dc.style.display = 'block';
      } catch {
        /* superseded / cancelled render: the next region or zoom replaces it */
      }
    }, 120);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      try { task?.cancel(); } catch { /* ignore */ }
    };
  }, [pdfDoc, pageMode, currentPage, zoom, renderZoom, regionNonce, lineWeightsOff]);

  // Picking a tool leaves the Zoom tool, as in Revu.
  useEffect(() => {
    setZoomAreaArmed(false);
  }, [activeTool]);"""),

# ── mousedown: Zoom tool owns the left press in every tool ──────────
("""      if (viewportDraftRef.current && e.button === 0) return;
""", """      if (viewportDraftRef.current && e.button === 0) return;
      // Revu Zoom tool (""" + TAG + """): works on top of any
      // tool without cancelling the shape in progress; the trailing click is
      // swallowed so it never places a point.
      if (zoomAreaArmedRef.current && e.button === 0 && !spaceHeldRef.current && !panLockRef.current) {
        const zpt = pointerToPdf(e);
        if (zpt) {
          zoomAreaRef.current = { start: zpt, current: zpt, out: e.altKey || e.shiftKey };
          setZoomAreaRect({ x0: zpt.x, y0: zpt.y, x1: zpt.x, y1: zpt.y });
          suppressNextClickRef.current = true;
          e.preventDefault();
        }
        return;
      }
"""),

# ── right-click with the Zoom tool zooms out ─────────────────────────
("""  const handleCanvasContextMenu = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
""", """  const handleCanvasContextMenu = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      // Revu Zoom tool: right-click zooms out around the cursor (""" + TAG + """).
      if (zoomAreaArmedRef.current) {
        e.preventDefault();
        zoomToRef.current((zoomRef.current || 1) / ZOOM_TOOL_STEP, { x: e.clientX, y: e.clientY });
        return;
      }
"""),

# ── keyboard ─────────────────────────────────────────────────────────
("""      // Tool letters — only when focus isn't in an input / textarea / etc.
      if (!shouldHandleShortcut(e.target)) return;""",
 """      // Revu / Acrobat zoom keys (""" + TAG + """): Ctrl+= in,
      // Ctrl+- out, Ctrl+0 fit page. Claimed so the browser does not zoom
      // the whole app instead of the drawing.
      if ((e.ctrlKey || e.metaKey) && !e.altKey && shouldHandleShortcut(e.target)) {
        if (e.key === '=' || e.key === '+') {
          e.preventDefault();
          zoomIn();
          return;
        }
        if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          zoomOut();
          return;
        }
        if (e.key === '0') {
          e.preventDefault();
          fitToViewport('page');
          return;
        }
      }

      // Tool letters — only when focus isn't in an input / textarea / etc.
      if (!shouldHandleShortcut(e.target)) return;"""),
("""      if (e.key === 'Escape' && viewportDraftRef.current) {""",
 """      // Z = Revu Zoom tool (toggle); Esc leaves it (""" + TAG + """).
      if (!e.shiftKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        setZoomAreaArmed((v) => !v);
        return;
      }
      if (e.key === 'Escape' && zoomAreaArmedRef.current) {
        e.preventDefault();
        zoomAreaRef.current = null;
        setZoomAreaRect(null);
        setZoomAreaArmed(false);
        return;
      }
      if (e.key === 'Escape' && viewportDraftRef.current) {"""),

# ── cursor + canvases ────────────────────────────────────────────────
("""                    cursor: panning
                      ? 'grabbing'""", """                    cursor: zoomAreaArmed && !panning
                      ? 'zoom-in'
                      : panning
                      ? 'grabbing'"""),
("""                  <canvas
                    ref={(el) => {
                      canvasRef.current = el;
                      if (el) setCanvasReady(true);
                    }}
                    className="block"
                  />
                ) : (""", """                  <>
                  <canvas
                    ref={(el) => {
                      canvasRef.current = el;
                      if (el) setCanvasReady(true);
                    }}
                    className="block"
                  />
                  {/* Deep-zoom sharp tile of the visible region (""" + TAG + """). */}
                  <canvas
                    ref={detailCanvasRef}
                    className="pointer-events-none absolute"
                    style={{ display: 'none' }}
                    aria-hidden="true"
                  />
                  </>
                ) : ("""),
("""                  onTouchEnd={handleTouchEnd}
                />
""", """                  onTouchEnd={handleTouchEnd}
                />
                {/* Deep-zoom markup layer: draws the visible region only;
                    pointer events fall through to the overlay above
                    (""" + TAG + """). */}
                <canvas
                  ref={deepCanvasRef}
                  className="pointer-events-none absolute"
                  style={{ display: 'none' }}
                  aria-hidden="true"
                />
"""),
# zoom button: now the sticky Zoom tool
("""                  title={t('takeoff_viewer.zoom_area_hint', { defaultValue: 'Zoom to area — drag a rectangle on the drawing to zoom into it' })}""",
 """                  title={t('takeoff_viewer.zoom_tool_hint', { defaultValue: 'Zoom tool (Z): click to zoom in, Alt/Shift-click or right-click to zoom out, drag a box to zoom to it. Works while drawing; Z or Esc to leave.' })}"""),
]


pairs += [
("""    const canvas = canvasRef.current ?? continuousCanvasesRef.current[currentPageRef.current - 1] ?? null;
    if (!canvas || canvas.width === 0) return null;""", """    // Single mode: the render's stored page size; the bitmap may be capped
    // under deep zoom (""" + TAG + """).
    const storedSize = pageSizePdfRef.current;
    if (canvasRef.current && storedSize && storedSize.page === currentPageRef.current) {
      return { width: storedSize.w, height: storedSize.h };
    }
    const canvas = canvasRef.current ?? continuousCanvasesRef.current[currentPageRef.current - 1] ?? null;
    if (!canvas || canvas.width === 0) return null;"""),
]

bad = [(old[:90], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if s.count(OLD_SIZE) != 2:
    bad.append(('OLD_SIZE', s.count(OLD_SIZE)))
if bad:
    print('NOT WRITTEN, anchors:', bad)
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
s = s.replace(OLD_SIZE, NEW_SIZE)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs) + 2)
