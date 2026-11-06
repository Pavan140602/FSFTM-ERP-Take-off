# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Users & Authentication module.

Provides user registration, JWT auth, API keys, and RBAC.
"""


async def on_startup() -> None:
    """Module startup hook - register permissions, warm the custom-role cache."""
    from app.modules.users.permissions import register_user_permissions

    register_user_permissions()

    # Best-effort warm of the custom-role permission cache. The DB may not
    # be migrated yet at this point (alembic runs in a later startup phase),
    # so any failure is swallowed: the role read endpoints retry the warm
    # lazily, and permission checks fail closed without the cache.
    try:
        from app.database import async_session_factory
        from app.modules.users.router import refresh_custom_role_cache_from_db

        async with async_session_factory() as session:
            await refresh_custom_role_cache_from_db(session)
    except Exception:  # noqa: BLE001 - best-effort by design, see above
        import logging

        logging.getLogger(__name__).warning(
            "Custom-role cache warm at startup failed; will retry on first role read",
            exc_info=True,
        )
