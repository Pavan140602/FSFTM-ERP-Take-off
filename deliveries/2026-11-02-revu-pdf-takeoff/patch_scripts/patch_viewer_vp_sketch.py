"""Viewports + Sketch to Scale wiring for TakeoffViewerModule (anchored, all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-viewports-sketch"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-viewports-sketch'
pairs = [
# ── imports ──────────────────────────────────────────────────────────
("""  Stamp,
""", """  Stamp,
  // Viewports (""" + TAG + """).
  Frame,
"""),
("""  setPageScale as setPageScaleIn,
  pageIsCalibrated,
} from './data/page-scales';""", """  setPageScale as setPageScaleIn,
  pageIsCalibrated,
  // Viewports (""" + TAG + """).
  type Viewport,
  viewportAt,
  viewportsForPage,
  upsertViewport,
  removeViewport,
  normalizeRect,
  scaleForMeasurement,
  hasAnyViewport,
} from './data/page-scales';
import {
  SKETCH_TOOLS,
  parseSketchInput,
  sketchPoint,
  reconcileViewportValues,
  reconcilePageValues,
} from './data/sketch-to-scale';"""),

# ── scale memo: viewport-aware while a shape is in progress ─────────
("""  const scale = useMemo(
    () => scaleForPage(pageScales, currentPage),
    [pageScales, currentPage],
  );""", """  // While a shape is in progress, ``scale`` is the scale of the viewport its
  // first point sits in (Revu: a measurement belongs to the viewport it
  // starts in), so live readouts and the create paths read the right ratio
  // (""" + TAG + """). Identity is stable: it is always
  // one of the stored ScaleConfig objects.
  const scale = useMemo(
    () => viewportAt(pageScales, currentPage, activePoints[0])?.scale ?? scaleForPage(pageScales, currentPage),
    [pageScales, currentPage, activePoints],
  );"""),

# ── state ────────────────────────────────────────────────────────────
("""  const [liveCursor, setLiveCursor] = useState<Point | null>(null);
""", """  const [liveCursor, setLiveCursor] = useState<Point | null>(null);
  /* Viewports + Sketch to Scale (""" + TAG + """).
   * viewportDraft: null = not drawing; {start:null} = armed, waiting for the
   * first corner; {start, cursor} = rubber-banding the second corner. */
  const [viewportDraft, setViewportDraft] = useState<{ start: Point | null; cursor: Point | null } | null>(null);
  const viewportDraftRef = useRef(viewportDraft);
  viewportDraftRef.current = viewportDraft;
  const [viewportDialog, setViewportDialog] = useState<{
    page: number;
    id: string | null;
    rect: Viewport['rect'];
    name: string;
    preset: string;
    ratio: string;
    knownLength: string;
  } | null>(null);
  const [showViewportPanel, setShowViewportPanel] = useState(false);
  /** Typed Sketch-to-Scale entry; null = closed. */
  const [sketchInput, setSketchInput] = useState<string | null>(null);
  /** One-shot exact vertex for the next click (bypasses snap + ortho). */
  const exactPointRef = useRef<Point | null>(null);
  const sketchCtxRef = useRef({ activeTool, activePoints, liveCursor, pageScales, currentPage });
  sketchCtxRef.current = { activeTool, activePoints, liveCursor, pageScales, currentPage };
"""),

# ── edit-time recompute: viewport-aware ──────────────────────────────
("""  const editScaleRef = useRef(scale);
  editScaleRef.current = scale;
""", """  const editScaleRef = useRef(scale);
  editScaleRef.current = scale;
  // Reshape recompute reads the scale the edited shape sits in: its
  // viewport, else its page (""" + TAG + """).
  const editPageScalesRef = useRef(pageScales);
  editPageScalesRef.current = pageScales;
  const editScaleFor = (m: { page: number }, pts: Point[]): ScaleConfig =>
    scaleForMeasurement(editPageScalesRef.current, m.page, pts);
