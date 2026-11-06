from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")

# ── imports ────────────────────────────────────────────────────────────
rep("import { columnShape, columnProfileOf, isColumnMarkup, isManualColumn, profileKey, drawColumnSymbol } from './data/column-shape';\n",
    "import { columnShape, columnProfileOf, isColumnMarkup, isManualColumn, profileKey, drawColumnSymbol } from './data/column-shape';\n"
    "import { type TextStyle, resolveTextStyle, layoutTextBox, drawTextBox, fontCss, loadToolTextStyle, saveToolTextStyle, LEGACY_TEXT_STYLE } from './data/text-box';\n"
    "import TextFormatBar from './components/TextFormatBar';\n")

# ── Measurement field ──────────────────────────────────────────────────
rep("""  text?: string; // Text content for text annotations
""", """  text?: string; // Text content for text annotations
  /** Revu-style text box style: font, size, B/I/U/S, alignment, colours,
   *  border, opacity (OE-DELIVERY 2026-11-07-text-box). Undefined = the
   *  older bold-14 look. */
  textStyle?: Partial<TextStyle>;
""")

# ── state ──────────────────────────────────────────────────────────────
rep("""  const [textInputWidth, setTextInputWidth] = useState(TEXT_BOX_DEFAULT_W);""", """  const [textInputWidth, setTextInputWidth] = useState(TEXT_BOX_DEFAULT_W);
  /** Text Box (OE-DELIVERY 2026-11-07-text-box): the style of the box being
   *  typed, the style new boxes start with (the Text Box tool's default),
   *  the height a dragged-out box keeps, and the drag that draws a box. */
  const [textInputStyle, setTextInputStyle] = useState<Partial<TextStyle> | undefined>(undefined);
  const [toolTextStyle, setToolTextStyle] = useState<Partial<TextStyle>>(() => loadToolTextStyle());
  const [textInputMinH, setTextInputMinH] = useState(0);
  const textDragRef = useRef<{ start: Point; moved: boolean } | null>(null);
  const pendingTextBoxRef = useRef<{ x: number; y: number; w: number; h: number } | null>(null);
  const [textDragRect, setTextDragRect] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  useEffect(() => saveToolTextStyle(toolTextStyle), [toolTextStyle]);""")

# resize ref gets the start height
rep("""    /** Box width at drag start (PDF units). */
    origW: number;""", """    /** Box width at drag start (PDF units). */
    origW: number;
    /** Box height at drag start (PDF units). */
    origH?: number;""")

# ── open editor ────────────────────────────────────────────────────────
rep("""    if (target) {
      setSelectedMeasurementId(target.id);
      setEditingTextId(target.id);
      setTextInputPos(target.points[0]!);
      setTextInputValue(target.text || '');
      setTextInputWidth(
        target.width && target.width > 0
          ? target.width
          : Math.max(120, measureTextUnits(target.text || target.annotation || '') + TEXT_PAD_X * 2 + 12),
      );
    } else {
      setEditingTextId(null);
      setTextInputPos(point);
      setTextInputValue('');
      setTextInputWidth(TEXT_BOX_DEFAULT_W);
    }
    setShowTextInput(true);""", """    if (target) {
      setSelectedMeasurementId(target.id);
      setEditingTextId(target.id);
      setTextInputPos(target.points[0]!);
      setTextInputValue(target.text || '');
      setTextInputWidth(
        target.width && target.width > 0
          ? target.width
          : Math.max(120, measureTextUnits(target.text || target.annotation || '') + TEXT_PAD_X * 2 + 12),
      );
      setTextInputStyle(target.textStyle);
      setTextInputMinH(target.height && target.height > 0 ? target.height : 0);
    } else {
      // A box dragged out with the Text Box tool keeps its drawn size
      // (Revu); a plain click opens a box of the default width.
      const drawn = pendingTextBoxRef.current;
      pendingTextBoxRef.current = null;
      setEditingTextId(null);
      setTextInputPos(drawn ? { x: drawn.x, y: drawn.y } : point);
      setTextInputValue('');
      setTextInputWidth(drawn ? Math.max(TEXT_BOX_MIN_W, drawn.w) : TEXT_BOX_DEFAULT_W);
      setTextInputMinH(drawn ? drawn.h : 0);
      setTextInputStyle({ ...toolTextStyle });
    }
    setShowTextInput(true);""")

