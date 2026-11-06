// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
//
// Detail page for a single file-approval workflow.
//
// Notification action URLs point at /file-approvals/:workflowId — without
// this route those links 404'd.
//
// Layout: left pane previews the document under review (fetched as a blob
// with the JWT auth header, since plain iframe src would 401); right pane
// shows the approval workflow side-by-side (no backdrop blur over the
// document). A toggle button on the drawer's left edge collapses it to the
// right; clicking again restores it.

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ChevronRight, FileText, Loader2 } from 'lucide-react';
import clsx from 'clsx';

import { downloadDocumentBlob } from '@/features/documents/api';
import { ApprovalDrawer } from './ApprovalDrawer';
import { useApproval } from './hooks';

export function FileApprovalDetailPage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: workflow, isLoading: wfLoading } = useApproval(workflowId ?? null);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(true);

  useEffect(() => {
    if (!workflowId) {
      navigate('/files/approvals', { replace: true });
    }
  }, [workflowId, navigate]);

  // Fetch the document under review as a blob (auth header required).
  useEffect(() => {
    if (!workflow?.file_id) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    setPreviewLoading(true);
    setPreviewError(null);
    downloadDocumentBlob(workflow.file_id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : 'Preview failed');
        }
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [workflow?.file_id]);

  if (!workflowId) return null;

  return (
    <div className="flex h-[calc(100vh-140px)] min-h-[500px]">
      {/* Left: document preview */}
      <div className="flex-1 min-w-0 bg-surface-secondary flex flex-col rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2">
          <FileText size={16} className="text-content-tertiary" />
          <span className="text-sm font-medium truncate">
            {t('files.approvals.document_under_review', {
              defaultValue: 'Document under review',
            })}
          </span>
        </div>
        <div className="flex-1 min-h-0">
          {previewLoading || wfLoading ? (
            <div className="h-full flex items-center justify-center text-content-tertiary">
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : previewError || !previewUrl ? (
            <div className="h-full flex flex-col items-center justify-center gap-2 text-content-tertiary px-8 text-center">
              <FileText size={32} />
              <p className="text-sm">
                {previewError
                  ? t('files.approvals.preview_failed', {
                      defaultValue: 'Could not load document preview.',
                    })
                  : t('files.approvals.no_preview', {
                      defaultValue: 'No preview available for this file.',
                    })}
              </p>
              {previewError && (
                <p className="text-xs text-content-quaternary">{previewError}</p>
              )}
            </div>
          ) : (
            <iframe
              src={previewUrl}
              title="Document preview"
              className="w-full h-full border-0"
            />
          )}
        </div>
      </div>

      {/* Right: approval workflow panel with edge toggle */}
      <div className="relative shrink-0 flex">
        {/* Toggle button — centered on the panel's left edge */}
        <button
          type="button"
          onClick={() => setDrawerOpen((v) => !v)}
          aria-label={
            drawerOpen
              ? t('files.approvals.collapse_panel', { defaultValue: 'Collapse panel' })
              : t('files.approvals.expand_panel', { defaultValue: 'Expand panel' })
          }
          className={clsx(
            'absolute top-1/2 -translate-y-1/2 z-10',
            'w-7 h-14 -left-3.5 rounded-full',
            'bg-surface-elevated border border-border-light shadow-lg',
            'flex items-center justify-center text-content-secondary',
            'hover:bg-surface-secondary hover:text-content-primary transition-colors',
          )}
        >
          <ChevronRight
            size={16}
            className={clsx('transition-transform', drawerOpen && 'rotate-180')}
          />
        </button>
        <div
          className={clsx(
            'overflow-hidden transition-all duration-300',
            drawerOpen ? 'w-[400px] opacity-100' : 'w-0 opacity-0',
          )}
        >
          <div className="w-[400px] h-full">
            <ApprovalDrawer
              open
              inline
              workflowId={workflowId}
              onClose={() => setDrawerOpen(false)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
