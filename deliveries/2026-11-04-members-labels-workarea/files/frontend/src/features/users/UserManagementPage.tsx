// OE-DELIVERY: 2026-10-22-problemfix
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * User Management Page — admin panel for managing users, roles, module access.
 *
 * Features:
 * - User list with role badges and status
 * - Invite new users
 * - Change roles (admin/manager/editor/viewer)
 * - Activate/deactivate users
 * - Per-user module access matrix (visible + access level per module)
 * - Custom role names
 */

import { useState, useCallback, useMemo, useEffect, useRef, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Users,
  Shield,
  ShieldCheck,
  UserPlus,
  UserCog,
  Plus,
  Search,
  Check,
  X,
  Mail,
  Clock,
  Crown,
  Eye,
  Edit3,
  ChevronDown,
  Settings2,
  Lock,
  Unlock,
  Save,
  Trash2,
} from 'lucide-react';
import type { TFunction } from 'i18next';
import { Card, Badge, Button, WideModal, Breadcrumb, ConfirmDialog, DismissibleInfo, IntroRichText, ModuleGuideButton } from '@/shared/ui';
import { PageHeader } from '@/shared/ui/PageHeader';
import { NoAccessState } from '@/shared/ui/NoAccessState';
import { useHasPermission } from '@/shared/lib/permissionGates';
import { usersGuide } from './usersGuide';
import { useConfirm } from '@/shared/hooks/useConfirm';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { apiGet } from '@/shared/lib/api';
import {
  createUserAccount,
  fetchUsers,
  updateUser,
  deleteUser,
  sendInviteLink,
  getUserModuleAccess,
  setUserModuleAccess,
  fetchRoles,
  fetchRoleModules,
  fetchRoleModuleConfigs,
  updateRoleModuleConfig,
  createCustomRole,
  deleteCustomRole,
  CANONICAL_ROLES,
  type User,
  type UserRole,
  type CustomRole,
  type RoleModuleConfig,
  type ModuleAccessLevel,
  type ModuleAccess,
} from './api';
import { getIntlLocale } from '@/shared/lib/formatters';
import { navGroups } from '@/app/layout/navCatalog';

const inputCls =
  'h-10 w-full rounded-lg border border-border bg-surface-primary px-3 text-sm focus:outline-none focus:ring-2 focus:ring-oe-blue/30 focus:border-oe-blue';

/* ── Role + module config ───────────────────────────────────────────────
 *
 * Display labels are i18n-keyed (NOT hardcoded English) so that admins
 * running the UI in DE / RU / AR / etc. see translated chips. The
 * canonical English copy lives in `frontend/src/app/locales/en.ts`
 * under `users.roles.*`, `users.access_levels.*`, `users.module_group.*`
 * and `users.modules.*`. Other locale files are backfilled in a
 * separate i18n sweep — until then react-i18next falls back to the
 * `en` resource via `fallbackLng: 'en'` (see app/i18n.ts).
 *
 * Note: no `labelDefault` strings are stored in this file. Doing so
 * would re-introduce hardcoded English literals that the regression
 * grep (Admin / Manager / Core / Planning / Bill of Quantities …) is
 * supposed to catch. The English fallback lives ONLY in `en.ts`.
 */

interface RoleConfigEntry {
  icon: React.ElementType;
  /** i18n key suffix under `users.roles.{key}`. */
  labelKey: UserRole;
  color: string;
  variant: 'neutral' | 'blue' | 'success' | 'warning' | 'error';
}

const ROLE_CONFIG: Record<UserRole, RoleConfigEntry> = {
  admin: {
    icon: Crown,
    labelKey: 'admin',
    color: 'text-red-600 dark:text-red-400',
    variant: 'error',
  },
  manager: {
    icon: ShieldCheck,
    labelKey: 'manager',
    color: 'text-amber-600 dark:text-amber-400',
    variant: 'warning',
  },
  editor: {
    icon: Edit3,
    labelKey: 'editor',
    color: 'text-blue-600 dark:text-blue-400',
    variant: 'blue',
  },
  viewer: {
    icon: Eye,
    labelKey: 'viewer',
    color: 'text-content-tertiary',
    variant: 'neutral',
  },
};

const ROLES: UserRole[] = ['admin', 'manager', 'editor', 'viewer'];

// Privilege ranking (higher = more access). Used to detect a role DOWNGRADE,
// which is treated as a destructive action and gated behind a confirmation.
const ROLE_RANK: Record<UserRole, number> = {
  admin: 3,
  manager: 2,
  editor: 1,
  viewer: 0,
};

/* ── Custom-role resolution ──────────────────────────────────────────
 *
 * Custom roles arrive from `GET /v1/users/roles/` as `{ slug, name, … }`
 * and must render everywhere a canonical role does (invite grid, row
 * dropdown, downgrade confirm) without crashing on a slug the client
 * hasn't seen before. These helpers centralise that resolution.
 */

interface ResolvedRoleConfig {
  icon: React.ElementType;
  /** Display label — translated for canonical roles, the role's own name for custom ones. */
  label: string;
  color: string;
  variant: 'neutral' | 'blue' | 'success' | 'warning' | 'error';
}

/** Chip config for any role slug; degrades gracefully for unknown slugs. */
function getRoleConfig(
  role: string,
  customRoles: CustomRole[],
  t: TFunction,
): ResolvedRoleConfig {
  const canonical = ROLE_CONFIG[role];
  if (canonical) {
    return {
      icon: canonical.icon,
      label: t(`users.roles.${canonical.labelKey}`),
      color: canonical.color,
      variant: canonical.variant,
    };
  }
  const custom = customRoles.find((r) => r.slug === role);
  return {
    icon: UserCog,
    label: custom?.name ?? role,
    color: 'text-content-tertiary',
    variant: 'neutral',
  };
}

/**
 * Privilege rank for any role slug. Canonical roles use ROLE_RANK; a custom
 * role ranks with its base role (server-provided `rank`). Unknown slugs rank
 * 0 (viewer-level) so downgrade gating fails safe.
 */
function getRoleRank(role: string, customRoles: CustomRole[]): number {
  const canonical = ROLE_RANK[role];
  if (typeof canonical === 'number') return canonical;
  return customRoles.find((r) => r.slug === role)?.rank ?? 0;
}

const ACCESS_LEVELS: {
  value: ModuleAccessLevel;
  labelKey: ModuleAccessLevel;
  color: string;
}[] = [
  { value: 'none', labelKey: 'none', color: 'text-content-quaternary' },
  { value: 'view', labelKey: 'view', color: 'text-blue-600' },
  { value: 'edit', labelKey: 'edit', color: 'text-amber-600' },
  { value: 'full', labelKey: 'full', color: 'text-green-600' },
];

interface ModuleEntry {
  /** Stable module key (used as i18n suffix and access map key). */
  id: string;
}

interface ModuleGroupEntry {
  /** Stable group key (used as i18n suffix under `users.module_group.{key}`). */
  key: string;
  modules: ModuleEntry[];
}

