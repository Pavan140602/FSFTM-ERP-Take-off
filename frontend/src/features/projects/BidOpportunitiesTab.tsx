// OE-DELIVERY: 2026-10-22-estimation-filter-v2-leaveallbids
// BidOpportunitiesTab — "Bid Opportunities" main tab content for the Projects page.
// Sub-tabs: All Bids (CRM opportunities) + Estimation / Estimation Submitted /
// Submitted to Client / Waiting Response / Won / Lost (projects by status).
// Strict separation: no awarded/execution project data here.

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, FileText } from 'lucide-react';
import { Card, Badge, EmptyState, SkeletonGrid } from '@/shared/ui';
import { useLocalStorage } from '@/shared/hooks/useLocalStorage';
import {
  listOpportunities,
  listOpportunityAttachments,
  type Opportunity,
} from '@/features/crm/api';
import { projectsApi, type Project } from '@/features/projects/api';

type BidSubTab = 'all' | 'estimating' | 'submitted' | 'toclient' | 'waiting' | 'won' | 'lost';

const SUB_TABS: { key: BidSubTab; labelDefault: string }[] = [
  { key: 'all', labelDefault: 'All Bids' },
  { key: 'estimating', labelDefault: 'Estimation' },
  { key: 'submitted', labelDefault: 'Estimation Submitted' },
  { key: 'toclient', labelDefault: 'Submitted to Client' },
  { key: 'waiting', labelDefault: 'Waiting Response' },
  { key: 'won', labelDefault: 'Won' },
  { key: 'lost', labelDefault: 'Lost' },
];

// Project statuses per sub-tab (mirrors the old outcome tabs).
const SUB_TAB_STATUSES: Record<Exclude<BidSubTab, 'all'>, string[]> = {
  estimating: ['active', 'estimation'],
  submitted: ['estimation_submitted'],
  toclient: ['submitted_to_client'],
  waiting: ['awaiting_response'],
  won: ['won'],
  lost: ['lost'],
};

