"""Show "Accounting team" instead of a person's name on invoice gate cards.

OE-DELIVERY: 2026-10-27-invoice-accounting-team-panel

Companion to patch_pipeline_invoice_names_v2.py. The backend script fixes
the email text; this script fixes the pipeline panel's gate card, which
renders "Invoice email sent to {stored name}". It changes ONLY that
rendered line (plus the now-unused variable that fed it) in the live
frontend/src/features/projects/AwardPipelinePanel.tsx - no whole-file
panel replacement, because the mirror's panel predates the live payment
schedule, receipts and receipt-chip builds.

v2 vs v1: the live panel defines dispInvSentTo as a single line from the
viewed milestone ("dispMilestone?.inv_sent_to"), not the old
pay10/pay60/pay30 ternary the mirror had. v2 accepts either definition
form, so it works on the live file and on older copies alike.

What changes:
- Gate card line: "Invoice email sent to {name}" becomes
  "Invoice email sent to Accounting team" (date part unchanged).
- The dispInvSentTo constant that fed that line is removed, so no unused
  variable is left behind.

What does NOT change:
- The stored inv_sent_to value keeps the real recipient: the receipts
  completion email resolves its Accounts recipient from it, so changing
  the stored value would silently drop Accounts from completion emails.
  Only the displayed text becomes generic - past and future sends alike.

Usage (from the repo root):
    .\\.venv\\Scripts\\python.exe patch_panel_invoice_display_v2.py
    .\\.venv\\Scripts\\python.exe patch_panel_invoice_display_v2.py frontend/src/features/projects/AwardPipelinePanel.tsx

The script refuses to write anything unless the invoice-sent line and
exactly one dispInvSentTo definition form are found, and it refuses to
run twice (idempotent: a second run reports "already patched" and
changes nothing).
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_PANEL = Path("frontend/src/features/projects/AwardPipelinePanel.tsx")

OLD_LINE = "Invoice email sent to {dispInvSentTo ?? 'Accounts'} \u00b7{' '}"
NEW_LINE = "Invoice email sent to Accounting team \u00b7{' '}"
ALREADY = "Invoice email sent to Accounting team"

# Live panel (receipts era): single line from the viewed milestone.
LIVE_BLOCK = "  const dispInvSentTo = dispMilestone?.inv_sent_to ?? null;\n"
# Older panel (mirror era): ternary over the legacy pay*_ columns.
OLD_BLOCK = (
    "  const dispInvSentTo =\n"
    "    displayStage === 'payment_10'\n"
    "      ? view.pay10_inv_sent_to\n"
    "      : displayStage === 'payment_60'\n"
    "        ? view.pay60_inv_sent_to\n"
    "        : displayStage === 'payment_30'\n"
    "          ? view.pay30_inv_sent_to\n"
    "          : null;\n"
)


def fail(message: str) -> int:
    print(f"PATCH FAILED: {message}")
    print(
        "Nothing was written. Check the panel path and that the live file "
        "still contains the invoice-sent line."
    )
    return 1


def main(argv: list[str]) -> int:
    panel_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_PANEL
    if not panel_path.is_file():
        return fail(f"panel file not found: {panel_path}")
    text = panel_path.read_text(encoding="utf-8")

    if OLD_LINE not in text and ALREADY in text:
        print("Already patched: the gate card already says Accounting team. Nothing changed.")
        return 0

    if text.count(OLD_LINE) != 1:
        return fail(
            f"invoice-sent line found {text.count(OLD_LINE)} times (expected exactly 1)."
        )
    found_blocks = [b for b in (LIVE_BLOCK, OLD_BLOCK) if text.count(b) == 1]
    if len(found_blocks) != 1:
        return fail(
            "dispInvSentTo definition found "
            f"{sum(text.count(b) for b in (LIVE_BLOCK, OLD_BLOCK))} times across "
            "known forms (expected exactly 1)."
        )

    patched = text.replace(OLD_LINE, NEW_LINE).replace(found_blocks[0], "")
    panel_path.write_text(patched, encoding="utf-8")
    print(f"Patched OK: {panel_path}")
    print(
        "Changed: gate card now says 'Invoice email sent to Accounting team'; "
        "the unused dispInvSentTo constant was removed."
    )
    print("Next step: hard-refresh the app and open a payment gate card to verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