"""),
("""          const patch = recomputeMeasurement(m, nextPoints, editScaleRef.current);
""", """          const patch = recomputeMeasurement(m, nextPoints, editScaleFor(m, nextPoints));
"""),
("""          const patch = recomputeMeasurement(base, drag.lastPoints, editScaleRef.current);""",
 """          const patch = recomputeMeasurement(base, drag.lastPoints, editScaleFor(base, drag.lastPoints));"""),
("""        ? recomputeMeasurement(m, next, editScaleRef.current)""",
 """        ? recomputeMeasurement(m, next, editScaleFor(m, next))"""),
("""
    const patch = recomputeMeasurement(m, nextPoints, editScaleRef.current);""",
 """
    const patch = recomputeMeasurement(m, nextPoints, editScaleFor(m, nextPoints));"""),

# ── page-scale recompute: leave viewport rows to the reconcile pass ──
("""        if (isAnnotationType(m.type)) return m; // annotations are scale-independent
""", """        if (isAnnotationType(m.type)) return m; // annotations are scale-independent
        // Rows inside a viewport read the viewport's scale, not the page's,
        // and the reconcile pass below keeps them right (""" + TAG + """).
        if (viewportAt(pageScales, m.page, m.points[0])) return m;
"""),
("""  }, [pageScales]);
""", """  }, [pageScales]);

  /* ── Viewport value reconciliation (""" + TAG + """) ──
   * The create paths compute against the page scale; on a page that has
   * viewports, re-derive every scale-dependent row against the scale it
   * actually sits in. Returns the same array when nothing moved, so it
   * settles in one pass. Pages without viewports are never touched. */
  useEffect(() => {
    if (!hasAnyViewport(pageScales)) return;
    setMeasurements((ms) =>
      reconcileViewportValues(ms, pageScales, (m, pts, sc) => recomputeMeasurement(m, pts, sc) as Partial<Measurement>),
    );
  }, [measurements, pageScales]);
