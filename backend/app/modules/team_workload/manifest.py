# OE-DELIVERY: 2026-10-23-team-workload-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_team_workload",
    version="0.1.0",
    display_name="Team Workload",
    description=(
        "Per-person project track record for managers and coordinators: "
        "who is assigned to which project, how far each project has "
        "progressed, and how long each project and stage took."
    ),
    author="OpenConstructionERP Core Team",
    category="core",
    depends=["oe_users", "oe_projects", "oe_teams"],
    auto_install=True,
    enabled=True,
)
