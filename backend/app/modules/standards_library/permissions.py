# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library module permission definitions.

Registering ``standards_library.read`` is what makes the
``standards_library`` module key appear in the permission registry, and
therefore in Users -> Role Module Access and in
``GET /users/me/role-modules/`` - the frontend gates the sidebar row
and the route on that key.
"""

from app.core.permissions import Role, permission_registry


def register_standards_library_permissions() -> None:
    """Register permissions for the standards library module."""
    permission_registry.register_module_permissions(
        "standards_library",
        {
            "standards_library.read": Role.VIEWER,
            "standards_library.manage": Role.EDITOR,
        },
    )
