"""Revu Properties + show/hide by type + zoom feel (anchored, all-or-nothing across files).
OE-DELIVERY: 2026-11-02-revu-properties"""
import sys
from pathlib import Path

root = Path(sys.argv[1])  # frontend/src
TAG = 'OE-DELIVERY 2026-11-02-revu-properties'
FIELDS_DOC = """  /** Revu-style per-markup properties (""" + TAG + """):
   *  line pattern, a fill colour independent of the line colour, and which
   *  label parts show on the drawing. Undefined = previous behaviour. */
  lineStyle?: 'solid' | 'dashed' | 'dotted' | 'dashdot';
  fillColor?: string;
  labelMode?: 'all' | 'value' | 'name' | 'none';
"""

edits = {
'features/takeoff/lib/takeoff-types.ts': [
("""  strokeAlpha?: number;
  /** True-surface slope""", """  strokeAlpha?: number;
""" + FIELDS_DOC + """  /** True-surface slope"""),
],
'modules/pdf-takeoff/useMeasurementPersistence.ts': [
("""  strokeAlpha?: number;
""", """  strokeAlpha?: number;
""" + FIELDS_DOC),
# create metadata
("""      stroke_alpha: m.strokeAlpha,
""", """      stroke_alpha: m.strokeAlpha,
      // Revu-style properties (""" + TAG + """).
      line_style: m.lineStyle,
      fill_color: m.fillColor,
      label_mode: m.labelMode,
"""),
# sync signature
("""    sa: m.strokeAlpha ?? null,
""", """    sa: m.strokeAlpha ?? null,
    ls: m.lineStyle ?? null,
    fc: m.fillColor ?? null,
    lm: m.labelMode ?? null,
"""),
# update metadata: explicit null clears (server merges metadata)
("""    stroke_alpha: m.strokeAlpha,
    // Reported-quantity adjustments (issue #332 wave). Explicitly NULL when""", """    stroke_alpha: m.strokeAlpha,
    // Revu-style properties (""" + TAG + """); NULL clears.
    line_style: m.lineStyle ?? null,
    fill_color: m.fillColor ?? null,
    label_mode: m.labelMode ?? null,
    // Reported-quantity adjustments (issue #332 wave). Explicitly NULL when"""),
# read back
("""    strokeAlpha: (meta.stroke_alpha as number) ?? undefined,
""", """    strokeAlpha: (meta.stroke_alpha as number) ?? undefined,
    lineStyle: isLineStyle(meta.line_style) ? meta.line_style : undefined,
    fillColor: typeof meta.fill_color === 'string' ? meta.fill_color : undefined,
    labelMode: isLabelMode(meta.label_mode) ? meta.label_mode : undefined,
"""),
("""import { normalizeOpening } from '@/features/takeoff/lib/takeoff-quantity';
""", """import { normalizeOpening } from '@/features/takeoff/lib/takeoff-quantity';
import { isLabelMode, isLineStyle } from './data/revu-style';
"""),
],
'modules/pdf-takeoff/TakeoffViewerModule.tsx': [
# types
("""  strokeAlpha?: number; // Per-measurement LINE opacity 0..1 for linear types (issue #332)
""", """  strokeAlpha?: number; // Per-measurement LINE opacity 0..1 for linear types (issue #332)
""" + FIELDS_DOC),
# imports
("""import { useTranslation } from 'react-i18next';
""", """import { useTranslation } from 'react-i18next';
// Revu Properties (""" + TAG + """).
import { RevuStyleFields, type StyleField } from './RevuStyleFields';
import {
  type ToolStyle,
  type ToolStyles,
  lineDashFor,
  labelParts,
  loadToolStyles,
  saveToolStyles,
  patchToolStyle,
  styleFieldsFor,
  wheelZoomFactor,
  TYPE_LABELS,
} from './data/revu-style';
"""),
("""import { useState, useRef, useCallback, useEffect, useMemo, lazy""",
 """import { useState, useRef, useCallback, useEffect, useLayoutEffect, useMemo, lazy"""),
# state, after the viewport state block
("""  const exactPointRef = useRef<Point | null>(null);
""", """  const exactPointRef = useRef<Point | null>(null);
  /* Revu Properties (""" + TAG + """): per-tool style for the
   * next markup, and show/hide by markup type. */
  const [toolStyles, setToolStyles] = useState<ToolStyles>(() => loadToolStyles());
  const toolStylesRef = useRef(toolStyles);
  toolStylesRef.current = toolStyles;
  useEffect(() => saveToolStyles(toolStyles), [toolStyles]);
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem('takeoff.hiddenTypes');
      const arr = raw ? (JSON.parse(raw) as unknown) : [];
      return new Set(Array.isArray(arr) ? arr.filter((x): x is string => typeof x === 'string') : []);
    } catch {
      return new Set();
    }
  });
  const hiddenTypesRef = useRef(hiddenTypes);
  hiddenTypesRef.current = hiddenTypes;
  useEffect(() => {
    try { localStorage.setItem('takeoff.hiddenTypes', JSON.stringify([...hiddenTypes])); } catch { /* ignore */ }
  }, [hiddenTypes]);
  const [showTypeFilter, setShowTypeFilter] = useState(false);
"""),
# new markups pick up the armed tool's style
("""    const stamp: Partial<Measurement> = {
      author: useAuthStore.getState().userFullName || undefined,
      createdAt: new Date().toISOString(),
    };""", """    const stamp: Partial<Measurement> = {
      // The armed tool's Revu-style properties (""" + TAG + """).
      ...styleFieldsFor(toolStylesRef.current, sketchCtxRef.current.activeTool),
      author: useAuthStore.getState().userFullName || undefined,
      createdAt: new Date().toISOString(),
    };"""),
("""      setAnnotationColor(DEFAULT_ANNOTATION_COLORS[tool]);""",
 """      setAnnotationColor(toolStylesRef.current[tool]?.color ?? DEFAULT_ANNOTATION_COLORS[tool]);"""),
# draw: label mode + line style + fill colour
("""    const isDark = document.documentElement.classList.contains('dark');
    const drawAnnotationLabel = (""", """    const isDark = document.documentElement.classList.contains('dark');
    /** Label mode of the measurement being painted (""" + TAG + """). */
    let curLabelMode: Measurement['labelMode'];
    const drawAnnotationLabel = ("""),
("""      if (!showLabels) return;
      const fontSize = 11 * dpr;""", """      if (!showLabels || curLabelMode === 'none' || curLabelMode === 'value') return;
      const fontSize = 11 * dpr;"""),
("""      const showName = labelShowName && name.length > 0;
      const showMaterial = labelShowMaterial && material.length > 0;
      const showValue = showDimensions && labelShowDimension && value.length > 0;""",
 """      // Per-markup label mode narrows the global switches (""" + TAG + """).
      const parts = labelParts(m.labelMode);
      const showName = labelShowName && parts.name && name.length > 0;
      const showMaterial = labelShowMaterial && parts.material && material.length > 0;
      const showValue = showDimensions && labelShowDimension && parts.value && value.length > 0;"""),
("""      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      // Optional per-measurement stroke width""", """      ctx.strokeStyle = color;
      // Revu fill colour, independent of the line colour (""" + TAG + """).
      ctx.fillStyle = m.fillColor ?? color;
      curLabelMode = m.labelMode;
      // Optional per-measurement stroke width"""),
("""      ctx.globalAlpha = m.suggested ? 0.5 : 1.0;
      ctx.setLineDash(m.suggested ? [6 * dpr, 4 * dpr] : []);""", """      ctx.globalAlpha = m.suggested ? 0.5 : 1.0;
      ctx.setLineDash(m.suggested ? [6 * dpr, 4 * dpr] : lineDashFor(m.lineStyle, baseStrokeWidth * dpr * zoom));"""),
# draw: hide by type
("""!hiddenMeasurements.has(m.id) && !(isAnnotationType(m.type) && hiddenGroups.has('__annotations__')))) {""",
 """!hiddenMeasurements.has(m.id) && !hiddenTypes.has(m.type) && !(isAnnotationType(m.type) && hiddenGroups.has('__annotations__')))) {"""),
("""showTextInput, editingTextId, viewportDraft]);""", """showTextInput, editingTextId, viewportDraft, hiddenTypes]);"""),
# hit-test: hidden types cannot be picked
("""        !hiddenM.has(m.id) &&
        !(isAnnotationType(m.type) && hidden.has('__annotations__')),""", """        !hiddenM.has(m.id) &&
        !hiddenTypesRef.current.has(m.type) &&
        !(isAnnotationType(m.type) && hidden.has('__annotations__')),"""),

# zoom feel: notch steps for a mouse wheel, smooth for trackpads
("""  const applyWheelZoom = useCallback((deltaY: number, clientX: number, clientY: number) => {
    const next = wheelZoomStep(liveZoomRef.current, deltaY);""", """  const applyWheelZoom = useCallback((deltaY: number, clientX: number, clientY: number, deltaMode = 0) => {
    // Revu feel (""" + TAG + """): one clear 1.2x step per
    // mouse-wheel notch, proportional glide for trackpads / pinch.
    const next = clampZoom(liveZoomRef.current * wheelZoomFactor(deltaY, deltaMode));"""),
("""      applyWheelZoom(e.deltaY, e.clientX, e.clientY);""", """      applyWheelZoom(e.deltaY, e.clientX, e.clientY, e.deltaMode);"""),
("""      applyWheelZoom(e.deltaY, rect.left + rect.width / 2, rect.top + rect.height / 2);""",
 """      applyWheelZoom(e.deltaY, rect.left + rect.width / 2, rect.top + rect.height / 2, e.deltaMode);"""),
# the crisp re-render lands sooner after a gesture settles
("""      setRenderZoom(zoom);
    }, 150);""", """      setRenderZoom(zoom);
    }, 90);"""),
# size + anchor + paint before the frame is shown, so the sheet never drifts
# from the cursor for a frame and markups never flash blank mid-zoom
("""  /* ── Live-zoom CSS follow ────────────────────────────────────────────""",
 """  /* Layout effects (""" + TAG + """): the canvas size, the
   * cursor anchor and the markup repaint all land before the browser paints,
   * so a zoom step is one clean frame (Revu feel) instead of a drift-and-snap. */
  /* ── Live-zoom CSS follow ────────────────────────────────────────────"""),
("""    canvas.style.width = `${pageW * zoom}px`;
    canvas.style.height = `${pageH * zoom}px`;
    const overlay = overlayRef.current;
    if (overlay) {
      overlay.style.width = canvas.style.width;
      overlay.style.height = canvas.style.height;
    }
  }, [zoom, pdfDoc, currentPage, pageMode]);""", """    canvas.style.width = `${pageW * zoom}px`;
    canvas.style.height = `${pageH * zoom}px`;
    const overlay = overlayRef.current;
    if (overlay) {
      overlay.style.width = canvas.style.width;
      overlay.style.height = canvas.style.height;
    }
    applyZoomAnchorRef.current();
  }, [zoom, pdfDoc, currentPage, pageMode]);"""),
]
}

