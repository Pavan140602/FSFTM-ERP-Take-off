// OE-DELIVERY: 2026-10-14-transmittal-tracking-v1
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
/** Public transmittal view page (``/transmittals/view/:token``).
 *
 * Rendered for unauthenticated recipients who follow the link from the
 * transmittal email. No ERP login, no app shell — the ack token in the
 * URL is the credential (same pattern as ``/share/:token``).
 *
 * Layout is a split view: transmittal details + file list on the left,
 * selected-file preview on the right. Clicking a file streams it from
 * the token-gated endpoint (which logs the file view server-side) and
 * shows it inline: PDF in an iframe, images natively, anything else as
 * a download link.
 *
 * Flow:
 *    1. ``GET /api/v1/file-transmittals/public/{token}/`` — fetch the
 *       transmittal. 404 → "Link not found". The fetch itself stamps
 *       the recipient's first page view server-side.
 *    2. Click a file → preview it in the right pane (view is logged).
 *    3. "Acknowledge receipt" → ``POST /ack/{token}/`` → acknowledged
 *       state. Idempotent: already-acknowledged shows the timestamp.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  MailOpen,
} from 'lucide-react';
import { Logo } from '@/shared/ui';

type PublicItem = {
  id: string;
  file_kind: string;
  file_id: string;
  file_version_snapshot: string | null;
  canonical_name_snapshot: string;
  sort_order: number;
};

type PublicView = {
  number: string;
  subject: string;
  reason_code: string;
  sent_at: string;
  status: string;
  notes: string | null;
  sender_name: string | null;
  project_name: string | null;
  recipient_email: string;
  recipient_name: string | null;
  acknowledged_at: string | null;
  items: PublicItem[];
};

type FetchState =
  | { kind: 'loading' }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }
  | { kind: 'open'; view: PublicView };

function fileUrl(token: string, itemId: string): string {
  return `/api/v1/file-transmittals/public/${encodeURIComponent(token)}/files/${encodeURIComponent(itemId)}`;
}

function isPdf(name: string): boolean {
  return name.toLowerCase().endsWith('.pdf');
}

function isImage(name: string): boolean {
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name);
}

function formatDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export function TransmittalViewPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<FetchState>({ kind: 'loading' });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [acking, setAcking] = useState(false);
  const [ackError, setAckError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setState({ kind: 'not_found' });
      return;
    }
    (async () => {
      try {
        const res = await fetch(
          `/api/v1/file-transmittals/public/${encodeURIComponent(token)}/`,
          { headers: { Accept: 'application/json' } },
        );
        if (res.status === 404) {
          if (!cancelled) setState({ kind: 'not_found' });
          return;
        }
        if (!res.ok) throw new Error(`Failed to load transmittal (${res.status})`);
        const view = (await res.json()) as PublicView;
        if (!cancelled) {
          setState({ kind: 'open', view });
          // Auto-select the first file so the preview pane is useful.
          if (view.items.length > 0) setSelectedId(view.items[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            kind: 'error',
            message: err instanceof Error ? err.message : 'Failed to load transmittal',
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const selected = useMemo(() => {
    if (state.kind !== 'open') return null;
    return state.view.items.find((i) => i.id === selectedId) ?? null;
  }, [state, selectedId]);

  const acknowledge = useCallback(async () => {
    if (!token || acking) return;
    setAcking(true);
    setAckError(null);
    try {
      const res = await fetch(
        `/api/v1/file-transmittals/ack/${encodeURIComponent(token)}/`,
        { method: 'POST', headers: { Accept: 'application/json' } },
      );
      if (!res.ok) throw new Error(`Acknowledgement failed (${res.status})`);
      const body = (await res.json()) as { acknowledged_at: string };
      setState((prev) =>
        prev.kind === 'open'
          ? { ...prev, view: { ...prev.view, acknowledged_at: body.acknowledged_at } }
          : prev,
      );
    } catch (err) {
      setAckError(err instanceof Error ? err.message : 'Acknowledgement failed');
    } finally {
      setAcking(false);
    }
  }, [token, acking]);

  if (state.kind === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading transmittal…</span>
        </div>
      </div>
    );
  }

  if (state.kind === 'not_found') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
          <AlertTriangle className="mx-auto h-10 w-10 text-amber-500" />
          <h1 className="mt-4 text-lg font-semibold text-slate-900">Link not found</h1>
          <p className="mt-2 text-sm text-slate-600">
            This transmittal link is invalid or has expired. Please contact the sender
            for a new link.
          </p>
        </div>
      </div>
    );
  }

  if (state.kind === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
          <AlertTriangle className="mx-auto h-10 w-10 text-red-500" />
          <h1 className="mt-4 text-lg font-semibold text-slate-900">Something went wrong</h1>
          <p className="mt-2 text-sm text-slate-600">{state.message}</p>
        </div>
      </div>
    );
  }

  const { view } = state;
  const acknowledged = view.acknowledged_at !== null;

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Header — no app shell, brand only. */}
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
        <Logo />
        <div>
          <h1 className="text-base font-semibold text-slate-900">
            Transmittal {view.number}
          </h1>
          <p className="text-xs text-slate-500">
            {view.project_name ? `${view.project_name} · ` : ''}Sent{' '}
            {formatDate(view.sent_at)}
          </p>
        </div>
      </header>

      {/* Split view: details left, file preview right. */}
      <main className="flex flex-1 flex-col gap-4 p-4 sm:p-6 lg:flex-row">
        {/* Left — details + file list. */}
        <section className="w-full shrink-0 rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:w-[380px]">
          <h2 className="text-lg font-semibold text-slate-900">{view.subject}</h2>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">From</dt>
              <dd className="text-right font-medium text-slate-900">
                {view.sender_name ?? '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">To</dt>
              <dd className="text-right font-medium text-slate-900">
                {view.recipient_name ?? view.recipient_email}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Status</dt>
              <dd className="text-right font-medium capitalize text-slate-900">
                {view.status}
              </dd>
            </div>
          </dl>
          {view.notes && (
            <p className="mt-4 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
              {view.notes}
            </p>
          )}

          <h3 className="mt-6 text-sm font-semibold text-slate-900">
            Documents ({view.items.length})
          </h3>
          {view.items.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No documents enclosed.</p>
          ) : (
            <ul className="mt-2 divide-y divide-slate-100 rounded-md border border-slate-200">
              {view.items.map((item) => {
                const active = item.id === selectedId;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors ${
                        active
                          ? 'bg-blue-50 font-medium text-blue-800'
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                      <span className="min-w-0 flex-1 truncate">
                        {item.canonical_name_snapshot}
                      </span>
                      {item.file_version_snapshot && (
                        <span className="shrink-0 text-xs text-slate-400">
                          {item.file_version_snapshot}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {/* Acknowledge. */}
          <div className="mt-6">
            {acknowledged ? (
              <p className="flex items-center gap-2 rounded-md bg-green-50 px-3 py-2.5 text-sm font-medium text-green-800">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Acknowledged {formatDate(view.acknowledged_at)}
              </p>
            ) : (
              <>
                <button
                  type="button"
                  onClick={acknowledge}
                  disabled={acking}
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-60"
                >
                  {acking ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <MailOpen className="h-4 w-4" />
                  )}
                  Acknowledge receipt
                </button>
                {ackError && (
                  <p className="mt-2 text-xs text-red-600">{ackError}</p>
                )}
              </>
            )}
          </div>
        </section>

        {/* Right — file preview. */}
        <section className="flex min-h-[480px] flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          {!selected || !token ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center">
              <p className="text-sm text-slate-500">
                Select a document on the left to preview it here.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
                <p className="min-w-0 truncate text-sm font-medium text-slate-900">
                  {selected.canonical_name_snapshot}
                </p>
                <a
                  href={fileUrl(token, selected.id)}
                  download
                  className="flex shrink-0 items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download
                </a>
              </div>
              <div className="min-h-0 flex-1">
                {isPdf(selected.canonical_name_snapshot) ? (
                  <iframe
                    src={fileUrl(token, selected.id)}
                    title={selected.canonical_name_snapshot}
                    className="h-full w-full border-0"
                  />
                ) : isImage(selected.canonical_name_snapshot) ? (
                  <div className="flex h-full items-center justify-center overflow-auto bg-slate-100 p-4">
                    {/* eslint-disable-next-line jsx-a11y/img-redundant-alt */}
                    <img
                      src={fileUrl(token, selected.id)}
                      alt={selected.canonical_name_snapshot}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
                    <FileText className="h-10 w-10 text-slate-300" />
                    <p className="text-sm text-slate-600">
                      Preview is not available for this file type.
                    </p>
                    <a
                      href={fileUrl(token, selected.id)}
                      download
                      className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                    >
                      <Download className="h-4 w-4" />
                      Download file
                    </a>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
