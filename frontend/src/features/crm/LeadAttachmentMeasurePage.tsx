// OE-DELIVERY: 2026-10-15-lead-measure-icon-v1
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP

/**
 * Standalone PDF measurement view for a CRM lead attachment.
 *
 * Route: `/takeoff/lead-attachment?leadId=<uuid>&attachmentId=<uuid>&name=<filename>`
 *
 * Mounts the shared TakeoffViewerModule with the attachment's download URL.
 * The module sends the Bearer token itself when loading `initialPdfUrl`,
 * so the protected lead-attachment endpoint works without extra plumbing.
 * Only PDFs get the measurement icon in the lead drawer, so this page
 * assumes a PDF.
 */

import { useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import TakeoffViewerModule from '@/modules/pdf-takeoff/TakeoffViewerModule';

export function LeadAttachmentMeasurePage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId') ?? '';
  const attachmentId = searchParams.get('attachmentId') ?? '';
  const name = searchParams.get('name') ?? '';

  const pdfUrl = useMemo(() => {
    if (!leadId || !attachmentId) return null;
    return `/api/v1/crm/leads/${leadId}/attachments/${attachmentId}/download`;
  }, [leadId, attachmentId]);

  if (!pdfUrl) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-sm text-content-secondary">
          {t('crm.measure_missing_params', {
            defaultValue: 'Missing lead or attachment reference.',
          })}
        </p>
        <Link
          to="/crm"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          <ArrowLeft size={14} />
          {t('crm.back_to_crm', { defaultValue: 'Back to CRM' })}
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <TakeoffViewerModule
        initialPdfUrl={pdfUrl}
        initialPdfName={name || undefined}
        initialDocumentId={null}
      />
    </div>
  );
}
