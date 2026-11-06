"""Add the Standards Library entry to the sidebar catalog.

OE-DELIVERY: 2026-10-29-standards-library-v1

One anchored insertion in navCatalog.ts, verified before writing: the
'Standards Library' item goes into the Takeoff group right after PDF
Measurements. moduleKey is the permission-registry key
('standards_library') so Role Module Access controls its visibility;
the BookOpen icon is already imported in that file.

Idempotent: if the entry already exists it prints so and exits. If the
anchor is missing or not unique it writes nothing and says so - send
that output back instead of editing by hand.

Run from the repo root with plain python (stdlib only):
    python patch_nav_standards_library.py
No restart needed - Vite picks the change up; hard-refresh the tab.
"""

from __future__ import annotations

from pathlib import Path

TARGET = Path("frontend/src/app/layout/navCatalog.ts")
MARKER = "nav.standards_library"

ANCHOR = "      { labelKey: 'nav.pdf_measurements', to: '/takeoff?tab=measurements', icon: Ruler },"
ADD = (
    "\n      // OE-DELIVERY: 2026-10-29-standards-library-v1 - moduleKey must be the\n"
    "      // permission-registry key ('standards_library').\n"
    "      { labelKey: 'nav.standards_library', defaultLabel: 'Standards Library', to: '/standards-library', icon: BookOpen, moduleKey: 'standards_library', advancedOnly: true },"
)


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"NOT FOUND: {TARGET} - run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("Already applied - Standards Library is in the sidebar catalog. Nothing changed.")
        return
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(
            f"ANCHOR MISSING: found {count} copies, need exactly 1. "
            "Nothing was written - send this output back."
        )
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    TARGET.write_text(text, encoding="utf-8")
    lines = text.count("\n") + 1
    print(f"Patched OK - navCatalog.ts now {lines} lines. Hard-refresh the browser tab (Ctrl+Shift+R).")


if __name__ == "__main__":
    main()
