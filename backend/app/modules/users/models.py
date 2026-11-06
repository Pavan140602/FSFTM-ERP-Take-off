# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""User ORM models.

Tables:
    oe_users_user - registered users
    oe_users_api_key - API keys for programmatic access
    oe_users_session - login sessions, so one can be revoked without the rest
    oe_users_custom_role - admin-defined custom roles (see CustomRole)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import GUID, Base


class User(Base):
    """Application user."""

    __tablename__ = "oe_users_user"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="editor")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Tracks when the password was last changed. Tokens issued (`iat`) before
    # this timestamp are considered invalid - see dependencies.get_current_user.
    # Used to invalidate existing sessions on password change.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # GDPR Art. 17 erasure marker. When the account holder self-erases via
    # DELETE /api/v1/users/me the row is anonymised in place (PII nulled,
    # password hash invalidated, is_active flipped False) rather than hard
    # deleted, so foreign-key references (projects, activity, audit) survive.
    # This timestamp records when that happened; NULL means a live account.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # OIDC subject identifier (Keycloak / any OIDC provider). Set on first
    # OIDC login and used to match returning OIDC users to local accounts.
    oidc_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    oidc_issuer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ── Per-user SMTP (individual sender) ──
    # When set, task-assignment (and future per-user) emails send through
    # THIS user's SMTP with their own From address, instead of the system
    # SMTP. Password is Fernet-encrypted at rest (app.core.crypto).
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_password_enc: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    smtp_from: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    smtp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # When True, automated emails (task assigned, etc.) are sent through the
    # user's own SMTP (their Sent box will contain them). When False (default),
    # the system SMTP sends with "Name via FSFTM ERP" as From and the user's
    # address as Reply-To — user's Sent box stays clean.
    smtp_use_for_automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Regional preferences
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC", server_default="UTC")
    measurement_system: Mapped[str] = mapped_column(
        String(20), nullable=False, default="metric", server_default="metric"
    )
    # "auto" means the paper size follows the country of the project the
    # document belongs to, resolved by app.core.paper_size. The old default of
    # "A4" was not a neutral start: it is a real choice a European user makes
    # on purpose, so "nobody chose" and "chose A4" were the same row and no
    # generator could have told a US account apart from a German one even once
    # it started reading this column. server_default stays "A4" for the reason
    # spelled out under date_format below - changing it alters the table DDL
    # and needs a migration for no functional gain, because ORM inserts always
    # supply the Python-side default. Accounts created before this still carry
    # "A4" and keep rendering A4, which is what they rendered yesterday.
    paper_size: Mapped[str] = mapped_column(String(10), nullable=False, default="auto", server_default="A4")
    # "auto" means numbers follow the interface language, the same neutral
    # start the date_format below already takes. The old default handed every
    # new account in the world German grouping, and because the column is
    # free-form nothing downstream could tell that seeded "1.234,56" apart from
    # a reader who deliberately picked German. server_default stays "1.234,56"
    # for the reason spelled out under date_format: changing it alters the
    # table DDL and needs a migration for no functional gain, because ORM
    # inserts always supply the Python-side default. Accounts created before
    # this still carry "1.234,56"; the frontend store treats that exact value
    # as "never chose" so their rendering does not change.
    number_format: Mapped[str] = mapped_column(String(20), nullable=False, default="auto", server_default="1.234,56")
    # "auto" means the UI follows the interface language when rendering dates.
    # New accounts start there so the stored value is only ever an order the
    # user actually picked. server_default stays "DD.MM.YYYY" for the same
    # reason as currency_code below - changing it would alter the table DDL and
    # require a migration for no functional gain, because ORM inserts always
    # supply the Python-side default. Accounts created before the automatic
    # option still carry "DD.MM.YYYY"; the frontend store treats that exact
    # value as "never chose" so their rendering does not change.
    date_format: Mapped[str] = mapped_column(String(20), nullable=False, default="auto", server_default="DD.MM.YYYY")
    # No EUR bias for new accounts: empty string means "not chosen yet" and
    # the UI falls back to the project currency / local preference store.
    # server_default stays "EUR" on purpose - changing it would alter the
    # table DDL and require an alembic migration for zero functional gain
    # (ORM inserts always supply the Python-side default).
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False, default="", server_default="EUR")

    # Relationships
    # Never loaded implicitly. Every authenticated request re-reads the caller
    # with session.get(User), and "selectin" made that a second SELECT against
    # oe_users_api_key for a collection nothing reads; keys are listed through
    # APIKeyRepository. passive_deletes leaves removal of a deleted user's keys
    # to the FK's ON DELETE CASCADE, which the table has carried since it was
    # first created, instead of loading them to delete one by one.
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise_on_sql",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