// All manageable modules grouped by category. Labels are translated at
// render time via `t('users.modules.{id}')` and
// `t('users.module_group.{key}')`. English copy lives in en.ts.
const MODULE_GROUPS: ModuleGroupEntry[] = [
  {
    key: 'core',
    modules: [
      { id: 'projects' },
      { id: 'boq' },
      { id: 'costs' },
      { id: 'assemblies' },
      { id: 'validation' },
    ],
  },
  {
    key: 'planning_finance',
    modules: [
      { id: 'schedule' },
      { id: 'costmodel' },
      { id: 'finance' },
      { id: 'procurement' },
      { id: 'changeorders' },
    ],
  },
  {
    key: 'communication',
    modules: [
      { id: 'tasks' },
      { id: 'meetings' },
      { id: 'rfi' },
      { id: 'correspondence' },
      { id: 'transmittals' },
    ],
  },
  {
    key: 'quality_safety',
    modules: [
      { id: 'inspections' },
      { id: 'ncr' },
      { id: 'safety' },
      { id: 'punchlist' },
      { id: 'submittals' },
    ],
  },
  {
    key: 'documents_bim',
    modules: [
      { id: 'documents' },
      { id: 'cde' },
      { id: 'bim_hub' },
      { id: 'fieldreports' },
      { id: 'contacts' },
    ],
  },
  {
    key: 'ai_analytics',
    modules: [
      { id: 'ai' },
      { id: 'takeoff' },
      { id: 'reporting' },
      { id: 'risk' },
    ],
  },
];

const PRESET_OPTIONS: { key: 'all' | 'viewer' | 'minimal' }[] = [
  { key: 'all' },
  { key: 'viewer' },
  { key: 'minimal' },
];

/* ── Invite User Modal ─────────────────────────────────────────────────
 *
 * Replaced the hand-rolled <div> dialog wrapper with the shared
 * <WideModal> component so we inherit focus-trap, Escape-to-close,
 * backdrop-click dismissal, body-scroll-lock and the consistent
 * surface / border / radii tokens. Round 2 audit flagged the old
 * hand-rolled markup as a regression — every other recent module
 * (Service / Resources / Procurement / Portal / etc.) standardised on
 * WideModal.
 */

function InviteModal({
  onClose,
  onSubmit,
  isPending,
}: {
  onClose: () => void;
  onSubmit: (data: { email: string; full_name: string }) => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ email: '', full_name: '' });
  const canSubmit = !isPending && !!form.full_name && /.+@.+\..+/.test(form.email);

  return (
    <WideModal
      open
      onClose={onClose}
      title={t('users.invite_user', { defaultValue: 'Invite User' })}
      size="sm"
      busy={isPending}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </Button>
          <Button
            variant="primary"
            icon={<UserPlus size={14} />}
            disabled={!canSubmit}
            loading={isPending}
            onClick={() => onSubmit(form)}
          >
            {isPending
              ? t('common.sending', { defaultValue: 'Sending...' })
              : t('users.invite', { defaultValue: 'Invite' })}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-content-secondary">
          {t('users.invite.linkHint', {
            defaultValue:
              'We email them a link to create their own account. They set their password and choose their role - you activate the account afterwards.',
          })}
        </p>
        <div>
          <label
            htmlFor="invite_full_name"
            className="block text-xs font-medium text-content-secondary mb-1"
          >
            {t('users.full_name', { defaultValue: 'Full Name' })}
          </label>
          <input
            id="invite_full_name"
            className={inputCls}
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            placeholder={t('users.invite.namePlaceholder', {
              defaultValue: 'e.g. Anna Schmidt',
            })}
            autoFocus
          />
        </div>
        <div>
          <label
            htmlFor="invite_email"
            className="block text-xs font-medium text-content-secondary mb-1"
          >
            {t('users.email', { defaultValue: 'Email' })}
          </label>
          <input
            id="invite_email"
            className={inputCls}
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder={t('users.invite.emailPlaceholder', {
              defaultValue: 'name@company.com',
            })}
          />
        </div>
      </div>
    </WideModal>
  );
}

/* ── Create Account Modal (OE-DELIVERY 2026-11-03-admin-create-user) ──
 * The admin sets name, email, a first password and the role; the account is
 * active at once (no email needed). The user can change the password later. */
function CreateAccountModal({
  onClose,
  onSubmit,
  isPending,
}: {
  onClose: () => void;
  onSubmit: (data: { email: string; full_name: string; password: string; role: string }) => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'editor' });
  const [show, setShow] = useState(false);
  const pwOk = form.password.length >= 12 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password);
  const canSubmit = !isPending && !!form.full_name.trim() && /.+@.+\..+/.test(form.email) && pwOk;
  return (
    <WideModal
      open
      onClose={onClose}
      title={t('users.create_account', { defaultValue: 'Create account' })}
      size="sm"
      busy={isPending}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </Button>
          <Button variant="primary" icon={<UserPlus size={14} />} disabled={!canSubmit} loading={isPending} onClick={() => onSubmit({ ...form, full_name: form.full_name.trim(), email: form.email.trim() })}>
            {t('users.create_account', { defaultValue: 'Create account' })}
          </Button>
        </>
      }
    >
      <div className="space-y-4" data-testid="create-account-form">
        <p className="text-sm text-content-secondary">
          {t('users.create_account_hint', { defaultValue: 'The account works straight away - no email or approval needed. Give the person their email and this first password; they can change it under their profile.' })}
        </p>
        <div>
          <label htmlFor="ca_name" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.full_name', { defaultValue: 'Full Name' })}</label>
          <input id="ca_name" className={inputCls} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoFocus data-testid="ca-name" />
        </div>
        <div>
          <label htmlFor="ca_email" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.email', { defaultValue: 'Email' })}</label>
          <input id="ca_email" type="email" className={inputCls} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@company.com" data-testid="ca-email" />
        </div>
        <div>
          <label htmlFor="ca_pw" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.first_password', { defaultValue: 'First password' })}</label>
          <div className="flex gap-2">
            <input id="ca_pw" type={show ? 'text' : 'password'} className={inputCls} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" data-testid="ca-password" />
            <Button variant="ghost" size="sm" onClick={() => setShow((v) => !v)}>{show ? t('common.hide', { defaultValue: 'Hide' }) : t('common.show', { defaultValue: 'Show' })}</Button>
          </div>
          <p className={clsx('mt-1 text-[11px]', form.password && !pwOk ? 'text-semantic-error' : 'text-content-tertiary')}>
            {t('users.password_rule_admin', { defaultValue: 'At least 12 characters, with a letter and a digit (not a common password).' })}
          </p>
        </div>
        <div>
          <label htmlFor="ca_role" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.role', { defaultValue: 'Role' })}</label>
          <select id="ca_role" className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} data-testid="ca-role">
            <option value="admin">{t('users.role_admin', { defaultValue: 'Admin - full access, manages users' })}</option>
            <option value="manager">{t('users.role_manager', { defaultValue: 'Manager' })}</option>
            <option value="editor">{t('users.role_editor', { defaultValue: 'Editor - can take off and edit' })}</option>
            <option value="viewer">{t('users.role_viewer', { defaultValue: 'Viewer - read only' })}</option>
          </select>
        </div>
      </div>
    </WideModal>
  );
}

/* ── Create Custom Role Modal ──────────────────────────────────────────
 *
 * Admin-only dialog for defining a new custom role: a name, the canonical
 * role its permissions start from, and the module set it grants. Uses the
 * shared <WideModal> shell like InviteModal. Module labels come from
 * `GET /v1/users/roles/modules/` (server is the source of truth); the
 * "All modules" master checkbox starts checked and toggles the whole grid.
 */

function CreateCustomRoleModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const currentUserId = useAuthStore((s) => s.userId);
  const [name, setName] = useState('');
  const [baseRole, setBaseRole] = useState<string>('editor');

  const { data: modules = [] } = useQuery({
    queryKey: ['role-modules'],
    queryFn: fetchRoleModules,
  });

  // OE-DELIVERY 2026-10-16: fetch all roles (canonical + custom) so custom
  // roles appear as base-permission options. New custom roles appear
  // automatically on refetch.
  const { data: allRoles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: fetchRoles,
  });
  const customRoles = useMemo(
    () => allRoles.filter((r) => r.is_custom),
    [allRoles]
  );

  // OE-DELIVERY 2026-10-16: current user's granted modules — the admin can
  // only grant modules they themselves have access to.
  const { data: myAccess } = useQuery({
    queryKey: ['user-module-access', currentUserId],
    queryFn: () => getUserModuleAccess(currentUserId!),
    enabled: !!currentUserId,
  });
  const myGrantedKeys = useMemo(() => {
    if (!myAccess?.modules) return null; // not loaded yet → show all
    const keys = new Set(
      Object.entries(myAccess.modules)
        .filter(([, v]) => v && v.visible && v.access !== 'none')
        .map(([k]) => k)
    );
    // OE-DELIVERY 2026-10-16 fix: admins have implicit access to everything
    // (no explicit grants), so an empty set means "no restriction", not
    // "no modules". Only filter when there are actual restrictions.
    return keys.size > 0 ? keys : null;
  }, [myAccess]);

  // OE-DELIVERY 2026-10-16: group modules by the sidebar navbar sections.
  // Derived from navGroups so new modules appear automatically. Modules
  // without a nav entry fall into "Other". Only modules the current user
  // can access are shown.
  const groupedModules = useMemo(() => {
    const byKey = new Map(modules.map((m) => [m.key, m]));
    const used = new Set<string>();
    const groups: { id: string; label: string; items: typeof modules }[] = [];
    const navKey = (item: { moduleKey?: string; to: string }) =>
      item.moduleKey || item.to.replace(/^\//, '').split('/')[0]?.split('?')[0] || undefined;

    for (const g of navGroups) {
      const items: typeof modules = [];
      for (const item of g.items) {
        const mk = navKey(item);
        if (!mk || used.has(mk)) continue;
        const mod = byKey.get(mk);
        if (!mod) continue;
        // Access filter: only show modules the admin themselves can grant
        if (myGrantedKeys && !myGrantedKeys.has(mk)) continue;
        used.add(mk);
        items.push(mod);
      }
      if (items.length > 0) {
        groups.push({
          id: g.id,
          label: g.defaultLabel || g.labelKey,
          items,
        });
      }
    }
    // Ungrouped modules (no nav entry, e.g. future/backend-only) → "Other"
    const other = modules.filter((m) => {
      if (used.has(m.key)) return false;
      if (myGrantedKeys && !myGrantedKeys.has(m.key)) return false;
      return true;
    });
    if (other.length > 0) {
      groups.push({ id: 'other', label: 'Other', items: other });
    }
    return groups;
  }, [modules, myGrantedKeys]);

  // Flat list of visible (grouped + access-filtered) module keys.
  // OE-DELIVERY 2026-10-16: module access is managed in Role Module Access
  // (Users page) — new roles start with all visible modules granted.
  const visibleKeys = useMemo(
    () => groupedModules.flatMap((g) => g.items.map((m) => m.key)),
    [groupedModules]
  );

  const handleBaseRoleChange = (r: string) => {
    setBaseRole(r);
  };

  const createMut = useMutation({
    mutationFn: () =>
      createCustomRole({
        name: name.trim(),
        base_role: baseRole,
        granted_modules: [...visibleKeys],
      }),
    onSuccess: (created) => {
      // OE-DELIVERY 2026-10-16: live update — add the new role to the
      // role-module-configs cache immediately so the tab appears without
      // a page refresh. Invalidate both queries for safety.
      queryClient.setQueryData<RoleModuleConfig[]>(
        ['role-module-configs'],
        (old) =>
          old
            ? [
                ...old,
                {
                  role_slug: created.slug,
                  role_name: created.name,
                  is_custom: true,
                  granted_modules: created.granted_modules ?? [],
                  locked: false,
                },
              ]
            : old
      );
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      queryClient.invalidateQueries({ queryKey: ['role-module-configs'] });
      addToast({
        type: 'success',
        title: t('users.custom_role_created', { defaultValue: 'Custom role created' }),
      });
      onClose();
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('users.custom_role_create_failed', {
          defaultValue: 'Could not create custom role',
        }),
        message: e.message,
      });
    },
  });

  const canSubmit = !createMut.isPending && name.trim().length > 0;

  return (
    <WideModal
      open
      onClose={onClose}
      title={t('users.create_custom_role', { defaultValue: 'Create custom role' })}
      size="md"
      busy={createMut.isPending}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={createMut.isPending}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </Button>
          <Button
            variant="primary"
            icon={<UserCog size={14} />}
            disabled={!canSubmit}
            loading={createMut.isPending}
            onClick={() => createMut.mutate()}
          >
            {t('users.create_role', { defaultValue: 'Create role' })}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label
            htmlFor="custom_role_name"
            className="block text-xs font-medium text-content-secondary mb-1"
          >
            {t('users.custom_role', { defaultValue: 'Custom Role Name' })}
          </label>
          <input
            id="custom_role_name"
            className={inputCls}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('users.custom_role_placeholder', {
              defaultValue: 'e.g. Site Engineer, Cost Manager...',
            })}
            autoFocus
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-content-secondary mb-1">
            {t('users.base_permissions_on', { defaultValue: 'Base permissions on' })}
          </label>
          <div className="grid grid-cols-4 gap-2">
            {CANONICAL_ROLES.map((r) => {
              const cfg = ROLE_CONFIG[r];
              if (!cfg) return null;
              const Icon = cfg.icon;
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => handleBaseRoleChange(r)}
                  className={clsx(
                    'flex flex-col items-center gap-1 p-2 rounded-lg border text-xs font-medium transition-all',
                    baseRole === r
                      ? 'border-oe-blue bg-oe-blue/5 ring-2 ring-oe-blue/20'
                      : 'border-border hover:border-border-hover',
                  )}
                >
                  <Icon size={16} className={cfg.color} />
                  {t(`users.roles.${cfg.labelKey}`)}
                </button>
              );
            })}
            {/* OE-DELIVERY 2026-10-16: custom roles as base options */}
            {customRoles.map((cr) => (
              <button
                key={cr.slug}
                type="button"
                onClick={() => handleBaseRoleChange(cr.slug)}
                className={clsx(
                  'flex flex-col items-center gap-1 p-2 rounded-lg border text-xs font-medium transition-all',
                  baseRole === cr.slug
                    ? 'border-oe-blue bg-oe-blue/5 ring-2 ring-oe-blue/20'
                    : 'border-border hover:border-border-hover',
                )}
                title={cr.name}
              >
                <UserCog size={16} className="text-violet-600 dark:text-violet-400" />
                <span className="truncate max-w-full">{cr.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </WideModal>
  );
}

/* ── Module Access Panel ─────────────────────────────────────────────── */

function ModuleAccessPanel({
  user,
  onClose,
}: {
  user: User;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [customRoleName, setCustomRoleName] = useState('');
  const [modules, setModules] = useState<Record<string, ModuleAccess>>({});
  const [dirty, setDirty] = useState(false);

  const { data: accessData, isLoading } = useQuery({
    queryKey: ['user-module-access', user.id],
    queryFn: () => getUserModuleAccess(user.id),
  });

  // Resync local edit state whenever the server data changes (initial load,
  // reopen for a different user, or a post-save refetch). We skip the resync
  // while there are unsaved edits so an in-flight refetch doesn't clobber what
  // the admin is typing; a fresh panel open starts with `dirty === false`, so
  // the freshly fetched data is always applied. Depending only on `accessData`
  // (a referentially-stable react-query result) avoids an update loop.
  useEffect(() => {
    if (!accessData || dirty) return;
    setModules(accessData.modules || {});
    setCustomRoleName(accessData.custom_role_name || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessData]);

  const saveMut = useMutation({
    mutationFn: () =>
      setUserModuleAccess(user.id, { modules, custom_role_name: customRoleName || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-module-access', user.id] });
      setDirty(false);
      addToast({ type: 'success', title: t('users.access_saved', { defaultValue: 'Access settings saved' }) });
    },
    onError: (e: Error) => {
      addToast({ type: 'error', title: t('common.error', { defaultValue: 'Error' }), message: e.message });
    },
  });

  const getModuleAccess = (modId: string): ModuleAccess =>
    modules[modId] || { visible: true, access: 'edit' };

  const toggleVisible = (modId: string) => {
    const cur = getModuleAccess(modId);
    setModules({ ...modules, [modId]: { ...cur, visible: !cur.visible } });
    setDirty(true);
  };

  const setAccessLevel = (modId: string, level: ModuleAccessLevel) => {
    const cur = getModuleAccess(modId);
    setModules({ ...modules, [modId]: { ...cur, access: level, visible: level !== 'none' } });
    setDirty(true);
  };

  const applyPreset = (preset: 'all' | 'viewer' | 'minimal') => {
    const newModules: Record<string, ModuleAccess> = {};
    for (const group of MODULE_GROUPS) {
      for (const mod of group.modules) {
        if (preset === 'all') {
          newModules[mod.id] = { visible: true, access: 'full' };
        } else if (preset === 'viewer') {
          newModules[mod.id] = { visible: true, access: 'view' };
        } else {
          // minimal — only core modules
          const isCore = ['projects', 'boq', 'costs', 'tasks', 'documents'].includes(mod.id);
          newModules[mod.id] = { visible: isCore, access: isCore ? 'edit' : 'none' };
        }
      }
    }
    setModules(newModules);
    setDirty(true);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-lg animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-primary rounded-t-xl sm:rounded-xl shadow-2xl border border-border w-full max-w-2xl mx-0 sm:mx-4 max-h-[85vh] flex flex-col animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <Settings2 size={18} className="text-oe-blue" />
              <h3 className="text-base font-semibold">
                {t('users.module_access', { defaultValue: 'Module Access' })}
              </h3>
            </div>
            <p className="text-xs text-content-secondary mt-0.5">
              {user.full_name} ({user.email})
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label={t('common.close', { defaultValue: 'Close' })}
            className="p-1 rounded hover:bg-surface-secondary"
          >
            <X size={16} />
          </button>
        </div>

        {/* Custom role name + presets */}
        <div className="px-5 py-3 border-b border-border flex items-center gap-3 shrink-0">
          <div className="flex-1">
            <label className="block text-2xs font-medium text-content-tertiary mb-0.5">
              {t('users.custom_role', { defaultValue: 'Custom Role Name' })}
            </label>
            <input
              className="h-8 w-full max-w-xs rounded-md border border-border bg-surface-primary px-2 text-xs focus:outline-none focus:ring-1 focus:ring-oe-blue/30"
              value={customRoleName}
              onChange={(e) => {
                setCustomRoleName(e.target.value);
                setDirty(true);
              }}
              placeholder={t('users.custom_role_placeholder', {
                defaultValue: 'e.g. Site Engineer, Cost Manager...',
              })}
            />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-2xs text-content-tertiary mr-1">
              {t('users.presets', { defaultValue: 'Presets' })}:
            </span>
            {PRESET_OPTIONS.map((p) => (
              <button
                key={p.key}
                onClick={() => applyPreset(p.key)}
                className="px-2 py-1 text-2xs rounded border border-border hover:bg-surface-secondary transition-colors"
              >
                {t(`users.presets.${p.key}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Module matrix */}
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {isLoading ? (
            <div className="text-center py-8 text-content-tertiary text-sm">
              {t('common.loading', { defaultValue: 'Loading...' })}
            </div>
          ) : (
            MODULE_GROUPS.map((group) => (
              <div key={group.key} className="mb-4">
                <h4 className="text-2xs font-semibold uppercase tracking-wider text-content-tertiary mb-2">
                  {t(`users.module_group.${group.key}`)}
                </h4>
                <div className="space-y-1">
                  {group.modules.map((mod) => {
                    const acc = getModuleAccess(mod.id);
                    return (
                      <div
                        key={mod.id}
                        className={clsx(
                          'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                          acc.visible ? 'bg-surface-secondary/50' : 'opacity-50',
                        )}
                      >
                        {/* Toggle visibility */}
                        <button
                          onClick={() => toggleVisible(mod.id)}
                          className={clsx(
                            'w-5 h-5 rounded border flex items-center justify-center transition-colors shrink-0',
                            acc.visible
                              ? 'bg-oe-blue border-oe-blue text-white'
                              : 'border-border hover:border-border-hover',
                          )}
                        >
                          {acc.visible && <Check size={12} />}
                        </button>

                        {/* Module name */}
                        <span className="text-sm font-medium flex-1 min-w-0">
                          {t(`users.modules.${mod.id}`)}
                        </span>

                        {/* Access level selector */}
                        <div className="flex items-center gap-0.5 bg-surface-primary rounded-md border border-border p-0.5">
                          {ACCESS_LEVELS.map((lvl) => (
                            <button
                              key={lvl.value}
                              onClick={() => setAccessLevel(mod.id, lvl.value)}
                              className={clsx(
                                'px-2 py-0.5 text-2xs font-medium rounded transition-all',
                                acc.access === lvl.value
                                  ? 'bg-oe-blue text-white shadow-sm'
                                  : 'hover:bg-surface-secondary text-content-secondary',
                              )}
                            >
                              {t(`users.access_levels.${lvl.labelKey}`)}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border shrink-0">
          <div className="text-xs text-content-tertiary">
            {Object.values(modules).filter((m) => m.visible).length} / {MODULE_GROUPS.reduce((n, g) => n + g.modules.length, 0)}{' '}
            {t('users.modules_enabled', { defaultValue: 'modules enabled' })}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg hover:bg-surface-secondary">
              {t('common.cancel', { defaultValue: 'Cancel' })}
            </button>
            <button
              onClick={() => saveMut.mutate()}
              disabled={!dirty || saveMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-oe-blue text-white hover:bg-oe-blue-dark disabled:opacity-50 transition-colors"
            >
              <Save size={14} />
              {saveMut.isPending
                ? t('common.saving', { defaultValue: 'Saving...' })
                : t('common.save', { defaultValue: 'Save' })}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Role Dropdown ───────────────────────────────────────────────────── */

function RoleDropdown({
  currentRole,
  userId,
  onUpdate,
  disabled = false,
  disabledTitle,
  customRoles = [],
}: {
  currentRole: UserRole;
  userId: string;
  onUpdate: (userId: string, role: UserRole) => void;
  disabled?: boolean;
  disabledTitle?: string;
  /** Active custom roles, appended after the canonical four. Empty while loading. */
  customRoles?: CustomRole[];
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const cfg = getRoleConfig(currentRole, customRoles, t);
  const Icon = cfg.icon;
  // Canonical four first, then custom roles only (the API list also
  // contains the canonical four, so filter by is_custom to avoid doubles).
  const listRoles: string[] = [
    ...CANONICAL_ROLES,
    ...customRoles.filter((r) => r.is_custom).map((r) => r.slug),
  ];

  /* Anchor the popover via fixed positioning + a portal to <body> so it
     escapes parent overflow/transform stacking contexts that were
     clipping it inside the table row. Right-aligned to the trigger so
     it matches the previous design but never goes off-screen. */
  useLayoutEffect(() => {
    if (!open || !buttonRef.current) return;
    const rect = buttonRef.current.getBoundingClientRect();
    const POPOVER_WIDTH = 144; // matches w-36
    setPos({
      top: rect.bottom + 4,
      left: Math.max(8, rect.right - POPOVER_WIDTH),
    });
  }, [open]);

  // Re-position on scroll/resize so the popover stays glued to the trigger.
  useEffect(() => {
    if (!open) return;
    const reposition = () => {
      if (!buttonRef.current) return;
      const rect = buttonRef.current.getBoundingClientRect();
      const POPOVER_WIDTH = 144;
      setPos({
        top: rect.bottom + 4,
        left: Math.max(8, rect.right - POPOVER_WIDTH),
      });
    };
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
    return () => {
      window.removeEventListener('scroll', reposition, true);
      window.removeEventListener('resize', reposition);
    };
  }, [open]);

  // Close the popover on Escape while it is open.
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  return (
    <>
      <button
        ref={buttonRef}
        onClick={() => setOpen(!open)}
        disabled={disabled}
        title={disabled ? disabledTitle : undefined}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={clsx(
          'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors',
          disabled
            ? 'cursor-not-allowed opacity-60'
            : 'hover:bg-surface-secondary cursor-pointer',
        )}
      >
        <Icon size={13} className={cfg.color} />
        <span className="truncate max-w-[7rem]">{cfg.label}</span>
        {!disabled && <ChevronDown size={12} className="text-content-quaternary" />}
      </button>
      {open && pos && createPortal(
        <>
          <div className="fixed inset-0 z-[60]" onClick={() => setOpen(false)} />
          <div
            role="listbox"
            className="fixed z-[61] w-36 bg-surface-primary rounded-lg shadow-lg border border-border py-1 animate-fade-in"
            style={{ top: pos.top, left: pos.left }}
          >
            {listRoles.map((r) => {
              const rc = getRoleConfig(r, customRoles, t);
              const RIcon = rc.icon;
              return (
                <button
                  key={r}
                  role="option"
                  aria-selected={r === currentRole}
                  onClick={() => {
                    onUpdate(userId, r);
                    setOpen(false);
                  }}
                  className={clsx(
                    'flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-secondary',
                    r === currentRole && 'bg-surface-secondary font-medium',
                  )}
                >
                  <RIcon size={13} className={clsx(rc.color, 'shrink-0')} />
                  <span className="truncate">{rc.label}</span>
                  {r === currentRole && <Check size={12} className="ml-auto shrink-0 text-oe-blue" />}
                </button>
              );
            })}
          </div>
        </>,
        document.body,
      )}
    </>
  );
}

/* ── Main Page ───────────────────────────────────────────────────────── */

export function UserManagementPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  // Creating users is ADMIN-only (POST /users/ is gated by users.create=ADMIN).
  // Managers can view the page (users.list) but must not see the invite control,
  // since the call would 403. Server-side gate is authoritative regardless.
  const isAdmin = useAuthStore((s) => s.userRole) === 'admin';
  // Below manager the directory itself is refused (users.list), so the page
  // says so instead of firing the call and rendering an empty table.
  const canListUsers = useHasPermission('users.list');
  const { confirm, ...confirmProps } = useConfirm();
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all');
  const [showInvite, setShowInvite] = useState(false);
  const [showCustomRole, setShowCustomRole] = useState(false);
  const [accessUser, setAccessUser] = useState<User | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users', filterActive],
    queryFn: () =>
      fetchUsers({
        is_active: filterActive === 'all' ? undefined : filterActive === 'active',
        limit: 100,
      }),
    enabled: canListUsers,
  });

  // Active custom roles for the invite grid and row dropdowns. Falls back to
  // the canonical four while loading — the UI never blocks on this query.
  const { data: customRoles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: fetchRoles,
    enabled: canListUsers,
  });

  // Identify the currently logged-in user so we can lock down self-demotion and
  // self-deactivation (prevents an admin from accidentally locking themselves
  // out). The id comes from the authoritative /me endpoint; if it can't be
  // resolved the guards simply never match and nothing crashes.
  const { data: currentUser } = useQuery({
    // Distinct namespace so invalidating ['users'] after an edit doesn't churn
    // this self-identity lookup.
    queryKey: ['current-user', 'me'],
    queryFn: () => apiGet<User>('/v1/users/me/'),
    staleTime: 5 * 60 * 1000,
  });
  const currentUserId = currentUser?.id ?? null;

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: UserRole; is_active?: boolean } }) =>
      updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast({ type: 'success', title: t('users.updated', { defaultValue: 'User updated' }) });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const createAccountMut = useMutation({
    mutationFn: createUserAccount,
    onSuccess: (u) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowCreateAccount(false);
      addToast({ type: 'success', title: t('users.account_created', { defaultValue: 'Account created' }), message: u.email });
    },
    onError: (e: Error) => {
      addToast({ type: 'error', title: t('common.error', { defaultValue: 'Error' }), message: e.message });
    },
  });

  const inviteMut = useMutation({
    mutationFn: sendInviteLink,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowInvite(false);
      addToast({
        type: 'success',
        title: t('users.invited', { defaultValue: 'User invited successfully' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast({ type: 'success', title: t('users.deleted', { defaultValue: 'User deleted' }) });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const handleRoleChange = useCallback(
    async (userId: string, role: UserRole) => {
      // Never let the signed-in user change their own role from this list.
      if (userId === currentUserId) return;
      const target = users.find((u) => u.id === userId);
      const isDowngrade =
        !!target && getRoleRank(role, customRoles) < getRoleRank(target.role, customRoles);
      if (isDowngrade) {
        const ok = await confirm({
          title: t('users.confirm_downgrade_title', { defaultValue: 'Lower this role?' }),
          message: t('users.confirm_downgrade', {
            defaultValue:
              "Change {{name}} from {{from}} to {{to}}? They will immediately lose the higher role's access.",
            name: target.full_name,
            from: getRoleConfig(target.role, customRoles, t).label,
            to: getRoleConfig(role, customRoles, t).label,
          }),
          variant: 'warning',
          confirmLabel: t('users.change_role', { defaultValue: 'Change role' }),
        });
        if (!ok) return;
      }
      updateMut.mutate({ id: userId, data: { role } });
    },
    [updateMut, users, currentUserId, confirm, customRoles, t],
  );

  const handleToggleActive = useCallback(
    async (user: User) => {
      // Never let the signed-in user deactivate themselves.
      if (user.id === currentUserId) return;
      // Activation is non-destructive; only deactivation needs confirmation.
      if (user.is_active) {
        const ok = await confirm({
          title: t('users.confirm_deactivate_title', { defaultValue: 'Deactivate user?' }),
          message: t('users.confirm_deactivate', {
            defaultValue:
              'Deactivate {{name}}? They will lose access immediately. You can reactivate them later.',
            name: user.full_name,
          }),
          variant: 'danger',
          confirmLabel: t('users.deactivate', { defaultValue: 'Deactivate' }),
        });
        if (!ok) return;
      }
      updateMut.mutate({ id: user.id, data: { is_active: !user.is_active } });
    },
    [updateMut, currentUserId, confirm, t],
  );

  const handleDelete = useCallback(
    async (user: User) => {
      // Self-deletion is intentionally not offered here - it must go through
      // account settings, which requires a password confirmation. The server
      // rejects a self-target on this route anyway.
      if (user.id === currentUserId) return;
      const ok = await confirm({
        title: t('users.confirm_delete_title', { defaultValue: 'Delete this user?' }),
        message: t('users.confirm_delete', {
          defaultValue:
            'Permanently delete {{name}}? Their personal data is erased and the account can no longer sign in. Projects and history they created stay intact. This cannot be undone.',
          name: user.full_name || user.email,
        }),
        variant: 'danger',
        confirmLabel: t('users.delete', { defaultValue: 'Delete' }),
      });
      if (!ok) return;
      deleteMut.mutate(user.id);
    },
    [deleteMut, currentUserId, confirm, t],
  );

  const filtered = useMemo(() => {
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u) => u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
    );
  }, [users, search]);

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => u.role === 'admin').length,
    managers: users.filter((u) => u.role === 'manager').length,
  };

  if (!canListUsers) {
    return (
      <div className="space-y-5 animate-fade-in">
        <Breadcrumb
          items={[{ label: t('users.management', { defaultValue: 'User Management' }) }]}
        />
        <NoAccessState />
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Breadcrumb — single-item trail auto-hides (canonical top block). */}
      <Breadcrumb
        items={[{ label: t('users.management', { defaultValue: 'User Management' }) }]}
      />

      {/* Canonical header row — module name + icon live in the top app bar. */}
      <PageHeader
        srTitle={t('users.management', { defaultValue: 'User Management' })}
        subtitle={t('users.management_desc', {
          defaultValue: 'Manage team members, roles, and access',
        })}
        actions={
          <div className="flex items-center gap-2">
            <ModuleGuideButton content={usersGuide} />
            {isAdmin && (
              <Button
                variant="ghost"
                size="sm"
                icon={<Plus size={14} />}
                onClick={() => setShowCustomRole(true)}
              >
                {t('users.custom_role_button', { defaultValue: 'Custom role' })}
              </Button>
            )}
            {isAdmin && (
              <Button
                variant="primary"
                size="sm"
                icon={<UserPlus size={14} />}
                onClick={() => setShowCreateAccount(true)}
                data-testid="users-create-account"
              >
                {t('users.create_account', { defaultValue: 'Create account' })}
              </Button>
            )}
            {isAdmin && (
              <Button
                variant="ghost"
                size="sm"
                icon={<UserPlus size={14} />}
                onClick={() => setShowInvite(true)}
              >
                {t('users.invite_user', { defaultValue: 'Invite User' })}
              </Button>
            )}
          </div>
        }
      />

      {/* Canonical module intro — pain-named, copy from MODULE_INTRO_COPY. */}
      <DismissibleInfo
        storageKey="users"
        title={t('users.intro_title', {
          defaultValue: 'Right people, right access',
        })}
        more={
          t('users.intro_more', { defaultValue: '' })
            ? <IntroRichText text={t('users.intro_more')} />
            : undefined
        }
        links={[
          { label: t('nav.governance', { defaultValue: 'Governance' }), onClick: () => navigate('/governance') },
          {
            label: t('nav.audit_log', { defaultValue: 'Audit Log' }),
            onClick: () => navigate('/admin/audit-log'),
          },
        ]}
      >
        {t('users.intro_body', {
          defaultValue:
            'Invite team members, assign their role and tune which modules each person can reach. Roles set here decide what every user sees and can do across the platform; for the rules behind those roles and approval steps, open Governance.',
        })}
      </DismissibleInfo>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: t('users.total', { defaultValue: 'Total Users' }), value: stats.total, icon: Users, color: 'text-oe-blue' },
          { label: t('users.active', { defaultValue: 'Active' }), value: stats.active, icon: Check, color: 'text-green-600' },
          { label: t('users.admins', { defaultValue: 'Admins' }), value: stats.admins, icon: Crown, color: 'text-red-500' },
          { label: t('users.managers', { defaultValue: 'Managers' }), value: stats.managers, icon: ShieldCheck, color: 'text-amber-500' },
        ].map((s) => (
          <Card key={s.label} className="p-3">
            <div className="flex items-center gap-2">
              <s.icon size={16} className={clsx('shrink-0', s.color)} />
              <span className="text-2xs uppercase tracking-wide text-content-tertiary">{s.label}</span>
            </div>
            <div className="text-lg font-semibold text-content-primary mt-1">{s.value}</div>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-content-quaternary" />
          <input
            className={clsx(inputCls, 'pl-8')}
            placeholder={t('users.search', { defaultValue: 'Search by name or email...' })}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-0.5">
          {(['all', 'active', 'inactive'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilterActive(f)}
              className={clsx(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                filterActive === f ? 'bg-surface-primary shadow-sm' : 'hover:bg-surface-primary/50',
              )}
            >
              {f === 'all'
                ? t('common.all', { defaultValue: 'All' })
                : f === 'active'
                  ? t('users.active', { defaultValue: 'Active' })
                  : t('users.inactive', { defaultValue: 'Inactive' })}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-secondary/50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.name', { defaultValue: 'Name' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.email', { defaultValue: 'Email' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.role', { defaultValue: 'Role' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.status', { defaultValue: 'Status' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.last_login', { defaultValue: 'Last Login' })}
                </th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.actions', { defaultValue: 'Actions' })}
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="h-4 w-full bg-surface-secondary rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-content-tertiary">
                    <Users size={32} className="mx-auto mb-2 opacity-30" />
                    <p>{t('users.no_users', { defaultValue: 'No users found' })}</p>
                  </td>
                </tr>
              ) : (
                filtered.map((user) => {
                  const isSelf = user.id === currentUserId;
                  return (
                  <tr
                    key={user.id}
                    className="border-b border-border/50 hover:bg-surface-secondary/30 transition-colors"
                  >
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={clsx(
                            'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white',
                            user.is_active ? 'bg-oe-blue' : 'bg-gray-400',
                          )}
                        >
                          {user.full_name?.[0]?.toUpperCase() || '?'}
                        </div>
                        <span className="font-medium">{user.full_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-content-secondary">
                      <div className="flex items-center gap-1.5">
                        <Mail size={12} className="text-content-quaternary" />
                        {user.email}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <RoleDropdown
                        currentRole={user.role}
                        userId={user.id}
                        onUpdate={handleRoleChange}
                        disabled={isSelf}
                        disabledTitle={t('users.cannot_change_own_role', {
                          defaultValue: 'You cannot change your own role.',
                        })}
                        customRoles={customRoles}
                      />
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant={user.is_active ? 'success' : 'neutral'}>
                        {user.is_active
                          ? t('users.active', { defaultValue: 'Active' })
                          : t('users.inactive', { defaultValue: 'Inactive' })}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-content-tertiary text-xs">
                      {user.last_login_at ? (
                        <div className="flex items-center gap-1">
                          <Clock size={11} />
                          {new Date(user.last_login_at).toLocaleDateString(getIntlLocale())}
                        </div>
                      ) : (
                        <span className="text-content-quaternary">
                          {t('users.never', { defaultValue: 'Never' })}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setAccessUser(user)}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-oe-blue hover:bg-oe-blue/10 transition-colors"
                          title={t('users.module_access', { defaultValue: 'Module Access' })}
                        >
                          <Settings2 size={13} />
                          {t('users.access', { defaultValue: 'Access' })}
                        </button>
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={isSelf}
                          title={
                            isSelf
                              ? t('users.cannot_deactivate_self', {
                                  defaultValue: 'You cannot deactivate your own account.',
                                })
                              : undefined
                          }
                          className={clsx(
                            'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                            isSelf
                              ? 'text-content-quaternary cursor-not-allowed opacity-60'
                              : user.is_active
                                ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30'
                                : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-950/30',
                          )}
                        >
                          {user.is_active ? <Lock size={13} /> : <Unlock size={13} />}
                          {user.is_active
                            ? t('users.deactivate', { defaultValue: 'Deactivate' })
                            : t('users.activate', { defaultValue: 'Activate' })}
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          disabled={isSelf}
                          title={
                            isSelf
                              ? t('users.cannot_delete_self', {
                                  defaultValue: 'Delete your own account from account settings.',
                                })
                              : t('users.delete', { defaultValue: 'Delete' })
                          }
                          className={clsx(
                            'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                            isSelf
                              ? 'text-content-quaternary cursor-not-allowed opacity-60'
                              : 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30',
                          )}
                        >
                          <Trash2 size={13} />
                          {t('users.delete', { defaultValue: 'Delete' })}
                        </button>
                      </div>
                    </td>
                  </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Role Legend */}
      <div className="mt-4 flex items-center gap-4 text-xs text-content-tertiary">
        <Shield size={13} />
        {ROLES.map((r) => {
          const cfg = ROLE_CONFIG[r];
          if (!cfg) return null;
          const Icon = cfg.icon;
          return (
            <span key={r} className="flex items-center gap-1">
              <Icon size={11} className={cfg.color} />
              <strong>
                {t(`users.roles.${cfg.labelKey}`)}
              </strong>
              :{' '}
              {r === 'admin'
                ? t('users.role_admin_desc', { defaultValue: 'Full access' })
                : r === 'manager'
                  ? t('users.role_manager_desc', { defaultValue: 'Project management' })
                  : r === 'editor'
                    ? t('users.role_editor_desc', { defaultValue: 'Create & edit' })
                    : t('users.role_viewer_desc', { defaultValue: 'Read-only' })}
            </span>
          );
        })}
      </div>

      {showCreateAccount && (
        <CreateAccountModal
          onClose={() => setShowCreateAccount(false)}
          onSubmit={(data) => createAccountMut.mutate(data)}
          isPending={createAccountMut.isPending}
        />
      )}

      {/* Invite Modal */}
      {showInvite && (
        <InviteModal
          onClose={() => setShowInvite(false)}
          onSubmit={(data) => inviteMut.mutate(data)}
          isPending={inviteMut.isPending}
        />
      )}

      {/* Create Custom Role Modal */}
      {showCustomRole && <CreateCustomRoleModal onClose={() => setShowCustomRole(false)} />}

      {/* OE-DELIVERY 2026-10-16: per-role module configuration (admin only) */}
      {isAdmin && <RoleModulesSection />}

      {/* Module Access Panel */}
      {accessUser && <ModuleAccessPanel user={accessUser} onClose={() => setAccessUser(null)} />}

      {/* Confirmation dialog for destructive actions (deactivate, role downgrade) */}
      <ConfirmDialog {...confirmProps} />
    </div>
  );
}

/* ── Role Modules Section (OE-DELIVERY 2026-10-16) ─────────────────────────
 *
 * Admin-only: configure which modules each role can see. Each role is
 * independent — changing Manager's modules never affects Editor's.
 * The admin role is locked (always all modules). New custom roles appear
 * automatically. Modules are grouped by the sidebar navbar sections
 * (from navGroups — future modules appear automatically).
 */
function RoleModulesSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [selectedRole, setSelectedRole] = useState<string>('manager');
  const [granted, setGranted] = useState<string[]>([]);
  const [dirty, setDirty] = useState(false);
  // OE-DELIVERY 2026-10-16: pending delete confirmation (Yes/No dialog).
  const [pendingDelete, setPendingDelete] = useState<{ slug: string; name: string } | null>(null);

  const { data: configs = [], isLoading: configsLoading } = useQuery({
    queryKey: ['role-module-configs'],
    queryFn: fetchRoleModuleConfigs,
  });

  const { data: modules = [], isLoading: modulesLoading } = useQuery({
    queryKey: ['role-modules'],
    queryFn: fetchRoleModules,
  });

  const activeConfig = useMemo(
    () => configs.find((c) => c.role_slug === selectedRole),
    [configs, selectedRole]
  );

  // OE-DELIVERY 2026-10-16 fix: explicit role selection handler — sets
  // granted DIRECTLY from the config, no useEffect resync race. Each role's
  // modules are fully independent.
  const handleRoleSelect = (roleSlug: string) => {
    const cfg = configs.find((c) => c.role_slug === roleSlug);
    setSelectedRole(roleSlug);
    setGranted(cfg ? [...cfg.granted_modules] : []);
    setDirty(false);
  };

  // Initial sync when configs first load
  const initialSynced = useRef(false);
  useEffect(() => {
    if (!initialSynced.current && configs.length > 0) {
      const cfg = configs.find((c) => c.role_slug === selectedRole);
      if (cfg) {
        setGranted([...cfg.granted_modules]);
        initialSynced.current = true;
      }
    }
  }, [configs, selectedRole]);

  // Auto-select first non-admin role on load
  useEffect(() => {
    if (configs.length > 0 && !configs.find((c) => c.role_slug === selectedRole)) {
      const first = configs.find((c) => c.role_slug !== 'admin');
      if (first) handleRoleSelect(first.role_slug);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configs]);

  // OE-DELIVERY 2026-10-16: group by SIDEBAR sections (LEARN, OVERVIEW,
  // TAKEOFF, ...) — every nav item is configurable, not just backend
  // registry modules. Label comes from backend module info when available,
  // otherwise from the nav item itself.
  const groupedModules = useMemo(() => {
    const used = new Set<string>();
    const groups: { id: string; label: string; items: { key: string; label: string }[] }[] = [];
    const navKey = (item: { moduleKey?: string; to: string }) =>
      item.moduleKey || item.to.replace(/^\//, '').split('/')[0]?.split('?')[0] || undefined;
    // OE-DELIVERY 2026-10-16: use the EXACT same label as the sidebar —
    // t(labelKey) with defaultLabel fallback. Never the backend module
    // label (e.g. "Quantity Takeoff" vs sidebar "PDF Measurements").
    const navLabel = (item: { defaultLabel?: string; labelKey?: string }) =>
      t(item.labelKey || '', { defaultValue: item.defaultLabel || item.labelKey || '' });
    for (const g of navGroups) {
      const items: { key: string; label: string }[] = [];
      for (const item of g.items) {
        const mk = navKey(item);
        if (!mk || used.has(mk)) continue;
        used.add(mk);
        items.push({ key: mk, label: navLabel(item) || mk });
      }
      if (items.length > 0) {
        groups.push({ id: g.id, label: g.defaultLabel || g.labelKey, items });
      }
    }
    return groups;
  }, [modules]);

  const visibleKeys = useMemo(
    () => groupedModules.flatMap((g) => g.items.map((m) => m.key)),
    [groupedModules]
  );
  // OE-DELIVERY 2026-10-16: admin is locked with all modules — show every
  // checkbox as checked for the admin tab (stored config is empty).
  const isLockedAll = !!activeConfig?.locked;
  const allChecked =
    isLockedAll || (visibleKeys.length > 0 && granted.length === visibleKeys.length);

  const toggleAll = () => {
    if (activeConfig?.locked) return;
    setGranted(allChecked ? [] : [...visibleKeys]);
    setDirty(true);
  };

  const toggleModule = (key: string) => {
    if (activeConfig?.locked) return;
    setGranted((g) => (g.includes(key) ? g.filter((k) => k !== key) : [...g, key]));
    setDirty(true);
  };

  // OE-DELIVERY 2026-10-16: delete a custom role. Backend refuses (409) while
  // users are still assigned — reassign them first.
  const deleteMut = useMutation({
    mutationFn: (slug: string) => deleteCustomRole(slug),
    onSuccess: (_v, slug) => {
      queryClient.setQueryData(['role-module-configs'], (old: typeof configs | undefined) =>
        old ? old.filter((c) => c.role_slug !== slug) : old
      );
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      if (selectedRole === slug) {
        const first = configs.find((c) => c.role_slug !== slug && c.role_slug !== 'admin');
        if (first) handleRoleSelect(first.role_slug);
      }
      addToast({
        type: 'success',
        title: t('users.custom_role_deleted', { defaultValue: 'Custom role deleted' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('users.custom_role_delete_failed', { defaultValue: 'Could not delete role' }),
        message: e.message,
      });
    },
  });

  const handleDeleteRole = (slug: string, name: string) => {
    // OE-DELIVERY 2026-10-16: open the in-app Yes/No confirm dialog instead
    // of window.confirm — prevents accidental deletes.
    setPendingDelete({ slug, name });
  };

  const saveMut = useMutation({
    mutationFn: () => updateRoleModuleConfig(selectedRole, granted),
    onSuccess: (updated) => {
      // OE-DELIVERY 2026-10-16 fix: update cache directly instead of
      // invalidating — avoids refetch race that could show stale modules.
      queryClient.setQueryData(['role-module-configs'], (old: typeof configs | undefined) =>
        old ? old.map((c) => (c.role_slug === updated.role_slug ? updated : c)) : old
      );
      setDirty(false);
      addToast({
        type: 'success',
        title: t('users.role_modules_saved', { defaultValue: 'Role modules saved' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('users.role_modules_save_failed', { defaultValue: 'Could not save' }),
        message: e.message,
      });
    },
  });

  const isLoading = configsLoading || modulesLoading;

  return (
    <Card className="mt-6 p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <Shield size={16} className="text-oe-blue" />
          {t('users.role_modules_title', { defaultValue: 'Role Module Access' })}
        </h3>
        {activeConfig && !activeConfig.locked && dirty && (
          <Button
            variant="primary"
            size="sm"
            icon={<Save size={14} />}
            loading={saveMut.isPending}
            onClick={() => saveMut.mutate()}
          >
            {t('common.save', { defaultValue: 'Save' })}
          </Button>
        )}
      </div>
      <p className="text-xs text-content-secondary mb-4">
        {t('users.role_modules_desc', {
          defaultValue: 'Set which modules each role can see. Each role is independent. Only admins can change this.',
        })}
      </p>

      {isLoading ? (
        <div className="text-center py-6 text-content-tertiary text-sm">
          {t('common.loading', { defaultValue: 'Loading...' })}
        </div>
      ) : (
        <>
          {/* Role tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {configs.map((c) => (
              <div
                key={c.role_slug}
                className={clsx(
                  'rounded-lg border text-sm font-medium transition-all flex items-center',
                  selectedRole === c.role_slug
                    ? 'border-oe-blue bg-oe-blue/5 ring-2 ring-oe-blue/20'
                    : 'border-border hover:border-border-hover',
                )}
              >
                <button
                  type="button"
                  onClick={() => handleRoleSelect(c.role_slug)}
                  className="px-3 py-1.5 flex items-center gap-1.5"
                >
                  {c.is_custom && <UserCog size={13} className="text-violet-600 dark:text-violet-400" />}
                  {c.role_name}
                  {c.locked && (
                    <Lock size={12} className="text-content-tertiary" />
                  )}
                </button>
                {/* OE-DELIVERY 2026-10-16: delete custom roles */}
                {c.is_custom && !c.locked && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteRole(c.role_slug, c.role_name);
                    }}
                    disabled={deleteMut.isPending}
                    title={t('users.delete_custom_role', { defaultValue: 'Delete role' })}
                    className="pr-2 pl-1 text-content-tertiary hover:text-red-500 transition-colors disabled:opacity-50"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {activeConfig?.locked && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-surface-secondary text-xs text-content-secondary flex items-center gap-2">
              <Lock size={13} />
              {t('users.role_modules_admin_locked', {
                defaultValue: 'The admin role always has access to all modules and cannot be changed.',
              })}
            </div>
          )}

          {/* All modules toggle */}
          <button
            type="button"
            onClick={toggleAll}
            disabled={activeConfig?.locked}
            className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg border border-border hover:border-border-hover transition-colors disabled:opacity-50"
          >
            <span
              className={clsx(
                'w-5 h-5 rounded border flex items-center justify-center transition-colors shrink-0',
                allChecked ? 'bg-oe-blue border-oe-blue text-white' : 'border-border',
              )}
            >
              {allChecked && <Check size={12} />}
            </span>
            <span className="text-sm font-medium">
              {t('users.all_modules', { defaultValue: 'All modules' })}
            </span>
          </button>

          {/* Grouped modules */}
          <div className="space-y-3 mt-3">
            {groupedModules.map((group) => (
              <div key={group.id}>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-content-tertiary mb-1.5">
                  {group.label}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
                  {group.items.map((m) => {
                    // OE-DELIVERY 2026-10-16: locked (admin) role shows all checked.
                    const checked = isLockedAll || granted.includes(m.key);
                    return (
                      <button
                        key={m.key}
                        type="button"
                        onClick={() => toggleModule(m.key)}
                        disabled={activeConfig?.locked}
                        className={clsx(
                          'flex items-center gap-2.5 px-3 py-2 rounded-lg border text-sm transition-colors text-left disabled:opacity-50',
                          checked
                            ? 'border-oe-blue/50 bg-oe-blue/5'
                            : 'border-border hover:border-border-hover',
                        )}
                      >
                        <span
                          className={clsx(
                            'w-5 h-5 rounded border flex items-center justify-center transition-colors shrink-0',
                            checked ? 'bg-oe-blue border-oe-blue text-white' : 'border-border',
                          )}
                        >
                          {checked && <Check size={12} />}
                        </span>
                        <span className="truncate">{m.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* OE-DELIVERY 2026-10-16: Yes/No delete confirmation dialog */}
      {pendingDelete && (
        <WideModal
          open
          onClose={() => setPendingDelete(null)}
          title={t('users.delete_custom_role', { defaultValue: 'Delete role' })}
          size="sm"
          footer={
            <>
              <Button variant="ghost" onClick={() => setPendingDelete(null)}>
                {t('common.no', { defaultValue: 'No' })}
              </Button>
              <Button
                variant="danger"
                loading={deleteMut.isPending}
                onClick={() => {
                  deleteMut.mutate(pendingDelete.slug);
                  setPendingDelete(null);
                }}
              >
                {t('common.yes', { defaultValue: 'Yes, delete' })}
              </Button>
            </>
          }
        >
          <p className="text-sm text-content-secondary">
            {t('users.custom_role_delete_confirm', {
              defaultValue: `Delete custom role "${pendingDelete.name}"? This cannot be undone. Users assigned to this role must be reassigned first.`,
              name: pendingDelete.name,
            })}
          </p>
        </WideModal>
      )}
    </Card>
  );
}
