// OE-DELIVERY: 2026-10-19-bid-awarded-tabs-v1
// BidDocumentsTab — "Bid Documents" tab for the Documents page.
// Shows ONLY pre-award bid attachments from the CRM module.
// Data: GET /v1/crm/opportunities/attachments/all (open opportunities only).
// Storage: uploads/opportunity-attachments/<opportunity_id>/ — separate.

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Search, FileText, Download } from 'lucide-react';
import { Card, EmptyState, SkeletonGrid, Badge } from '@/shared/ui';
import {
  listAllOpportunityAttachments,
  type AllOpportunityAttachment,
} from '@/features/crm/api';

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function BidDocumentsTab() {
  const { t } = useTranslation();
  const [nameFilter, setNameFilter] = useState('');

  const docsQ = useQuery({
    queryKey: ['bid-documents-tab'],
    queryFn: () => listAllOpportunityAttachments(false),
    staleTime: 2 * 60 * 1000,
  });

  const docs: AllOpportunityAttachment[] = useMemo(
    () => docsQ.data ?? [],
    [docsQ.data],
  );

  const filtered = useMemo(() => {
    const q = nameFilter.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter(
      (d) =>
        d.opportunity_title.toLowerCase().includes(q) ||
        d.file_name.toLowerCase().includes(q),
    );
  }, [docs, nameFilter]);

  if (docsQ.isLoading) return <SkeletonGrid count={6} />;
  if (docsQ.isError) {
    return (
      <EmptyState
        title={t('common.error', { defaultValue: 'Error' })}
        description={String(docsQ.error)}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative max-w-md">
        <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center pl-3 text-content-tertiary">
          <Search size={16} />
        </div>
        <input
          type="text"
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
          placeholder={t('documents.bid_filter_name', {
            defaultValue: 'Filter by deal / file name...',
          })}
          className="w-full rounded-lg border border-border bg-surface-primary py-2 pl-10 pr-3 text-sm text-content-primary placeholder:text-content-tertiary"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={t('documents.bid_empty', { defaultValue: 'No bid documents' })}
          description={t('documents.bid_empty_desc', {
            defaultValue: 'Bid attachments from live opportunities will appear here.',
          })}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((doc) => (
            <Card key={doc.id} padding="md" className="flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <Badge variant="info">BID</Badge>
                <span className="text-xs text-content-tertiary">
                  {formatSize(doc.size_bytes)}
                </span>
              </div>
              <p className="text-sm font-semibold text-content-primary">
                {doc.opportunity_title}
              </p>
              <p className="flex items-center gap-1.5 truncate text-xs text-content-secondary">
                <FileText size={13} className="shrink-0" />
                <span className="truncate">{doc.file_name}</span>
              </p>
              <a
                href={`/v1/crm/opportunities/${doc.opportunity_id}/attachments/${doc.id}/download/`}
                className="mt-1 inline-flex items-center gap-1 self-start text-sm font-medium text-oe-blue hover:underline"
              >
                <Download size={14} />
                {t('common.download', { defaultValue: 'Download' })}
              </a>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
