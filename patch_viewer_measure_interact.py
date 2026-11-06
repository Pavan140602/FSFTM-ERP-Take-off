# OE-DELIVERY: 2026-10-30-viewer-measure-interact
"""Viewer patch 5: universal markup interaction for PDF Measurements.

Run AFTER patch_viewer_detect4.py:
    python patch_viewer_measure_interact.py   (from the repo root)

What changes in TakeoffViewerModule.tsx:
  1. Arrow keys nudge the selected markup(s) on the current page
     (1 unit per press, Shift = 10). A burst of presses coalesces
     into one undo frame per markup, flushed ~700 ms after the last
     press. Typing in a field never nudges (the standard shortcut
     focus guard), and the arrows belong to the Detect lines while
     Detect pick mode is on.
  2. Shift+drag on a markup duplicates it: the copy follows the
     pointer and lands where it is released, recorded as ONE
     creation undo frame; Esc mid-drag removes the copy again. A
     plain Shift+click (no drag) still toggles the markup in the
     multi-select set, exactly as before - the toggle now happens
     on release so the two gestures can be told apart.
  3. The Properties panel gains a Length field for distance
     markups: typing a new length resizes the segment on the sheet
     live (start point fixed, along its own direction); the undo
     frame is pushed once when the field loses focus.

Ledger <-> canvas selection sync already exists in the product
(MeasurementLedger scrolls the selected row into view and row
clicks select on the canvas), so it is not touched here.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-measure-interact.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-measure-interact")
ALREADY_MARKER = "shiftPendingRef"
REQUIRED_MARKER = "oe-detect:duplicate"

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "dragRef gains duplicate-drag fields",
        """    /** The latest dragged points - the authoritative geometry the commit
     *  uses on mouseup (state only holds the pre-drag copy mid-drag). */
    lastPoints: Point[];
  } | null>(null);""",
        """    /** The latest dragged points - the authoritative geometry the commit
     *  uses on mouseup (state only holds the pre-drag copy mid-drag). */
    lastPoints: Point[];
    /** Shift+drag duplicate: this drag moves a freshly minted clone of
     *  `sourceId`; commit records a creation (not an edit) and abort
     *  removes the clone again. */
    wasDuplicate?: boolean;
    /** The measurement the clone was copied from (abort reselect). */
    sourceId?: string;
  } | null>(null);""",
    ),
    (
        "shift-pending + nudge bookkeeping refs",
        """  } | null>(null);
  /** Active legend-box corner resize. Separate from dragRef so the two never""",
        """  } | null>(null);
  /** A Shift+press on a markup body whose intent is not yet known: a
   *  plain release toggles the markup in the multi-select set (the
   *  long-standing Shift+click), while a drag past the threshold
   *  converts it into a duplicate drag of a fresh clone. */
  const shiftPendingRef = useRef<{
    measurementId: string;
    startPt: Point;
    source: Measurement;
  } | null>(null);
  /** Arrow-key nudge bookkeeping: the pre-burst originals of every
   *  measurement the current key burst has moved, flushed into undo
   *  frames ~700 ms after the last press so a held key stays a
   *  single undo step per markup. */
  const nudgeUndoRef = useRef<{ originals: Map<string, Measurement>; timer: number | null }>({
    originals: new Map(),
    timer: null,
  });
  /** Active legend-box corner resize. Separate from dragRef so the two never""",
    ),
    (
        "finishDrag: duplicate commit records a creation",
        """      if (commit && drag.moved) {
        // The committed geometry is the last dragged points (state only
        // holds the pre-drag copy mid-drag), recomputed server-side on PATCH.
        commitGeometryEdit(drag.measurementId, drag.original, drag.lastPoints);
      } else if (!commit) {""",
        """      if (commit && drag.moved) {
        if (drag.wasDuplicate) {
          // Shift+drag copy: the clone already lives in state at its
          // birth position; land it at the dragged points and record
          // the whole gesture as ONE creation undo frame.
          const base = drag.original;
          const patch = recomputeMeasurement(base, drag.lastPoints, editScaleRef.current);
          const finalClone: Measurement = {
            ...base,
            points: drag.lastPoints,
            value: patch.value,
            label: patch.label,
            unit: patch.unit ?? base.unit,
            ...(patch.area !== undefined ? { area: patch.area } : {}),
            ...(patch.width !== undefined ? { width: patch.width } : {}),
            ...(patch.height !== undefined ? { height: patch.height } : {}),
          };
          setMeasurements((prev) => prev.map((x) => (x.id === drag.measurementId ? finalClone : x)));
          pushUndo({ kind: 'complete_measurement', measurement: finalClone, previousActivePoints: [] });
        } else {
          // The committed geometry is the last dragged points (state only
          // holds the pre-drag copy mid-drag), recomputed server-side on PATCH.
          commitGeometryEdit(drag.measurementId, drag.original, drag.lastPoints);
        }
      } else if (!commit) {""",
    ),
    (
        "finishDrag: duplicate abort removes the clone",
        """      } else if (!commit) {
        // Abort: restore the pre-drag geometry, no undo frame.
        setMeasurements((prev) =>""",
        """      } else if (!commit) {
        if (drag.wasDuplicate) {
          // Abort: the copy never happened - remove the clone and put
          // the selection back on the source markup.
          setMeasurements((prev) => prev.filter((x) => x.id !== drag.measurementId));
          if (drag.sourceId) setSelectedMeasurementId(drag.sourceId);
          return;
        }
        // Abort: restore the pre-drag geometry, no undo frame.
        setMeasurements((prev) =>""",
    ),
    (
        "finishDrag deps + nudge helpers",
        """        setMeasurements((prev) =>
          prev.map((m) =>
            m.id === drag.measurementId
              ? { ...drag.original, points: [...drag.original.points] }
              : m,
          ),
        );
      }
    },
    [commitGeometryEdit],
  );""",
        """        setMeasurements((prev) =>
          prev.map((m) =>
            m.id === drag.measurementId
              ? { ...drag.original, points: [...drag.original.points] }
              : m,
          ),
        );
      }
    },
    [commitGeometryEdit, pushUndo],
  );

  /** Flush the pending arrow-key nudge burst into undo frames: one
   *  edit_geometry frame per moved markup, previous = its position
   *  before the burst started. */
  const flushNudgeUndo = useCallback(() => {
    const bag = nudgeUndoRef.current;
    bag.timer = null;
    if (bag.originals.size === 0) return;
    const originals = bag.originals;
    bag.originals = new Map();
    for (const [id, original] of originals) {
      const cur = measurementsRef.current.find((x) => x.id === id);
      if (!cur) continue;
      const moved =
        cur.points.length !== original.points.length ||
        cur.points.some((p, i) => p.x !== original.points[i]!.x || p.y !== original.points[i]!.y);
      if (moved) {
        pushUndo({
          kind: 'edit_geometry',
          measurementId: id,
          previousMeasurement: { ...original, points: [...original.points] },
          nextMeasurement: { ...cur, points: [...cur.points] },
        });
      }
    }
  }, [pushUndo]);

  /** Translate the given markups by (dx, dy) PDF units, remembering
   *  pre-burst originals for the coalesced undo flush. Translation
   *  never changes a markup's value, so no recompute is needed. */
  const nudgeMeasurements = useCallback(
    (ids: Set<string>, dx: number, dy: number) => {
      const bag = nudgeUndoRef.current;
      setMeasurements((prev) =>
        prev.map((m) => {
          if (!ids.has(m.id)) return m;
          if (!bag.originals.has(m.id)) {
            bag.originals.set(m.id, { ...m, points: [...m.points] });
          }
          return { ...m, points: translatePoints(m.points, dx, dy) };
        }),
      );
      if (bag.timer) window.clearTimeout(bag.timer);
      bag.timer = window.setTimeout(flushNudgeUndo, 700);
    },
    [flushNudgeUndo],
  );""",
    ),
    (
        "pointerdown: shift press defers the toggle (drag may duplicate)",
        """        // Shift+click: toggle this markup in the multi-select set (no drag).
        if (e.shiftKey) {
          e.preventDefault();
          setHoverInfo(null);
          toggleMarqueeSelection(m.id);
          return;
        }""",
        """        // Shift+press: a plain release toggles this markup in the
        // multi-select set (the long-standing Shift+click); a drag
        // instead duplicates the markup - the copy follows the
        // pointer and lands on release. The toggle is deferred to
        // the release so the two gestures can be told apart.
        if (e.shiftKey) {
          e.preventDefault();
          setHoverInfo(null);
          shiftPendingRef.current = {
            measurementId: m.id,
            startPt: pt,
            source: { ...m, points: [...m.points] },
          };
          return;
        }""",
    ),
    (
        "canvas mousemove: a dragged shift-press converts into a duplicate drag",
        """      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;
      if (dragRef.current) {""",
        """      // A pan in progress is driven by the window listener; ignore here.
      if (panRef.current) return;
      if (shiftPendingRef.current) {
        const pending = shiftPendingRef.current;
        if (e.buttons === 0) {
          // The press ended off-canvas without a mouseup reaching
          // us: treat it as the plain Shift+click it turned out to be.
          shiftPendingRef.current = null;
          toggleMarqueeSelection(pending.measurementId);
          return;
        }
        const cur0 = pointerToPdf(e);
        if (cur0 && Math.hypot(cur0.x - pending.startPt.x, cur0.y - pending.startPt.y) * (zoomRef.current || 1) > 5) {
          // The press became a drag: mint the copy now (at the source
          // position) and arm a normal shape drag on it.
          shiftPendingRef.current = null;
          const src = pending.source;
          const clone: Measurement = {
            ...src,
            id: `m_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            points: src.points.map((p) => ({ ...p })),
            serverId: undefined,
            suggested: undefined,
            linkedPositionId: undefined,
            linkedPositionOrdinal: undefined,
            linkedBoqId: undefined,
            linkedPositionLabel: undefined,
          };
          setMeasurements((prev) => [...prev, clone]);
          setSelectedMeasurementId(clone.id);
          dragRef.current = {
            mode: 'shape',
            measurementId: clone.id,
            original: { ...clone, points: [...clone.points] },
            origPoints: [...clone.points],
            vertexIndex: -1,
            startPt: pending.startPt,
            moved: true,
            lastPoints: [...clone.points],
            wasDuplicate: true,
            sourceId: src.id,
          };
          handleEditDragMove(e);
        }
        return;
      }
      if (dragRef.current) {""",
    ),
    (
        "canvas mousemove deps",
        """    [activeTool, rectStartPoint, pointerToPdf, handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, activePoints, orthoLock, liveCursor, editableOnPage, hoverInfo, settingScale, scalePoints],""",
        """    [activeTool, rectStartPoint, pointerToPdf, handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, activePoints, orthoLock, liveCursor, editableOnPage, hoverInfo, settingScale, scalePoints, toggleMarqueeSelection],""",
    ),
    (
        "canvas mouseup: an un-dragged shift-press performs its toggle",
        """    if (zoomAreaRef.current) finishZoomArea();
    else if (marqueeRef.current) finishMarquee();
    if (dragRef.current) finishDrag(true);""",
        """    if (zoomAreaRef.current) finishZoomArea();
    else if (marqueeRef.current) finishMarquee();
    if (shiftPendingRef.current) {
      const pending = shiftPendingRef.current;
      shiftPendingRef.current = null;
      toggleMarqueeSelection(pending.measurementId);
    }
    if (dragRef.current) finishDrag(true);""",
    ),
    (
        "canvas mouseup deps",
        """  }, [finishDrag, finishMarquee, finishZoomArea, finishLegendResize, finishTextResize]);""",
        """  }, [finishDrag, finishMarquee, finishZoomArea, finishLegendResize, finishTextResize, toggleMarqueeSelection]);""",
    ),
    (
        "window mouseup: an un-dragged shift-press performs its toggle",
        """    const onUp = (e: MouseEvent) => {
      // Catches a primary release outside the canvas, where no React mouseup or
      // click fires (#356).
      if (e.button === 0) pressActiveRef.current = false;""",
        """    const onUp = (e: MouseEvent) => {
      // Catches a primary release outside the canvas, where no React mouseup or
      // click fires (#356).
      if (e.button === 0) pressActiveRef.current = false;
      if (e.button === 0 && shiftPendingRef.current) {
        const pending = shiftPendingRef.current;
        shiftPendingRef.current = null;
        toggleMarqueeSelection(pending.measurementId);
      }""",
    ),
    (
        "window mouse listeners deps",
        """  }, [handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, finishDrag, finishLegendResize, finishTextResize, finishMarquee, pointerToPdf]);""",
        """  }, [handleEditDragMove, handleLegendResizeMove, handleTextResizeMove, finishDrag, finishLegendResize, finishTextResize, finishMarquee, pointerToPdf, toggleMarqueeSelection]);""",
    ),
    (
        "keyboard: arrow keys nudge the selection",
        """      // Delete / Backspace. Multi-select (ledger/marquee) takes precedence:""",
        """      // Arrow keys nudge the selected markup(s) on the current
      // page: 1 unit per press, Shift for a bigger step; a burst of
      // presses coalesces into one undo frame per markup (see
      // nudgeMeasurements). Skipped while Detect pick mode owns the
      // arrows for its lines, and behind the focus guard so typing
      // in a field never moves geometry.
      if (
        (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown') &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey &&
        shouldHandleShortcut(e.target) &&
        !detectPickMode
      ) {
        const wanted = new Set<string>(selectedLedgerIds);
        if (selectedMeasurementId) wanted.add(selectedMeasurementId);
        const targetIds = new Set<string>();
        for (const m of measurements) {
          if (wanted.has(m.id) && m.page === currentPage) targetIds.add(m.id);
        }
        if (targetIds.size > 0) {
          e.preventDefault();
          const step = e.shiftKey ? 10 : 1;
          const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
          const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
          nudgeMeasurements(targetIds, dx, dy);
          return;
        }
      }

      // Delete / Backspace. Multi-select (ledger/marquee) takes precedence:""",
    ),
    (
        "keyboard handler deps",
        """  }, [handleUndo, handleRedo, selectTool, activeTool, activePoints.length, rectStartPoint, showTextInput, showScaleDialog, showVolumeDepthInput, selectedMeasurementId, selectedLedgerIds, bulkDeleteSelected, calibrationMode, settingScale, measurements, finishDrag, commitGeometryEdit, pushUndo, fitToViewport, zoomToSelection, duplicateMeasurement, handleCanvasDblClick]);""",
        """  }, [handleUndo, handleRedo, selectTool, activeTool, activePoints.length, rectStartPoint, showTextInput, showScaleDialog, showVolumeDepthInput, selectedMeasurementId, selectedLedgerIds, bulkDeleteSelected, calibrationMode, settingScale, measurements, finishDrag, commitGeometryEdit, pushUndo, fitToViewport, zoomToSelection, duplicateMeasurement, handleCanvasDblClick, currentPage, detectPickMode, nudgeMeasurements]);""",
    ),
    (
        "Properties Length field handlers",
        """    [selectedMeasurementId, selectedLedgerIds, customGroupColors],
  );

  /** The markups the Colours-tab label sliders act on: the multi-select set""",
        """    [selectedMeasurementId, selectedLedgerIds, customGroupColors],
  );

  /** Properties-panel Length editing for distance markups: typing a
   *  new length resizes the segment on the sheet at once (start point
   *  fixed, along its own direction, via the measurement's own
   *  value-to-points ratio so it is exact at any page scale); the
   *  undo frame is pushed once, when the field loses focus. */
  const propLengthEditRef = useRef<{ id: string; original: Measurement } | null>(null);
  const handleLengthFieldChange = (m: Measurement, raw: string) => {
    const target = parseFloat(raw);
    if (!Number.isFinite(target) || target <= 0 || m.points.length !== 2) return;
    const a = m.points[0];
    const b = m.points[1];
    if (!a || !b) return;
    const curPx = Math.hypot(b.x - a.x, b.y - a.y);
    if (curPx < 0.001 || m.value <= 0) return;
    if (!propLengthEditRef.current || propLengthEditRef.current.id !== m.id) {
      propLengthEditRef.current = { id: m.id, original: { ...m, points: [...m.points] } };
    }
    const newPx = (target / m.value) * curPx;
    const nextPoints: Point[] = [
      { ...a },
      { x: a.x + ((b.x - a.x) / curPx) * newPx, y: a.y + ((b.y - a.y) / curPx) * newPx },
    ];
    const patch = recomputeMeasurement(m, nextPoints, editScaleRef.current);
    setMeasurements((prev) =>
      prev.map((x) =>
        x.id === m.id
          ? { ...x, points: nextPoints, value: patch.value, label: patch.label, unit: patch.unit ?? x.unit }
          : x,
      ),
    );
  };
  const handleLengthFieldCommit = (m: Measurement) => {
    const bag = propLengthEditRef.current;
    propLengthEditRef.current = null;
    if (!bag || bag.id !== m.id) return;
    const cur = measurementsRef.current.find((x) => x.id === m.id);
    if (!cur) return;
    const moved =
      cur.points.length !== bag.original.points.length ||
      cur.points.some((p, i) => p.x !== bag.original.points[i]!.x || p.y !== bag.original.points[i]!.y);
    if (moved) {
      pushUndo({
        kind: 'edit_geometry',
        measurementId: m.id,
        previousMeasurement: { ...bag.original, points: [...bag.original.points] },
        nextMeasurement: { ...cur, points: [...cur.points] },
      });
    }
  };

  /** The markups the Colours-tab label sliders act on: the multi-select set""",
    ),
    (
        "Properties panel: Length field for distance markups",
        """                {/* Color: 6 quick swatches plus a native picker for any hex, so
                    a busy sheet with many measurement types is not limited to
                    six colors (#310). The chosen color persists round-trip and
                    both renderers honor it over the group color. */}""",
        """                {/* Length (distance markups only): typing a new
                    length resizes the segment on the sheet live -
                    the start point stays fixed. */}
                {selectedMeasurement.type === 'distance' && selectedMeasurement.points.length === 2 && (
                  <div>
                    <label className="text-[10px] font-semibold text-content-tertiary block mb-0.5">
                      {t('takeoff_viewer.prop_length', { defaultValue: 'Length' })} ({selectedMeasurement.unit})
                    </label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      key={selectedMeasurement.id}
                      defaultValue={Number(selectedMeasurement.value.toFixed(3))}
                      onChange={(e) => handleLengthFieldChange(selectedMeasurement, e.target.value)}
                      onBlur={() => handleLengthFieldCommit(selectedMeasurement)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
                      }}
                      className="w-full rounded border border-border bg-surface-primary px-2 py-1 text-xs text-content-primary"
                      data-testid="prop-length-input"
                    />
                  </div>
                )}

                {/* Color: 6 quick swatches plus a native picker for any hex, so
                    a busy sheet with many measurement types is not limited to
                    six colors (#310). The chosen color persists round-trip and
                    both renderers honor it over the group color. */}""",
    ),
]


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (measure interact present). Nothing to do.")
        return
    if REQUIRED_MARKER not in text:
        raise SystemExit(
            "Detect overlay v4 not found — run patch_viewer_detect4.py first. Nothing was written."
        )
    for label, old, _new in REPLACEMENTS:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"Anchor '{label}' found {count} times (expected 1). Nothing was written.")
    BACKUP.write_text(text, encoding="utf-8")
    for _label, old, new in REPLACEMENTS:
        text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8")
    after_lines = text.count("\n") + 1
    print(f"Patched OK. Backup: {BACKUP}")
    print(f"TakeoffViewerModule.tsx: {before_lines} -> {after_lines} lines.")


if __name__ == "__main__":
    main()
