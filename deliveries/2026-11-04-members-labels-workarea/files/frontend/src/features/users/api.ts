// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * API helpers for User Management.
 */

import { apiGet, apiPatch, apiPost, apiPut, apiDelete } from '@/shared/lib/api';

export const CANONICAL_ROLES = ['admin', 'manager', 'editor', 'viewer'] as const;
export type CanonicalRole = (typeof CANONICAL_ROLES)[number];
/**
 * Any role slug: one of the canonical four or a custom role created by an
 * admin (see CustomRole). Widened to `string` so custom slugs flow through
 * `User.role` and the invite/update payloads; use CANONICAL_ROLES wherever
 * only the built-in four are meant.
 */
export type UserRole = string;
export type ModuleAccessLevel = 'none' | 'view' | 'edit' | 'full';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  locale: string;
  is_active: boolean;
  last_login_at: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface UserAdminUpdate {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  locale?: string;
}

export interface InviteLinkPayload {
  email: string;
  full_name: string;
}

export interface InviteLinkResult {
  email: string;
  sent: boolean;
}

export interface ModuleAccess {
  visible: boolean;
  access: ModuleAccessLevel;
}

export interface UserModuleAccessPayload {
  modules: Record<string, ModuleAccess>;
  custom_role_name?: string | null;
}

export async function fetchUsers(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<User[]> {
  const qs = new URLSearchParams();
  if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active));
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  const q = qs.toString();
  return apiGet<User[]>(`/v1/users/${q ? `?${q}` : ''}`);
}

export async function updateUser(id: string, data: UserAdminUpdate): Promise<User> {
  return apiPatch<User>(`/v1/users/${id}`, data);
}

/**
 * Admin-only: permanently delete (erase) a user account. The server anonymises
 * the row in place so the user's projects and history keep resolving, but every
 * personal field is stripped and the account can no longer log in. The last
 * active admin cannot be deleted (409), and an admin cannot delete their own
 * account through this route (400) - that goes through account settings.
 */
export async function deleteUser(id: string): Promise<void> {
  await apiDelete(`/v1/users/${id}`);
}

/** Admin creates a ready-to-use account through the existing admin endpoint
 *  POST /v1/users/ (OE-DELIVERY 2026-11-03-admin-create-user). */
export async function createUserAccount(data: { email: string; full_name: string; password: string; role: string }): Promise<{ id: string; email: string }> {
  return apiPost<{ id: string; email: string }>('/v1/users/', { ...data, is_active: true });
}

export async function sendInviteLink(data: InviteLinkPayload): Promise<InviteLinkResult> {
  // Invite = email a registration link (POST /v1/users/invite/, gated by
  // users.create). No account is created: the invitee registers, picks a
  // role on the form (admin is never offered), and an admin activates
  // the account afterwards.
  return apiPost<InviteLinkResult>('/v1/users/invite/', data);
}

export async function getUserModuleAccess(userId: string): Promise<UserModuleAccessPayload> {
  return apiGet<UserModuleAccessPayload>(`/v1/users/${userId}/module-access/`);
}

export async function setUserModuleAccess(
  userId: string,
  data: UserModuleAccessPayload,
): Promise<UserModuleAccessPayload> {
  return apiPatch<UserModuleAccessPayload>(`/v1/users/${userId}/module-access/`, data);
}

/* ── Custom roles ──────────────────────────────────────────────────── */

export interface CustomRole {
  slug: string;
  name: string;
  description?: string;
  base_role: string;
  granted_modules: string[];
  is_custom: boolean;
  rank: number;
}

export interface RoleModule {
  key: string;
  label: string;
}

/** Canonical roles plus active custom roles. */
export async function fetchRoles(): Promise<CustomRole[]> {
  return apiGet<CustomRole[]>('/v1/users/roles/');
}

/** Canonical module list — source of truth for the create-role checkboxes. */
export async function fetchRoleModules(): Promise<RoleModule[]> {
  return apiGet<RoleModule[]>('/v1/users/roles/modules/');
}

export async function createCustomRole(data: {
  name: string;
  description?: string;
  base_role: string;
  granted_modules: string[];
}): Promise<CustomRole> {
  return apiPost<CustomRole>('/v1/users/roles/custom/', data);
}

/**
 * Delete a custom role. Rejects with the server's 409 payload
 * (`{ detail, assigned_count }`) when users are still assigned to it —
 * callers should surface that to the admin instead of swallowing it.
 */
export async function deleteCustomRole(slug: string): Promise<void> {
  await apiDelete(`/v1/users/roles/custom/${slug}`);
}

/* ── Role module configuration (OE-DELIVERY 2026-10-16) ──────────────── */

export interface RoleModuleConfig {
  role_slug: string;
  role_name: string;
  is_custom: boolean;
  granted_modules: string[];
  locked: boolean;
}

/** All roles with their configured modules (admin only). */
export async function fetchRoleModuleConfigs(): Promise<RoleModuleConfig[]> {
  return apiGet<RoleModuleConfig[]>('/v1/users/roles/module-config/');
}

/** Update one role's granted modules (admin only). */
export async function updateRoleModuleConfig(
  roleSlug: string,
  grantedModules: string[]
): Promise<RoleModuleConfig> {
  return apiPut<RoleModuleConfig>(`/v1/users/roles/module-config/${roleSlug}`, {
    granted_modules: grantedModules,
  });
}

/** Module keys visible to the current user's role (for sidebar filtering). */
export async function fetchMyRoleModules(): Promise<string[]> {
  return apiGet<string[]>('/v1/users/me/role-modules/');
}