# ── confirm ────────────────────────────────────────────────────────────
rep("""    if (editingTextId) {
      // Edit mode: update the existing text annotation in place.
      setMeasurements((prev) =>
        prev.map((m) =>
          m.id === editingTextId
            ? { ...m, text: trimmed, width: textInputWidth, height: textBoxHeight(trimmed, textInputWidth) }
            : m,
        ),
      );""", """    // Height the content needs in its style; a box drawn taller keeps its size.
    const tst = resolveTextStyle(textInputStyle);
    const fitH = Math.max(layoutTextBox(trimmed, textInputWidth, tst).contentHeight, textInputMinH);
    if (editingTextId) {
      // Edit mode: update the existing text annotation in place.
      setMeasurements((prev) =>
        prev.map((m) =>
          m.id === editingTextId
            ? { ...m, text: trimmed, width: textInputWidth, height: textInputStyle ? fitH : textBoxHeight(trimmed, textInputWidth), textStyle: textInputStyle }
            : m,
        ),
      );""")
rep("""      text: trimmed,
      width: textInputWidth,
      height: textBoxHeight(trimmed, textInputWidth),
      page: currentPage,
      group: activeGroup,
      color: annotationColor,
    };""", """      text: trimmed,
      width: textInputWidth,
      height: fitH,
      textStyle: textInputStyle ?? { ...toolTextStyle },
      page: currentPage,
      group: activeGroup,
      color: annotationColor,
    };""")
rep("""  }, [textInputValue, textInputPos, currentPage, activeGroup, annotationColor, pushUndo, nextAnnotation, editingTextId, textInputWidth]);""",
    """  }, [textInputValue, textInputPos, currentPage, activeGroup, annotationColor, pushUndo, nextAnnotation, editingTextId, textInputWidth, textInputStyle, textInputMinH, toolTextStyle]);""")

# ── canvas draw: styled box ────────────────────────────────────────────
rep("""          const textContent = m.text || m.annotation;
          const boxW = m.width && m.width > 0 ? m.width : 0;
          ctx.font = `bold ${TEXT_FONT_PX * dpr * zoom}px sans-serif`;""", """          const textContent = m.text || m.annotation;
          const boxW = m.width && m.width > 0 ? m.width : 0;
          if (boxW > 0 && m.textStyle) {
            // Revu Text Box (OE-DELIVERY 2026-11-07-text-box): fill, border,
            // font and alignment of its own.
            const st = resolveTextStyle(m.textStyle);
            const lay = layoutTextBox(textContent, boxW, st);
            const bh = Math.max(m.height && m.height > 0 ? m.height : 0, lay.contentHeight);
            drawTextBox(ctx, p.x, p.y, boxW, bh, lay.lines, st, dpr * zoom, annoColor);
            if (m.id === selectedMeasurementId || selectedLedgerIds.has(m.id)) {
              const bw = boxW * dpr * zoom;
              const bhs = bh * dpr * zoom;
              ctx.save();
              ctx.strokeStyle = '#2563eb';
              ctx.lineWidth = 1.2 * dpr;
              ctx.setLineDash([4 * dpr, 3 * dpr]);
              ctx.strokeRect(tx - 2 * dpr, ty - 2 * dpr, bw + 4 * dpr, bhs + 4 * dpr);
              ctx.setLineDash([]);
              if (m.id === selectedMeasurementId) {
                const hs = 8 * dpr;
                ctx.fillStyle = '#2563eb';
                ctx.fillRect(tx + bw - hs / 2, ty + bhs - hs / 2, hs, hs);
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1 * dpr;
                ctx.strokeRect(tx + bw - hs / 2, ty + bhs - hs / 2, hs, hs);
              }
              ctx.restore();
            }
          } else {
          ctx.font = `bold ${TEXT_FONT_PX * dpr * zoom}px sans-serif`;""")
rep("""            ctx.fillRect(tx + bw - hs / 2, ty + bh - hs / 2, hs, hs);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1 * dpr;
            ctx.strokeRect(tx + bw - hs / 2, ty + bh - hs / 2, hs, hs);
            ctx.lineWidth = 2 * dpr;
          }
        }
      }""", """            ctx.fillRect(tx + bw - hs / 2, ty + bh - hs / 2, hs, hs);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1 * dpr;
            ctx.strokeRect(tx + bw - hs / 2, ty + bh - hs / 2, hs, hs);
            ctx.lineWidth = 2 * dpr;
          }
          }
        }
      }""")

