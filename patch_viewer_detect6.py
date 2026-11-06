# OE-DELIVERY: 2026-10-30-viewer-detect6
"""Viewer patch 7 for the Detect feature: strict type-clean overlay.

Run AFTER patch_viewer_detect5.py:
    python patch_viewer_detect6.py          (from the repo root)

What changes in TakeoffViewerModule.tsx:
  - The detect overlay's geometry types become fixed 4-tuples
    ([x1, y1, x2, y2]) instead of number[], and the endpoint-handle
    block guards its single selected mark before use. Behaviour is
    unchanged; the change only makes the overlay clean under the
    project's strict TypeScript settings (strict +
    noUncheckedIndexedAccess), where plain array indexing reads as
    possibly-undefined and lit up the Problems panel.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-detect6.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-detect6")
ALREADY_MARKER = "rect: [number, number, number, number]; label: string"
REQUIRED_MARKER = "oe-detect:linemove"

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "detect marks state: tuple geometry",
        """  const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected'; category: string; line: number[] | null; angle: number | null; lengthFt: number | null }[]>([]);""",
        """  const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: [number, number, number, number]; label: string; status: 'confirmed' | 'verify' | 'selected'; category: string; line: [number, number, number, number] | null; angle: number | null; lengthFt: number | null }[]>([]);""",
    ),
    (
        "drag line state: tuple geometry",
        """  const [detectDragLine, setDetectDragLine] = useState<{ id: string; line: number[] } | null>(null);""",
        """  const [detectDragLine, setDetectDragLine] = useState<{ id: string; line: [number, number, number, number] } | null>(null);""",
    ),
    (
        "duplicate ghost state: tuple geometry",
        """  const [detectDupGhost, setDetectDupGhost] = useState<{ line: number[] | null; rect: number[] | null; category: string } | null>(null);""",
        """  const [detectDupGhost, setDetectDupGhost] = useState<{ line: [number, number, number, number] | null; rect: [number, number, number, number] | null; category: string } | null>(null);""",
    ),
    (
        "endpoint handles: guard the selected mark",
        """                      const sel = detectMarks.filter((x) => x.page === currentPage && x.status === 'selected');
                      if (sel.length !== 1 || !sel[0].line) return null;
                      const m = sel[0];""",
        """                      const sel = detectMarks.filter((x) => x.page === currentPage && x.status === 'selected');
                      if (sel.length !== 1) return null;
                      const m = sel[0];
                      if (!m || !m.line) return null;""",
    ),
]


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (detect overlay strict types present). Nothing to do.")
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
