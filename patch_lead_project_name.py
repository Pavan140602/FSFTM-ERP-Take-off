"""Add a Project Name field to New Lead + map it (and the client) on convert.

OE-DELIVERY: 2026-10-27-lead-project-name

What changes, in the LIVE files only (every anchor verified first; if any
anchor is missing, NOTHING is written):

1. New Lead form (frontend/src/features/crm/CRMPage.tsx):
   - Contact Name loses its full-width span and sits side by side with a
     new Project Name field, exactly like the Email / Phone row.
   - The create payload sends project_name.
2. Lead API types (frontend/src/features/crm/api.ts): Lead and
   LeadCreatePayload gain project_name.
3. Lead model (backend/app/modules/crm/models.py): new nullable column
   project_name (VARCHAR 255). The column itself is added to the live
   database by the companion script backend/add_lead_project_name_column.py
   - this patch only teaches the ORM about it.
4. Lead schemas (backend/app/modules/crm/schemas.py): LeadCreate,
   LeadUpdate and LeadResponse gain project_name.
5. Lead service (backend/app/modules/crm/service.py):
   - create_lead stores project_name.
   - convert_lead auto-creates the Project with name = lead.project_name
     (falling back to the convert dialog title only for old leads that
     have no project_name), and client = lead contact name, stored in the
     project's client_id field - the same field the manual Create Project
     page already uses for the client name. client_id allows 36 chars, so
     a longer contact name is truncated to 36 so conversion never fails
     on this field.

What does NOT change:
- The convert dialog's title still becomes the Opportunity title; only
  the Project name now comes from the lead's Project Name field.
- Website leads are untouched (project_name stays empty for them, and
  the convert fallback covers them).
- No other lead fields, no lead list/detail layout.

Usage (from the repo root, with the project venv):
    .\\.venv\\Scripts\\python.exe patch_lead_project_name.py

Run the companion DB script FIRST with the backend stopped, then this
patch, then restart the backend:
    .\\.venv\\Scripts\\python.exe backend\\add_lead_project_name_column.py
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "OE-DELIVERY 2026-10-27-lead-project-name"

CRM_MODELS = Path("backend/app/modules/crm/models.py")
CRM_SCHEMAS = Path("backend/app/modules/crm/schemas.py")
CRM_SERVICE = Path("backend/app/modules/crm/service.py")
CRM_PAGE = Path("frontend/src/features/crm/CRMPage.tsx")
CRM_API = Path("frontend/src/features/crm/api.ts")


def region(text: str, start_marker: str, end_marker: str) -> tuple[int, int]:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"region start not found: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        end = len(text)
    return start, end


def class_region(text: str, class_name: str) -> tuple[int, int]:
    start = text.find(f"class {class_name}")
    if start < 0:
        raise ValueError(f"class not found: {class_name}")
    end = text.find("\nclass ", start + 1)
    if end < 0:
        end = len(text)
    return start, end


# Each job: (path, label, old, new, region_fn or None for whole file).
JOBS = [
    (
        CRM_MODELS,
        "Lead model column",
        "    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)\n",
        "    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)\n"
        "    # OE-DELIVERY 2026-10-27-lead-project-name: name for the auto-created project.\n"
        "    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)\n",
        None,
    ),
    (
        CRM_SCHEMAS,
        "LeadCreate.project_name",
        "    contact_name: str = Field(..., min_length=1, max_length=255)\n",
        "    contact_name: str = Field(..., min_length=1, max_length=255)\n"
        "    # OE-DELIVERY 2026-10-27-lead-project-name\n"
        "    project_name: str | None = Field(default=None, max_length=255)\n",
        lambda t: class_region(t, "LeadCreate"),
    ),
    (
        CRM_SCHEMAS,
        "LeadUpdate.project_name",
        "    contact_name: str | None = Field(default=None, max_length=255)\n",
        "    contact_name: str | None = Field(default=None, max_length=255)\n"
        "    project_name: str | None = Field(default=None, max_length=255)\n",
        lambda t: class_region(t, "LeadUpdate"),
    ),
    (
        CRM_SCHEMAS,
        "LeadResponse.project_name",
        "    contact_name: str\n",
        "    contact_name: str\n    project_name: str | None\n",
        lambda t: class_region(t, "LeadResponse"),
    ),
    (
        CRM_SERVICE,
        "create_lead stores project_name",
        "            message=data.message,\n        )",
        "            message=data.message,\n            project_name=data.project_name,\n        )",
        None,
    ),
    (
        CRM_SERVICE,
        "convert project name from lead",
        "                name=payload.title,\n",
        "                # OE-DELIVERY 2026-10-27-lead-project-name: project name from the lead; client = lead contact name.\n"
        "                name=lead.project_name or payload.title,\n",
        None,
    ),
    (
        CRM_SERVICE,
        "convert project client from contact",
        "                budget_estimate=str(payload.estimated_value) if payload.estimated_value else None,\n"
        '                status="new",\n',
        "                budget_estimate=str(payload.estimated_value) if payload.estimated_value else None,\n"
        '                status="new",\n'
        "                client_id=(lead.contact_name[:36] if lead.contact_name else None),\n",
        None,
    ),
    (
        CRM_PAGE,
        "leadForm.project_name state",
        "    contact_name: '',\n",
        "    contact_name: '',\n    project_name: '',\n",
        None,
    ),
    (
        CRM_PAGE,
        "Contact Name half width",
        "          <WideModalField\n"
        "            label={t('crm.contact_name', { defaultValue: 'Contact name' })}\n"
        "            required\n"
        "            span={2}\n"
        "          >\n",
        "          <WideModalField\n"
        "            label={t('crm.contact_name', { defaultValue: 'Contact name' })}\n"
        "            required\n"
        "          >\n",
        None,
    ),
    (
        CRM_PAGE,
        "Project Name modal field",
        "              value={leadForm.contact_name}\n"
        "              onChange={(e) =>\n"
        "                setLeadForm({ ...leadForm, contact_name: e.target.value })\n"
        "              }\n"
        "              className={inputCls}\n"
        "            />\n"
        "          </WideModalField>\n",
        "              value={leadForm.contact_name}\n"
        "              onChange={(e) =>\n"
        "                setLeadForm({ ...leadForm, contact_name: e.target.value })\n"
        "              }\n"
        "              className={inputCls}\n"
        "            />\n"
        "          </WideModalField>\n"
        "          {/* OE-DELIVERY 2026-10-27-lead-project-name */}\n"
        "          <WideModalField\n"
        "            label={t('crm.project_name', { defaultValue: 'Project name' })}\n"
        "          >\n"
        "            <input\n"
        "              value={leadForm.project_name}\n"
        "              onChange={(e) =>\n"
        "                setLeadForm({ ...leadForm, project_name: e.target.value })\n"
        "              }\n"
        "              className={inputCls}\n"
        "            />\n"
        "          </WideModalField>\n",
        None,
    ),
    (
        CRM_PAGE,
        "create payload project_name",
        "          contact_name: leadForm.contact_name.trim(),\n",
        "          contact_name: leadForm.contact_name.trim(),\n"
        "          project_name: leadForm.project_name.trim() || undefined,\n",
        None,
    ),
    (
        CRM_API,
        "Lead.project_name type",
        "  contact_name: string;\n  contact_email: string | null;\n",
        "  contact_name: string;\n"
        "  // OE-DELIVERY 2026-10-27-lead-project-name\n"
        "  project_name: string | null;\n"
        "  contact_email: string | null;\n",
        None,
    ),
    (
        CRM_API,
        "LeadCreatePayload.project_name type",
        "  contact_name: string;\n  contact_email?: string;\n",
        "  contact_name: string;\n"
        "  project_name?: string;\n"
        "  contact_email?: string;\n",
        None,
    ),
]


def fail(message: str) -> int:
    print(f"PATCH FAILED: {message}")
    print("Nothing was written.")
    return 1


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    paths = sorted({job[0] for job in JOBS})
    texts: dict[Path, str] = {}
    for path in paths:
        full = root / path
        if not full.is_file():
            return fail(f"file not found: {full}")
        texts[path] = full.read_text(encoding="utf-8")

    patched = {path for path in paths if MARKER in texts[path]}
    if len(patched) == len(paths):
        print("Already patched: Project Name is already in place. Nothing changed.")
        return 0
    if patched:
        return fail(
            "PARTIAL STATE: the marker is already present in "
            + ", ".join(str(p) for p in sorted(patched))
            + " but not in the rest. Report this output before re-running; "
            "nothing was written."
        )

    # Verify every anchor before writing anything.
    for path, label, old, _new, region_fn in JOBS:
        text = texts[path]
        if region_fn is not None:
            try:
                start, end = region_fn(text)
            except ValueError as exc:
                return fail(f"{label}: {exc}")
            scope = text[start:end]
        else:
            scope = text
        if scope.count(old) != 1:
            return fail(f"{label}: anchor found {scope.count(old)} times (expected exactly 1).")

    # Apply.
    for path, _label, old, new, region_fn in JOBS:
        text = texts[path]
        if region_fn is not None:
            start, end = region_fn(text)
            texts[path] = text[:start] + text[start:end].replace(old, new, 1) + text[end:]
        else:
            texts[path] = text.replace(old, new, 1)

    for path in paths:
        (root / path).write_text(texts[path], encoding="utf-8")
        print(f"Patched OK: {path}")
    print(
        "Next steps: restart the backend, hard-refresh the app, create a lead "
        "with a Project Name, convert it, and check the project name + client."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