# ── resize: width and height ──────────────────────────────────────────
rep("""      const nw = Math.max(TEXT_BOX_MIN_W, rs.origW + (cur.x - rs.startPt.x));
      rs.moved = true;
      setMeasurements((prev) =>
        prev.map((m) =>
          m.id === rs.measurementId
            ? { ...m, width: nw, height: textBoxHeight(m.text || '', nw) }
            : m,
        ),
      );""", """      const nw = Math.max(TEXT_BOX_MIN_W, rs.origW + (cur.x - rs.startPt.x));
      rs.moved = true;
      setMeasurements((prev) =>
        prev.map((m) => {
          if (m.id !== rs.measurementId) return m;
          if (!m.textStyle) return { ...m, width: nw, height: textBoxHeight(m.text || '', nw) };
          // Revu text box: the corner sets width and height; the height never
          // goes below what the text needs at that width.
          const need = layoutTextBox(m.text || '', nw, resolveTextStyle(m.textStyle)).contentHeight;
          const nh = Math.max(need, (rs.origH ?? need) + (cur.y - rs.startPt.y));
          return { ...m, width: nw, height: nh };
        }),
      );""")
rep("""            origW: m.width && m.width > 0 ? m.width : TEXT_BOX_DEFAULT_W,
            moved: false,""", """            origW: m.width && m.width > 0 ? m.width : TEXT_BOX_DEFAULT_W,
            origH: m.height && m.height > 0 ? m.height : undefined,
            moved: false,""")

# ── drag out a box with the Text Box tool ─────────────────────────────
rep("""      if (activeTool !== 'select' || e.button !== 0) return;
      const pt = pointerToPdf(e);
      if (!pt) return;
      const z = zoomRef.current || 1;
      const onPage = editableOnPage();""", """      // Text Box tool: a press-and-drag draws the box (Revu); a plain click
      // still opens a default-width box (OE-DELIVERY 2026-11-07-text-box).
      if (activeTool === 'text' && e.button === 0 && !showTextInputRef.current) {
        const tp = pointerToPdf(e);
        if (tp) textDragRef.current = { start: tp, moved: false };
        return;
      }
      if (activeTool !== 'select' || e.button !== 0) return;
      const pt = pointerToPdf(e);
      if (!pt) return;
      const z = zoomRef.current || 1;
      const onPage = editableOnPage();""")
rep("""      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;""", """      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;
      // Text Box drawn by dragging: show the box as it is drawn.
      if (textDragRef.current) {
        const tp = pointerToPdf(e);
        const d = textDragRef.current;
        if (tp && Math.hypot(tp.x - d.start.x, tp.y - d.start.y) * (zoomRef.current || 1) > 6) {
          d.moved = true;
          setTextDragRect({ x0: d.start.x, y0: d.start.y, x1: tp.x, y1: tp.y });
        }
      }""")
rep("""    if (e.button === 0) pressActiveRef.current = false;
    if (zoomAreaRef.current) finishZoomArea();""", """    if (e.button === 0) pressActiveRef.current = false;
    if (textDragRef.current) {
      const d = textDragRef.current;
      textDragRef.current = null;
      const tp = pointerToPdf(e);
      setTextDragRect(null);
      if (d.moved && tp) {
        // The click that follows opens the editor on this drawn box.
        pendingTextBoxRef.current = {
          x: Math.min(d.start.x, tp.x),
          y: Math.min(d.start.y, tp.y),
          w: Math.abs(tp.x - d.start.x),
          h: Math.abs(tp.y - d.start.y),
        };
      }
    }
    if (zoomAreaRef.current) finishZoomArea();""")
rep("""  }, [finishDrag, finishMarquee, finishZoomArea, finishLegendResize, finishTextResize, toggleMarqueeSelection]);""",
    """  }, [finishDrag, finishMarquee, finishZoomArea, finishLegendResize, finishTextResize, toggleMarqueeSelection, pointerToPdf]);""")
rep("""        const existingText = findTextAnnotationAt(measurementsRef.current, currentPage, point, zoom);
        openTextEditor(existingText, point);
        return;""", """        const existingText = pendingTextBoxRef.current ? undefined : findTextAnnotationAt(measurementsRef.current, currentPage, point, zoom);
        openTextEditor(existingText, point);
        return;""")

