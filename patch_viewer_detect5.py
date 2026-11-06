# OE-DELIVERY: 2026-10-30-viewer-detect5
"""Viewer patch 6 for the Detect feature: drag a line to MOVE it.

Run AFTER patch_viewer_measure_interact.py:
    python patch_viewer_detect5.py          (from the repo root)

What changes in TakeoffViewerModule.tsx:
  - In pick mode, pressing on a detect line and dragging now MOVES
    the line: past a small threshold the press turns into a move
    drag (the line itself follows the pointer live; a box-only mark
    shows a dashed ghost of its destination). On release the overlay
    reports 'oe-detect:linemove' with the drag delta (PDF units) and
    the panel translates the row. A press released without moving
    still selects the line, exactly as before.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-detect5.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-detect5")
ALREADY_MARKER = "oe-detect:linemove"
REQUIRED_MARKER = "oe-detect:duplicate"

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "drag state: move kind",
        """  const [detectDrag, setDetectDrag] = useState<{ kind: 'click' | 'marquee' | 'end' | 'dup'; id?: string; end?: number; startX: number; startY: number; additive: boolean; moved?: boolean } | null>(null);""",
        """  const [detectDrag, setDetectDrag] = useState<{ kind: 'click' | 'marquee' | 'end' | 'dup' | 'move'; id?: string; end?: number; startX: number; startY: number; additive: boolean; moved?: boolean } | null>(null);""",
    ),
    (
        "pointermove: a dragged press becomes a move; the line follows",
        """                      if (detectDrag.kind === 'dup' && detectDrag.id) {""",
        """                      if (detectDrag.kind === 'click' && detectDrag.id) {
                        // A press that travels becomes a MOVE drag:
                        // the line follows the pointer (box-only
                        // marks show a dashed destination ghost).
                        if (Math.hypot(pos.x - detectDrag.startX, pos.y - detectDrag.startY) > 5) {
                          const mark = detectMarks.find((x) => x.id === detectDrag.id);
                          if (mark) {
                            const dx = (pos.x - detectDrag.startX) / zoom;
                            const dy = (pos.y - detectDrag.startY) / zoom;
                            if (mark.line) {
                              setDetectDragLine({ id: mark.id, line: [mark.line[0] + dx, mark.line[1] + dy, mark.line[2] + dx, mark.line[3] + dy] });
                            } else {
                              setDetectDupGhost({ line: null, rect: [mark.rect[0] + dx, mark.rect[1] + dy, mark.rect[2] + dx, mark.rect[3] + dy], category: mark.category });
                            }
                            setDetectDrag({ ...detectDrag, kind: 'move', moved: true });
                          }
                        }
                        return;
                      }
                      if (detectDrag.kind === 'move' && detectDrag.id) {
                        const mark = detectMarks.find((x) => x.id === detectDrag.id);
                        if (!mark) return;
                        const dx = (pos.x - detectDrag.startX) / zoom;
                        const dy = (pos.y - detectDrag.startY) / zoom;
                        if (mark.line) {
                          setDetectDragLine({ id: mark.id, line: [mark.line[0] + dx, mark.line[1] + dy, mark.line[2] + dx, mark.line[3] + dy] });
                        } else {
                          setDetectDupGhost({ line: null, rect: [mark.rect[0] + dx, mark.rect[1] + dy, mark.rect[2] + dx, mark.rect[3] + dy], category: mark.category });
                        }
                        return;
                      }
                      if (detectDrag.kind === 'dup' && detectDrag.id) {""",
    ),
    (
        "pointerup: dropping a move reports the delta",
        """                      } else if (detectDrag.kind === 'dup' && detectDrag.id) {
                        if (detectDrag.moved) {
                          window.dispatchEvent(new CustomEvent('oe-detect:duplicate', { detail: { id: detectDrag.id, dx: (pos.x - detectDrag.startX) / zoom, dy: (pos.y - detectDrag.startY) / zoom } }));
                        } else {
                          window.dispatchEvent(new CustomEvent('oe-detect:toggle', { detail: { id: detectDrag.id, additive: true, focus: false } }));
                        }
                        setDetectDupGhost(null);
                      }
                      setDetectDrag(null);""",
        """                      } else if (detectDrag.kind === 'dup' && detectDrag.id) {
                        if (detectDrag.moved) {
                          window.dispatchEvent(new CustomEvent('oe-detect:duplicate', { detail: { id: detectDrag.id, dx: (pos.x - detectDrag.startX) / zoom, dy: (pos.y - detectDrag.startY) / zoom } }));
                        } else {
                          window.dispatchEvent(new CustomEvent('oe-detect:toggle', { detail: { id: detectDrag.id, additive: true, focus: false } }));
                        }
                        setDetectDupGhost(null);
                      } else if (detectDrag.kind === 'move' && detectDrag.id) {
                        window.dispatchEvent(new CustomEvent('oe-detect:linemove', { detail: { id: detectDrag.id, dx: (pos.x - detectDrag.startX) / zoom, dy: (pos.y - detectDrag.startY) / zoom } }));
                        setDetectDragLine(null);
                        setDetectDupGhost(null);
                      }
                      setDetectDrag(null);""",
    ),
]


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (detect overlay v5 present). Nothing to do.")
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
