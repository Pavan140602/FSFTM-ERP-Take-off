// OE-DELIVERY: 2026-10-19-bid-awarded-tabs-v1
// AwardedDocumentsTab — "Awarded Documents" tab for the Documents page.
// Shows ONLY documents from awarded/official projects. No bid (opportunity)
// data is read here: the bid/awarded separation rule forbids mixing.
// Data: projects API (awarded filter) + per-project documents.

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Search, FileText } from 'lucide-react';
import { Card, EmptyState, SkeletonGrid, Badge } from '@/shared/ui';
import { projectsApi, type Project } from '@/features/projects/api';
import { takeoffApi } from '@/features/takeoff/api';

const AWARDED_STATUSES = new Set(['won', 'awarded', 'active', 'in_progress']);

interface AwardedDoc {
  id: string;
  project_id: string;
  project_name: string;
  file_name: string;
  size_bytes: number;
}

export function AwardedDocumentsTab() {
  const { t } = useTranslation();
  const [nameFilter, setNameFilter] = useState('');

  const projectsQ = useQuery({
    queryKey: ['awarded-docs-projects'],
    queryFn: () => projectsApi.list({ limit: 200 }),
    staleTime: 2 * 60 * 1000,
  });

  const awarded: Project[] = useMemo(() => {
    const all = (projectsQ.data as Project[] | undefined) ?? [];
    return all.filter((p) => AWARDED_STATUSES.has((p.status ?? '').toLowerCase()));
  }, [projectsQ.data]);

  const docsQ = useQuery({
    queryKey: ['awarded-documents-tab', awarded.map((p) => p.id).join(',')],
    queryFn: async (): Promise<AwardedDoc[]> => {
      const all: AwardedDoc[] = [];
      await Promise.all(
        awarded.map(async (p) => {
          try {
            const docs = await takeoffApi.listDocuments(p.id);
            for (const d of docs) {
              all.push({
                id: d.id,
                project_id: p.id,
                project_name: p.name ?? '',
                file_name: d.filename ?? d.id,
                size_bytes: d.size_bytes ?? 0,
              });
            }
          } catch {
            // Project without accessible documents — skip silently.
          }
        }),
      );
      return all;
    },
    enabled: awarded.length > 0,
    staleTime: 2 * 60 * 1000,
  });

  const docs = useMemo(() => docsQ.data ?? [], [docsQ.data]);

  const filtered = useMemo(() => {
    const q = nameFilter.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter(
      (d) =>
        d.project_name.toLowerCase().includes(q) ||
        d.file_name.toLowerCase().includes(q),
    );
  }, [docs, nameFilter]);

  if (projectsQ.isLoading || docsQ.isLoading) return <SkeletonGrid count={6} />;

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
          placeholder={t('documents.awarded_filter_name', {
            defaultValue: 'Filter by project / file name...',
          })}
          className="w-full rounded-lg border border-border bg-surface-primary py-2 pl-10 pr-3 text-sm text-content-primary placeholder:text-content-tertiary"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={t('documents.awarded_empty', { defaultValue: 'No awarded documents' })}
          description={t('documents.awarded_empty_desc', {
            defaultValue: 'Documents from awarded projects will appear here.',
          })}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((doc) => (
            <Card key={doc.id} padding="md" className="flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <Badge variant="success">AWARDED</Badge>
                <span className="text-xs text-content-tertiary">
                  {doc.size_bytes > 0
                    ? `${(doc.size_bytes / 1024 / 1024).toFixed(1)} MB`
                    : ''}
                </span>
              </div>
              <p className="text-sm font-semibold text-content-primary">
                {doc.project_name}
              </p>
              <p className="flex items-center gap-1.5 truncate text-xs text-content-secondary">
                <FileText size={13} className="shrink-0" />
                <span className="truncate">{doc.file_name}</span>
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