function useBidAttachments(opportunities: Opportunity[]) {
  return useQuery({
    queryKey: ['bid-tab-attachments', opportunities.map((o) => o.id).join(',')],
    queryFn: async () => {
      const entries = await Promise.all(
        opportunities.map(async (o) => {
          try {
            const files = await listOpportunityAttachments(o.id);
            return [o.id, files] as const;
          } catch {
            return [o.id, []] as const;
          }
        }),
      );
      return new Map(entries.map(([id, files]) => [id, files]));
    },
    enabled: opportunities.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function BidOpportunitiesTab() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  // OE-DELIVERY 2026-10-21: persist the sub-tab so a browser refresh
  // reopens the same sub-tab instead of resetting to All Bids. The guard
  // falls back to 'all' if a stale key from an older build was stored.
  const [storedSubTab, setStoredSubTab] = useLocalStorage<BidSubTab>('oe_bid_subtab', 'all');
  const subTab: BidSubTab = SUB_TABS.some((t) => t.key === storedSubTab) ? storedSubTab : 'all';
  const setSubTab = (tab: BidSubTab) => setStoredSubTab(tab);
  const [nameFilter, setNameFilter] = useState('');

  // All Bids: CRM opportunities
  const oppsQ = useQuery({
    queryKey: ['bid-opportunities-tab'],
    queryFn: () => listOpportunities({ status: 'open', limit: 200 }),
    staleTime: 2 * 60 * 1000,
    enabled: subTab === 'all',
  });

  // Projects by status: drives the stage tabs AND the All Bids
  // exclusion below, so it loads on every sub-tab.
  const projectsQ = useQuery({
    queryKey: ['bid-stage-projects'],
    queryFn: () => projectsApi.list(),
    staleTime: 2 * 60 * 1000,
  });

  const opportunities = useMemo(() => oppsQ.data ?? [], [oppsQ.data]);

  const stageProjects = useMemo(() => {
    if (subTab === 'all') return [];
    const allowed = SUB_TAB_STATUSES[subTab];
    const list = (projectsQ.data as Project[] | undefined) ?? [];
    const q = nameFilter.trim().toLowerCase();
    return list.filter((p) => {
      if (!allowed.includes(p.status)) return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [projectsQ.data, subTab, nameFilter]);

  const projectStatusById = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of (projectsQ.data as Project[] | undefined) ?? []) {
      map.set(p.id, p.status);
    }
    return map;
  }, [projectsQ.data]);

  const filteredOpps = useMemo(() => {
    const q = nameFilter.trim().toLowerCase();
    return opportunities.filter((o) => {
      // A converted bid leaves All Bids once its project moves past
      // 'new' — assigning an estimator flips it to 'estimation' and
      // the Estimation tab owns it from there. Bids with no project
      // (or still 'new') stay.
      const pStatus = o.project_id ? projectStatusById.get(o.project_id) : undefined;
      if (pStatus && pStatus !== 'new') return false;
      if (q && !o.title.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [opportunities, nameFilter, projectStatusById]);

  const attachmentsQ = useBidAttachments(filteredOpps);

  const isLoading =
    subTab === 'all' ? oppsQ.isLoading || projectsQ.isLoading : projectsQ.isLoading;
  const isError = subTab === 'all' ? oppsQ.isError : projectsQ.isError;
  const error = subTab === 'all' ? oppsQ.error : projectsQ.error;

  if (isLoading) return <SkeletonGrid items={6} />;
  if (isError) {
    return (
      <EmptyState
        title={t('common.error', { defaultValue: 'Error' })}
        description={String(error)}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex flex-wrap items-center gap-2" role="tablist"
        aria-label={t('projects.bid_subtabs', { defaultValue: 'Bid stages' })}>
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={subTab === tab.key}
            onClick={() => setSubTab(tab.key)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
              subTab === tab.key
                ? 'border-oe-blue bg-oe-blue text-white shadow-sm'
                : 'border-border bg-surface-primary text-content-secondary hover:bg-surface-secondary hover:text-content-primary'
            }`}
          >
            {t(`projects.bid_subtab_${tab.key}`, { defaultValue: tab.labelDefault })}
          </button>
        ))}
      </div>

      {/* Name filter */}
      <div className="relative max-w-md">
        <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center pl-3 text-content-tertiary">
          <Search size={16} />
        </div>
        <input
          type="text"
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
          placeholder={t('projects.bid_filter_name', {
            defaultValue: 'Filter by name...',
          })}
          className="w-full rounded-lg border border-border bg-surface-primary py-2 pl-10 pr-3 text-sm text-content-primary placeholder:text-content-tertiary"
        />
      </div>

      {subTab === 'all' ? (
        filteredOpps.length === 0 ? (
          <EmptyState
            title={t('projects.bid_empty', { defaultValue: 'No bid opportunities' })}
            description={t('projects.bid_empty_desc', {
              defaultValue: 'Live bids from CRM will appear here.',
            })}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredOpps.map((opp) => {
              const files = attachmentsQ.data?.get(opp.id) ?? [];
              return (
                <Card key={opp.id} padding="md" className="flex flex-col gap-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-content-primary">{opp.title}</h3>
                    <Badge variant="blue">{opp.status}</Badge>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-content-secondary">
                    <FileText size={13} />
                    {t('projects.bid_docs_count', {
                      defaultValue: '{{count}} docs',
                      count: files.length,
                    })}
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate(opp.project_id ? `/projects/${opp.project_id}` : `/crm?view=pipeline&opp=${opp.id}`)}
                    className="mt-1 self-start text-sm font-medium text-oe-blue hover:underline"
                  >
                    {t('common.open', { defaultValue: 'Open' })} →
                  </button>
                </Card>
              );
            })}
          </div>
        )
      ) : stageProjects.length === 0 ? (
        <EmptyState
          title={t('projects.bid_stage_empty', { defaultValue: 'No projects in this stage' })}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stageProjects.map((p) => (
            <Card key={p.id} padding="md" className="flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-content-primary">{p.name}</h3>
                <Badge variant="blue">{p.status}</Badge>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/projects/${p.id}`)}
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
