# OE-DELIVERY: 2026-10-23-team-workload-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload module permission definitions.

Registering ``team_workload.read`` is what makes the ``team_workload``
module key appear in the permission registry, and therefore in
Users -> Role Module Access and in ``GET /users/me/role-modules/`` -
the frontend gates the sidebar row and the route on that key.
"""

from app.core.permissions import Role, permission_registry


def register_team_workload_permissions() -> None:
    """Register permissions for the team workload module."""
    permission_registry.register_module_permissions(
        "team_workload",
        {
            "team_workload.read": Role.VIEWER,
        },
    )
