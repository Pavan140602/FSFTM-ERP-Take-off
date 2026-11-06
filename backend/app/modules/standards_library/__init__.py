# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library module.

Structured section-property tables (AISC Shapes Database v16.0 and the
SSMA Technical Guide) behind one designation lookup, a MasterFormat
division index for scope tagging, and a document shelf for code books.
The lookup is the single source of truth the takeoff Tool Chest, the
CFS engine and the AI extraction features read member weights from.
"""


async def on_startup() -> None:
    """Module startup hook - register permissions."""
    from app.modules.standards_library.permissions import (
        register_standards_library_permissions,
    )

    register_standards_library_permissions()