# useEffect -> useLayoutEffect for the three zoom-critical effects, by anchor
LAYOUT = [
("""  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !pdfDoc || pageMode !== 'single') return;
    // Don't size from a stale bitmap while a page change is in flight.""",
 """  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !pdfDoc || pageMode !== 'single') return;
    // Don't size from a stale bitmap while a page change is in flight."""),
("""  useEffect(() => {
    const overlay = overlayRef.current;
    const canvas = canvasRef.current;
    if (!overlay || !canvas || !pdfDoc || pageMode !== 'single') return;""",
 """  useLayoutEffect(() => {
    const overlay = overlayRef.current;
    const canvas = canvasRef.current;
    if (!overlay || !canvas || !pdfDoc || pageMode !== 'single') return;"""),
("""  useEffect(() => {
    if (!overlayRef.current) return;
    const dpr = window.devicePixelRatio;
    // Deep zoom""", """  useLayoutEffect(() => {
    if (!overlayRef.current) return;
    const dpr = window.devicePixelRatio;
    // Deep zoom"""),
]

texts = {f: (root / f).read_text(encoding='utf-8') for f in edits}
bad = []
for f, pairs in edits.items():
    for old, _ in pairs:
        if texts[f].count(old) != 1:
            bad.append((f.split('/')[-1], old[:70], texts[f].count(old)))
v = 'modules/pdf-takeoff/TakeoffViewerModule.tsx'
for old, _ in LAYOUT:
    if texts[v].count(old) != 1:
        bad.append(('layout', old[:70], texts[v].count(old)))
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for f, pairs in edits.items():
    s = texts[f]
    for old, new in pairs:
        s = s.replace(old, new)
    if f == v:
        for old, new in LAYOUT:
            s = s.replace(old, new)
    (root / f).write_text(s, encoding='utf-8')
print('ok')
