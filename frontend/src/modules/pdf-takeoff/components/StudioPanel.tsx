// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * Studio panel (left rail > Studio): working sessions for several people.
 *
 * - Start a session: pick PDFs (from the open tabs), invite people by email.
 *   Everyone gets a notification and an email with the session link and its
 *   ID (123-456-789).
 * - Join a session with its ID, or from the invite.
 * - In a session: its PDFs (click to open - also PDFs of other projects),
 *   who is in it and who is online on which PDF and page, markups per person,
 *   chat, invite more people, add the open PDF.
 * - The host can let anyone with the ID join, remove people, and Finish the
 *   session, which ends it for everyone and gives the report (CSV).
 *
 * Markups made in a session's PDFs reach the others within ~3 s (the viewer's
 * live sync runs faster for PDFs in the active session, see STUDIO_ACTIVE_KEY).
 * Server: /v1/takeoff/studio/sessions/...
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Copy, LogOut, Plus, Send, X } from 'lucide-react';
import { apiDelete, apiGet, apiPatch, apiPost } from '@/shared/lib/api';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { setShared, useSharedState } from '../data/shared-state';

/** Shared key: the session this browser is working in ({ id, docIds }). */
export const STUDIO_ACTIVE_KEY = 'studio.active';
const ACTIVE_STORE = 'takeoff.studio.active';

export type StudioActive = { id: string; docIds: string[] } | null;
export type StudioDoc = { id: string; name: string; pages?: number | null; project_id: string | null; project_name: string };
type Attendee = {
  id: string;
  user_id: string | null;
  name: string;
  email: string;
  role: 'host' | 'attendee';
  status: 'invited' | 'joined' | 'left';
  online: boolean;
  document_id: string | null;
  page: number | null;
};
type SessionDetail = {
  id: string;
  name: string;
  code: string;
  status: 'active' | 'finished';
  open_join: boolean;
  created_at: string | null;
  finished_at: string | null;
  me: { attendee_id: string; role: 'host' | 'attendee'; status: string };
  documents: StudioDoc[];
  attendees: Attendee[];
  invites?: { email: string; status: string }[];
};
type SessionRow = { id: string; name: string; code: string; status: string; role: string; my_status: string; created_at: string | null };
type Report = {
  total: number;
  people: { user_id: string; name: string; email: string; count: number; by_type: Record<string, number> }[];
  documents: { document_id: string; name: string; count: number; by_user: Record<string, number> }[];
};
type Message = { id: string; user_id: string; name: string; text: string; at: string | null };

/** Read once at load so the viewer knows the active session before the panel opens. */
export function readStoredStudio(): StudioActive {
  try {
    const v = JSON.parse(localStorage.getItem(ACTIVE_STORE) || 'null') as StudioActive;
    return v && typeof v.id === 'string' ? { id: v.id, docIds: Array.isArray(v.docIds) ? v.docIds : [] } : null;
  } catch {
    return null;
  }
}
export function setStudioActive(v: StudioActive): void {
  setShared<StudioActive>(STUDIO_ACTIVE_KEY, () => v);
  try {
    if (v) localStorage.setItem(ACTIVE_STORE, JSON.stringify(v));
    else localStorage.removeItem(ACTIVE_STORE);
  } catch { /* ignore */ }
}

