// OE-DELIVERY: 2026-10-23-team-workload-v1.2-filters (was 2026-10-23-team-workload-v1.1-api-path-fix)
/**
 * API helpers for the Team Workload page.
 *
 * Backed by /api/v1/team-workload/ — see
 * backend/app/modules/team_workload/. Read-only reporting: who is
 * assigned to which project, progress, and how long things took.
 */

import { apiGet } from '@/shared/lib/api';

export interface WorkloadAssignee {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  role_label: string;
  assigned_at: string | null;
}

export interface WorkloadProject {
  project_id: string;
  project_name: string;
  kind: 'bid' | 'awarded';
  status: string;
  stage_label: string;
  progress: number;
  completed: boolean;
  result: string | null;
  assigned_at: string | null;
  completed_at: string | null;
  days: number | null;
  assignees: WorkloadAssignee[];
}

export interface WorkloadUser {
  user_id: string;
  full_name: string;
  email: string;
  role_label: string;
  total: number;
  running: number;
  completed: number;
  won: number;
  avg_days: number | null;
}

export interface TeamWorkload {
  users: WorkloadUser[];
  projects: WorkloadProject[];
}

export interface WorkloadHistoryEvent {
  date: string;
  project_id: string;
  project_name: string;
  text: string;
}

export interface UserWorkloadDetail {
  user: WorkloadUser;
  projects: WorkloadProject[];
  history: WorkloadHistoryEvent[];
}

/** Team view data. `days > 0` = period filter: only projects completed
 *  within the last N days are counted (running projects always stay),
 *  and the per-person stats follow the same window. */
export function fetchTeamWorkload(days = 0): Promise<TeamWorkload> {
  return apiGet<TeamWorkload>(
    days > 0 ? `/v1/team-workload/?days=${days}` : '/v1/team-workload/',
  );
}

export function fetchUserWorkload(userId: string): Promise<UserWorkloadDetail> {
  return apiGet<UserWorkloadDetail>(`/v1/team-workload/users/${userId}/`);
}
