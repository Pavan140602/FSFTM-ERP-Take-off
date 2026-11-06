# OE-DELIVERY: 2026-10-30-viewer-detect7
"""Viewer patch 8 for the Detect feature: keyboard ownership.

Run AFTER patch_viewer_detect6.py:
    python patch_viewer_detect7.py          (from the repo root)

What changes in TakeoffViewerModule.tsx:
  - While Detect pick mode is ON, the viewer's own Ctrl+Z /
    Ctrl+Shift+Z / Ctrl+Y and Delete / Backspace shortcuts stand
    down: in pick mode those keys belong to the Detect panel (undo /
    redo / remove for detected lines). Before this, Ctrl+Z in pick
    mode would ALSO undo a measurement, and Delete could remove a
    selected measurement alongside the detected lines. When pick
    mode is off, every shortcut behaves exactly as before.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-detect7.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-detect7")
ALREADY_MARKER = "toLowerCase() === 'z' && !e.shiftKey && !detectPickMode"
REQUIRED_MARKER = "oe-detect:linemove"

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "undo shortcut: stand down in detect pick mode",
        """      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {""",
        """      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey && !detectPickMode) {""",
    ),
    (
        "redo shortcut: stand down in detect pick mode",
        """      if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))) {""",
        """      if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey)) && !detectPickMode) {""",
    ),
    (
        "delete shortcut: stand down in detect pick mode",
        """      if ((e.key === 'Delete' || e.key === 'Backspace') && (selectedMeasurementId || selectedLedgerIds.size > 0)) {""",
        """      if (!detectPickMode && (e.key === 'Delete' || e.key === 'Backspace') && (selectedMeasurementId || selectedLedgerIds.size > 0)) {""",
    ),
]


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (pick-mode keyboard ownership present). Nothing to do.")
        return
    if REQUIRED_MARKER not in text:
        raise SystemExit(
            "Detect overlay v5 not found — run patch_viewer_detect5.py first. Nothing was written."
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
