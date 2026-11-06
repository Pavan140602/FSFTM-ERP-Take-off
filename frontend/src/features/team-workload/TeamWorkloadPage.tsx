// OE-DELIVERY: 2026-10-23-team-workload-v1.4-fullwidth (was 2026-10-23-team-workload-v1.3-role-filter)
/**
 * Team Workload — manager / coordinator track record.
 *
 * Team view: one card per person (running / completed / average time)
 * plus a table of every project with its assignees, stage, progress
 * and time taken. Clicking a person opens the individual view: that
 * person's stats, their projects, and a history timeline assembled
 * from assignments, status transitions and pipeline stage completions.
 *
 * Data: GET /api/v1/team-workload/ and /users/{id}/ (read-only).
 * Visibility is governed by the 'team_workload' module grant
 * (Users -> Role Module Access) — see ModuleRouteGate in App.tsx.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Search } from 'lucide-react';
import {
  fetchTeamWorkload,
  fetchUserWorkload,
  type WorkloadProject,
  type WorkloadUser,
} from './api';

/* ── helpers ─────────────────────────────────────────────────────── */

const AVATAR_COLORS = [
  '#7c5cd6',
  '#2f7fd0',
  '#3fae6a',
  '#e8a13a',
  '#e05252',
  '#0e9594',
  '#b0529e',
  '#5b8c5a',
];

function avatarColor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length]!;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 1).toUpperCase();
  return (parts[0]!.slice(0, 1) + parts[parts.length - 1]!.slice(0, 1)).toUpperCase();
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function fmtDays(days: number | null): string {
  if (days === null) return '—';
  const v = Number.isInteger(days) ? String(days) : days.toFixed(1);
  return `${v} days`;
}

function badgeClasses(p: WorkloadProject): string {
  if (p.completed)
    return 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400';
  if (p.kind === 'awarded')
    return 'bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300';
  if (p.status === 'submitted_to_client' || p.status === 'awaiting_response')
    return 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400';
  return 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400';
}

function barColor(p: WorkloadProject): string {
  if (p.completed) return '#3fae6a';
  if (p.kind === 'awarded') return '#7c5cd6';
  return '#3f85e0';
}

/* ── shared bits ─────────────────────────────────────────────────── */

function Avatar({ name, seed, size = 34 }: { name: string; seed: string; size?: number }) {
  return (
    <div
      className="flex flex-none items-center justify-center rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        background: avatarColor(seed),
        fontSize: Math.round(size * 0.38),
      }}
    >
      {initials(name)}
    </div>
  );
}

