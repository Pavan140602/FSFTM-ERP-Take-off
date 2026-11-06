# OE-DELIVERY: 2026-10-29-textsearch-viewport-transform-patch4
"""Patch live frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx:
pass the pdf.js viewport TRANSFORM (not just the height) to the
text-layer placement helper, so highlight boxes land in display
space on ROTATED pages too.

Run once from the repo root (no backend restart; hard-refresh after):

    python patch_viewer_highlight4.py

Pair with the takeoff-textsearch-20261029-fix2.ts library file
(replace frontend/src/features/takeoff/lib/takeoff-textsearch.ts).

Why: sheets whose pages are rotated 90/270 degrees (common in
extracted drawing sets - the Gold Rush set is rotation 90) rendered
fine, but the find/highlight boxes were computed in unrotated user
space flipped against the DISPLAY height, so every box landed in
the wrong region of the sheet. The library now maps each text run
through the viewport transform; the viewer only has to hand it
over (one argument: vp.height -> vp.transform).

Anchor-verified + idempotent; a .bak copy is written first.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

OLD = """              items = itemsFromTextContent(
                content.items as unknown as Parameters<typeof itemsFromTextContent>[0],
                vp.height,
              );"""
NEW = """              items = itemsFromTextContent(
                content.items as unknown as Parameters<typeof itemsFromTextContent>[0],
                vp.transform,
              );"""


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if NEW in text:
        print("Already applied: viewport transform is passed, nothing changed.")
        return 0
    if text.count(OLD) != 1:
        print(f"ANCHOR MISSING/AMBIGUOUS: found {text.count(OLD)}x, nothing changed.")
        return 1
    backup = TARGET.with_suffix(".tsx.bak5")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
