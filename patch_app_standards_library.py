"""Add the Standards Library page registration to App.tsx.

OE-DELIVERY: 2026-10-29-standards-library-v1

Two anchored insertions, both verified before anything is written:
  1. the lazy page import, right after the TeamWorkloadPage lazy block;
  2. the /standards-library route, right after the /team-workload route,
     gated by ModuleRouteGate on the 'standards_library' role grant.

Idempotent: if the page is already registered it prints so and exits.
If an anchor is missing or not unique it writes nothing and says which
anchor failed - send that output back instead of editing by hand.

Run from the repo root with plain python (stdlib only):
    python patch_app_standards_library.py
No restart needed - Vite picks the change up; hard-refresh the tab.
"""

from __future__ import annotations

from pathlib import Path

TARGET = Path("frontend/src/app/App.tsx")
MARKER = "features/standards-library"

LAZY_ANCHOR = (
    "// OE-DELIVERY: 2026-10-23-team-workload-v1\n"
    "const TeamWorkloadPage = lazy(() =>\n"
    "  import('@/features/team-workload').then((m) => ({ default: m.TeamWorkloadPage }))\n"
    ");"
)
LAZY_ADD = (
    "\n// OE-DELIVERY: 2026-10-29-standards-library-v1\n"
    "const StandardsLibraryPage = lazy(() =>\n"
    "  import('@/features/standards-library').then((m) => ({ default: m.StandardsLibraryPage }))\n"
    ");"
)

ROUTE_ANCHOR = (
    '        <Route path="/team-workload" element={<P title="Team Workload">'
    '<ModuleRouteGate moduleKey="team_workload"><TeamWorkloadPage /></ModuleRouteGate></P>} />'
)
ROUTE_ADD = (
    "\n        {/* OE-DELIVERY: 2026-10-29-standards-library-v1 - gated by the 'standards_library' role module grant */}\n"
    '        <Route path="/standards-library" element={<P title="Standards Library">'
    '<ModuleRouteGate moduleKey="standards_library"><StandardsLibraryPage /></ModuleRouteGate></P>} />'
)


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"NOT FOUND: {TARGET} - run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("Already applied - Standards Library is registered in App.tsx. Nothing changed.")
        return
    for name, anchor in (("lazy import", LAZY_ANCHOR), ("route", ROUTE_ANCHOR)):
        count = text.count(anchor)
        if count != 1:
            raise SystemExit(
                f"ANCHOR MISSING ({name}): found {count} copies, need exactly 1. "
                "Nothing was written - send this output back."
            )
    text = text.replace(LAZY_ANCHOR, LAZY_ANCHOR + LAZY_ADD, 1)
    text = text.replace(ROUTE_ANCHOR, ROUTE_ANCHOR + ROUTE_ADD, 1)
    TARGET.write_text(text, encoding="utf-8")
    lines = text.count("\n") + 1
    print(f"Patched OK - App.tsx now {lines} lines. Hard-refresh the browser tab (Ctrl+Shift+R).")


if __name__ == "__main__":
    main()
