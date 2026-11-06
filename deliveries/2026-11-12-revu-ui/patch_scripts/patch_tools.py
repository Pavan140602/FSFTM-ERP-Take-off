"""Cloud / rectangle tools draw by dragging; tools exit to Select after one
markup unless locked (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)


# State / refs.
rep('''  const textDragRef = useRef<{ start: Point; moved: boolean } | null>(null);''',
    '''  const textDragRef = useRef<{ start: Point; moved: boolean } | null>(null);
  /** Press-and-drag box for the cloud / rectangle / highlight / ellipse
   *  tools (Revu: drag out the shape) (OE-DELIVERY 2026-11-12-revu-ui). */
  const boxDragRef = useRef<{ start: Point; moved: boolean } | null>(null);
  const [boxDragRect, setBoxDragRect] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  /** Revu tool lock: off = a tool goes back to Select once its markup is
   *  done; double-click a tool button to keep it on. */
  const [toolLock, setToolLock] = useState(false);
  const toolLockRef = useRef(false);
  toolLockRef.current = toolLock;
  const exitToolRef = useRef<(() => void) | null>(null);''')

# Mouse down: start a box drag.
rep('''      if (activeTool === 'text' && e.button === 0 && !showTextInputRef.current) {
        const tp = pointerToPdf(e);
        if (tp) textDragRef.current = { start: tp, moved: false };
        return;
      }''', '''      if (activeTool === 'text' && e.button === 0 && !showTextInputRef.current) {
        const tp = pointerToPdf(e);
        if (tp) textDragRef.current = { start: tp, moved: false };
        return;
      }
      if (
        e.button === 0 &&
        (activeTool === 'cloud' || activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse')
      ) {
        const bp = pointerToPdf(e);
        boxDragRef.current = bp ? { start: bp, moved: false } : null;
        return;
      }''')

# Mouse move: preview.
rep('''      // Text Box drawn by dragging: show the box as it is drawn.
      if (textDragRef.current) {''', '''      // Cloud / rectangle drawn by dragging (OE-DELIVERY 2026-11-12-revu-ui).
      if (boxDragRef.current && (e.buttons & 1)) {
        const bp = pointerToPdf(e);
        const d = boxDragRef.current;
        if (bp && Math.hypot(bp.x - d.start.x, bp.y - d.start.y) * (zoomRef.current || 1) > 6) {
          d.moved = true;
          setBoxDragRect({ x0: d.start.x, y0: d.start.y, x1: bp.x, y1: bp.y });
        }
      }
      // Text Box drawn by dragging: show the box as it is drawn.
      if (textDragRef.current) {''')

# Click: a finished drag makes the whole shape.
rep('''      /* ── Annotation tool click handlers ──────────────────────────── */

      if (activeTool === 'cloud') {''', '''      /* ── Annotation tool click handlers ──────────────────────────── */

      // A press-and-drag drew the whole box: rectangular cloud, rectangle,
      // highlight or ellipse in one go, like Revu (OE-DELIVERY 2026-11-12-revu-ui).
      {
        const bd = boxDragRef.current;
        boxDragRef.current = null;
        setBoxDragRect(null);
        const ep = bd && bd.moved ? pointerToPdf(e) : null;
        if (bd && ep && Math.abs(ep.x - bd.start.x) > 1 && Math.abs(ep.y - bd.start.y) > 1) {
          const a = bd.start;
          if (activeTool === 'cloud' && activePoints.length === 0) {
            const corners = [a, { x: ep.x, y: a.y }, ep, { x: a.x, y: ep.y }];
            const cloudM: Measurement = {
              id: `m_${Date.now()}`,
              type: 'cloud',
              points: corners,
              value: 0,
              unit: '',
              label: '',
              annotation: nextAnnotation('cloud'),
              ...toolFieldSpread(),
              page: currentPage,
              group: activeGroup,
              color: annotationColor,
            };
            pushUndo({ kind: 'complete_measurement', measurement: cloudM, previousActivePoints: [] });
            setMeasurements((prev) => [...prev, cloudM]);
            setActivePoints([]);
            return;
          }
          if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse') && !rectStartPoint) {
            const boxM: Measurement = {
              id: `m_${Date.now()}`,
              type: activeTool,
              points: [a, ep],
              value: 0,
              unit: '',
              label: '',
              annotation: nextAnnotation(activeTool),
              ...toolFieldSpread(),
              page: currentPage,
              group: activeGroup,
              color: annotationColor,
              width: Math.abs(ep.x - a.x),
              height: Math.abs(ep.y - a.y),
            };
            pushUndo({ kind: 'complete_measurement', measurement: boxM, previousActivePoints: [] });
            setMeasurements((prev) => [...prev, boxM]);
            setActivePoints([]);
            return;
          }
        }
      }

      if (activeTool === 'cloud') {''')

# Preview on the canvas.
rep('''      if (marqueeRect) {
        const rx = Math.min(marqueeRect.x0, marqueeRect.x1) * dpr * zoom;''', '''      if (boxDragRect) {
        // Shape being dragged out (cloud / rectangle / highlight / ellipse).
        const bx = Math.min(boxDragRect.x0, boxDragRect.x1) * dpr * zoom;
        const by = Math.min(boxDragRect.y0, boxDragRect.y1) * dpr * zoom;
        const bw = Math.abs(boxDragRect.x1 - boxDragRect.x0) * dpr * zoom;
        const bh = Math.abs(boxDragRect.y1 - boxDragRect.y0) * dpr * zoom;
        ctx.save();
        ctx.setLineDash([6 * dpr, 4 * dpr]);
        ctx.lineWidth = 1.5 * dpr;
        ctx.strokeStyle = annotationColor || '#EF4444';
        if (activeTool === 'ellipse') {
          ctx.beginPath();
          ctx.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
          ctx.stroke();
        } else {
          ctx.strokeRect(bx, by, bw, bh);
        }
        ctx.restore();
      }
      if (marqueeRect) {
        const rx = Math.min(marqueeRect.x0, marqueeRect.x1) * dpr * zoom;''')

rep('''selectedMeasurementId, selectedLedgerIds, marqueeRect, zoomAreaRect,''',
    '''selectedMeasurementId, selectedLedgerIds, marqueeRect, boxDragRect, zoomAreaRect,''')

# Auto exit after one markup (count keeps counting; locked tools stay).
rep('''  const pushUndo = useCallback((op: UndoOperation) => {
    undoStackRef.current.push(op);
    setUndoCount(undoStackRef.current.length);''', '''  const pushUndo = useCallback((op: UndoOperation) => {
    undoStackRef.current.push(op);
    setUndoCount(undoStackRef.current.length);
    // Revu: a tool is used once, then back to Select - unless it is locked
    // (double-click its button) or it is Count, which keeps counting until
    // Esc (OE-DELIVERY 2026-11-12-revu-ui).
    if (op.kind === 'complete_measurement' && !toolLockRef.current) {
      setTimeout(() => exitToolRef.current?.(), 0);
    }''')

rep('''  const selectTool = useCallback((tool: MeasureTool) => {''', '''  const activeToolRef = useRef(activeTool);
  activeToolRef.current = activeTool;
  const selectToolRef = useRef<((t: MeasureTool) => void) | null>(null);
  /** Back to Select after a markup is done (see pushUndo). */
  exitToolRef.current = () => {
    const tl = activeToolRef.current;
    if (tl === 'select' || tl === 'count' || offsetToolRef.current) return;
    selectToolRef.current?.('select');
  };
  const selectTool = useCallback((tool: MeasureTool) => {''')

i = s.index('  const selectTool = useCallback((tool: MeasureTool) => {')
j = s.index('\n  }, [', i)
k = s.index('\n', j + 1)
s = s[:k + 1] + '  selectToolRef.current = selectTool;\n' + s[k + 1:]
p.write_text(s, encoding="utf-8")
print("ok")
