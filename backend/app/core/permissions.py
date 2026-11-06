# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""RBAC permission engine.

Role-Based Access Control with permission inheritance.
Roles are hierarchical: admin > manager > editor > viewer.
Modules register their own permissions at startup.

Usage:
    from app.core.permissions import permission_registry, Role

    # Register module permissions
    permission_registry.register_module_permissions("projects", [
        "projects.create",
        "projects.read",
        "projects.update",
        "projects.delete",
    ])

    # Check permission
    if permission_registry.role_has_permission(Role.EDITOR, "projects.update"):
        ...
"""

import logging
from enum import StrEnum

logger = logging.getLogger(__name__)

_RBAC_BUILD_TAG: str = "0d2d651aebd117b4"


class Role(StrEnum):
    """Built-in roles with hierarchical permissions."""

    ADMIN = "admin"  # Full access to everything
    MANAGER = "manager"  # Project management, team management
    EDITOR = "editor"  # Create and modify content
    VIEWER = "viewer"  # Read-only access
    # ── Field-worker surface (mobile/tablet, see
    # docs/architecture/FIELD_WORKER_MOBILE_DESIGN.md). DESIGN-STAGE
    # placeholders - the permission set is intentionally empty until
    # the pilot router lands so adding the enum value does not
    # accidentally widen any existing endpoint's scope.
    SITE_INSPECTOR = "site_inspector"  # QA/HSE inspector, read-broad write-narrow
    SITE_FOREMAN = "site_foreman"  # crew foreman, signs off worker entries
    FIELD_WORKER = "field_worker"  # site labourer, lowest-trust persona


# Role hierarchy: higher roles inherit all permissions of lower roles.
#
# Field-role ranks are NEGATIVE (below VIEWER=0) to ensure that a
# default-`-1` lookup (the legacy fallback shape used by
# `role_has_permission`) cannot accidentally promote a field worker
# above a viewer. Anywhere the legacy `-1` floor is read, it must be
# audited as part of the field-pilot landing PR - see the design doc
# §11 Risk #3.
ROLE_HIERARCHY: dict[Role, int] = {
    Role.FIELD_WORKER: -2,
    Role.SITE_FOREMAN: -1,
    Role.SITE_INSPECTOR: 0,
    Role.VIEWER: 0,
    Role.EDITOR: 1,
    Role.MANAGER: 2,
    Role.ADMIN: 3,
}


# Alias map - legacy / industry-specific role names that should behave like
# one of the canonical four roles. Keeps the core Role enum small while
# allowing construction-industry titles ("estimator", "surveyor", ...) to
# work without manual migration. Values are ALWAYS canonical Role members.
ROLE_ALIASES: dict[str, Role] = {
    "estimator": Role.EDITOR,
    "quantity_surveyor": Role.EDITOR,
    "qs": Role.EDITOR,
    "user": Role.EDITOR,
    "superuser": Role.ADMIN,
    "owner": Role.ADMIN,
    "readonly": Role.VIEWER,
    "guest": Role.VIEWER,
}


# ── Custom roles (admin-defined, stored in oe_users_custom_role) ──────────
#
# A custom role is a slug like ``custom_senior_estimator`` carried on the
# free-form ``User.role`` column. This module never touches the database:
# the users module pushes the active rows in via
# ``refresh_custom_roles_cache`` (after every CRUD, and once at startup).
# Until the cache is populated an unknown custom slug resolves to nothing
# and every permission check fails closed.

_custom_role_cache: dict[str, dict] = {}
"""slug → {"base_role": str, "granted_modules": list[str]}.