class APIKey(Base):
    """API key for programmatic access."""

    __tablename__ = "oe_users_api_key"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # First 8 chars for identification
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permissions: Mapped[list] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=list, server_default="[]"
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}... ({self.name})>"


class UserSession(Base):
    """One login session, named by the ``sid`` claim its tokens carry.

    This row is what makes revoking a single session expressible. Before it,
    every token carried a ``jti`` that nothing read, so an issued credential
    had a name but no record, and the only way to end one session was to
    rotate the signing secret, which ends everybody's. Revocation now has
    something to point at: the access token and the refresh token minted
    together carry the same ``sid``, so refusing this row refuses the pair and
    every pair rotated out of it.

    Revocation sets ``revoked_at``; it never deletes the row. That is the
    whole reason a "revoked" column exists rather than just a missing row: a
    token whose session cannot be found is honoured (see
    ``reject_revoked_session`` in ``app.dependencies`` for why), so deleting
    the row would *undo* the revocation instead of enforcing it. Pruning is
    therefore only ever allowed to touch rows already past ``expires_at``,
    which no live credential can be pointing at.
    """

    __tablename__ = "oe_users_session"

    # The token claim, ``uuid4().hex`` (32 chars); sized with headroom so a
    # future change of generator does not need a migration. Unique because it
    # names one session, indexed because every authenticated request looks a
    # token up by it.
    sid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The refresh horizon, not the access horizon: the session stays alive as
    # long as its refresh token can still mint, which is what a person means
    # by "I am still logged in on that laptop". Also the pruning boundary.
    # Indexed here as well as in the migration so the two descriptions of this
    # table stay identical; declared in only one of them, the next
    # autogenerated revision would propose dropping the index.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Written on refresh rather than on every request: it exists so a person
    # can recognise which session to end, and paying a write on each
    # authenticated call to sharpen that timestamp is not worth it.
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        state = "revoked" if self.revoked_at else "active"
        return f"<UserSession {self.sid[:8]}... ({state})>"


class CustomRole(Base):
    """Admin-defined custom role category.

    Lets an admin add role categories (e.g. "Senior Estimator") without a
    code change or a migration per role. A user carries the role through the
    free-form ``User.role`` column as the slug (``custom_senior_estimator``),
    so the users table itself needs no change.

    Semantics are resolved at read time by ``app.core.permissions`` from an
    in-memory cache the users module refreshes after every CRUD:

      * ``base_role`` - one of the canonical four; sets the rank and the
        starting permission list (a custom role never exceeds its base).
      * ``granted_modules`` - module keys (as registered via
        ``register_module_permissions``); permissions whose module is not
        listed here are removed from the base role's list. Empty list means
        the role keeps the module-less permissions only - effectively almost
        nothing.
    """

    __tablename__ = "oe_users_custom_role"

    # The value stored on User.role. Always ``custom_``-prefixed so the
    # permission engine can tell it apart from canonical roles and aliases.
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_role: Mapped[str] = mapped_column(String(20), nullable=False, default="editor")
    granted_modules: Mapped[list] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=list, server_default="[]"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # No FK: the creator may later be erased (GDPR anonymisation keeps the
    # row), and a dangling creator id must never block that.
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    def __repr__(self) -> str:
        return f"<CustomRole {self.slug} (base={self.base_role})>"


class RoleModuleConfig(Base):
    """OE-DELIVERY 2026-10-16: Per-role module visibility configuration.

    Admin sets which modules each role can see. Covers both canonical roles
    (admin/manager/editor/viewer) and custom roles (custom_* slugs).
    The admin role always has all modules (enforced in the service layer,
    not here).

    If no row exists for a role, the role falls back to its default:
    custom roles use their granted_modules; canonical roles see all modules
    their permission rank allows.
    """

    __tablename__ = "oe_role_module_config"

    # Role slug: 'admin', 'manager', 'editor', 'viewer', or custom_* slug.
    role_slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    granted_modules: Mapped[list] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=list, server_default="[]"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    def __repr__(self) -> str:
        return f"<RoleModuleConfig {self.role_slug} ({len(self.granted_modules or [])} modules)>"
