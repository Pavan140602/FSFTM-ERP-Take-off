# OE-DELIVERY: 2026-10-30-viewer-detect4
"""Viewer patch 4 for the Detect feature: Shift+drag duplicates a mark.

Run AFTER patch_viewer_detect3.py:
    python patch_viewer_detect4.py          (from the repo root)

What changes in TakeoffViewerModule.tsx:
  - In pick mode, Shift+dragging a detect mark drags a dashed ghost
    copy of it; on release the overlay reports 'oe-detect:duplicate'
    with the drag delta (PDF units) and the panel clones the row at
    the dropped position. A plain Shift+click (no drag) still
    toggles the mark in the selection, exactly as before.
  - Leaving pick mode now also clears any half-finished detect drag
    state, so no ghost or marquee can be left frozen on the sheet.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-detect4.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-detect4")
ALREADY_MARKER = "oe-detect:duplicate"
REQUIRED_MARKER = "oe-detect:linedrag"

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "drag state: dup kind + ghost state",
        """  const [detectDrag, setDetectDrag] = useState<{ kind: 'click' | 'marquee' | 'end'; id?: string; end?: number; startX: number; startY: number; additive: boolean } | null>(null);
  const [detectMarquee, setDetectMarquee] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const [detectDragLine, setDetectDragLine] = useState<{ id: string; line: number[] } | null>(null);""",
        """  const [detectDrag, setDetectDrag] = useState<{ kind: 'click' | 'marquee' | 'end' | 'dup'; id?: string; end?: number; startX: number; startY: number; additive: boolean; moved?: boolean } | null>(null);
  const [detectMarquee, setDetectMarquee] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const [detectDragLine, setDetectDragLine] = useState<{ id: string; line: number[] } | null>(null);
  const [detectDupGhost, setDetectDupGhost] = useState<{ line: number[] | null; rect: number[] | null; category: string } | null>(null);""",
    ),
    (
        "pick mode off clears drag state",
        """    const onPick = (e: Event) => {
      const d = (e as CustomEvent).detail as { on?: boolean } | undefined;
      setDetectPickMode(Boolean(d?.on));
    };""",
        """    const onPick = (e: Event) => {
      const d = (e as CustomEvent).detail as { on?: boolean } | undefined;
      const on = Boolean(d?.on);
      setDetectPickMode(on);
      if (!on) {
        setDetectDrag(null);
        setDetectMarquee(null);
        setDetectDragLine(null);
        setDetectDupGhost(null);
      }
    };""",
    ),
    (
        "pointerdown: shift starts a potential duplicate drag",
        """                      } else if (markId) {
                        setDetectDrag({ kind: 'click', id: markId, startX: pos.x, startY: pos.y, additive });
                      } else {""",
        """                      } else if (markId) {
                        if (e.shiftKey && !e.ctrlKey && !e.metaKey) {
                          // Shift+drag duplicates the mark (a ghost
                          // copy follows the pointer); a plain
                          // Shift+click with no drag still toggles it
                          // in the selection - decided on release.
                          setDetectDrag({ kind: 'dup', id: markId, startX: pos.x, startY: pos.y, additive: true });
                        } else {
                          setDetectDrag({ kind: 'click', id: markId, startX: pos.x, startY: pos.y, additive });
                        }
                      } else {""",
    ),
    (
        "pointermove: duplicate ghost follows the pointer",
        """                      if (detectDrag.kind === 'end' && detectDrag.id) {""",
        """                      if (detectDrag.kind === 'dup' && detectDrag.id) {
                        const mark = detectMarks.find((x) => x.id === detectDrag.id);
                        if (!mark) return;
                        const movedFar = Math.hypot(pos.x - detectDrag.startX, pos.y - detectDrag.startY) > 5;
                        if (movedFar && !detectDrag.moved) setDetectDrag({ ...detectDrag, moved: true });
                        if (movedFar || detectDrag.moved) {
                          const dx = (pos.x - detectDrag.startX) / zoom;
                          const dy = (pos.y - detectDrag.startY) / zoom;
                          setDetectDupGhost({
                            line: mark.line ? [mark.line[0] + dx, mark.line[1] + dy, mark.line[2] + dx, mark.line[3] + dy] : null,
                            rect: [mark.rect[0] + dx, mark.rect[1] + dy, mark.rect[2] + dx, mark.rect[3] + dy],
                            category: mark.category,
                          });
                        }
                        return;
                      }
                      if (detectDrag.kind === 'end' && detectDrag.id) {""",
    ),
    (
        "pointerup: release drops the copy (or toggles on a plain shift+click)",
        """                      } else if (detectDrag.kind === 'end' && detectDrag.id && detectDragLine) {
                        window.dispatchEvent(new CustomEvent('oe-detect:linedrag', { detail: { id: detectDrag.id, line: detectDragLine.line } }));
                        setDetectDragLine(null);
                      }
                      setDetectDrag(null);""",
        """                      } else if (detectDrag.kind === 'end' && detectDrag.id && detectDragLine) {
                        window.dispatchEvent(new CustomEvent('oe-detect:linedrag', { detail: { id: detectDrag.id, line: detectDragLine.line } }));
                        setDetectDragLine(null);
                      } else if (detectDrag.kind === 'dup' && detectDrag.id) {
                        if (detectDrag.moved) {
                          window.dispatchEvent(new CustomEvent('oe-detect:duplicate', { detail: { id: detectDrag.id, dx: (pos.x - detectDrag.startX) / zoom, dy: (pos.y - detectDrag.startY) / zoom } }));
                        } else {
                          window.dispatchEvent(new CustomEvent('oe-detect:toggle', { detail: { id: detectDrag.id, additive: true, focus: false } }));
                        }
                        setDetectDupGhost(null);
                      }
                      setDetectDrag(null);""",
    ),
    (
        "render the duplicate ghost above the marks",
        """                    {detectMarquee && (
                      <rect""",
        """                    {detectDupGhost && (
                      <g pointerEvents="none" opacity={0.75}>
                        {detectDupGhost.line ? (
                          <line x1={detectDupGhost.line[0] * zoom} y1={detectDupGhost.line[1] * zoom} x2={detectDupGhost.line[2] * zoom} y2={detectDupGhost.line[3] * zoom} stroke={DETECT_CATEGORY_COLORS[detectDupGhost.category] ?? '#9CA3AF'} strokeWidth={3} strokeLinecap="round" strokeDasharray="6 4" />
                        ) : detectDupGhost.rect ? (
                          <rect x={detectDupGhost.rect[0] * zoom} y={detectDupGhost.rect[1] * zoom} width={(detectDupGhost.rect[2] - detectDupGhost.rect[0]) * zoom} height={(detectDupGhost.rect[3] - detectDupGhost.rect[1]) * zoom} fill="none" stroke={DETECT_CATEGORY_COLORS[detectDupGhost.category] ?? '#9CA3AF'} strokeWidth={1.6} strokeDasharray="6 4" />
                        ) : null}
                      </g>
                    )}
                    {detectMarquee && (
                      <rect""",
    ),
]


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (detect overlay v4 present). Nothing to do.")
        return
    if REQUIRED_MARKER not in text:
        raise SystemExit(
            "Detect overlay v3 not found — run patch_viewer_detect3.py first. Nothing was written."
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