Replaced wholesale on every refresh, never mutated in place, so readers
never observe a half-written map.
"""


def refresh_custom_roles_cache(entries: "list[dict]") -> None:
    """Replace the custom-role cache with fresh rows from the database.

    Each entry is ``{"slug": str, "base_role": str,
    "granted_modules": list[str]}``. Rows whose ``base_role`` is not one of
    the canonical four are skipped rather than stored - a corrupt row must
    never widen into a real role.
    """
    global _custom_role_cache
    fresh: dict[str, dict] = {}
    for entry in entries:
        slug = str(entry.get("slug", "")).strip().lower()
        base = str(entry.get("base_role", "")).strip().lower()
        if not slug.startswith("custom_"):
            continue
        try:
            Role(base)
        except ValueError:
            logger.warning("Skipping custom role %r: unknown base_role %r", slug, base)
            continue
        modules = entry.get("granted_modules") or []
        fresh[slug] = {
            "base_role": base,
            "granted_modules": [str(m) for m in modules if isinstance(m, str)],
        }
    _custom_role_cache = fresh
    logger.info("Custom-role cache refreshed: %d active roles", len(fresh))


def invalidate_custom_roles_cache() -> None:
    """Drop the custom-role cache. Checks fail closed until the next refresh."""
    global _custom_role_cache
    _custom_role_cache = {}


def get_custom_role_slugs() -> "frozenset[str]":
    """Slugs the registry currently recognises as custom roles.

    The users schemas reuse this so role validation and permission
    resolution read the same cache instead of maintaining a second one.
    """
    return frozenset(_custom_role_cache)


def _custom_role_entry(role: "Role | str") -> "dict | None":
    """Return the cached entry for a ``custom_*`` slug, else None."""
    if isinstance(role, Role) or not role:
        return None
    key = role.strip().lower()
    if not key.startswith("custom_"):
        return None
    return _custom_role_cache.get(key)


def _resolve_role(role: "Role | str") -> "Role | None":
    """Resolve any role string (including aliases and cached custom roles)
    to a canonical Role, or None.

    A ``custom_*`` slug that the users module has pushed into the cache
    resolves to its configured base role, so rank-based gates
    (``RequireRole``) treat it as that base role. An uncached custom slug
    resolves to None - fail-closed, exactly like any other unknown string.
    """
    if isinstance(role, Role):
        return role
    if not role:
        return None
    key = role.strip().lower()
    try:
        return Role(key)
    except ValueError:
        pass
    if key.startswith("custom_"):
        entry = _custom_role_cache.get(key)
        if entry is not None:
            try:
                return Role(entry["base_role"])
            except ValueError:
                return None
        return None
    return ROLE_ALIASES.get(key)


class PermissionRegistry:
    """Central registry of all permissions in the system.

    Permissions follow the pattern: '{module}.{action}'
    Examples: 'projects.create', 'boq.export', 'users.manage'

    Each permission has a minimum required role level.
    """

    def __init__(self) -> None:
        # permission_name → minimum Role required
        self._permissions: dict[str, Role] = {}
        # module_name → list of permission names
        self._module_permissions: dict[str, list[str]] = {}
        # permission_name → module_name (reverse map, used to scope custom
        # roles to their granted modules). Only permissions registered via
        # register_module_permissions have an entry; register() callers carry
        # no module, and those permissions keep base-role behaviour.
        self._permission_modules: dict[str, str] = {}

    def register(self, permission: str, min_role: Role = Role.EDITOR) -> None:
        """Register a single permission with its minimum required role."""
        self._permissions[permission] = min_role
        logger.debug("Registered permission: %s (min_role=%s)", permission, min_role.value)

    def register_module_permissions(
        self,
        module_name: str,
        permissions: dict[str, Role],
    ) -> None:
        """Register all permissions for a module.

        Args:
            module_name: Module identifier (e.g., 'projects').
            permissions: Dict of permission_name → minimum Role.
        """
        self._module_permissions[module_name] = list(permissions.keys())
        for perm, min_role in permissions.items():
            self._permissions[perm] = min_role
            self._permission_modules[perm] = module_name
        logger.info(
            "Registered %d permissions for module '%s'",
            len(permissions),
            module_name,
        )

    def unregister_module_permissions(self, module_name: str) -> list[str]:
        """Forget a module's permissions. Returns the names it was asked to remove.

        Needed because a module can now leave while the server runs. Left
        behind, its permissions would still be offered by the admin matrix and
        still be granted to roles, with nothing on the other end enforcing
        them; and a module reinstalled from a different spec would inherit
        whatever its previous shape happened to register.

        A permission another module also registered is kept: the registry is a
        flat dictionary, so removing the shared entry would leave that module's
        endpoints checking a key the registry no longer knows, and an unknown
        permission is denied to everyone below admin.

        Args:
            module_name: Module identifier as passed to
                :meth:`register_module_permissions`.
        """
        names = self._module_permissions.pop(module_name, [])
        still_owned = {perm for perms in self._module_permissions.values() for perm in perms}
        for perm in names:
            if perm not in still_owned:
                self._permissions.pop(perm, None)
                self._permission_modules.pop(perm, None)
            else:
                # Shared permission: re-point the reverse map at a module
                # that still owns it instead of the one leaving.
                for mod, perms in self._module_permissions.items():
                    if perm in perms:
                        self._permission_modules[perm] = mod
                        break
        if names:
            logger.info("Unregistered %d permissions for module '%s'", len(names), module_name)
        return names

    def role_has_permission(self, role: Role | str, permission: str) -> bool:
        """Check if a role has a specific permission.

        Admin always has all permissions.
        Other roles are checked against the hierarchy.
        Accepts canonical roles and legacy aliases (e.g. "estimator").
        A cached ``custom_*`` slug is checked against its base role's rank
        AND its granted modules; an uncached custom slug fails closed.
        """
        custom = _custom_role_entry(role)
        if custom is not None:
            return self._custom_role_has_permission(custom, permission)

        resolved = _resolve_role(role)
        if resolved is None:
            return False

        # Admin bypasses all checks
        if resolved == Role.ADMIN:
            return True

        min_role = self._permissions.get(permission)
        if min_role is None:
            # Unknown permission - deny by default
            logger.warning("Unknown permission checked: %s", permission)
            return False

        return ROLE_HIERARCHY.get(resolved, -1) >= ROLE_HIERARCHY.get(min_role, 999)

    def _custom_role_has_permission(self, entry: dict, permission: str) -> bool:
        """Permission check for a cached custom role.

        Both conditions must hold: the base role's rank must clear the
        permission's minimum role, and the permission's module must be in
        the role's granted modules. Permissions with no module mapping keep
        base-role behaviour. (The ``role == "admin"`` string bypass in
        dependencies.py is untouched - it only fires for the literal admin
        role, never for a custom slug.)
        """
        base = Role(entry["base_role"])
        min_role = self._permissions.get(permission)
        if min_role is None:
            logger.warning("Unknown permission checked: %s", permission)
            return False
        if ROLE_HIERARCHY.get(base, -1) < ROLE_HIERARCHY.get(min_role, 999):
            return False
        module = self._permission_modules.get(permission)
        if module is not None and module not in entry["granted_modules"]:
            return False
        return True

    def get_role_permissions(self, role: Role | str) -> list[str]:
        """Get all permissions available to a role.

        A cached ``custom_*`` slug gets its base role's permission list with
        every permission whose module is not granted removed; permissions
        with no module mapping stay as per the base role. An uncached custom
        slug gets nothing (fail-closed).
        """
        custom = _custom_role_entry(role)
        if custom is not None:
            return self._custom_role_permissions(custom)

        resolved = _resolve_role(role)
        if resolved is None:
            return []

        if resolved == Role.ADMIN:
            return list(self._permissions.keys())

        return [
            perm
            for perm, min_role in self._permissions.items()
            if ROLE_HIERARCHY.get(resolved, -1) >= ROLE_HIERARCHY.get(min_role, 999)
        ]

    def _custom_role_permissions(self, entry: dict) -> list[str]:
        """Permission list for a cached custom role (module-scoped)."""
        base = Role(entry["base_role"])
        granted = set(entry["granted_modules"])
        if base == Role.ADMIN:
            # No rank gate for an admin-based custom role, but the module
            # grant still applies - it is the whole point of the scoping.
            base_perms = list(self._permissions.keys())
        else:
            base_perms = [
                perm
                for perm, min_role in self._permissions.items()
                if ROLE_HIERARCHY.get(base, -1) >= ROLE_HIERARCHY.get(min_role, 999)
            ]
        return [
            perm
            for perm in base_perms
            if (module := self._permission_modules.get(perm)) is None or module in granted
        ]

    def list_all(self) -> dict[str, str]:
        """List all registered permissions with their minimum role."""
        return {perm: role.value for perm, role in sorted(self._permissions.items())}

    def list_modules(self) -> dict[str, list[str]]:
        """List permissions grouped by module."""
        return dict(self._module_permissions)

    def clear(self) -> None:
        """Remove all permissions. Used in testing."""
        self._permissions.clear()
        self._module_permissions.clear()
        self._permission_modules.clear()

    # ── Edit operations (used by the admin permissions matrix UI) ─────────

    def has(self, permission: str) -> bool:
        """True iff the permission key exists in the registry."""
        return permission in self._permissions

    def get_min_role(self, permission: str) -> Role | None:
        """Return the minimum role required for ``permission`` or ``None``."""
        return self._permissions.get(permission)

    def set_min_role(self, permission: str, min_role: Role) -> Role:
        """Update the minimum role for an existing permission.

        Returns the previous ``min_role`` so callers can audit the delta.
        Raises ``KeyError`` if the permission is not registered - we never
        silently create permissions through the admin UI.
        """
        previous = self._permissions.get(permission)
        if previous is None:
            raise KeyError(permission)
        self._permissions[permission] = min_role
        logger.info(
            "Permission min_role updated: %s %s → %s",
            permission,
            previous.value,
            min_role.value,
        )
        return previous

    def snapshot(self) -> dict[str, Role]:
        """Return a copy of the current permission → min_role map.

        Used by the admin UI to diff against a preset / baseline without
        mutating the live registry.
        """
        return dict(self._permissions)


# Global singleton (lineage ref ddc-lineage:a17f93c4-core-01)
permission_registry = PermissionRegistry()


# ── Role presets for the admin UI ─────────────────────────────────────────
#
# A preset answers "what should role X be able to do by default?" without
# resetting every permission row by hand. Applied by walking every
# registered permission and computing the implied min_role from a rule.
#
# Each preset is a callable (permission_key) -> Role:
#
#   • viewer-default   - viewer can read, everything else stays Editor+.
#   • editor-default   - editor can read/create/update, manager+ for
#                        delete / destructive actions, admin for "system."
#   • manager-default  - manager can do almost anything; admin still owns
#                        system-level toggles.
#
# Presets are intentionally derived from the permission key shape rather
# than from a hard-coded list - this keeps them working even as new
# modules register new permissions.


def _viewer_default(key: str) -> Role:
    # Everything readable to viewers, structural changes manager+, system
    # toggles admin-only.
    if key.startswith("system.") or key.endswith(".delete"):
        return Role.ADMIN if key.startswith("system.") else Role.MANAGER
    if any(key.endswith(s) for s in (".read", ".list", ".view", ".export")):
        return Role.VIEWER
    return Role.EDITOR


def _editor_default(key: str) -> Role:
    if key.startswith("system."):
        return Role.ADMIN
    if key.endswith(".delete") or key.endswith(".approve") or key.endswith(".reject"):
        return Role.MANAGER
    if any(key.endswith(s) for s in (".read", ".list", ".view", ".export")):
        return Role.VIEWER
    return Role.EDITOR


def _manager_default(key: str) -> Role:
    if key.startswith("system."):
        return Role.ADMIN
    if any(key.endswith(s) for s in (".read", ".list", ".view", ".export")):
        return Role.VIEWER
    if any(key.endswith(s) for s in (".create", ".update", ".import")):
        return Role.EDITOR
    return Role.MANAGER


PRESETS: dict[str, "callable"] = {
    "viewer-default": _viewer_default,
    "editor-default": _editor_default,
    "manager-default": _manager_default,
}


def register_field_role_permissions() -> None:
    """Register the field-worker surface permission set.

    DESIGN-STAGE STUB - intentionally empty until the pilot
    ``/api/v1/field/*`` router lands. See
    ``docs/architecture/FIELD_WORKER_MOBILE_DESIGN.md`` §4 for the
    full permission matrix the pilot will fill in.

    TODO (pilot, Daily Diary surface):
      * ``daily_diary.read``           → FIELD_WORKER (own day only,
        scope enforced at service layer via
        ``oe_field_module_grant``)
      * ``daily_diary.create``         → FIELD_WORKER
      * ``daily_diary.update``         → FIELD_WORKER (own entries
        <24 h; foreman-and-above for others)
      * ``daily_diary.upload_photo``   → FIELD_WORKER
      * ``daily_diary.fetch_weather``  → FIELD_WORKER
      * ``daily_diary.close``          → SITE_FOREMAN (sign-off)
      * ``daily_diary.sign``           → MANAGER (unchanged)

    TODO (phase 2 - design-doc §4.2):
      * ``hse_advanced.report_incident`` → FIELD_WORKER
      * ``ncr.flag``                     → FIELD_WORKER
      * ``inspections.create``           → SITE_INSPECTOR
      * ``punchlist.update_own``         → FIELD_WORKER
      * ``equipment.log_usage``          → FIELD_WORKER

    Until those permissions are registered here, the three field
    roles can sign in (the ``Role`` enum members exist) but every
    permission check returns False - by design.
    """
    # Intentionally empty. See module docstring above.
    return


def register_core_permissions() -> None:
    """Register permissions for core system features."""
    permission_registry.register_module_permissions(
        "system",
        {
            "system.settings.read": Role.MANAGER,
            "system.settings.write": Role.ADMIN,
            "system.modules.list": Role.VIEWER,
            "system.modules.install": Role.ADMIN,
            "system.modules.uninstall": Role.ADMIN,
            "system.modules.enable": Role.ADMIN,
            "system.modules.disable": Role.ADMIN,
            "system.hooks.list": Role.ADMIN,
            "system.validation_rules.list": Role.VIEWER,
            # Audit log + viewer (audit_router.py + future admin UI).
            # Without these, `RequirePermission("audit.view")` resolved to an
            # unknown permission and fell through to the ADMIN-role bypass -
            # technically safe but the gate was effectively ADMIN-only by
            # accident, and "audit.delete" was completely unreachable.
            "audit.view": Role.MANAGER,
            "audit.delete": Role.ADMIN,
            # Epic H §H9 - GDPR right-to-erasure on activity-log rows.
            # ADMIN-only by design: a redact mutates compliance records.
            "audit.redact": Role.ADMIN,
        },
    )
