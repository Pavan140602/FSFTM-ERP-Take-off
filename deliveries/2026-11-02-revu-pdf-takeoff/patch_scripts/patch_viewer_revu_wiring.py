"""Wire the Revu markup + arc tools into TakeoffViewerModule.tsx (anchored, all-or-nothing)."""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
pairs = [
# state
("""  const [rectStartPoint, setRectStartPoint] = useState<Point | null>(null);
  const [isDraggingRect, setIsDraggingRect] = useState(false);
""", """  const [rectStartPoint, setRectStartPoint] = useState<Point | null>(null);
  const [isDraggingRect, setIsDraggingRect] = useState(false);
  /* ── Revu markup tools (OE-DELIVERY 2026-10-30-revu-markup-tools) ──── */
  /** Active stamp preset id, or 'custom' to type the stamp text. */
  const [stampPresetId, setStampPresetId] = useState<string>(STAMP_PRESETS[0]!.id);
  /** Text prompt for a Callout (tip + box anchor placed) or a custom Stamp. */
  const [markupTextPrompt, setMarkupTextPrompt] = useState<
    { kind: 'callout' | 'stamp'; points: Point[]; value: string } | null
  >(null);
  /** Live Pen stroke while the primary button is held (PDF units). */
  const penStrokeRef = useRef<Point[] | null>(null);
  /** Commits the live Pen stroke; reassigned every render (latest state). */
  const finishPenStrokeRef = useRef<() => void>(() => {});
"""),
# snap / ortho / close-on-first in click
("""      const canVertexSnap =
        activeTool === 'distance' ||
        activeTool === 'polyline' ||
        activeTool === 'area' ||
        activeTool === 'volume';""", """      const canVertexSnap =
        activeTool === 'distance' ||
        activeTool === 'polyline' ||
        activeTool === 'area' ||
        activeTool === 'volume' ||
        activeTool === 'line' ||
        activeTool === 'polygon' ||
        activeTool === 'callout' ||
        activeTool === 'arc';"""),
("""          (activeTool === 'area' || activeTool === 'volume' || activeTool === 'perimeter') &&
          activePoints.length >= 3 &&""", """          (activeTool === 'area' || activeTool === 'volume' || activeTool === 'perimeter' || activeTool === 'polygon') &&
          activePoints.length >= 3 &&"""),
("""          activeTool === 'cloud' ||
          activeTool === 'arrow')
      ) {
        point = orthoSnap(""", """          activeTool === 'cloud' ||
          activeTool === 'arrow' ||
          activeTool === 'line' ||
          activeTool === 'polygon' ||
          activeTool === 'callout')
      ) {
        point = orthoSnap("""),
# click branches
("""      if (activeTool === 'text') {
        // The click that blurred the editor open above already saved and""", """      /* ── Revu markup + arc tools (OE-DELIVERY 2026-10-30-revu-markup-tools) ── */

      // Line (2 clicks), Callout (tip, then box), Arc (start, a point on the
      // arc, end). A callout asks for its text once both points are down.
      if (activeTool === 'line' || activeTool === 'callout' || activeTool === 'arc') {
        const need = activeTool === 'arc' ? 3 : 2;
        const newPoints = [...activePoints, point];
        if (newPoints.length < need) {
          pushUndo({ kind: 'add_point', tool: activeTool, point });
          setActivePoints(newPoints);
          return;
        }
        setActivePoints([]);
        if (activeTool === 'callout') {
          setMarkupTextPrompt({ kind: 'callout', points: newPoints, value: '' });
          return;
        }
        const isArc = activeTool === 'arc';
        const arcLen = isArc ? toRealDistance(arcLengthPx(newPoints), scale) : 0;
        const newMeasurement: Measurement = {
          id: `m_${Date.now()}`,
          type: activeTool,
          points: newPoints,
          value: arcLen,
          unit: isArc ? scale.unitLabel : '',
          label: isArc ? `\\u2312 ${formatMeasurement(arcLen, scale.unitLabel)}` : '',
          annotation: nextAnnotation(activeTool),
          ...toolFieldSpread(),
          page: currentPage,
          group: activeGroup,
          ...(isArc ? {} : { color: annotationColor }),
        };
        pushUndo({ kind: 'complete_measurement', measurement: newMeasurement, previousActivePoints: [...activePoints] });
        setMeasurements((prev) => [...prev, newMeasurement]);
        return;
      }

      // Polygon markup: click vertices, double-click / right-click to close.
      if (activeTool === 'polygon') {
        pushUndo({ kind: 'add_point', tool: 'polygon', point });
        setActivePoints((prev) => [...prev, point]);
        return;
      }

      // Stamp: one click drops the active preset; "custom" asks for text.
      if (activeTool === 'stamp') {
        const preset = STAMP_PRESETS.find((sp) => sp.id === stampPresetId);
        if (preset) placeStamp(point, preset.text, preset.color);
        else setMarkupTextPrompt({ kind: 'stamp', points: [point], value: '' });
        return;
      }

      if (activeTool === 'text') {
        // The click that blurred the editor open above already saved and"""),
("""      if (activeTool === 'rectangle' || activeTool === 'highlight') {
        if (!rectStartPoint) {""", """      if (activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse') {
        if (!rectStartPoint) {"""),
("""    [activeTool, activePoints, scale, currentPage, countLabel, settingScale, scalePoints, zoom, pushUndo, nextAnnotation, activeGroup, annotationColor, rectStartPoint, orthoLock],
  );""", """    [activeTool, activePoints, scale, currentPage, countLabel, settingScale, scalePoints, zoom, pushUndo, nextAnnotation, activeGroup, annotationColor, rectStartPoint, orthoLock, stampPresetId, placeStamp],
  );"""),
# dblclick finish polygon
("""    // Double-click on a placed text annotation reopens it for editing.
    // Reached only when no drawing was in progress""", """    // Polygon markup (OE-DELIVERY 2026-10-30-revu-markup-tools): close it.
    if (activeTool === 'polygon' && pts.length >= 3) {
      const newMeasurement: Measurement = {
        id: `m_${Date.now()}`,
        type: 'polygon',
        points: [...pts],
        value: 0,
        unit: '',
        label: '',
        annotation: nextAnnotation('polygon'),
        ...toolFieldSpread(),
        page: currentPage,
        group: activeGroup,
        color: annotationColor,
      };
      pushUndo({ kind: 'complete_measurement', measurement: newMeasurement, previousActivePoints: [...pts] });
      setMeasurements((prev) => [...prev, newMeasurement]);
      setActivePoints([]);
      return;
    }

    // Double-click on a placed text annotation reopens it for editing.
    // Reached only when no drawing was in progress"""),
# context-menu finish polygon
("""      } else if (activeTool === 'cloud' && activePoints.length >= 3) {
        e.preventDefault();
        handleCanvasDblClick();
      } else if (activeTool === 'select') {""", """      } else if ((activeTool === 'cloud' || activeTool === 'polygon') && activePoints.length >= 3) {
        e.preventDefault();
        handleCanvasDblClick();
      } else if (activeTool === 'select') {"""),
# pen press
("""      if (activeTool !== 'select' || e.button !== 0) return;
      const pt = pointerToPdf(e);
      if (!pt) return;
      const z = zoomRef.current || 1;
      const onPage = editableOnPage();""", """      // Revu Pen (OE-DELIVERY 2026-10-30-revu-markup-tools): a held press
      // draws a freehand stroke; the window mouseup commits it.
      if (activeTool === 'pen' && e.button === 0) {
        const start = pointerToPdf(e);
        if (start) {
          penStrokeRef.current = [start];
          setActivePoints([start]);
          e.preventDefault();
        }
        return;
      }
      if (activeTool !== 'select' || e.button !== 0) return;
      const pt = pointerToPdf(e);
      if (!pt) return;
      const z = zoomRef.current || 1;
      const onPage = editableOnPage();"""),
# pen move
("""      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;
      if (shiftPendingRef.current) {""", """      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;
      // Live Pen stroke (OE-DELIVERY 2026-10-30-revu-markup-tools): sample
      // every ~2 screen px so the stroke stays smooth without flooding state.
      if (penStrokeRef.current) {
        const ppt = pointerToPdf(e);
        const stroke = penStrokeRef.current;
        const last = stroke[stroke.length - 1];
        if (ppt && last && Math.hypot(ppt.x - last.x, ppt.y - last.y) * (zoomRef.current || 1) >= 2) {
          stroke.push(ppt);
          setActivePoints([...stroke]);
        }
        return;
      }
      if (shiftPendingRef.current) {"""),
# ellipse drag + live cursor tools
("""      if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'rectarea') && rectStartPoint) {""",
 """      if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'rectarea' || activeTool === 'ellipse') && rectStartPoint) {"""),
("""        (activeTool === 'distance' ||
          activeTool === 'polyline' ||
          activeTool === 'area' ||
          activeTool === 'volume')
      ) {
        // Vertex snap wins over ortho (issue #303)""", """        (activeTool === 'distance' ||
          activeTool === 'polyline' ||
          activeTool === 'area' ||
          activeTool === 'volume' ||
          activeTool === 'line' ||
          activeTool === 'polygon' ||
          activeTool === 'callout' ||
          activeTool === 'arc')
      ) {
        // Vertex snap wins over ortho (issue #303)"""),
# pen release (window mouseup sees every release)
("""      if (e.button === 0) pressActiveRef.current = false;
      if (e.button === 0 && shiftPendingRef.current) {""", """      if (e.button === 0) pressActiveRef.current = false;
      if (e.button === 0 && penStrokeRef.current) finishPenStrokeRef.current();
      if (e.button === 0 && shiftPendingRef.current) {"""),
]
bad = [(old[:100], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if bad:
    print('NOT WRITTEN, anchors:', bad)
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs))
