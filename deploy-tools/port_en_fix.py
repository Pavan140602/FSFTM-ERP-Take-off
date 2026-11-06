#!/usr/bin/env python3
"""port_en_fix.py -- Re-apply the Kind/Page Label ledger fix onto a FRESH upstream en.ts.

Background
----------
The user's PageLabelFix-v1 en.ts was edited from the Oct-5 upstream copy. Upstream
has since shipped 18.5.0 (Oct 8-9) with new i18n keys, so during the fsftm.lan
deploy do NOT overwrite the server's frontend/src/app/locales/en.ts wholesale --
that would wipe upstream's new keys. Instead: pull the fresh en.ts from the
server (or git), run this script, and it applies ONLY the two ledger-header
string changes, then prints line count + sha256 for the usual verify ritual.

The fix (matches the user's PageLabelFix-v1 scope):
    "takeoff_viewer.col_page": "Page",  ->  "takeoff_viewer.col_page": "Page Label",
    "takeoff_viewer.col_type": "Type",  ->  "takeoff_viewer.col_type": "Kind",

Custom roles (2026-10-12 feature): 7 new users.* keys are injected after the
"users.access" anchor (idempotent; skipped if already present):
    users.create_custom_role / users.custom_role_button / users.base_permissions_on /
    users.all_modules / users.create_role / users.custom_role_created /
    users.custom_role_create_failed

NOTE: "takeoff_viewer.page_label": "Page" (the page-selector label) is a different
UI element and was NOT part of the user's fix -- this script leaves it alone.

Usage:
    python port_en_fix.py path/to/en.ts
"""

import hashlib
import sys

OLD_NEW = [
    ('"takeoff_viewer.col_page": "Page",', '"takeoff_viewer.col_page": "Page Label",'),
    ('"takeoff_viewer.col_type": "Type",', '"takeoff_viewer.col_type": "Kind",'),
]

# Custom-role i18n keys (2026-10-12). Injected after the anchor line below.
CUSTOM_ROLE_ANCHOR = '    "users.access": "Access",\n'
CUSTOM_ROLE_KEYS = '''    "users.create_custom_role": "Create custom role",
    "users.custom_role_button": "Custom role",
    "users.base_permissions_on": "Base permissions on",
    "users.all_modules": "All modules",
    "users.create_role": "Create role",
    "users.custom_role_created": "Custom role created",
    "users.custom_role_create_failed": "Could not create custom role",
'''


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python port_en_fix.py path/to/en.ts")
        return 2
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    for old, new in OLD_NEW:
        n_old = text.count(old)
        n_new = text.count(new)
        if n_old == 1 and n_new == 0:
            text = text.replace(old, new)
            print(f"applied: {old}  ->  {new}")
        elif n_old == 0 and n_new == 1:
            print(f"already applied, skipped: {new}")
        else:
            print(
                f"ABORT: unexpected counts for {old!r} "
                f"(old={n_old}, new={n_new}) -- file not in expected state, nothing written."
            )
            return 1

    # --- Custom-role keys (idempotent) ---
    missing_keys = [k for k in CUSTOM_ROLE_KEYS.strip().splitlines() if k.strip() not in text]
    if not missing_keys:
        print("custom-role keys already present, skipped.")
    elif text.count(CUSTOM_ROLE_ANCHOR) == 1:
        text = text.replace(CUSTOM_ROLE_ANCHOR, CUSTOM_ROLE_ANCHOR + CUSTOM_ROLE_KEYS)
        print(f"injected {len(CUSTOM_ROLE_KEYS.strip().splitlines())} custom-role keys after users.access.")
    else:
        print(
            "ABORT: custom-role anchor '\"users.access\": \"Access\",' not found exactly once "
            "-- file not in expected state, nothing written."
        )
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"lines: {lines}")
    print(f"sha256: {sha}")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