function ProgressCell({ p }: { p: WorkloadProject }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-[7px] min-w-[90px] flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700/60">
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.max(0, Math.min(100, p.progress))}%`, background: barColor(p) }}
        />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">{p.progress}%</span>
    </div>
  );
}

function ProjectRows({
  projects,
  showAssignees,
  onOpen,
}: {
  projects: WorkloadProject[];
  showAssignees: boolean;
  onOpen: (projectId: string) => void;
}) {
  const { t } = useTranslation();
  if (projects.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {t('team_workload.no_projects', { defaultValue: 'No projects match.' })}
      </div>
    );
  }
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-gray-200 dark:border-gray-800">
          <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {t('team_workload.col_project', { defaultValue: 'Project' })}
          </th>
          {showAssignees && (
            <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              {t('team_workload.col_assigned', { defaultValue: 'Assigned To' })}
            </th>
          )}
          <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {t('team_workload.col_stage', { defaultValue: 'Status / Stage' })}
          </th>
          <th className="min-w-[140px] px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {t('team_workload.col_progress', { defaultValue: 'Progress' })}
          </th>
          <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {t('team_workload.col_started', { defaultValue: 'Started' })}
          </th>
          <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            {t('team_workload.col_time', { defaultValue: 'Time' })}
          </th>
          {!showAssignees && (
            <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              {t('team_workload.col_result', { defaultValue: 'Result' })}
            </th>
          )}
        </tr>
      </thead>
      <tbody>
        {projects.map((p) => (
          <tr
            key={p.project_id}
            onClick={() => onOpen(p.project_id)}
            className="cursor-pointer border-b border-gray-100 transition-colors last:border-0 hover:bg-gray-50 dark:border-gray-800/70 dark:hover:bg-gray-800/40"
          >
            <td className="px-3 py-2.5 text-sm font-semibold text-gray-900 dark:text-gray-100">
              {p.project_name}
            </td>
            {showAssignees && (
              <td className="px-3 py-2.5 text-sm text-gray-600 dark:text-gray-300">
                {p.assignees.length === 0
                  ? '—'
                  : p.assignees.map((a) => `${a.full_name || a.email} · ${a.role_label}`).join(', ')}
              </td>
            )}
            <td className="px-3 py-2.5">
              <span
                className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${badgeClasses(p)}`}
              >
                {p.kind === 'awarded' && !p.completed
                  ? `${p.stage_label} · Pipeline`
                  : p.stage_label}
              </span>
            </td>
            <td className="px-3 py-2.5">
              <ProgressCell p={p} />
            </td>
            <td className="whitespace-nowrap px-3 py-2.5 text-sm text-gray-500 dark:text-gray-400">
              {fmtDate(p.assigned_at)}
            </td>
            <td className="whitespace-nowrap px-3 py-2.5 text-sm text-gray-700 dark:text-gray-200">
              {p.completed ? (
                <>
                  <span className="font-semibold">{fmtDays(p.days)}</span>{' '}
                  <span className="text-gray-500 dark:text-gray-400">total</span>
                </>
              ) : (
                <>
                  {fmtDays(p.days)}{' '}
                  <span className="text-gray-500 dark:text-gray-400">(running)</span>
                </>
              )}
            </td>
            {!showAssignees && (
              <td className="px-3 py-2.5">
                {p.result ? (
                  <span
                    className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                      p.result === 'Lost'
                        ? 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400'
                        : 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400'
                    }`}
                  >
                    {p.result}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">—</span>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function UserCard({ u, onSelect }: { u: WorkloadUser; onSelect: (id: string) => void }) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={() => onSelect(u.user_id)}
      className="rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 hover:shadow dark:border-gray-800 dark:bg-gray-900 dark:hover:border-blue-500/40"
    >
      <div className="mb-3 flex items-center gap-2.5">
        <Avatar name={u.full_name || u.email} seed={u.user_id} />
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-gray-900 dark:text-gray-100">
            {u.full_name || u.email}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{u.role_label}</div>
        </div>
      </div>
      <div className="flex gap-5">
        <div>
          <div className="text-lg font-bold leading-tight text-amber-500">{u.running}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('team_workload.running', { defaultValue: 'Running' })}
          </div>
        </div>
        <div>
          <div className="text-lg font-bold leading-tight text-green-600 dark:text-green-400">
            {u.completed}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('team_workload.completed', { defaultValue: 'Completed' })}
          </div>
        </div>
        <div>
          <div className="text-lg font-bold leading-tight text-gray-900 dark:text-gray-100">
            {u.avg_days === null ? '—' : fmtDays(u.avg_days)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('team_workload.avg_time', { defaultValue: 'Avg time / project' })}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ── page ────────────────────────────────────────────────────────── */

type StatusFilter = 'all' | 'running' | 'completed';

export function TeamWorkloadPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [period, setPeriod] = useState(0);
  const [userFilter, setUserFilter] = useState<string>('all');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  const teamQ = useQuery({
    queryKey: ['team-workload', period],
    queryFn: () => fetchTeamWorkload(period),
  });
  const detailQ = useQuery({
    queryKey: ['team-workload-user', selectedUserId],
    queryFn: () => fetchUserWorkload(selectedUserId!),
    enabled: selectedUserId !== null,
  });

  const openProject = (projectId: string) => navigate(`/projects/${projectId}`);

  // Roles actually present in the current data window — the role
  // filter only offers roles somebody holds (as their headline role
  // or on any shown project).
  const roleOptions = useMemo(() => {
    const s = new Set<string>();
    for (const u of teamQ.data?.users ?? []) s.add(u.role_label);
    for (const p of teamQ.data?.projects ?? [])
      for (const a of p.assignees) s.add(a.role_label);
    return Array.from(s).sort();
  }, [teamQ.data]);

  // If a period change shrinks the data so the picked role no longer
  // exists, fall back to 'all' instead of showing an empty page.
  const activeRole =
    roleFilter !== 'all' && roleOptions.includes(roleFilter) ? roleFilter : 'all';

  const filteredProjects = useMemo(() => {
    const all = teamQ.data?.projects ?? [];
    const q = search.trim().toLowerCase();
    return all.filter((p) => {
      if (statusFilter === 'running' && p.completed) return false;
      if (statusFilter === 'completed' && !p.completed) return false;
      if (userFilter !== 'all' && !p.assignees.some((a) => a.user_id === userFilter))
        return false;
      if (activeRole !== 'all' && !p.assignees.some((a) => a.role_label === activeRole))
        return false;
      if (
        q &&
        !p.project_name.toLowerCase().includes(q) &&
        !p.assignees.some((a) => (a.full_name || a.email).toLowerCase().includes(q))
      )
        return false;
      return true;
    });
  }, [teamQ.data, statusFilter, search, userFilter, activeRole]);

  const filteredUsers = useMemo(() => {
    const all = teamQ.data?.users ?? [];
    const q = search.trim().toLowerCase();
    return all.filter((u) => {
      if (userFilter !== 'all' && u.user_id !== userFilter) return false;
      if (activeRole !== 'all' && u.role_label !== activeRole) return false;
      if (q && !(u.full_name || u.email).toLowerCase().includes(q)) return false;
      return true;
    });
  }, [teamQ.data, search, userFilter, activeRole]);

  /* ── individual view ── */
  if (selectedUserId !== null) {
    const detail = detailQ.data;
    return (
      <div className="w-full space-y-4 p-4 sm:p-6">
        <button
          type="button"
          onClick={() => setSelectedUserId(null)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
        >
          <ArrowLeft size={15} />
          {t('team_workload.back_to_team', { defaultValue: 'Team Workload' })}
        </button>

        {detailQ.isLoading || !detail ? (
          <div className="py-16 text-center text-sm text-gray-500 dark:text-gray-400">
            {detailQ.isError
              ? t('team_workload.load_failed', { defaultValue: 'Could not load this person.' })
              : t('common.loading', { defaultValue: 'Loading…' })}
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <Avatar name={detail.user.full_name || detail.user.email} seed={detail.user.user_id} size={44} />
              <div>
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {detail.user.full_name || detail.user.email}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {detail.user.role_label} · {detail.user.email}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
              <div className="min-w-[90px] flex-1">
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{detail.user.total}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {t('team_workload.total_projects', { defaultValue: 'Total projects' })}
                </div>
              </div>
              <div className="min-w-[90px] flex-1">
                <div className="text-xl font-bold text-amber-500">{detail.user.running}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {t('team_workload.running_now', { defaultValue: 'Running now' })}
                </div>
              </div>
              <div className="min-w-[90px] flex-1">
                <div className="text-xl font-bold text-green-600 dark:text-green-400">{detail.user.completed}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {t('team_workload.completed', { defaultValue: 'Completed' })}
                </div>
              </div>
              <div className="min-w-[90px] flex-1">
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {detail.user.avg_days === null ? '—' : fmtDays(detail.user.avg_days)}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {t('team_workload.avg_time', { defaultValue: 'Avg time / project' })}
                </div>
              </div>
              <div className="min-w-[90px] flex-1">
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {detail.user.won} / {detail.user.completed}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {t('team_workload.won_of_completed', { defaultValue: 'Won · of completed' })}
                </div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
              <ProjectRows projects={detail.projects} showAssignees={false} onOpen={openProject} />
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
              <div className="mb-3 text-sm font-bold text-gray-900 dark:text-gray-100">
                {t('team_workload.recent_history', { defaultValue: 'Recent History' })}
              </div>
              {detail.history.length === 0 ? (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {t('team_workload.no_history', { defaultValue: 'No recorded activity yet.' })}
                </div>
              ) : (
                <div className="space-y-2.5">
                  {detail.history.map((e, i) => (
                    <div key={i} className="flex gap-2.5">
                      <div
                        className="mt-1.5 h-[9px] w-[9px] flex-none rounded-full"
                        style={{ background: avatarColor(e.project_id) }}
                      />
                      <div className="text-sm text-gray-700 dark:text-gray-200">
                        <span className="font-semibold">{e.project_name}</span>
                        {' — '}
                        {e.text}
                        <span className="text-gray-500 dark:text-gray-400">
                          {' · '}
                          {fmtDate(e.date)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  /* ── team view ── */
  return (
    <div className="w-full space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {t('team_workload.title', { defaultValue: 'Team Workload' })}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('team_workload.subtitle', {
              defaultValue: 'Who is assigned to which project · how far it has progressed · how long it took',
            })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search
              size={14}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('team_workload.search_ph', { defaultValue: 'Search person or project' })}
              className="w-56 rounded-full border border-gray-300 bg-white py-1.5 pl-8 pr-3 text-sm text-gray-900 outline-none focus:border-blue-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            />
          </div>
          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 outline-none focus:border-blue-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="all">{t('team_workload.all_users', { defaultValue: 'All Users' })}</option>
            {(teamQ.data?.users ?? []).map((u) => (
              <option key={u.user_id} value={u.user_id}>
                {u.full_name || u.email}
              </option>
            ))}
          </select>
          <select
            value={activeRole}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 outline-none focus:border-blue-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="all">{t('team_workload.all_roles', { defaultValue: 'All Roles' })}</option>
            {roleOptions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 outline-none focus:border-blue-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value={0}>{t('team_workload.all_time', { defaultValue: 'All Time' })}</option>
            <option value={7}>{t('team_workload.last_7_days', { defaultValue: 'Last 7 days' })}</option>
            <option value={30}>{t('team_workload.last_30_days', { defaultValue: 'Last 30 days' })}</option>
            <option value={90}>{t('team_workload.last_90_days', { defaultValue: 'Last 90 days' })}</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 outline-none focus:border-blue-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="all">{t('team_workload.all_statuses', { defaultValue: 'All Statuses' })}</option>
            <option value="running">{t('team_workload.running', { defaultValue: 'Running' })}</option>
            <option value="completed">{t('team_workload.completed', { defaultValue: 'Completed' })}</option>
          </select>
        </div>
      </div>

      {teamQ.isLoading ? (
        <div className="py-16 text-center text-sm text-gray-500 dark:text-gray-400">
          {t('common.loading', { defaultValue: 'Loading…' })}
        </div>
      ) : teamQ.isError ? (
        <div className="py-16 text-center text-sm text-red-500">
          {t('team_workload.load_failed_team', { defaultValue: 'Could not load team workload.' })}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredUsers.map((u) => (
              <UserCard key={u.user_id} u={u} onSelect={setSelectedUserId} />
            ))}
          </div>
          {filteredUsers.length === 0 && (
            <div className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
              {t('team_workload.no_people', {
                defaultValue: 'No team members with assigned projects yet.',
              })}
            </div>
          )}
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <ProjectRows projects={filteredProjects} showAssignees onOpen={openProject} />
          </div>
        </>
      )}
    </div>
  );
}
