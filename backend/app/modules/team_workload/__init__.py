# OE-DELIVERY: 2026-10-23-team-workload-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload module.

Read-only manager/coordinator reporting over data the ERP already
records: project team memberships (who is assigned to what, and since
when), project status history (how long each stage took) and the
post-award pipeline (stage completion timestamps). No new tables.
"""


async def on_startup() -> None:
    """Module startup hook - register permissions."""
    from app.modules.team_workload.permissions import register_team_workload_permissions

    register_team_workload_permissions()