# ── editor: styled like the box, with the properties bar above it ─────
rep("""                {showTextInput && (
                  <div
                    className="absolute z-10"
                    style={{
                      left: `${textInputPos.x * zoom}px`,
                      top: `${textInputPos.y * zoom + overlayTop}px`,
                    }}
                  >
                    <textarea""", """                {textDragRect && (
                  <div
                    className="pointer-events-none absolute z-10 border-2 border-dashed border-blue-600 bg-blue-500/5"
                    style={{
                      left: `${Math.min(textDragRect.x0, textDragRect.x1) * zoom}px`,
                      top: `${Math.min(textDragRect.y0, textDragRect.y1) * zoom + overlayTop}px`,
                      width: `${Math.abs(textDragRect.x1 - textDragRect.x0) * zoom}px`,
                      height: `${Math.abs(textDragRect.y1 - textDragRect.y0) * zoom}px`,
                    }}
                    data-testid="text-drag-rect"
                  />
                )}
                {/* Selected text box(es), or the Text Box tool's default: the properties bar (OE-DELIVERY 2026-11-07-text-box). */}
                {!showTextInput && (() => {
                  const selText = measurements.filter(
                    (m) => m.type === 'text' && m.page === currentPage && (m.id === selectedMeasurementId || selectedLedgerIds.has(m.id)) && (m.width ?? 0) > 0,
                  );
                  if (selText.length === 0) {
                    if (activeTool !== 'text') return null;
                    return (
                      <div className="absolute left-2 z-20" style={{ top: `${overlayTop + 8}px` }}>
                        <TextFormatBar
                          style={resolveTextStyle(toolTextStyle)}
                          markupColour={annotationColor}
                          caption="New text boxes:"
                          onChange={(patch) => setToolTextStyle((s) => ({ ...s, ...patch }))}
                        />
                      </div>
                    );
                  }
                  const first = selText[0]!;
                  const anchor = first.points[0]!;
                  return (
                    <div
                      className="absolute z-20"
                      style={{ left: `${anchor.x * zoom}px`, top: `${anchor.y * zoom + overlayTop - 6}px`, transform: 'translateY(-100%)' }}
                    >
                      <TextFormatBar
                        style={first.textStyle ? resolveTextStyle(first.textStyle) : LEGACY_TEXT_STYLE}
                        markupColour={first.color || annotationColor}
                        caption={selText.length > 1 ? `${selText.length} text boxes:` : undefined}
                        onChange={(patch) => {
                          const ids = new Set(selText.map((x) => x.id));
                          setMeasurements((prev) =>
                            prev.map((m) => {
                              if (!ids.has(m.id)) return m;
                              const own = { ...(m.textStyle ?? LEGACY_TEXT_STYLE), ...patch };
                              const need = layoutTextBox(m.text || '', m.width || TEXT_BOX_DEFAULT_W, resolveTextStyle(own)).contentHeight;
                              const next = { ...m, textStyle: own, height: need };
                              pushUndo({ kind: 'edit_geometry', measurementId: m.id, previousMeasurement: { ...m, points: [...m.points] }, nextMeasurement: { ...next, points: [...next.points] } });
                              return next;
                            }),
                          );
                          // The look you set becomes the Text Box tool's default too (Revu).
                          setToolTextStyle((s) => ({ ...s, ...patch }));
                        }}
                      />
                    </div>
                  );
                })()}
                {showTextInput && (() => {
                  const est = textInputStyle ? resolveTextStyle(textInputStyle) : LEGACY_TEXT_STYLE;
                  const tcol = est.color || annotationColor;
                  const bcol = est.border === undefined ? tcol : est.border;
                  return (
                  <div
                    className="absolute z-10"
                    style={{
                      left: `${textInputPos.x * zoom}px`,
                      top: `${textInputPos.y * zoom + overlayTop}px`,
                    }}
                  >
                    <div className="absolute bottom-full left-0 mb-1.5 w-max max-w-[640px]">
                      <TextFormatBar
                        style={est}
                        markupColour={annotationColor}
                        onChange={(patch) => {
                          setTextInputStyle((s0) => ({ ...(s0 ?? LEGACY_TEXT_STYLE), ...patch }));
                          setToolTextStyle((s0) => ({ ...s0, ...patch }));
                        }}
                      />
                    </div>
                    <textarea""")
