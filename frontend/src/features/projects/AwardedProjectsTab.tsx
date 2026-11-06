// OE-DELIVERY: 2026-10-19-bid-awarded-tabs-v1
// AwardedProjectsTab — "Awarded Projects" tab content for the Projects page.
// Shows ONLY awarded/official projects (status won/awarded). No bid
// (opportunity) data is read here: the bid/awarded separation rule forbids
// mixing. Data: GET /v1/projects/ via the projects API.

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, FileText, Users } from 'lucide-react';
import { Card, Badge, EmptyState, SkeletonGrid } from '@/shared/ui';
import { projectsApi, type Project } from './api';

// Statuses that count as "awarded" — official post-win projects only.
const AWARDED_STATUSES = new Set(['won', 'awarded', 'active', 'in_progress']);

export function AwardedProjectsTab() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [nameFilter, setNameFilter] = useState('');

  const projectsQ = useQuery({
    queryKey: ['awarded-projects-tab'],
    queryFn: () => projectsApi.list({ limit: 200 }),
    staleTime: 2 * 60 * 1000,
  });

  const awarded = useMemo(() => {
    const all: Project[] = (projectsQ.data as Project[] | undefined) ?? [];
    return all.filter((p) => AWARDED_STATUSES.has((p.status ?? '').toLowerCase()));
  }, [projectsQ.data]);

  const filtered = useMemo(() => {
    const q = nameFilter.trim().toLowerCase();
    if (!q) return awarded;
    return awarded.filter((p) =>
      (p.name ?? '').toLowerCase().includes(q),
    );
  }, [awarded, nameFilter]);

  if (projectsQ.isLoading) return <SkeletonGrid count={6} />;

  if (projectsQ.isError) {
    return (
      <EmptyState
        title={t('common.error', { defaultValue: 'Error' })}
        description={String(projectsQ.error)}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Name-wise filter — more filters (estimator, date) are the
          user's choice to add later. */}
      <div className="relative max-w-md">
        <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center pl-3 text-content-tertiary">
          <Search size={16} />
        </div>
        <input
          type="text"
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
          placeholder={t('projects.awarded_filter_name', {
            defaultValue: 'Filter by project name...',
          })}
          className="w-full rounded-lg border border-border bg-surface-primary py-2 pl-10 pr-3 text-sm text-content-primary placeholder:text-content-tertiary"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={t('projects.awarded_empty', { defaultValue: 'No awarded projects' })}
          description={t('projects.awarded_empty_desc', {
            defaultValue: 'Won bids will appear here as official projects.',
          })}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((project) => (
            <Card key={project.id} padding="md" className="flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-content-primary">
                  {project.name}
                </h3>
                <Badge variant="success">{project.status}</Badge>
              </div>
              <div className="flex items-center gap-3 text-xs text-content-secondary">
                <span className="inline-flex items-center gap-1">
                  <Users size={13} />
                  {t('projects.team', { defaultValue: 'Team' })}
                </span>
                <span className="inline-flex items-center gap-1">
                  <FileText size={13} />
                  {t('projects.documents', { defaultValue: 'Documents' })}
                </span>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/projects/${project.id}`)}
                className="mt-1 self-start text-sm font-medium text-oe-blue hover:underline"
              >
                {t('common.open', { defaultValue: 'Open' })} →
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
