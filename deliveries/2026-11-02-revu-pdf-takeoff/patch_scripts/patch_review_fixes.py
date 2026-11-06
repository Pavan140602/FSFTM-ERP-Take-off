"""Fixes from the independent review (all-or-nothing). OE-DELIVERY: 2026-11-02-review-fixes"""
import sys
from pathlib import Path

root = Path(sys.argv[1])  # frontend/src/modules/pdf-takeoff
TAG = 'OE-DELIVERY 2026-11-02-review-fixes'
v = root / 'TakeoffViewerModule.tsx'
pm = root / 'useMeasurementPersistence.ts'
s = v.read_text(encoding='utf-8')
ps = pm.read_text(encoding='utf-8')

pairs = [
# 1. reconcile must not overwrite a cutout parent's net area with its gross
("""    setMeasurements((ms) =>
      reconcileViewportValues(ms, pageScales, (m, pts, sc) => recomputeMeasurement(m, pts, sc) as Partial<Measurement>),
    );
  }, [measurements, pageScales]);""", """    setMeasurements((ms) => {
      // An area with cutouts stores NET (gross - cutouts) in value; a plain
      // recompute would reset it to gross, so leave those to the cutout
      // logic (""" + TAG + """).
      const cutParents = new Set(ms.filter((c) => c.cutoutOf).map((c) => c.cutoutOf!));
      return reconcileViewportValues(ms, pageScales, (m, pts, sc) =>
        cutParents.has(m.id) || (m as { _grossArea?: number })._grossArea != null
          ? {}
          : (recomputeMeasurement(m, pts, sc) as Partial<Measurement>),
      );
    });
  }, [measurements, pageScales]);"""),

# 2. Esc for Zoom tool / viewport draft must run before the general Esc block
("""      // Esc: cancel any in-progress drawing + deselect any selected measurement
      if (e.key === 'Escape') {""", """      // Esc leaves the Zoom tool / viewport drawing first, without touching the
      // shape in progress (""" + TAG + """).
      if (e.key === 'Escape' && zoomAreaArmedRef.current) {
        e.preventDefault();
        zoomAreaRef.current = null;
        setZoomAreaRect(null);
        setZoomAreaArmed(false);
        return;
      }
      if (e.key === 'Escape' && viewportDraftRef.current) {
        e.preventDefault();
        setViewportDraft(null);
        return;
      }
      // Esc: cancel any in-progress drawing + deselect any selected measurement
      if (e.key === 'Escape') {"""),
("""      if (e.key === 'Escape' && zoomAreaArmedRef.current) {
        e.preventDefault();
        zoomAreaRef.current = null;
        setZoomAreaRect(null);
        setZoomAreaArmed(false);
        return;
      }
      if (e.key === 'Escape' && viewportDraftRef.current) {
        e.preventDefault();
        setViewportDraft(null);
        return;
      }

      // Fit shortcuts""", """      // Fit shortcuts"""),

# 3. continuous mode cannot keep a deep-zoom level
("""  useEffect(() => {
    // Continuous mode has no deep zoom (it caps at 400%).
    if (pageMode !== 'single') deepModeRef.current = false;""", """  useEffect(() => {
    // Continuous mode has no deep zoom (it caps at 400%): bring the zoom down
    // when switching into it (""" + TAG + """).
    if (pageMode !== 'single') {
      deepModeRef.current = false;
      if (zoomRef.current > CONTINUOUS_ZOOM_MAX) zoomToRef.current(CONTINUOUS_ZOOM_MAX);
    }"""),

# 4. a double-click with the Zoom tool must not finish the shape
("""  const handleCanvasDblClick = useCallback((e?: React.MouseEvent<HTMLCanvasElement>) => {
""", """  const handleCanvasDblClick = useCallback((e?: React.MouseEvent<HTMLCanvasElement>) => {
    // The Zoom tool sits on top of the drawing tool (""" + TAG + """).
    if (zoomAreaArmedRef.current) return;
"""),

# 5. Esc in the Sketch-to-Scale box must not also cancel the shape
("""              } else if (e.key === 'Escape') {
                e.preventDefault();
                setSketchInput(null);
              }""", """              } else if (e.key === 'Escape') {
                e.preventDefault();
                // Keep the window Esc handler from discarding the shape too.
                e.stopPropagation();
                setSketchInput(null);
              }"""),

# 6. zoom-area drag released outside the canvas
("""      if (marqueeRef.current) finishMarquee();
      if (dragRef.current) finishDrag(true);
      if (legendResizeRef.current) finishLegendResize(true);
      if (textResizeRef.current) finishTextResize(true);
    };
    window.addEventListener('mousemove', onMove);""", """      if (zoomAreaRef.current) finishZoomArea(); // released off-canvas (""" + TAG + """)
      if (marqueeRef.current) finishMarquee();
      if (dragRef.current) finishDrag(true);
      if (legendResizeRef.current) finishLegendResize(true);
      if (textResizeRef.current) finishTextResize(true);
    };
    window.addEventListener('mousemove', onMove);"""),
("""  }, [handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, finishDrag, finishLegendResize, finishTextResize, finishMarquee, pointerToPdf, toggleMarqueeSelection]);""",
 """  }, [handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, finishDrag, finishLegendResize, finishTextResize, finishMarquee, finishZoomArea, pointerToPdf, toggleMarqueeSelection]);"""),

# 7. a typed sketch point is consumed by THIS click or dropped, never later
("""    (e: React.MouseEvent<HTMLCanvasElement>) => {
      // A press that began before the tool changed (a mid-press shortcut switch)""", """    (e: React.MouseEvent<HTMLCanvasElement>) => {
      // Take the typed Sketch-to-Scale point now so an early return below can
      // never leave it to hijack a later real click (""" + TAG + """).
      const pendingExactPoint = exactPointRef.current;
      exactPointRef.current = null;
      // A press that began before the tool changed (a mid-press shortcut switch)"""),
("""      const exactPoint = exactPointRef.current;
      exactPointRef.current = null;
      if (exactPoint) point = exactPoint;""", """      const exactPoint = pendingExactPoint;
      if (exactPoint) point = exactPoint;"""),

# 8. on-canvas text and real-width bands read the viewport scale
("""      const value = measurementLabel(m, scale, measurementSystem, areaAreaUnitRef.current, imperialDenominator);""",
 """      const value = measurementLabel(m, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnitRef.current, imperialDenominator);"""),
("""        const areaLabel = measurementLabel(m, scale, measurementSystem, areaAreaUnitRef.current, imperialDenominator);""",
 """        const areaLabel = measurementLabel(m, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnitRef.current, imperialDenominator);"""),
("""      const ownPixelsPerUnit = scaleForPage(pageScales, m.page).pixelsPerUnit;
      const baseStrokeWidth =""", """      const ownPixelsPerUnit = scaleForMeasurement(pageScales, m.page, m.points).pixelsPerUnit;
      const baseStrokeWidth ="""),

# 10. recalibration re-derives every scale-dependent type, not just four
("""        return m;
      }),
    );
  }, [pageScales]);""", """        // Perimeter, diameter, radius, arc, cutouts, dynamic fill: re-derive
        // from geometry at the new scale (""" + TAG + """).
        if (SCALE_DEPENDENT_TYPES.has(m.type) && m.type !== 'volume' && m.type !== 'area' && m.points.length > 0) {
          return { ...m, ...(recomputeMeasurement(m, m.points, scale) as Partial<Measurement>) };
        }
        return m;
      }),
    );
  }, [pageScales]);"""),
("""import {
  SKETCH_TOOLS,""", """import {
  SCALE_DEPENDENT_TYPES,
  SKETCH_TOOLS,"""),

# 12a. deep region updated in the same frame
("""    requestAnimationFrame(() => updateDeepRegionRef.current());
    overlay.style.width = canvas.style.width;
    overlay.style.height = canvas.style.height;
  }, [zoom, renderNonce, pdfDoc, currentPage, pageMode]);""", """    overlay.style.width = canvas.style.width;
    overlay.style.height = canvas.style.height;
    // Same frame, so the draw effect below paints the right region
    // (""" + TAG + """).
    updateDeepRegionRef.current();
  }, [zoom, renderNonce, pdfDoc, currentPage, pageMode]);"""),

# 12b. a selected markup of a hidden type draws no handles
("""          hiddenMeasurements.has(selected.id) ||
          (isAnnotationType(selected.type) && hiddenGroups.has('__annotations__')));""", """          hiddenMeasurements.has(selected.id) ||
          hiddenTypes.has(selected.type) ||
          (isAnnotationType(selected.type) && hiddenGroups.has('__annotations__')));"""),
]
ppairs = [
# 9. the page-calibrated flag stays about the PAGE, so a load fallback never
# turns a viewport's scale into the page scale
("""    ? pageIsCalibrated(pageScales, m.page) || viewportAt(pageScales, m.page, m.points[0]) != null
    : false;""", """    ? pageIsCalibrated(pageScales, m.page)
    : false;"""),
("""                pageIsCalibrated(pageScales, m.page) || viewportAt(pageScales, m.page, m.points[0]) != null,""",
 """                pageIsCalibrated(pageScales, m.page),"""),
("""  scaleForMeasurement,
  viewportAt,
} from './data/page-scales';""", """  scaleForMeasurement,
} from './data/page-scales';"""),
]
bad = [('viewer', o[:80], s.count(o)) for o, _ in pairs if s.count(o) != 1]
bad += [('persist', o[:80], ps.count(o)) for o, _ in ppairs if ps.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
for o, n in ppairs:
    ps = ps.replace(o, n)
v.write_text(s, encoding='utf-8')
pm.write_text(ps, encoding='utf-8')
print('ok', len(pairs) + len(ppairs))