rep("""                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleTextConfirm();
                        }
                        if (e.key === 'Escape') {
                          textInputCancellingRef.current = true;
                          setShowTextInput(false);
                          setTextInputValue('');
                        }
                      }}
                      onBlur={() => {
                        if (textInputCancellingRef.current) {""", """                      onKeyDown={(e) => {
                        // Revu: Enter is a new line; Ctrl+Enter or Esc finishes
                        // the box; Ctrl+B / I / U style it (OE-DELIVERY 2026-11-07-text-box).
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                          e.preventDefault();
                          handleTextConfirm();
                          return;
                        }
                        if ((e.ctrlKey || e.metaKey) && ['b', 'i', 'u'].includes(e.key.toLowerCase())) {
                          e.preventDefault();
                          const key = e.key.toLowerCase() === 'b' ? 'bold' : e.key.toLowerCase() === 'i' ? 'italic' : 'underline';
                          setTextInputStyle((s0) => {
                            const cur = { ...(s0 ?? LEGACY_TEXT_STYLE) };
                            cur[key] = !cur[key];
                            return cur;
                          });
                          return;
                        }
                        if (e.key === 'Escape') {
                          e.preventDefault();
                          handleTextConfirm();
                        }
                      }}
                      onBlur={(e) => {
                        // Focus moved into the properties bar: still editing.
                        const to = e.relatedTarget as HTMLElement | null;
                        if (to && to.closest('[data-text-format-bar]')) return;
                        if (textInputCancellingRef.current) {""")
rep("""                      placeholder={t('takeoff_viewer.text_placeholder', { defaultValue: 'Type text... (Enter to save, Shift+Enter for new line)' })}
                      className="rounded-[3px] border-2 bg-white outline-none shadow-xl resize-none overflow-hidden"
                      style={{
                        borderColor: '#2563eb',
                        color: annotationColor,
                        width: `${textInputWidth * zoom}px`,
                        fontSize: `${TEXT_FONT_PX * zoom}px`,
                        lineHeight: TEXT_LINE_HEIGHT_PX / TEXT_FONT_PX,
                        fontWeight: 700,
                        padding: `${TEXT_PAD_Y * zoom}px ${TEXT_PAD_X * zoom}px`,
                      }}
                    />
                  </div>
                )}""", """                      placeholder="Type text… (Enter: new line · Ctrl+Enter, Esc or click outside: done)"
                      className="outline-none shadow-xl resize-none overflow-hidden ring-2 ring-blue-500/60"
                      data-testid="text-box-editor"
                      style={{
                        // Exactly the box as it will land on the sheet.
                        color: tcol,
                        background: est.fill ? `color-mix(in srgb, ${est.fill} ${Math.round(est.fillAlpha * 100)}%, white)` : 'rgba(255,255,255,0.92)',
                        border: bcol && est.borderWidth > 0 ? `${Math.max(1, est.borderWidth * zoom)}px ${est.borderStyle === 'cloud' ? 'dashed' : est.borderStyle} ${bcol}` : '1px dashed #93c5fd',
                        width: `${textInputWidth * zoom}px`,
                        minHeight: textInputMinH > 0 ? `${textInputMinH * zoom}px` : undefined,
                        font: fontCss(est, est.size * zoom),
                        lineHeight: est.lineHeight,
                        textAlign: est.align,
                        textDecoration: [est.underline ? 'underline' : '', est.strike ? 'line-through' : ''].filter(Boolean).join(' ') || 'none',
                        opacity: est.opacity,
                        padding: `${est.padding * zoom}px`,
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  );
                })()}""")
p.write_text(s, encoding="utf-8")

# ── persistence ────────────────────────────────────────────────────────
p = base / "useMeasurementPersistence.ts"
s = p.read_text(encoding="utf-8")
rep("""    metadata: {
      text: m.text,
      width: m.width,
      height: m.height,""", """    metadata: {
      text: m.text,
      width: m.width,
      height: m.height,
      // Revu-style text box look (OE-DELIVERY 2026-11-07-text-box).
      text_style: m.textStyle,""")
rep("""  const metadata: Record<string, unknown> = {
    text: m.text,
    width: m.width,
    height: m.height,""", """  const metadata: Record<string, unknown> = {
    text: m.text,
    width: m.width,
    height: m.height,
    text_style: m.textStyle ?? null,""")
rep("""    text: (meta.text as string) ?? undefined,
    color: r.group_color || undefined,""", """    text: (meta.text as string) ?? undefined,
    textStyle: cleanTextStyle(meta.text_style),
    color: r.group_color || undefined,""")
rep("""    a: annotationForWire(m),
    n: m.text ?? null,
  });""", """    a: annotationForWire(m),
    n: m.text ?? null,
    // Text box look and size: a restyle or resize must re-save
    // (OE-DELIVERY 2026-11-07-text-box).
    ts: m.textStyle ?? null,
    bw: m.type === 'text' ? m.width ?? null : null,
    bh: m.type === 'text' ? m.height ?? null : null,
  });""")
first_import_end = s.index("\n", s.index("\nimport ") + 1)
s = s[: first_import_end + 1] + "import { cleanTextStyle } from './data/text-box';\n" + s[first_import_end + 1 :]
p.write_text(s, encoding="utf-8")
print("ok")