const initials = (p: { name?: string; email?: string }) =>
  ((p.name || p.email || '?').trim().split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?');
const label = (p: { name?: string; email?: string }) => (p.name || '').trim() || p.email || 'Someone';
const timeOf = (iso: string | null) => {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};
const splitEmails = (s: string) => s.split(/[\s,;]+/).map((x) => x.trim()).filter((x) => x.includes('@'));
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const inviteSummary = (rows: { email: string; status: string }[] = []) => {
  const by = (st: string) => rows.filter((r) => r.status === st).map((r) => r.email);
  const parts: string[] = [];
  if (by('invited').length) parts.push(`Invited: ${by('invited').join(', ')}`);
  if (by('emailed').length) parts.push(`Sign-up link emailed (no account yet): ${by('emailed').join(', ')}`);
  if (by('no_account').length) parts.push(`No account - ask an admin to add: ${by('no_account').join(', ')}`);
  if (by('already').length) parts.push(`Already in the session: ${by('already').join(', ')}`);
  return parts.join(' · ');
};

export function reportCsv(detail: SessionDetail, report: Report): string {
  const q = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`;
  const types = Array.from(new Set(report.people.flatMap((p) => Object.keys(p.by_type)))).sort();
  const lines = [
    [q('Session'), q(detail.name), q('ID'), q(detail.code), q('Started'), q(timeOf(detail.created_at)), q('Finished'), q(timeOf(detail.finished_at))].join(','),
    '',
    [q('Person'), q('Email'), q('Markups'), ...types.map(q)].join(','),
    ...report.people.map((p) => [q(label(p)), q(p.email), p.count, ...types.map((t) => p.by_type[t] ?? 0)].join(',')),
    '',
    [q('PDF'), q('Markups'), ...report.people.map((p) => q(label(p)))].join(','),
    ...report.documents.map((d) => [q(d.name), d.count, ...report.people.map((p) => d.by_user[p.user_id] ?? 0)].join(',')),
  ];
  return lines.join('\r\n');
}

/** The session report as a one-or-more-page PDF (A4 landscape). */
export async function reportPdf(detail: SessionDetail, report: Report): Promise<Uint8Array> {
  const { PDFDocument, StandardFonts, rgb } = await import('pdf-lib');
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  // Standard fonts only cover Latin-1.
  const safe = (t: string) => t.replace(/[\u2000-\u200B\u202F\u205F]/g, ' ').replace(/[\u2010-\u2015]/g, '-').replace(/[^\x20-\x7E\xA0-\xFF]/g, '?');
  const W = 842;
  const H = 595;
  const M = 40;
  let page = doc.addPage([W, H]);
  let y = H - M;
  const line = (text: string, x: number, size = 10, f = font, color = rgb(0.1, 0.1, 0.1)) =>
    page.drawText(safe(text), { x, y, size, font: f, color, maxWidth: W - x - M });
  const need = (h: number) => {
    if (y - h < M) {
      page = doc.addPage([W, H]);
      y = H - M;
    }
  };
  line(`Session report - ${detail.name}`, M, 18, bold);
  y -= 24;
  line(`Session ID ${detail.code}   ·   Started ${timeOf(detail.created_at)}${detail.finished_at ? `   ·   Finished ${timeOf(detail.finished_at)}` : '   ·   Still running'}`, M, 10, font, rgb(0.35, 0.35, 0.35));
  y -= 14;
  line(`${report.total} markups by ${report.people.length} ${report.people.length === 1 ? 'person' : 'people'} in ${detail.documents.length} PDF${detail.documents.length === 1 ? '' : 's'}`, M, 10, font, rgb(0.35, 0.35, 0.35));
  y -= 26;
  const types = Array.from(new Set(report.people.flatMap((p) => Object.keys(p.by_type)))).sort();
  const table = (head: string[], rows: string[][], widths: number[]) => {
    need(40);
    page.drawRectangle({ x: M, y: y - 4, width: W - 2 * M, height: 16, color: rgb(0.92, 0.94, 0.98) });
    let x = M + 4;
    head.forEach((h, i) => { line(h, x, 9, bold); x += widths[i]!; });
    y -= 18;
    for (const r of rows) {
      need(16);
      x = M + 4;
      r.forEach((c, i) => { line(c, x, 9); x += widths[i]!; });
      y -= 14;
    }
    y -= 14;
  };
  line('People', M, 12, bold);
  y -= 18;
  const typeW = Math.max(60, Math.min(90, (W - 2 * M - 330) / Math.max(1, types.length)));
  table(
    ['Person', 'Email', 'Markups', ...types],
    report.people.map((p) => [label(p), p.email, String(p.count), ...types.map((t) => String(p.by_type[t] ?? 0))]),
    [150, 180, 60, ...types.map(() => typeW)],
  );
  line('PDFs', M, 12, bold);
  y -= 18;
  table(
    ['PDF', 'Project', 'Markups'],
    detail.documents.map((d) => {
      const r = report.documents.find((x) => x.document_id === d.id);
      return [d.name, d.project_name || '', String(r?.count ?? 0)];
    }),
    [330, 250, 60],
  );
  line('People in the session', M, 12, bold);
  y -= 18;
  table(
    ['Name', 'Email', 'Role', 'Status'],
    detail.attendees.map((a) => [label(a), a.email, a.role === 'host' ? 'Host' : 'Attendee', a.status]),
    [180, 230, 90, 90],
  );
  return doc.save();
}

export function StudioPanel({
  currentDocument,
  openDocuments,
  onOpenDocument,
}: {
  /** The PDF open in the focused pane (server id), if any. */
  currentDocument: { id: string; name: string } | null;
  /** PDFs open as tabs, offered when starting a session. */
  openDocuments: { id: string; name: string }[];
  /** Open a session PDF (switches project when it belongs to another one). */
  onOpenDocument: (doc: StudioDoc) => void;
}) {
  const me = useAuthStore((s) => s.userId);
  const addToast = useToastStore((s) => s.addToast);
  const qc = useQueryClient();
  const [active] = useSharedState<StudioActive>(STUDIO_ACTIVE_KEY, readStoredStudio);
  const activeId = active?.id ?? null;

  // ── lobby state ──
  const [starting, setStarting] = useState(false);
  const [name, setName] = useState('');
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [inviteText, setInviteText] = useState('');
  const [openJoin, setOpenJoin] = useState(false);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const serverTabs = useMemo(() => {
    const list = [...openDocuments];
    if (currentDocument && !list.some((d) => d.id === currentDocument.id)) list.unshift(currentDocument);
    return list.filter((d) => !d.id.startsWith('local:') && !d.id.startsWith('temp-') && d.id !== '__local');
  }, [openDocuments, currentDocument]);
  useEffect(() => {
    if (!starting) return;
    setName((n) => n || `${(currentDocument?.name || 'Takeoff').replace(/\.pdf$/i, '')} session`);
    setPicked((p) => (p.size ? p : new Set(currentDocument ? [currentDocument.id] : serverTabs.slice(0, 1).map((d) => d.id))));
  }, [starting, currentDocument, serverTabs]);

  const sessions = useQuery({
    queryKey: ['studio-sessions'],
    queryFn: () => apiGet<{ sessions: SessionRow[] }>('/v1/takeoff/studio/sessions/'),
    enabled: !activeId,
    refetchInterval: 20000,
  });
  const detail = useQuery({
    queryKey: ['studio-session', activeId],
    queryFn: () => apiGet<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/`),
    enabled: !!activeId,
    refetchInterval: 5000,
    retry: 1,
  });
  const d = detail.data;
  const live = d?.status === 'active';
  const messages = useQuery({
    queryKey: ['studio-messages', activeId],
    queryFn: () => apiGet<{ messages: Message[] }>(`/v1/takeoff/studio/sessions/${activeId}/messages/`),
    enabled: !!activeId,
    refetchInterval: live ? 4000 : false,
  });
  const report = useQuery({
    queryKey: ['studio-report', activeId],
    queryFn: () => apiGet<Report>(`/v1/takeoff/studio/sessions/${activeId}/report/`),
    enabled: !!activeId,
    refetchInterval: live ? 15000 : false,
  });

  // Keep the viewer's "PDFs in my session" list current (faster live sync).
  const docKey = (d?.documents ?? []).map((x) => x.id).join(',');
  useEffect(() => {
    if (!activeId || !d) return;
    if (d.status !== 'active') return;
    if ((active?.docIds ?? []).join(',') !== docKey) setStudioActive({ id: activeId, docIds: docKey ? docKey.split(',') : [] });
  }, [activeId, d, docKey, active]);
  // Removed from the session (or it was deleted): back to the lobby.
  useEffect(() => {
    if (activeId && detail.isError) {
      setStudioActive(null);
      addToast({ type: 'info', title: 'You are no longer in that session' });
    }
  }, [activeId, detail.isError, addToast]);

  const enter = (s: SessionDetail) => {
    qc.setQueryData(['studio-session', s.id], s);
    setStudioActive({ id: s.id, docIds: s.documents.map((x) => x.id) });
  };
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      addToast({ type: 'error', title: errText(e) });
    } finally {
      setBusy(false);
    }
  };

  const start = () =>
    run(async () => {
      const s = await apiPost<SessionDetail>('/v1/takeoff/studio/sessions/', {
        name: name.trim() || 'Session',
        document_ids: Array.from(picked),
        invite: splitEmails(inviteText),
        open_join: openJoin,
      });
      enter(s);
      setStarting(false);
      setInviteText('');
      addToast({ type: 'success', title: `Session started - ID ${s.code}`, message: inviteSummary(s.invites) || undefined });
    });
  const joinByCode = () =>
    run(async () => {
      const s = await apiPost<SessionDetail>('/v1/takeoff/studio/sessions/join/', { code });
      enter(s);
      setCode('');
      if (s.documents[0]) onOpenDocument(s.documents[0]);
    });
  const openRow = (r: SessionRow) =>
    run(async () => {
      const s =
        r.status === 'active' && r.my_status !== 'joined'
          ? await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${r.id}/join/`)
          : await apiGet<SessionDetail>(`/v1/takeoff/studio/sessions/${r.id}/`);
      enter(s);
    });

  // ── in-session actions ──
  const [inviteMore, setInviteMore] = useState('');
  const [chat, setChat] = useState('');
  const chatEnd = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ block: 'end' });
  }, [messages.data?.messages.length]);
  const refresh = (s?: SessionDetail) => {
    if (s) qc.setQueryData(['studio-session', s.id], s);
    else void qc.invalidateQueries({ queryKey: ['studio-session', activeId] });
  };
  const invite = () =>
    run(async () => {
      const emails = splitEmails(inviteMore);
      if (!emails.length) throw new Error('Type one or more email addresses');
      const r = await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/invite/`, { emails });
      refresh(r);
      setInviteMore('');
      addToast({ type: 'success', title: inviteSummary(r.invites) || 'Invited' });
    });
  const addCurrent = () =>
    run(async () => {
      if (!currentDocument) return;
      refresh(await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/`, { document_ids: [currentDocument.id] }));
    });
  const removeDoc = (id: string) =>
    run(async () => refresh(await apiDelete<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/${id}/`)));
  const removePerson = (a: Attendee) =>
    run(async () => {
      if (!window.confirm(`Remove ${label(a)} from the session?`)) return;
      refresh(await apiDelete<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/attendees/${a.id}/`));
    });
  const toggleOpen = () =>
    run(async () => refresh(await apiPatch<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/`, { open_join: !d?.open_join })));
  const send = () =>
    run(async () => {
      const text = chat.trim();
      if (!text) return;
      const r = await apiPost<{ messages: Message[] }>(`/v1/takeoff/studio/sessions/${activeId}/messages/`, { text });
      qc.setQueryData(['studio-messages', activeId], r);
      setChat('');
    });
  const leave = () =>
    run(async () => {
      if (!window.confirm('Leave this session? You can join again with its ID while it runs.')) return;
      await apiPost(`/v1/takeoff/studio/sessions/${activeId}/leave/`);
      setStudioActive(null);
      void qc.invalidateQueries({ queryKey: ['studio-sessions'] });
    });
  const finish = () =>
    run(async () => {
      if (!window.confirm('Finish the session for everyone? People who only had access through it lose access to its PDFs.')) return;
      const r = await apiPost<SessionDetail & { report: Report }>(`/v1/takeoff/studio/sessions/${activeId}/finish/`);
      refresh(r);
      qc.setQueryData(['studio-report', activeId], r.report);
      addToast({ type: 'success', title: 'Session finished', message: 'The report is ready below.' });
    });
  const downloadReport = () => {
    if (!d || !report.data) return;
    const blob = new Blob([reportCsv(d, report.data)], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${d.name.replace(/[^\w\- ]+/g, '').trim() || 'session'} report.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const downloadReportPdf = () =>
    run(async () => {
      if (!d || !report.data) return;
      const bytes = await reportPdf(d, report.data);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([bytes as unknown as BlobPart], { type: 'application/pdf' }));
      a.download = `${d.name.replace(/[^\w\- ]+/g, '').trim() || 'session'} report.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
  const copyId = () => {
    if (!d) return;
    void navigator.clipboard?.writeText(d.code).then(
      () => addToast({ type: 'success', title: `Session ID ${d.code} copied` }),
      () => undefined,
    );
  };

  const section = 'px-2 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wide text-content-tertiary';
  const input = 'w-full rounded border border-border bg-surface-primary px-2 py-1 text-[12px] outline-none focus:border-oe-blue';
  const btn = 'rounded px-2 py-1 text-[11px] font-semibold disabled:opacity-50';

  // ───────────────────────── lobby ─────────────────────────
  if (!activeId) {
    const rows = sessions.data?.sessions ?? [];
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto text-[12px]" data-testid="studio-panel">
        <div className={section}>Studio</div>
        <p className="px-2 pb-2 text-[11px] text-content-secondary">
          Work on the same PDFs with other people at the same time. Everyone sees each other's markups within seconds.
        </p>
        {!starting ? (
          <div className="px-2">
            <button type="button" className={clsx(btn, 'w-full bg-oe-blue py-1.5 text-white')} onClick={() => setStarting(true)} data-testid="studio-start-open">
              Start a session
            </button>
          </div>
        ) : (
          <div className="mx-2 space-y-2 rounded border border-border p-2" data-testid="studio-start-form">
            <label className="block text-[11px] text-content-secondary">
              Session name
              <input className={input} value={name} onChange={(e) => setName(e.target.value)} data-testid="studio-name" />
            </label>
            <div className="text-[11px] text-content-secondary">PDFs in the session</div>
            {serverTabs.length === 0 && <div className="text-[11px] text-content-tertiary">Open a project PDF first.</div>}
            {serverTabs.map((t) => (
              <label key={t.id} className="flex items-center gap-1.5 text-[12px]">
                <input
                  type="checkbox"
                  checked={picked.has(t.id)}
                  onChange={(e) => setPicked((p) => { const n = new Set(p); if (e.target.checked) n.add(t.id); else n.delete(t.id); return n; })}
                  data-testid="studio-pick-doc"
                />
                <span className="truncate">{t.name}</span>
              </label>
            ))}
            <label className="block text-[11px] text-content-secondary">
              Invite (emails, separated by commas)
              <textarea className={clsx(input, 'h-14 resize-none')} value={inviteText} onChange={(e) => setInviteText(e.target.value)} placeholder="name@company.com, ..." data-testid="studio-invite-emails" />
            </label>
            <label className="flex items-center gap-1.5 text-[11px] text-content-secondary">
              <input type="checkbox" checked={openJoin} onChange={(e) => setOpenJoin(e.target.checked)} />
              Anyone signed in who has the session ID may join
            </label>
            <div className="flex justify-end gap-1.5">
              <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setStarting(false)}>Cancel</button>
              <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || picked.size === 0} onClick={start} data-testid="studio-start">
                Start
              </button>
            </div>
          </div>
        )}
        <div className={section}>Join with a session ID</div>
        <div className="flex gap-1.5 px-2">
          <input className={input} value={code} onChange={(e) => setCode(e.target.value)} placeholder="123-456-789" onKeyDown={(e) => { if (e.key === 'Enter') joinByCode(); }} data-testid="studio-code" />
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || code.replace(/\D/g, '').length !== 9} onClick={joinByCode} data-testid="studio-join">
            Join
          </button>
        </div>
        <div className={section}>My sessions</div>
        {rows.length === 0 && <div className="px-2 text-[11px] text-content-tertiary">No sessions yet.</div>}
        {rows.map((r) => (
          <button key={r.id} type="button" onClick={() => openRow(r)} className="flex w-full items-center gap-2 px-2 py-1.5 text-left hover:bg-surface-secondary" data-testid="studio-session-row">
            <span className={clsx('h-2 w-2 shrink-0 rounded-full', r.status === 'active' ? 'bg-emerald-500' : 'bg-content-tertiary')} />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{r.name}</span>
              <span className="block text-[10px] text-content-tertiary">
                {r.code} · {r.status === 'active' ? (r.my_status === 'invited' ? 'invited - click to join' : r.role === 'host' ? 'you host' : 'active') : 'finished'} · {timeOf(r.created_at)}
              </span>
            </span>
          </button>
        ))}
      </div>
    );
  }

  // ───────────────────────── in a session ─────────────────────────
  if (!d) {
    return <div className="p-3 text-[12px] text-content-tertiary" data-testid="studio-panel">Loading session…</div>;
  }
  const host = d.me.role === 'host';
  const counts = new Map((report.data?.people ?? []).map((p) => [p.user_id, p.count]));
  const docName = new Map(d.documents.map((x) => [x.id, x.name]));
  const curInSession = !!currentDocument && d.documents.some((x) => x.id === currentDocument.id);
  const canAddCurrent = live && !!currentDocument && !curInSession && !currentDocument.id.startsWith('local:') && !currentDocument.id.startsWith('temp-');
  const sortedPeople = [...d.attendees].sort((a, b) => Number(b.online) - Number(a.online) || (a.role === 'host' ? -1 : 1));
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto text-[12px]" data-testid="studio-panel">
      <div className="border-b border-border px-2 py-2" data-testid="studio-session">
        <div className="flex items-center gap-1.5">
          <span className={clsx('h-2 w-2 shrink-0 rounded-full', live ? 'bg-emerald-500' : 'bg-content-tertiary')} />
          <span className="min-w-0 flex-1 truncate text-[13px] font-semibold" title={d.name}>{d.name}</span>
          <button type="button" className="text-[10px] text-content-tertiary hover:text-content-primary" title="Back to the session list (you stay in it)" onClick={() => setStudioActive(null)} data-testid="studio-back">
            Sessions
          </button>
        </div>
        <div className="mt-1 flex items-center gap-1.5 text-[11px] text-content-secondary">
          ID <span className="font-mono text-content-primary" data-testid="studio-code-shown">{d.code}</span>
          <button type="button" onClick={copyId} title="Copy the session ID" className="rounded p-0.5 hover:bg-surface-secondary"><Copy size={11} /></button>
          <span className="ml-auto">{live ? (host ? 'You host' : 'Attendee') : `Finished ${timeOf(d.finished_at)}`}</span>
        </div>
        {live && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {host ? (
              <>
                <label className="flex items-center gap-1 text-[10px] text-content-secondary" title="Off: only invited people can join">
                  <input type="checkbox" checked={d.open_join} onChange={toggleOpen} /> Anyone with the ID can join
                </label>
                <button type="button" className={clsx(btn, 'ml-auto bg-red-600 text-white')} onClick={finish} disabled={busy} data-testid="studio-finish">
                  Finish session
                </button>
              </>
            ) : (
              <button type="button" className={clsx(btn, 'ml-auto flex items-center gap-1 border border-border')} onClick={leave} disabled={busy} data-testid="studio-leave">
                <LogOut size={11} /> Leave
              </button>
            )}
          </div>
        )}
      </div>

      <div className={section}>PDFs ({d.documents.length})</div>
      {d.documents.map((doc) => {
        const here = d.attendees.filter((a) => a.online && a.document_id === doc.id && a.user_id !== me);
        return (
          <div key={doc.id} className={clsx('group flex items-center gap-1.5 px-2 py-1 hover:bg-surface-secondary', currentDocument?.id === doc.id && 'bg-oe-blue/10')}>
            <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onOpenDocument(doc)} title="Open this PDF" data-testid="studio-doc">
              <span className="block truncate">{doc.name}</span>
              {doc.project_name && <span className="block truncate text-[10px] text-content-tertiary">{doc.project_name}</span>}
            </button>
            <span className="flex -space-x-1">
              {here.slice(0, 3).map((a) => (
                <span key={a.id} title={`${label(a)} is here (page ${a.page ?? 1})`} className="flex h-4 w-4 items-center justify-center rounded-full border border-black/30 bg-emerald-600 text-[8px] font-bold text-white">
                  {initials(a)}
                </span>
              ))}
            </span>
            {host && live && (
              <button type="button" className="hidden rounded p-0.5 text-content-tertiary hover:text-red-500 group-hover:block" title="Take this PDF out of the session" onClick={() => removeDoc(doc.id)}>
                <X size={11} />
              </button>
            )}
          </div>
        );
      })}
      {canAddCurrent && (
        <div className="px-2 pt-1">
          <button type="button" className={clsx(btn, 'flex items-center gap-1 border border-border')} onClick={addCurrent} disabled={busy} data-testid="studio-add-current">
            <Plus size={11} /> Add “{currentDocument!.name}”
          </button>
        </div>
      )}

      <div className={section}>People ({d.attendees.filter((a) => a.status === 'joined').length} in · {d.attendees.filter((a) => a.online).length} online)</div>
      {sortedPeople.map((a) => (
        <div key={a.id} className="group flex items-center gap-2 px-2 py-1" data-testid="studio-person">
          <span className={clsx('relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white', a.status === 'joined' ? 'bg-oe-blue' : 'bg-content-tertiary')}>
            {initials(a)}
            <span className={clsx('absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface-primary', a.online ? 'bg-emerald-500' : 'bg-neutral-400')} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate">
              {label(a)}
              {a.user_id === me && ' (you)'}
              {a.role === 'host' && <span className="ml-1 rounded bg-amber-500/20 px-1 text-[9px] font-semibold text-amber-600">HOST</span>}
            </span>
            <span className="block truncate text-[10px] text-content-tertiary">
              {a.status === 'invited' ? 'invited, not joined yet' : a.status === 'left' ? 'left' : a.online ? `on ${docName.get(a.document_id ?? '') ?? 'a PDF'} · page ${a.page ?? 1}` : 'offline'}
            </span>
          </span>
          {a.user_id && (counts.get(a.user_id) ?? 0) > 0 && (
            <span className="rounded bg-surface-secondary px-1 text-[10px] text-content-secondary" title="Markups made in this session">{counts.get(a.user_id)}</span>
          )}
          {host && live && a.role !== 'host' && (
            <button type="button" className="hidden rounded p-0.5 text-content-tertiary hover:text-red-500 group-hover:block" title="Remove from the session" onClick={() => removePerson(a)}>
              <X size={11} />
            </button>
          )}
        </div>
      ))}
      {live && (
        <div className="flex gap-1.5 px-2 pt-1">
          <input className={input} value={inviteMore} onChange={(e) => setInviteMore(e.target.value)} placeholder="Invite by email…" onKeyDown={(e) => { if (e.key === 'Enter') invite(); }} data-testid="studio-invite-more" />
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={invite} disabled={busy} data-testid="studio-invite">
            Invite
          </button>
        </div>
      )}

      <div className={clsx(section, 'flex items-center')}>
        Report
        <span className="ml-auto normal-case tracking-normal">{report.data ? `${report.data.total} markups` : ''}</span>
      </div>
      <div className="px-2" data-testid="studio-report">
        {(report.data?.people ?? []).map((p) => (
          <div key={p.user_id} className="flex justify-between text-[11px]">
            <span className="truncate">{label(p)}</span>
            <span className="text-content-secondary">{Object.entries(p.by_type).map(([t, n]) => `${n} ${t}`).join(', ')}</span>
          </div>
        ))}
        {report.data && report.data.total === 0 && <div className="text-[11px] text-content-tertiary">No markups yet in this session.</div>}
        <div className="mt-1 flex gap-1.5">
          <button type="button" className={clsx(btn, 'border border-border')} onClick={downloadReportPdf} disabled={!report.data || busy} data-testid="studio-report-pdf">
            Report (PDF)
          </button>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={downloadReport} disabled={!report.data} data-testid="studio-report-csv">
            Report (CSV)
          </button>
        </div>
      </div>

      <div className={section}>Chat</div>
      <div className="min-h-[80px] space-y-1.5 px-2" data-testid="studio-chat">
        {(messages.data?.messages ?? []).map((m) => (
          <div key={m.id} className={clsx('rounded px-2 py-1', m.user_id === me ? 'bg-oe-blue/10' : 'bg-surface-secondary')}>
            <div className="flex justify-between text-[10px] text-content-tertiary">
              <span className="font-semibold text-content-secondary">{m.user_id === me ? 'You' : m.name || 'Someone'}</span>
              <span>{timeOf(m.at)}</span>
            </div>
            <div className="whitespace-pre-wrap break-words">{m.text}</div>
          </div>
        ))}
        {(messages.data?.messages.length ?? 0) === 0 && <div className="text-[11px] text-content-tertiary">No messages yet.</div>}
        <div ref={chatEnd} />
      </div>
      {live && (
        <div className="sticky bottom-0 flex gap-1.5 border-t border-border bg-surface-primary p-2">
          <input className={input} value={chat} onChange={(e) => setChat(e.target.value)} placeholder="Message everyone in the session…" onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} data-testid="studio-chat-input" />
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={send} disabled={busy || !chat.trim()} data-testid="studio-chat-send" aria-label="Send">
            <Send size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
