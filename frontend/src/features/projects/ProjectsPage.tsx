// OE-DELIVERY: 2026-10-19-projects-clean-v2
// Clean ProjectsPage — 2 tabs (Bid Opportunities + Awarded Projects) + stats cards.
// Stats: bid opportunities count, awarded projects count, won, lost.

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { FileText, Trophy, TrendingUp, TrendingDown } from 'lucide-react';
import { BidOpportunitiesTab } from './BidOpportunitiesTab';
import { AwardedProjectsTab } from './AwardedProjectsTab';
import { listOpportunities } from '@/features/crm/api';
import { projectsApi } from '@/features/projects/api';
import { Card } from '@/shared/ui';

type MainTab = 'bids' | 'awarded';

function StatCard({ label, value, icon: Icon }: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-oe-blue-subtle p-2">
          <Icon size={20} className="text-oe-blue-text" />
        </div>
        <div>
          <div className="text-2xl font-bold text-content-primary">{value}</div>
          <div className="text-xs text-content-secondary">{label}</div>
        </div>
      </div>
    </Card>
  );
}

export function ProjectsPage() {
  const { t } = useTranslation();
  const [mainTab, setMainTab] = useState<MainTab>('bids');

  // Stats: opportunities by status
  const oppsQ = useQuery({
    queryKey: ['projects-page-opp-stats'],
    queryFn: () => listOpportunities({ limit: 500 }),
    staleTime: 2 * 60 * 1000,
  });
  const opps = oppsQ.data ?? [];
  const openOpps = opps.filter((o) => o.status === 'open').length;
  const wonOpps = opps.filter((o) => o.status === 'won').length;
  const lostOpps = opps.filter((o) => o.status === 'lost').length;

  // Stats: awarded projects
  const projsQ = useQuery({
    queryKey: ['projects-page-proj-stats'],
    queryFn: () => projectsApi.list(),
    staleTime: 2 * 60 * 1000,
  });
  const awardedCount = (projsQ.data ?? []).filter((p) =>
    ['won', 'awarded', 'active', 'in_progress'].includes(p.status)
  ).length;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label={t('projects.stat_open_bids', { defaultValue: 'Open Bids' })}
          value={oppsQ.isLoading ? '…' : openOpps}
          icon={FileText}
        />
        <StatCard
          label={t('projects.stat_awarded', { defaultValue: 'Awarded Projects' })}
          value={projsQ.isLoading ? '…' : awardedCount}
          icon={Trophy}
        />
        <StatCard
          label={t('projects.stat_won', { defaultValue: 'Won' })}
          value={oppsQ.isLoading ? '…' : wonOpps}
          icon={TrendingUp}
        />
        <StatCard
          label={t('projects.stat_lost', { defaultValue: 'Lost' })}
          value={oppsQ.isLoading ? '…' : lostOpps}
          icon={TrendingDown}
        />
      </div>

      {/* Main tabs */}
      <div className="flex flex-wrap items-center gap-2" role="tablist"
        aria-label={t('projects.main_tabs', { defaultValue: 'Projects views' })}>
        <button
          type="button"
          role="tab"
          aria-selected={mainTab === 'bids'}
          onClick={() => setMainTab('bids')}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
            mainTab === 'bids'
              ? 'border-oe-blue bg-oe-blue text-white shadow-sm'
              : 'border-border bg-surface-primary text-content-secondary hover:bg-surface-secondary hover:text-content-primary'
          }`}
        >
          <FileText size={14} />
          {t('projects.tab_bids', { defaultValue: 'Bid Opportunities' })}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mainTab === 'awarded'}
          onClick={() => setMainTab('awarded')}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
            mainTab === 'awarded'
              ? 'border-oe-blue bg-oe-blue text-white shadow-sm'
              : 'border-border bg-surface-primary text-content-secondary hover:bg-surface-secondary hover:text-content-primary'
          }`}
        >
          <Trophy size={14} />
          {t('projects.tab_awarded', { defaultValue: 'Awarded Projects' })}
        </button>
      </div>

      {/* Tab content — direct render, no complex conditional */}
      {mainTab === 'bids' ? <BidOpportunitiesTab /> : <AwardedProjectsTab />}
    </div>
  );
}