"""),

# ── Sketch to Scale confirm helper ───────────────────────────────────
("""  const placeStamp = useCallback(""", """  /** Sketch to Scale (""" + TAG + """): place the next
   *  vertex exactly the typed length (and optional angle) from the last one,
   *  through the normal click path so every tool finishes as if clicked. */
  const confirmSketch = useCallback(
    (text: string) => {
      const sc = sketchCtxRef.current;
      const from = sc.activePoints[sc.activePoints.length - 1];
      if (!from) {
        setSketchInput(null);
        return;
      }
      const parsed = parseSketchInput(text, measurementSystem);
      if (!parsed) {
        addToast({
          type: 'warning',
          title: t('takeoff_viewer.sketch_bad_title', { defaultValue: 'Could not read that length' }),
          message: t('takeoff_viewer.sketch_bad_msg', { defaultValue: 'Try 12.5, 12.5<90, 3500mm or 12\\'6".' }),
        });
        return;
      }
      const target = sketchPoint(
        from,
        sc.liveCursor,
        parsed,
        scaleForMeasurement(sc.pageScales, sc.currentPage, sc.activePoints),
      );
      const rect = overlayRef.current?.getBoundingClientRect();
      setSketchInput(null);
      if (!target || !rect) return;
      exactPointRef.current = target;
      handleCanvasClickRef.current?.({
        clientX: rect.left + target.x * zoom,
        clientY: rect.top + target.y * zoom,
      } as React.MouseEvent<HTMLCanvasElement>);
    },
    [measurementSystem, addToast, t, zoom],
  );

  /** Save the viewport dialog: resolve the chosen scale and upsert. */
  const saveViewportDialog = useCallback(() => {
    const d = viewportDialog;
    if (!d) return;
    let vpScale: ScaleConfig | null = null;
    let scaleLabel: string | undefined;
    if (d.preset === '__ratio') {
      const n = Number(d.ratio.trim().replace(/^1\\s*:\\s*/, '').replace(',', '.'));
      if (Number.isFinite(n) && n > 0) {
        vpScale = presetScale(n);
        scaleLabel = `1:${n}`;
      }
    } else if (d.preset === '__line') {
      const line = measurementsRef.current.find((m) => m.id === selectedMeasurementId);
      const meters = parseSketchInput(d.knownLength, measurementSystem)?.meters;
      if (line && line.points.length >= 2 && meters) {
        const a = line.points[0]!;
        const b = line.points[1]!;
        const px = pixelDistance(a.x, a.y, b.x, b.y);
        if (px > 0) {
          vpScale = { pixelsPerUnit: px / meters, unitLabel: 'm' };
          scaleLabel = formatScaleRatio(vpScale);
        }
      }
    } else {
      const preset = DRAWING_SCALE_PRESETS.find((sp) => sp.label === d.preset);
      if (preset) {
        vpScale = preset.scale;
        scaleLabel = preset.label;
      }
    }
    if (!vpScale || !(vpScale.pixelsPerUnit > 0)) {
      addToast({
        type: 'warning',
        title: t('takeoff_viewer.viewport_scale_missing', { defaultValue: 'Pick a scale for the viewport' }),
      });
      return;
    }
    const vp: Viewport = {
      id: d.id ?? `vp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
      name: d.name.trim() || 'Viewport',
      rect: d.rect,
      scale: vpScale,
      scaleLabel,
    };
    setPageScales((prev) => upsertViewport(prev, d.page, vp));
    setViewportDialog(null);
  }, [viewportDialog, selectedMeasurementId, measurementSystem, addToast, t]);

  /** Delete a viewport; rows that were inside it fall back to the page scale. */
  const deleteViewport = useCallback(
    (page: number, id: string) => {
      const next = removeViewport(pageScales, page, id);
      setPageScales(next);
      setMeasurements((ms) =>
        reconcilePageValues(ms, next, page, (m, pts, sc) => recomputeMeasurement(m, pts, sc) as Partial<Measurement>),
      );
    },
    [pageScales],
  );

  const placeStamp = useCallback("""),

# ── click: exact point + viewport corners ────────────────────────────
("""      let point: Point = { x, y };
""", """      let point: Point = { x, y };
      // Sketch to Scale: a typed exact vertex replaces the synthetic click
      // position and skips snap / ortho below (""" + TAG + """).
      const exactPoint = exactPointRef.current;
      exactPointRef.current = null;
      if (exactPoint) point = exactPoint;
      // Viewport drawing: two corner clicks, then the scale dialog.
      const vpDraft = viewportDraftRef.current;
      if (vpDraft && !exactPoint) {
        if (!vpDraft.start) {
          setViewportDraft({ start: point, cursor: point });
          return;
        }
        const vpRect = normalizeRect(vpDraft.start, point);
        setViewportDraft(null);
        if (vpRect.w * zoom < 8 || vpRect.h * zoom < 8) return;
        const existing = viewportsForPage(sketchCtxRef.current.pageScales, currentPage);
        setViewportDialog({
          page: currentPage,
          id: null,
          rect: vpRect,
          name: `Viewport ${existing.length + 1}`,
          preset: '1:20',
          ratio: '',
          knownLength: '',
        });
        return;
      }
"""),
("""      const vsnap = vertexSnapRef.current && canVertexSnap""",
 """      const vsnap = !exactPoint && vertexSnapRef.current && canVertexSnap"""),
("""        const csnap = canVertexSnap && contentSnapRef.current""",
 """        const csnap = !exactPoint && canVertexSnap && contentSnapRef.current"""),
("""        !settingScale &&
        !vsnap &&
        (orthoLock || shiftHeldRef.current) &&""", """        !settingScale &&
        !vsnap &&
        !exactPoint &&
        (orthoLock || shiftHeldRef.current) &&"""),

# ── mousedown: an armed viewport owns the press ──────────────────────
("""  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
""", """  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      // Drawing a viewport: the click handler takes the corners; no marquee,
      // drag or pen stroke may start (""" + TAG + """).
      if (viewportDraftRef.current && e.button === 0) return;
"""),

# ── mousemove: rubber-band the viewport ──────────────────────────────
("""      if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'rectarea' || activeTool === 'ellipse') && rectStartPoint) {""",
 """      if (viewportDraftRef.current?.start && pt) {
        const vStart = viewportDraftRef.current.start;
        setViewportDraft({ start: vStart, cursor: pt });
        return;
      }

      if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'rectarea' || activeTool === 'ellipse') && rectStartPoint) {"""),

# ── keyboard: digits open Sketch to Scale, Esc cancels a viewport ───
("""      // Fit shortcuts (Shift+1 / Shift+2 / Shift+3). Digit codes are used so""",
 """      // Sketch to Scale (""" + TAG + """): a digit while a
      // segment is in progress opens the exact-length entry with that digit.
      if (!e.shiftKey && /^[0-9.]$/.test(e.key)) {
        const sc = sketchCtxRef.current;
        if (SKETCH_TOOLS.has(sc.activeTool) && sc.activePoints.length > 0) {
          e.preventDefault();
          setSketchInput(e.key);
          return;
        }
      }
      if (e.key === 'Escape' && viewportDraftRef.current) {
        e.preventDefault();
        setViewportDraft(null);
        return;
      }

      // Fit shortcuts (Shift+1 / Shift+2 / Shift+3). Digit codes are used so"""),

# ── render: viewport frames + draft ──────────────────────────────────
("""    // Draw active points (in-progress measurement)
""", """    // Viewports (""" + TAG + """): dashed purple frame
    // with a name + scale tag, plus the rubber-band while drawing one.
    {
      const vk = dpr * zoom;
      ctx.save();
      ctx.setLineDash([6 * dpr, 4 * dpr]);
      ctx.lineWidth = 1.5 * dpr;
      ctx.font = `600 ${11 * dpr}px system-ui, sans-serif`;
      ctx.textBaseline = 'alphabetic';
      for (const vp of viewportsForPage(pageScales, currentPage)) {
        const { x, y, w, h } = vp.rect;
        ctx.strokeStyle = '#7c3aed';
        ctx.strokeRect(x * vk, y * vk, w * vk, h * vk);
        const tag = `${vp.name} \\u00B7 ${vp.scaleLabel ?? formatScaleRatio(vp.scale)}`;
        const tw = ctx.measureText(tag).width + 8 * dpr;
        const th = 16 * dpr;
        const ty = y * vk >= th ? y * vk - th : y * vk;
        ctx.fillStyle = 'rgba(124,58,237,0.9)';
        ctx.fillRect(x * vk, ty, tw, th);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(tag, x * vk + 4 * dpr, ty + th - 4 * dpr);
      }
      if (viewportDraft?.start && viewportDraft.cursor) {
        const r = normalizeRect(viewportDraft.start, viewportDraft.cursor);
        ctx.fillStyle = 'rgba(124,58,237,0.08)';
        ctx.fillRect(r.x * vk, r.y * vk, r.w * vk, r.h * vk);
        ctx.strokeStyle = '#7c3aed';
        ctx.strokeRect(r.x * vk, r.y * vk, r.w * vk, r.h * vk);
      }
      ctx.restore();
    }

    // Draw active points (in-progress measurement)
"""),
("""showTextInput, editingTextId]);""", """showTextInput, editingTextId, viewportDraft]);"""),

# ── toolbar: Viewports button + panel ────────────────────────────────
("""              {/* Measure tools - one segmented track, icon-only with tooltips""",
 """              {/* Viewports (""" + TAG + """): scaled regions of
                  the sheet. Button arms drawing; the chevron panel lists them. */}
              <div className="relative inline-flex items-center gap-0.5">
                <button
                  onClick={() => {
                    setShowViewportPanel(false);
                    setViewportDraft((d) => (d ? null : { start: null, cursor: null }));
                  }}
                  className={tbBtn(viewportDraft != null, 'purple')}
                  title={t('takeoff_viewer.viewport_draw', { defaultValue: 'Draw a viewport with its own scale (click two corners)' })}
                  aria-pressed={viewportDraft != null}
                  data-testid="viewport-button"
                >
                  <Frame size={15} />
                  <span className="hidden sm:inline">
                    {viewportDraft
                      ? t('takeoff_viewer.viewport_drawing', { defaultValue: 'Click 2 corners…' })
                      : t('takeoff_viewer.viewports', { defaultValue: 'Viewports' })}
                    {!viewportDraft && viewportsForPage(pageScales, currentPage).length > 0
                      ? ` (${viewportsForPage(pageScales, currentPage).length})`
                      : ''}
                  </span>
                </button>
                {viewportsForPage(pageScales, currentPage).length > 0 && (
                  <button
                    onClick={() => setShowViewportPanel((v) => !v)}
                    className="h-7 rounded-md px-1 text-content-tertiary hover:bg-surface-secondary"
                    aria-label={t('takeoff_viewer.viewport_list', { defaultValue: 'Viewport list' })}
                    data-testid="viewport-list-toggle"
                  >
                    <ChevronDown size={13} />
                  </button>
                )}
                {showViewportPanel && (
                  <div className="absolute left-0 top-full z-40 mt-1 w-72 rounded-lg border border-border bg-surface-elevated p-2 shadow-lg" data-testid="viewport-panel">
                    <div className="mb-1 px-1 text-[11px] font-semibold uppercase tracking-wide text-content-tertiary">
                      {t('takeoff_viewer.viewports_on_page', { defaultValue: 'Viewports on this page' })}
                    </div>
                    {viewportsForPage(pageScales, currentPage).map((vp) => (
                      <div key={vp.id} className="flex items-center gap-2 rounded px-1 py-1 text-xs hover:bg-surface-secondary">
                        <span className="min-w-0 flex-1 truncate text-content-primary">{vp.name}</span>
                        <span className="font-mono text-[11px] text-purple-600 dark:text-purple-300">{vp.scaleLabel ?? formatScaleRatio(vp.scale)}</span>
                        <button
                          onClick={() => {
                            setShowViewportPanel(false);
                            const known = DRAWING_SCALE_PRESETS.find((sp) => sp.label === vp.scaleLabel);
                            setViewportDialog({
                              page: currentPage,
                              id: vp.id,
                              rect: vp.rect,
                              name: vp.name,
                              preset: known ? known.label : '__ratio',
                              ratio: known ? '' : String(Math.round(ratioFromScale(vp.scale))),
                              knownLength: '',
                            });
                          }}
                          className="text-content-secondary hover:text-content-primary"
                          title={t('common.edit', { defaultValue: 'Edit' })}
                        >
                          <Pencil size={12} />
                        </button>
                        <button
                          onClick={() => deleteViewport(currentPage, vp.id)}
                          className="text-content-secondary hover:text-red-600"
                          title={t('common.delete', { defaultValue: 'Delete' })}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Measure tools - one segmented track, icon-only with tooltips"""),

# ── dialogs: viewport scale + sketch entry ──────────────────────────
("""      {/* Callout / custom stamp text (OE-DELIVERY 2026-10-30-revu-markup-tools) */}""",
 """      {/* Viewport scale dialog (""" + TAG + """) */}
      {viewportDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-80 rounded-xl border border-border bg-surface-elevated p-5 shadow-lg" data-testid="viewport-dialog">
            <h3 className="mb-3 text-sm font-semibold text-content-primary">
              {viewportDialog.id
                ? t('takeoff_viewer.viewport_edit', { defaultValue: 'Edit viewport' })
                : t('takeoff_viewer.viewport_new', { defaultValue: 'New viewport' })}
            </h3>
            <label className="mb-1 block text-xs text-content-secondary">{t('common.name', { defaultValue: 'Name' })}</label>
            <input
              value={viewportDialog.name}
              onChange={(e) => {
                const name = e.target.value;
                setViewportDialog((d) => (d ? { ...d, name } : d));
              }}
              autoFocus
              className="mb-3 w-full rounded border border-border bg-surface-secondary px-2 py-1.5 text-sm text-content-primary"
            />
            <label className="mb-1 block text-xs text-content-secondary">{t('takeoff_viewer.viewport_scale', { defaultValue: 'Scale' })}</label>
            <select
              value={viewportDialog.preset}
              onChange={(e) => {
                const preset = e.target.value;
                setViewportDialog((d) => (d ? { ...d, preset } : d));
              }}
              className="mb-3 w-full rounded border border-border bg-surface-secondary px-2 py-1.5 text-sm text-content-primary"
            >
              {(['metric', 'architectural', 'civil'] as const).map((g) => (
                <optgroup key={g} label={g === 'metric' ? 'Metric' : g === 'architectural' ? 'Architectural' : 'Civil'}>
                  {DRAWING_SCALE_PRESETS.filter((sp) => sp.group === g).map((sp) => (
                    <option key={sp.label} value={sp.label}>{sp.label}</option>
                  ))}
                </optgroup>
              ))}
              <option value="__ratio">{t('takeoff_viewer.viewport_custom_ratio', { defaultValue: 'Custom 1:N…' })}</option>
              <option value="__line">{t('takeoff_viewer.viewport_from_line', { defaultValue: 'From the selected line…' })}</option>
            </select>
            {viewportDialog.preset === '__ratio' && (
              <input
                value={viewportDialog.ratio}
                onChange={(e) => {
                  const ratio = e.target.value;
                  setViewportDialog((d) => (d ? { ...d, ratio } : d));
                }}
                placeholder="1:75"
                className="mb-3 w-full rounded border border-border bg-surface-secondary px-2 py-1.5 text-sm text-content-primary"
              />
            )}
            {viewportDialog.preset === '__line' && (
              <>
                <p className="mb-1 text-[11px] text-content-tertiary">
                  {(() => {
                    const sel = measurements.find((m) => m.id === selectedMeasurementId);
                    return sel && sel.points.length >= 2
                      ? t('takeoff_viewer.viewport_line_hint', { defaultValue: 'True length of the selected line:' })
                      : t('takeoff_viewer.viewport_line_none', { defaultValue: 'Select a line inside the viewport first (Distance), then reopen this dialog.' });
                  })()}
                </p>
                <input
                  value={viewportDialog.knownLength}
                  onChange={(e) => {
                    const knownLength = e.target.value;
                    setViewportDialog((d) => (d ? { ...d, knownLength } : d));
                  }}
                  placeholder={measurementSystem === 'imperial' ? `12'6"` : '2.4'}
                  className="mb-3 w-full rounded border border-border bg-surface-secondary px-2 py-1.5 text-sm text-content-primary"
                />
              </>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setViewportDialog(null)}
                className="rounded-lg px-3 py-1.5 text-xs text-content-secondary transition-colors hover:bg-surface-secondary"
              >
                {t('common.cancel', { defaultValue: 'Cancel' })}
              </button>
              <button
                onClick={saveViewportDialog}
                className="rounded-lg bg-oe-blue px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-oe-blue-hover"
                data-testid="viewport-save"
              >
                {t('common.save', { defaultValue: 'Save' })}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Sketch to Scale entry (""" + TAG + """) */}
      {sketchInput !== null && (
        <div className="fixed bottom-6 left-1/2 z-50 w-[22rem] max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-xl border border-border bg-surface-elevated p-3 shadow-lg" data-testid="sketch-to-scale">
          <div className="mb-1 text-xs font-semibold text-content-primary">
            {t('takeoff_viewer.sketch_title', { defaultValue: 'Sketch to Scale - next segment length' })}
          </div>
          <input
            value={sketchInput}
            onChange={(e) => setSketchInput(e.target.value)}
            autoFocus
            onFocus={(e) => {
              const el = e.currentTarget;
              el.setSelectionRange(el.value.length, el.value.length);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                confirmSketch(sketchInput);
              } else if (e.key === 'Escape') {
                e.preventDefault();
                setSketchInput(null);
              }
            }}
            className="w-full rounded border border-border bg-surface-secondary px-2 py-1.5 font-mono text-sm text-content-primary"
          />
          <div className="mt-1 text-[11px] text-content-tertiary">
            {t('takeoff_viewer.sketch_help', {
              defaultValue: 'Enter places it toward the cursor. Add <angle for a direction (12.5<90 = straight up). Units: {{unit}}, or type mm / cm / m / ft / in / 12\\'6".',
              unit: measurementSystem === 'imperial' ? 'ft' : 'm',
            })}
          </div>
        </div>
      )}
      {/* Callout / custom stamp text (OE-DELIVERY 2026-10-30-revu-markup-tools) */}"""),
]
bad = [(old[:90], s.count(old)) for old, _ in pairs if s.count(old) != 1]
if bad:
    print('NOT WRITTEN, anchors:', bad)
    sys.exit(1)
for old, new in pairs:
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok', len(pairs))
