// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * Studio panel (left rail > Studio): working sessions for several people,
 * all in one list - each session folds open in place to show its folders
 * and PDFs (upload files or whole folders, drag PDFs between folders), its
 * people (every FSFTM account, invite with one click) and its chat.
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
import { useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import {
  ChevronDown,
  ChevronRight,
  CircleStop,
  Copy,
  FilePlus,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  FolderUp,
  LogIn,
  LogOut,
  Plus,
  RefreshCw,
  Search,
  Send,
  Upload,
  UserPlus,
  X,
} from 'lucide-react';
import { apiDelete, apiGet, apiPatch, apiPost } from '@/shared/lib/api';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { setShared, useSharedState } from '../data/shared-state';
import { highlightMentions, mentionedIn, personLabel, useMentionComposer } from './mentions';

/** Shared key: the session this browser is working in ({ id, docIds }). */
export const STUDIO_ACTIVE_KEY = 'studio.active';
const ACTIVE_STORE = 'takeoff.studio.active';

export type StudioActive = { id: string; docIds: string[] } | null;
export type StudioDoc = { id: string; name: string; pages?: number | null; project_id: string | null; project_name: string; folder?: string };
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
  project_id?: string | null;
  project_name?: string;
  folders?: string[];
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

type Person = { id: string; name: string; email: string };
type UploadItem = { file: File; rel: string };

const DOC_DND = 'application/x-studio-doc';
const thumbCache = new Map<string, string>();

/** Page 1 of a PDF as a small picture (fetched with the sign-in token). */
function Thumb({ id }: { id: string }) {
  const [src, setSrc] = useState<string | null>(thumbCache.get(id) ?? null);
  useEffect(() => {
    if (src) return;
    let gone = false;
    const token = useAuthStore.getState().accessToken;
    fetch(`/api/v1/takeoff/documents/${encodeURIComponent(id)}/thumbnail/1/?w=96`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => {
        if (!b || gone) return;
        const u = URL.createObjectURL(b);
        thumbCache.set(id, u);
        setSrc(u);
      })
      .catch(() => undefined);
    return () => { gone = true; };
  }, [id, src]);
  return (
    <span className="flex h-9 w-7 shrink-0 items-center justify-center overflow-hidden rounded-sm border border-border bg-white">
      {src ? <img src={src} alt="" className="h-full w-full object-contain" /> : <FileText size={14} className="text-neutral-400" />}
    </span>
  );
}

/** Files (and whole folders) dropped from the computer, with their paths. */
async function filesFromDrop(dt: DataTransfer): Promise<UploadItem[]> {
  type Entry = { isFile: boolean; isDirectory: boolean; name: string; fullPath: string; file?: (cb: (f: File) => void, err: () => void) => void; createReader?: () => { readEntries: (cb: (e: Entry[]) => void, err: () => void) => void } };
  const entries = Array.from(dt.items ?? [])
    .map((it) => (it as unknown as { webkitGetAsEntry?: () => Entry | null }).webkitGetAsEntry?.() ?? null)
    .filter((e): e is Entry => !!e);
  if (!entries.length) return Array.from(dt.files ?? []).map((f) => ({ file: f, rel: f.name }));
  const out: UploadItem[] = [];
  const walk = async (e: Entry): Promise<void> => {
    if (e.isFile && e.file) {
      const f = await new Promise<File | null>((res) => e.file!(res, () => res(null)));
      if (f) out.push({ file: f, rel: e.fullPath.replace(/^\//, '') });
    } else if (e.isDirectory && e.createReader) {
      const reader = e.createReader();
      for (;;) {
        const batch = await new Promise<Entry[]>((res) => reader.readEntries(res, () => res([])));
        if (!batch.length) break;
        for (const c of batch) await walk(c);
      }
    }
  };
  for (const e of entries) await walk(e);
  return out;
}

const parentOf = (rel: string) => rel.split('/').slice(0, -1).join('/');
const joinPath = (a: string, b: string) => [a, b].filter(Boolean).join('/');

export function StudioPanel({
  currentDocument,
  openDocuments,
  projectId,
  onOpenDocument,
}: {
  /** The PDF open in the focused pane (server id), if any. */
  currentDocument: { id: string; name: string } | null;
  /** PDFs open as tabs, offered when starting a session. */
  openDocuments: { id: string; name: string }[];
  /** The project open in PDF Measurements: new sessions keep uploads there. */
  projectId?: string | null;
  /** Open a session PDF (switches project when it belongs to another one).
   *  ``again`` re-opens the PDF already open (its project changed). */
  onOpenDocument: (doc: StudioDoc, again?: boolean) => void;
}) {
  const me = useAuthStore((s) => s.userId);
  const myEmail = useAuthStore((s) => s.userEmail);
  const addToast = useToastStore((s) => s.addToast);
  const qc = useQueryClient();
  const [active] = useSharedState<StudioActive>(STUDIO_ACTIVE_KEY, readStoredStudio);
  const activeId = active?.id ?? null;
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState('');
  const [menu, setMenu] = useState<'plus' | 'add' | 'actions' | null>(null);
  const [dialog, setDialog] = useState<'new' | 'join' | 'invite' | 'upload' | 'folder' | 'project' | null>(null);
  const [projPicked, setProjPicked] = useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [dropFolder, setDropFolder] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(true);

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

  // ── data ──
  const sessions = useQuery({
    queryKey: ['studio-sessions'],
    queryFn: () => apiGet<{ sessions: SessionRow[] }>('/v1/takeoff/studio/sessions/'),
    refetchInterval: 20000,
  });
  const people = useQuery({
    queryKey: ['takeoff-people'],
    queryFn: () => apiGet<{ people: Person[] }>('/v1/takeoff/people/'),
    staleTime: 5 * 60_000,
  });
  const detail = useQuery({
    queryKey: ['studio-session', activeId],
    queryFn: () => apiGet<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/`),
    enabled: !!activeId,
    refetchInterval: 5000,
    retry: 1,
  });
  const d = detail.data && detail.data.id === activeId ? detail.data : undefined;
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
    if (!activeId || !d || d.status !== 'active') return;
    if ((active?.docIds ?? []).join(',') !== docKey) setStudioActive({ id: activeId, docIds: docKey ? docKey.split(',') : [] });
  }, [activeId, d, docKey, active]);
  useEffect(() => {
    if (!d || !currentDocument) return;
    const cur = d.documents.find((x) => x.id === currentDocument.id);
    if (cur?.project_id && cur.project_id !== projectId) onOpenDocument(cur, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d?.documents, currentDocument?.id, projectId]);
  useEffect(() => {
    if (activeId && detail.isError) {
      setStudioActive(null);
      addToast({ type: 'info', title: 'You are no longer in that session' });
    }
  }, [activeId, detail.isError, addToast]);

  const enter = (s: SessionDetail) => {
    qc.setQueryData(['studio-session', s.id], s);
    setStudioActive({ id: s.id, docIds: s.documents.map((x) => x.id) });
    void qc.invalidateQueries({ queryKey: ['studio-sessions'] });
  };
  const refresh = (s?: SessionDetail) => {
    if (s) qc.setQueryData(['studio-session', s.id], s);
    else void qc.invalidateQueries({ queryKey: ['studio-session', activeId] });
  };
  const openRow = (r: SessionRow) =>
    run(async () => {
      if (r.id === activeId) {
        setStudioActive(null); // click the open one again: fold it up
        return;
      }
      const s =
        r.status === 'active' && r.my_status !== 'joined'
          ? await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${r.id}/join/`)
          : await apiGet<SessionDetail>(`/v1/takeoff/studio/sessions/${r.id}/`);
      enter(s);
    });

  // ── new session / join / invite ──
  const [name, setName] = useState('');
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [who, setWho] = useState<Set<string>>(new Set());
  const [extraEmails, setExtraEmails] = useState('');
  const [openJoin, setOpenJoin] = useState(false);
  const [code, setCode] = useState('');
  const [peopleFilter, setPeopleFilter] = useState('');
  const serverTabs = useMemo(() => {
    const list = [...openDocuments];
    if (currentDocument && !list.some((x) => x.id === currentDocument.id)) list.unshift(currentDocument);
    return list.filter((x) => !x.id.startsWith('local:') && !x.id.startsWith('temp-') && x.id !== '__local');
  }, [openDocuments, currentDocument]);
  const openNew = () => {
    setName(`${(currentDocument?.name || 'Takeoff').replace(/\.pdf$/i, '')} session`);
    setPicked(new Set(currentDocument ? [currentDocument.id] : []));
    setWho(new Set());
    setExtraEmails('');
    setOpenJoin(false);
    setPeopleFilter('');
    setDialog('new');
  };
  const chosenEmails = () => [
    ...(people.data?.people ?? []).filter((p) => who.has(p.id)).map((p) => p.email),
    ...splitEmails(extraEmails),
  ];
  const start = () =>
    run(async () => {
      const s = await apiPost<SessionDetail>('/v1/takeoff/studio/sessions/', {
        name: name.trim() || 'Session',
        document_ids: Array.from(picked),
        invite: chosenEmails(),
        open_join: openJoin,
        project_id: projectId || null,
      });
      enter(s);
      setDialog(null);
      addToast({ type: 'success', title: `Session started - ID ${s.code}`, message: inviteSummary(s.invites) || undefined });
    });
  const joinByCode = () =>
    run(async () => {
      const s = await apiPost<SessionDetail>('/v1/takeoff/studio/sessions/join/', { code });
      enter(s);
      setCode('');
      setDialog(null);
      if (s.documents[0]) onOpenDocument(s.documents[0]);
    });
  const invite = (emails: string[]) =>
    run(async () => {
      if (!emails.length) throw new Error('Pick people or type email addresses');
      const r = await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/invite/`, { emails });
      refresh(r);
      setDialog(null);
      addToast({ type: 'success', title: inviteSummary(r.invites) || 'Invited' });
    });

  // ── files and folders ──
  const homeProject = d?.project_id || d?.documents[0]?.project_id || projectId || null;
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [uploadTo, setUploadTo] = useState('');
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [newFolder, setNewFolder] = useState('');
  const filePick = useRef<HTMLInputElement | null>(null);
  const folderPick = useRef<HTMLInputElement | null>(null);
  const openUpload = (folder: string, items: UploadItem[] = []) => {
    setUploadTo(folder);
    setUploads(items);
    setDialog('upload');
  };
  const doUpload = (items: UploadItem[], base: string) =>
    run(async () => {
      if (!activeId) return;
      if (!homeProject) throw new Error('Open a project first - the files are kept in a project');
      const pdfs = items.filter((u) => /\.pdf$/i.test(u.file.name));
      const skipped = items.length - pdfs.length;
      if (!pdfs.length) throw new Error('Only PDF files can be added');
      const token = useAuthStore.getState().accessToken;
      const byFolder = new Map<string, string[]>();
      setProgress({ done: 0, total: pdfs.length });
      for (const [i, u] of pdfs.entries()) {
        const fd = new FormData();
        fd.append('file', u.file);
        const res = await fetch(`/api/v1/takeoff/documents/upload/?project_id=${encodeURIComponent(homeProject)}`, {
          method: 'POST',
          body: fd,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) {
          const msg = await res.json().then((j: { detail?: string }) => j.detail).catch(() => null);
          throw new Error(`${u.file.name}: ${msg || `upload failed (${res.status})`}`);
        }
        const row = (await res.json()) as { id: string };
        const folder = joinPath(base, parentOf(u.rel));
        byFolder.set(folder, [...(byFolder.get(folder) ?? []), row.id]);
        setProgress({ done: i + 1, total: pdfs.length });
      }
      let last: SessionDetail | null = null;
      for (const [folder, ids] of byFolder) {
        last = await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/`, { document_ids: ids, folder });
      }
      if (last) refresh(last);
      setDialog(null);
      setUploads([]);
      addToast({ type: 'success', title: `${pdfs.length} PDF${pdfs.length === 1 ? '' : 's'} added`, message: skipped ? `${skipped} non-PDF file(s) skipped` : undefined });
    }).finally(() => setProgress(null));
  const addFolder = () =>
    run(async () => {
      const path = joinPath(uploadTo, newFolder.trim());
      if (!newFolder.trim()) throw new Error('Give the folder a name');
      refresh(await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/folders/`, { path }));
      setNewFolder('');
      setDialog(null);
    });
  const removeFolder = (path: string) =>
    run(async () => {
      refresh(await apiDelete<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/folders/?path=${encodeURIComponent(path)}`));
    });
  const moveDoc = (docId: string, folder: string) =>
    run(async () => {
      refresh(await apiPatch<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/${docId}/`, { path: folder || '/' }));
    });
  const listProject = projectId || d?.project_id || null;
  const projectDocs = useQuery({
    queryKey: ['studio-project-docs', listProject],
    queryFn: () => apiGet<{ id: string; filename: string; pages?: number }[]>(`/v1/takeoff/documents/?project_id=${encodeURIComponent(listProject!)}`),
    enabled: dialog === 'project' && !!listProject,
  });
  const addFromProject = () =>
    run(async () => {
      if (!projPicked.size) throw new Error('Pick one or more PDFs');
      refresh(await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/`, { document_ids: Array.from(projPicked), folder: uploadTo }));
      setDialog(null);
    });
  const addCurrent = () =>
    run(async () => {
      if (!currentDocument) return;
      refresh(await apiPost<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/`, { document_ids: [currentDocument.id], folder: '' }));
    });
  const removeDoc = (id: string) =>
    run(async () => refresh(await apiDelete<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/documents/${id}/`)));
  const onDropFiles = (e: DragEvent, folder: string) => {
    setDropFolder(null);
    const docId = e.dataTransfer.getData(DOC_DND);
    e.preventDefault();
    e.stopPropagation();
    if (docId) {
      moveDoc(docId, folder);
      return;
    }
    if (!e.dataTransfer.types.includes('Files')) return;
    void filesFromDrop(e.dataTransfer).then((items) => { if (items.length) doUpload(items, folder); });
  };
  const dragOver = (e: DragEvent, folder: string) => {
    if (!live) return;
    if (!e.dataTransfer.types.includes('Files') && !e.dataTransfer.types.includes(DOC_DND)) return;
    e.preventDefault();
    e.stopPropagation();
    if (dropFolder !== folder) setDropFolder(folder);
  };

  // ── people / session actions ──
  const removePerson = (a: Attendee) =>
    run(async () => {
      if (!window.confirm(`Remove ${label(a)} from the session?`)) return;
      refresh(await apiDelete<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/attendees/${a.id}/`));
    });
  const toggleOpen = () =>
    run(async () => refresh(await apiPatch<SessionDetail>(`/v1/takeoff/studio/sessions/${activeId}/`, { open_join: !d?.open_join })));
  const chatComposer = useMentionComposer(people.data?.people ?? [], me);
  const chat = chatComposer.text;
  const chatEnd = useRef<HTMLDivElement | null>(null);
  useEffect(() => { chatEnd.current?.scrollIntoView({ block: 'nearest' }); }, [messages.data?.messages.length]);
  const send = () =>
    run(async () => {
      const text = chat.trim();
      if (!text) return;
      const mentions = mentionedIn(text, chatComposer.others).map((p) => p.id);
      const r = await apiPost<{ messages: Message[] }>(`/v1/takeoff/studio/sessions/${activeId}/messages/`, { text, mentions });
      qc.setQueryData(['studio-messages', activeId], r);
      chatComposer.reset();
      if (mentions.length) addToast({ type: 'success', title: `${mentions.length} ${mentions.length === 1 ? 'person' : 'people'} notified` });
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
      void qc.invalidateQueries({ queryKey: ['studio-sessions'] });
      addToast({ type: 'success', title: 'Session finished', message: 'The report is in Actions.' });
    });
  const save = (blob: Blob, ext: string) => {
    if (!d) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${d.name.replace(/[^\w\- ]+/g, '').trim() || 'session'} report.${ext}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const downloadReport = () => { if (d && report.data) save(new Blob([reportCsv(d, report.data)], { type: 'text/csv' }), 'csv'); };
  const downloadReportPdf = () =>
    run(async () => {
      if (!d || !report.data) return;
      const bytes = await reportPdf(d, report.data);
      save(new Blob([bytes as unknown as BlobPart], { type: 'application/pdf' }), 'pdf');
    });
  const shareId = () => {
    if (!d) return;
    const msg = `Join my PDF Measurements session "${d.name}": open PDF Measurements > Studio > Join with ID, and enter ${d.code}`;
    void navigator.clipboard?.writeText(msg).then(() => addToast({ type: 'success', title: 'Invite text copied', message: msg }), () => undefined);
  };
  const copyId = () => {
    if (!d) return;
    void navigator.clipboard?.writeText(d.code).then(() => addToast({ type: 'success', title: `Session ID ${d.code} copied` }), () => undefined);
  };

  // ── render helpers ──
  const input = 'w-full rounded border border-border bg-surface-primary px-2 py-1 text-[12px] outline-none focus:border-oe-blue';
  const btn = 'rounded px-2 py-1 text-[11px] font-semibold disabled:opacity-50';
  const menuItem = 'flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] hover:bg-surface-secondary disabled:opacity-40';
  const rows = (sessions.data?.sessions ?? []).filter((r) => {
    const q = search.trim().toLowerCase();
    return !q || r.name.toLowerCase().includes(q) || r.code.replace(/-/g, '').includes(q.replace(/-/g, ''));
  });
  const host = d?.me.role === 'host';
  const counts = new Map((report.data?.people ?? []).map((p) => [p.user_id, p.count]));
  const docName = new Map((d?.documents ?? []).map((x) => [x.id, x.name]));
  const canAddCurrent = !!d && live && !!currentDocument && !d.documents.some((x) => x.id === currentDocument.id) && !currentDocument.id.startsWith('local:') && !currentDocument.id.startsWith('temp-');
  const folders = d?.folders ?? [];
  const childFolders = (parent: string) =>
    folders.filter((f) => parentOf(f) === parent).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  const docsIn = (folder: string) => (d?.documents ?? []).filter((x) => (x.folder || '') === folder);
  const countUnder = (folder: string) => (d?.documents ?? []).filter((x) => (x.folder || '') === folder || (x.folder || '').startsWith(`${folder}/`)).length;
  const peopleRows = useMemo(() => {
    const att = d?.attendees ?? [];
    const inSession = new Map(att.filter((a) => a.user_id).map((a) => [a.user_id!, a]));
    const others = (people.data?.people ?? []).filter((p) => !inSession.has(p.id) && !att.some((a) => a.email === p.email.toLowerCase()));
    const sorted = [...att].sort((a, b) => Number(b.online) - Number(a.online) || (a.role === 'host' ? -1 : b.role === 'host' ? 1 : 0));
    return { att: sorted, others };
  }, [d, people.data]);

  const docRow = (x: StudioDoc, depth: number) => {
    const here = (d?.attendees ?? []).filter((a) => a.online && a.document_id === x.id && a.user_id !== me);
    return (
      <div
        key={x.id}
        draggable={live}
        onDragStart={(e) => { e.dataTransfer.setData(DOC_DND, x.id); e.dataTransfer.effectAllowed = 'move'; }}
        className={clsx('group flex items-center gap-1.5 py-0.5 pr-1.5 hover:bg-surface-secondary', currentDocument?.id === x.id && 'bg-oe-blue/10')}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        <button type="button" className="flex min-w-0 flex-1 items-center gap-1.5 text-left" onClick={() => { if (x.id !== currentDocument?.id) onOpenDocument(x); }} title={`Open ${x.name}`} data-testid="studio-doc">
          <Thumb id={x.id} />
          <span className="min-w-0">
            <span className="block truncate text-[12px]">{x.name}</span>
            <span className="block truncate text-[10px] text-content-tertiary">{x.pages ? `${x.pages} page${x.pages === 1 ? '' : 's'}` : ''}{x.project_name ? ` · ${x.project_name}` : ''}</span>
          </span>
        </button>
        <span className="flex -space-x-1">
          {here.slice(0, 3).map((a) => (
            <span key={a.id} title={`${label(a)} is here (page ${a.page ?? 1})`} className="flex h-4 w-4 items-center justify-center rounded-full border border-black/30 bg-emerald-600 text-[8px] font-bold text-white">
              {initials(a)}
            </span>
          ))}
        </span>
        {host && live && (
          <button type="button" className="hidden rounded p-0.5 text-content-tertiary hover:text-red-500 group-hover:block" title="Take this PDF out of the session" onClick={() => removeDoc(x.id)}>
            <X size={11} />
          </button>
        )}
      </div>
    );
  };
  const folderBlock = (path: string, depth: number): ReactNode => {
    const open = !collapsed.has(path);
    return (
      <div key={path}>
        <div
          className={clsx('group flex items-center gap-1 py-1 pr-1.5 hover:bg-surface-secondary', dropFolder === path && 'bg-oe-blue/20 ring-1 ring-oe-blue')}
          style={{ paddingLeft: 4 + depth * 14 }}
          onDragOver={(e) => dragOver(e, path)}
          onDragLeave={() => setDropFolder(null)}
          onDrop={(e) => onDropFiles(e, path)}
          data-testid="studio-folder"
        >
          <button type="button" className="flex min-w-0 flex-1 items-center gap-1 text-left" onClick={() => setCollapsed((c) => { const n = new Set(c); if (n.has(path)) n.delete(path); else n.add(path); return n; })}>
            {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {open ? <FolderOpen size={14} className="text-amber-500" /> : <Folder size={14} className="text-amber-500" />}
            <span className="truncate text-[12px]">{path.split('/').pop()}</span>
            <span className="text-[10px] text-content-tertiary">{countUnder(path)}</span>
          </button>
          {live && (
            <span className="hidden items-center gap-0.5 group-hover:flex">
              <button type="button" title="Upload files into this folder" className="rounded p-0.5 hover:bg-surface-tertiary" onClick={() => openUpload(path)}><Upload size={11} /></button>
              <button type="button" title="New folder inside" className="rounded p-0.5 hover:bg-surface-tertiary" onClick={() => { setUploadTo(path); setNewFolder(''); setDialog('folder'); }}><FolderPlus size={11} /></button>
              {host && countUnder(path) === 0 && <button type="button" title="Delete this empty folder" className="rounded p-0.5 hover:text-red-500" onClick={() => removeFolder(path)}><X size={11} /></button>}
            </span>
          )}
        </div>
        {open && (
          <>
            {childFolders(path).map((f) => folderBlock(f, depth + 1))}
            {docsIn(path).map((x) => docRow(x, depth + 1))}
          </>
        )}
      </div>
    );
  };

  // ── people picker (new session / invite) ──
  const pickerPeople = (exclude: Set<string>) =>
    (people.data?.people ?? [])
      .filter((p) => p.id !== me && !exclude.has(p.id))
      .filter((p) => { const q = peopleFilter.trim().toLowerCase(); return !q || p.name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q); });
  const peoplePicker = (exclude: Set<string>) => (
    <div>
      <input className={input} value={peopleFilter} onChange={(e) => setPeopleFilter(e.target.value)} placeholder="Search people…" />
      <div className="mt-1 max-h-40 overflow-y-auto rounded border border-border" data-testid="studio-people-picker">
        {pickerPeople(exclude).length === 0 && <div className="px-2 py-1.5 text-[11px] text-content-tertiary">No one else to add.</div>}
        {pickerPeople(exclude).map((p) => (
          <label key={p.id} className="flex cursor-pointer items-center gap-2 px-2 py-1 hover:bg-surface-secondary">
            <input type="checkbox" checked={who.has(p.id)} onChange={(e) => setWho((w) => { const n = new Set(w); if (e.target.checked) n.add(p.id); else n.delete(p.id); return n; })} />
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-oe-blue text-[9px] font-bold text-white">{initials(p)}</span>
            <span className="min-w-0 flex-1 truncate text-[12px]">{label(p)}</span>
            <span className="truncate text-[10px] text-content-tertiary">{p.email}</span>
          </label>
        ))}
      </div>
      <input className={clsx(input, 'mt-1')} value={extraEmails} onChange={(e) => setExtraEmails(e.target.value)} placeholder="Or type other emails, separated by commas" data-testid="studio-invite-emails" />
    </div>
  );
  const modal = (title: string, body: ReactNode, foot: ReactNode, testId: string) => (
    <div className="fixed inset-0 z-[95] flex items-center justify-center bg-black/40" onMouseDown={(e) => { if (e.target === e.currentTarget && !progress) setDialog(null); }}>
      <div className="w-[460px] max-w-[94vw] rounded-md border border-border bg-surface-elevated shadow-2xl" data-testid={testId}>
        <div className="flex items-center border-b border-border px-3 py-2 text-[13px] font-semibold">
          {title}
          <button type="button" className="ml-auto rounded p-0.5 hover:bg-surface-secondary" onClick={() => !progress && setDialog(null)} aria-label="Close"><X size={14} /></button>
        </div>
        <div className="space-y-2 p-3 text-[12px]">{body}</div>
        <div className="flex justify-end gap-1.5 border-t border-border px-3 py-2">{foot}</div>
      </div>
    </div>
  );

  return (
    <div className="relative flex min-h-0 flex-1 flex-col text-[12px]" data-testid="studio-panel">
      {/* header: Studio, who is signed in, + (new / join), refresh */}
      <div className="flex items-center gap-1.5 border-b border-border px-2 py-1.5">
        <span className="text-[13px] font-semibold">Studio</span>
        <span className="ml-auto max-w-[55%] truncate text-[11px] text-content-secondary" title="Signed in as">{myEmail || ''}</span>
      </div>
      {(sessions.error as { status?: number } | null)?.status === 404 || /not found/i.test(String((sessions.error as Error | null)?.message ?? '')) ? (
        <div className="m-2 rounded border border-amber-500/50 bg-amber-500/10 p-2 text-[11px]" data-testid="studio-server-old">
          Studio is not on the server yet. Restart the backend (it was started before Studio was added), then press refresh.
        </div>
      ) : null}
      <div className="flex gap-1.5 px-2 pt-2">
        <button type="button" className={clsx(btn, 'flex flex-1 items-center justify-center gap-1 bg-oe-blue py-1.5 text-white')} onClick={openNew} data-testid="studio-new-btn">
          <FolderPlus size={13} /> New session
        </button>
        <button type="button" className={clsx(btn, 'flex flex-1 items-center justify-center gap-1 border border-border py-1.5')} onClick={() => setDialog('join')} data-testid="studio-join-btn">
          <LogIn size={13} /> Join with ID
        </button>
      </div>
      <div className="flex items-center gap-1 px-2 pb-1 pt-1.5">
        <span className="text-[12px] font-semibold">All sessions</span>
        <div className="relative ml-auto">
          <button type="button" className="rounded p-1 hover:bg-surface-secondary" title="New session or join one" onClick={() => setMenu((m) => (m === 'plus' ? null : 'plus'))} data-testid="studio-plus">
            <Plus size={14} />
          </button>
          {menu === 'plus' && (
            <>
              <div className="fixed inset-0 z-[80]" onClick={() => setMenu(null)} />
              <div className="absolute right-0 top-full z-[81] mt-1 w-44 rounded border border-border bg-surface-elevated py-1 shadow-xl">
                <button type="button" className={menuItem} onClick={() => { setMenu(null); openNew(); }} data-testid="studio-start-open"><FolderPlus size={13} /> New session</button>
                <button type="button" className={menuItem} onClick={() => { setMenu(null); setDialog('join'); }} data-testid="studio-join-open"><LogIn size={13} /> Join with ID</button>
              </div>
            </>
          )}
        </div>
        <button type="button" className="rounded p-1 hover:bg-surface-secondary" title="Refresh" onClick={() => { void sessions.refetch(); if (activeId) void detail.refetch(); }}>
          <RefreshCw size={13} />
        </button>
      </div>
      <div className="px-2 pb-1.5">
        <div className="relative">
          <input className={clsx(input, 'pr-6')} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search" data-testid="studio-search" />
          <Search size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-content-tertiary" />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="px-3 py-4 text-center text-[11px] text-content-tertiary">
            {sessions.isLoading ? 'Loading…' : 'No sessions yet. Start one with New session, or Join with ID.'}
          </div>
        )}
        {rows.length > 0 && !activeId && (
          <div className="px-2 pb-1 text-[10px] text-content-tertiary">Click a session to open it - its PDFs, people and chat open right here.</div>
        )}
        {rows.map((r) => {
          const isOpen = r.id === activeId;
          return (
            <div key={r.id} className={clsx(isOpen && 'border-y border-border bg-surface-secondary/30')}>
              <div className={clsx('flex items-center gap-1.5 px-2 py-1.5 hover:bg-surface-secondary', isOpen && 'bg-oe-blue/10')}>
                <button type="button" onClick={() => openRow(r)} className="flex min-w-0 flex-1 items-center gap-1.5 text-left" data-testid="studio-session-row">
                  {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  <span className={clsx('h-2 w-2 shrink-0 rounded-full', r.status === 'active' ? 'bg-emerald-500' : 'bg-content-tertiary')} />
                  <span className={clsx('min-w-0 flex-1 truncate', isOpen ? 'font-semibold' : '', r.status !== 'active' && 'text-content-tertiary')}>{r.name}</span>
                </button>
                {r.status === 'active' && r.my_status === 'invited' && (
                  <button type="button" className={clsx(btn, 'bg-oe-blue py-0.5 text-white')} onClick={() => openRow(r)}>Join</button>
                )}
                <span className="shrink-0 font-mono text-[11px] text-content-secondary">{r.code}</span>
              </div>

              {isOpen && !d && <div className="px-6 py-2 text-[11px] text-content-tertiary">Loading…</div>}
              {isOpen && d && (
                <div data-testid="studio-session">
                  {/* session bar: Add / Actions, ID, role */}
                  <div className="flex flex-wrap items-center gap-1 px-2 pb-1">
                    <span className="text-[10px] text-content-tertiary">
                      ID <span className="font-mono text-content-primary" data-testid="studio-code-shown">{d.code}</span>
                    </span>
                    <button type="button" onClick={copyId} title="Copy the session ID" className="rounded p-0.5 hover:bg-surface-secondary"><Copy size={10} /></button>
                    <span className="text-[10px] text-content-tertiary">· {live ? (host ? 'you host' : 'attendee') : `finished ${timeOf(d.finished_at)}`}</span>
                    <div className="relative ml-auto flex gap-1">
                      {live && (
                        <button type="button" className={clsx(btn, 'flex items-center gap-0.5 bg-oe-blue text-white')} onClick={() => setMenu((m) => (m === 'add' ? null : 'add'))} title="Add PDFs: from this computer, from the project, or the open PDF" data-testid="studio-add">
                          <Plus size={11} /> Add PDF <ChevronDown size={10} />
                        </button>
                      )}
                      <button type="button" className={clsx(btn, 'flex items-center gap-0.5 border border-border')} onClick={() => setMenu((m) => (m === 'actions' ? null : 'actions'))} data-testid="studio-actions">
                        Actions <ChevronDown size={10} />
                      </button>
                      {(menu === 'add' || menu === 'actions') && (
                        <>
                          <div className="fixed inset-0 z-[80]" onClick={() => setMenu(null)} />
                          <div className="absolute right-0 top-full z-[81] mt-1 w-56 rounded border border-border bg-surface-elevated py-1 shadow-xl">
                            {menu === 'add' ? (
                              <>
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); openUpload(''); }} data-testid="studio-upload-open"><Upload size={13} /> Upload PDFs from this computer…</button>
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); setUploadTo(''); folderPick.current?.click(); }}><FolderUp size={13} /> Upload folder…</button>
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); setUploadTo(''); setNewFolder(''); setDialog('folder'); }} data-testid="studio-new-folder"><FolderPlus size={13} /> New folder</button>
                                <button type="button" className={menuItem} disabled={!canAddCurrent} onClick={() => { setMenu(null); addCurrent(); }} data-testid="studio-add-current"><FilePlus size={13} /> Add the open PDF</button>
                                <button type="button" className={menuItem} disabled={!projectId} onClick={() => { setMenu(null); setProjPicked(new Set()); setDialog('project'); }} data-testid="studio-add-project"><FolderOpen size={13} /> Add PDFs from the project…</button>
                                <div className="my-1 h-px bg-border" />
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); setWho(new Set()); setExtraEmails(''); setPeopleFilter(''); setDialog('invite'); }} data-testid="studio-invite-open"><UserPlus size={13} /> Invite people…</button>
                              </>
                            ) : (
                              <>
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); copyId(); }}><Copy size={13} /> Copy session ID</button>
                                <button type="button" className={menuItem} onClick={() => { setMenu(null); shareId(); }} data-testid="studio-share-id"><Send size={13} /> Copy invite text (ID + how to join)</button>
                                <button type="button" className={menuItem} disabled={!report.data} onClick={() => { setMenu(null); downloadReportPdf(); }} data-testid="studio-report-pdf"><FileText size={13} /> Report (PDF)</button>
                                <button type="button" className={menuItem} disabled={!report.data} onClick={() => { setMenu(null); downloadReport(); }} data-testid="studio-report-csv"><FileText size={13} /> Report (CSV)</button>
                                {live && host && (
                                  <button type="button" className={menuItem} onClick={() => { setMenu(null); toggleOpen(); }}>
                                    <span className="w-[13px] text-center">{d.open_join ? '✓' : ''}</span> Anyone with the ID can join
                                  </button>
                                )}
                                {live && <div className="my-1 h-px bg-border" />}
                                {live && host && <button type="button" className={clsx(menuItem, 'text-red-500')} onClick={() => { setMenu(null); finish(); }} data-testid="studio-finish"><CircleStop size={13} /> Finish session</button>}
                                {live && !host && <button type="button" className={menuItem} onClick={() => { setMenu(null); leave(); }} data-testid="studio-leave"><LogOut size={13} /> Leave session</button>}
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="mx-2 mb-1 rounded border border-oe-blue/40 bg-oe-blue/5 px-2 py-1.5 text-[11px]" data-testid="studio-id-card">
                    <div className="flex items-center gap-1">
                      Session ID <span className="font-mono text-[13px] font-semibold text-content-primary">{d.code}</span>
                      <button type="button" onClick={copyId} className="ml-auto flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] hover:bg-surface-secondary"><Copy size={10} /> Copy</button>
                    </div>
                    <div className="text-[10px] text-content-tertiary">Others join with Studio &gt; Join with ID. People you invite also get it by notification and email.</div>
                  </div>
                  {live && (
                    <div className="flex gap-1 px-2 pb-1.5">
                      <button type="button" className={clsx(btn, 'flex flex-1 items-center justify-center gap-1 bg-oe-blue py-1.5 text-white')} onClick={() => openUpload('')} data-testid="studio-add-pdf-big">
                        <Upload size={12} /> Add PDF from computer
                      </button>
                      <button type="button" className={clsx(btn, 'flex flex-1 items-center justify-center gap-1 border border-oe-blue py-1.5 text-oe-blue')} disabled={!projectId && !d.project_id} onClick={() => { setUploadTo(''); setProjPicked(new Set()); setDialog('project'); }} data-testid="studio-add-project-big">
                        <FolderOpen size={12} /> From project
                      </button>
                      <button type="button" className={clsx(btn, 'flex items-center justify-center gap-1 border border-border py-1.5')} onClick={() => { setWho(new Set()); setExtraEmails(''); setPeopleFilter(''); setDialog('invite'); }} title="Invite people" data-testid="studio-invite-big">
                        <UserPlus size={12} />
                      </button>
                    </div>
                  )}
                  {/* files: folders and PDFs, drop files from the computer anywhere here */}
                  <div
                    className={clsx('min-h-[56px] pb-1', dropFolder === '' && 'bg-oe-blue/10 ring-1 ring-inset ring-oe-blue')}
                    onDragOver={(e) => dragOver(e, '')}
                    onDragLeave={() => setDropFolder(null)}
                    onDrop={(e) => onDropFiles(e, '')}
                    data-testid="studio-files"
                  >
                    {d.documents.length === 0 && folders.length === 0 ? (
                      <div className="px-3 py-3 text-center">
                        <FileText size={28} className="mx-auto mb-1 text-content-tertiary" />
                        <div className="text-[11px] font-semibold">No documents uploaded yet.</div>
                        <div className="mb-2 text-[10px] text-content-tertiary">Drag files or folders here, or select an option below.</div>
                        {live && (
                          <div className="flex flex-wrap justify-center gap-1">
                            <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={() => { setUploadTo(''); setNewFolder(''); setDialog('folder'); }}>New Folder</button>
                            <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={() => openUpload('')}>Upload Files</button>
                            <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={() => { setUploadTo(''); folderPick.current?.click(); }}>Upload Folder</button>
                            {projectId && <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={() => { setUploadTo(''); setProjPicked(new Set()); setDialog('project'); }}>From Project</button>}
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        {childFolders('').map((f) => folderBlock(f, 0))}
                        {docsIn('').map((x) => docRow(x, 0))}
                      </>
                    )}
                    {progress && (
                      <div className="mx-2 mt-1 rounded bg-surface-secondary px-2 py-1 text-[10px]" data-testid="studio-upload-progress">
                        Uploading {progress.done} / {progress.total}…
                        <div className="mt-0.5 h-1 rounded bg-border"><div className="h-1 rounded bg-oe-blue transition-all" style={{ width: `${(progress.done / Math.max(1, progress.total)) * 100}%` }} /></div>
                      </div>
                    )}
                  </div>

                  {/* people: everyone in the session, then every other FSFTM account */}
                  <div className="flex items-center px-2 pb-0.5 pt-2 text-[10px] font-semibold uppercase tracking-wide text-content-tertiary">
                    People
                    <span className="ml-auto normal-case tracking-normal">{d.attendees.filter((a) => a.online).length} online</span>
                  </div>
                  <div className="px-2 pb-1 text-[10px] text-content-tertiary" data-testid="studio-visibility-note">
                    {d.open_join ? 'Anyone signed in who has the session ID can join.' : 'Only the people added here can see this session and its PDFs.'}
                  </div>
                  {peopleRows.att.map((a) => (
                    <div key={a.id} className="group flex items-center gap-2 px-2 py-0.5" data-testid="studio-person">
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
                          {a.status === 'invited' ? 'invited' : a.status === 'left' ? 'left' : a.online ? `on ${docName.get(a.document_id ?? '') ?? 'a PDF'} · page ${a.page ?? 1}` : 'offline'}
                        </span>
                      </span>
                      {a.user_id && (counts.get(a.user_id) ?? 0) > 0 && <span className="rounded bg-surface-secondary px-1 text-[10px] text-content-secondary" title="Markups made in this session">{counts.get(a.user_id)}</span>}
                      {host && live && a.role !== 'host' && (
                        <button type="button" className="hidden rounded p-0.5 text-content-tertiary hover:text-red-500 group-hover:block" title="Remove from the session" onClick={() => removePerson(a)}><X size={11} /></button>
                      )}
                    </div>
                  ))}
                  {live && peopleRows.others.map((p) => (
                    <div key={p.id} className="flex items-center gap-2 px-2 py-0.5 opacity-80" data-testid="studio-account">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-500 text-[10px] font-bold text-white">{initials(p)}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{label(p)}</span>
                        <span className="block truncate text-[10px] text-content-tertiary">{p.email}</span>
                      </span>
                      <button type="button" className={clsx(btn, 'border border-border py-0.5')} onClick={() => invite([p.email])} disabled={busy}>Invite</button>
                    </div>
                  ))}

                  {/* chat */}
                  <button type="button" className="flex w-full items-center gap-1 px-2 pb-0.5 pt-2 text-[10px] font-semibold uppercase tracking-wide text-content-tertiary" onClick={() => setShowChat((v) => !v)}>
                    {showChat ? <ChevronDown size={11} /> : <ChevronRight size={11} />} Chat ({messages.data?.messages.length ?? 0})
                  </button>
                  {showChat && (
                    <>
                      <div className="max-h-48 space-y-1 overflow-y-auto px-2" data-testid="studio-chat">
                        {(messages.data?.messages ?? []).map((m) => (
                          <div key={m.id} className={clsx('rounded px-2 py-1', m.user_id === me ? 'bg-oe-blue/10' : 'bg-surface-secondary')}>
                            <div className="flex justify-between text-[10px] text-content-tertiary">
                              <span className="font-semibold text-content-secondary">{m.user_id === me ? 'You' : m.name || 'Someone'}</span>
                              <span>{timeOf(m.at)}</span>
                            </div>
                            <div className="whitespace-pre-wrap break-words">{highlightMentions(m.text, people.data?.people ?? [], 'rounded bg-oe-blue/15 px-0.5 font-semibold text-oe-blue')}</div>
                          </div>
                        ))}
                        <div ref={chatEnd} />
                      </div>
                      {live && (
                        <div className="relative flex gap-1.5 p-2">
                          {chatComposer.suggestions.length > 0 && (
                            <div className="absolute bottom-full left-2 right-2 z-10 max-h-48 overflow-y-auto rounded border border-border bg-surface-elevated shadow-lg" data-testid="studio-mention-list">
                              {chatComposer.suggestions.map((p) => (
                                <button key={p.id} type="button" onMouseDown={(e) => { e.preventDefault(); chatComposer.pick(p); }} className="flex w-full items-center gap-2 px-2 py-1 text-left hover:bg-surface-secondary">
                                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-oe-blue text-[9px] font-bold text-white">{initials(p)}</span>
                                  <span className="min-w-0 flex-1 truncate font-semibold text-oe-blue">{personLabel(p)}</span>
                                  <span className="truncate text-[10px] text-content-tertiary">{p.email}</span>
                                </button>
                              ))}
                            </div>
                          )}
                          <input
                            ref={(el) => { chatComposer.boxRef.current = el; }}
                            className={input}
                            value={chat}
                            onChange={(e) => chatComposer.onChange(e.target.value, e.target.selectionStart)}
                            onSelect={(e) => chatComposer.setCaret(e.currentTarget.selectionStart ?? chat.length)}
                            placeholder="Message everyone… type @ to mention"
                            onKeyDown={(e) => { e.stopPropagation(); if (e.key === 'Enter' && !chatComposer.suggestions.length) { e.preventDefault(); send(); } }}
                            data-testid="studio-chat-input"
                          />
                          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} onClick={send} disabled={busy || !chat.trim()} data-testid="studio-chat-send" aria-label="Send"><Send size={12} /></button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* hidden pickers for files and whole folders */}
      <input ref={filePick} type="file" accept="application/pdf,.pdf" multiple className="hidden" onChange={(e) => { const fs = Array.from(e.target.files ?? []); e.target.value = ''; setUploads((u) => [...u, ...fs.map((f) => ({ file: f, rel: f.name }))]); }} data-testid="studio-file-input" />
      <input
        ref={(el) => { folderPick.current = el; if (el) el.setAttribute('webkitdirectory', ''); }}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          const fs = Array.from(e.target.files ?? []);
          e.target.value = '';
          const items = fs.map((f) => ({ file: f, rel: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name }));
          if (dialog === 'upload') setUploads((u) => [...u, ...items]);
          else openUpload(uploadTo, items);
        }}
      />

      {dialog === 'new' && modal(
        'New session',
        <>
          <label className="block text-[11px] text-content-secondary">Session name<input className={input} value={name} onChange={(e) => setName(e.target.value)} data-testid="studio-name" /></label>
          <div className="text-[11px] text-content-secondary">PDFs to start with (more can be uploaded later)</div>
          <div className="max-h-28 overflow-y-auto rounded border border-border">
            {serverTabs.length === 0 && <div className="px-2 py-1.5 text-[11px] text-content-tertiary">No PDFs open - upload into the session after starting it.</div>}
            {serverTabs.map((t) => (
              <label key={t.id} className="flex items-center gap-1.5 px-2 py-1">
                <input type="checkbox" checked={picked.has(t.id)} onChange={(e) => setPicked((p) => { const n = new Set(p); if (e.target.checked) n.add(t.id); else n.delete(t.id); return n; })} data-testid="studio-pick-doc" />
                <span className="truncate">{t.name}</span>
              </label>
            ))}
          </div>
          <div className="text-[11px] text-content-secondary">People - only the people you add can see the session</div>
          {peoplePicker(new Set())}
          <label className="flex items-center gap-1.5 text-[11px] text-content-secondary">
            <input type="checkbox" checked={openJoin} onChange={(e) => setOpenJoin(e.target.checked)} /> Anyone signed in who has the session ID may join
          </label>
        </>,
        <>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || (!picked.size && !projectId)} onClick={start} data-testid="studio-start" title={!picked.size && !projectId ? 'Open a project or pick a PDF first' : ''}>Start</button>
        </>,
        'studio-start-form',
      )}
      {dialog === 'project' && d && modal(
        'Add PDFs from the project',
        <>
          <div className="max-h-60 overflow-y-auto rounded border border-border" data-testid="studio-project-docs">
            {projectDocs.isLoading && <div className="px-2 py-1.5 text-[11px] text-content-tertiary">Loading…</div>}
            {(projectDocs.data ?? []).filter((x) => !d.documents.some((y) => y.id === x.id)).map((x) => (
              <label key={x.id} className="flex cursor-pointer items-center gap-2 px-2 py-1 hover:bg-surface-secondary">
                <input type="checkbox" checked={projPicked.has(x.id)} onChange={(e) => setProjPicked((p) => { const n = new Set(p); if (e.target.checked) n.add(x.id); else n.delete(x.id); return n; })} />
                <Thumb id={x.id} />
                <span className="min-w-0 flex-1 truncate">{x.filename}</span>
              </label>
            ))}
            {projectDocs.data && projectDocs.data.filter((x) => !d.documents.some((y) => y.id === x.id)).length === 0 && (
              <div className="px-2 py-1.5 text-[11px] text-content-tertiary">All of the project's PDFs are already in the session.</div>
            )}
          </div>
          <label className="flex items-center gap-2 text-[11px] text-content-secondary">
            Into
            <select className={input} value={uploadTo} onChange={(e) => setUploadTo(e.target.value)}>
              <option value="">(top level)</option>
              {folders.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
        </>,
        <>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || !projPicked.size} onClick={addFromProject} data-testid="studio-project-ok">Add</button>
        </>,
        'studio-project-form',
      )}
      {dialog === 'join' && modal(
        'Join a session',
        <label className="block text-[11px] text-content-secondary">Session ID
          <input className={input} autoFocus value={code} onChange={(e) => setCode(e.target.value)} placeholder="123-456-789" onKeyDown={(e) => { e.stopPropagation(); if (e.key === 'Enter') joinByCode(); }} data-testid="studio-code" />
        </label>,
        <>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || code.replace(/\D/g, '').length !== 9} onClick={joinByCode} data-testid="studio-join">Join</button>
        </>,
        'studio-join-form',
      )}
      {dialog === 'invite' && d && modal(
        'Invite people',
        peoplePicker(new Set(d.attendees.filter((a) => a.status !== 'left').map((a) => a.user_id ?? ''))),
        <>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy} onClick={() => invite(chosenEmails())} data-testid="studio-invite">Invite</button>
        </>,
        'studio-invite-form',
      )}
      {dialog === 'folder' && modal(
        'New folder',
        <label className="block text-[11px] text-content-secondary">
          {uploadTo ? `Inside “${uploadTo}”` : 'Folder name'}
          <input className={input} autoFocus value={newFolder} onChange={(e) => setNewFolder(e.target.value)} onKeyDown={(e) => { e.stopPropagation(); if (e.key === 'Enter') addFolder(); }} data-testid="studio-folder-name" />
        </label>,
        <>
          <button type="button" className={clsx(btn, 'border border-border')} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || !newFolder.trim()} onClick={addFolder} data-testid="studio-folder-ok">OK</button>
        </>,
        'studio-folder-form',
      )}
      {dialog === 'upload' && modal(
        'Upload Files',
        <>
          <label className="flex items-center gap-2 text-[11px] text-content-secondary">
            Into
            <select className={input} value={uploadTo} onChange={(e) => setUploadTo(e.target.value)}>
              <option value="">(top level)</option>
              {folders.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
          <div className="rounded border border-border">
            <div className="border-b border-border bg-surface-secondary px-2 py-1 text-[11px] font-semibold">Name</div>
            <div className="h-40 overflow-y-auto" data-testid="studio-upload-list">
              {uploads.map((u, i) => (
                <div key={`${u.rel}:${i}`} className="group flex items-center gap-1.5 px-2 py-0.5">
                  <FileText size={12} className={/\.pdf$/i.test(u.file.name) ? 'text-red-500' : 'text-content-tertiary'} />
                  <span className="min-w-0 flex-1 truncate">{u.rel}</span>
                  <button type="button" className="hidden text-content-tertiary hover:text-red-500 group-hover:block" onClick={() => setUploads((x) => x.filter((_, j) => j !== i))} aria-label="Remove"><X size={11} /></button>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-1.5">
            <button type="button" className={clsx(btn, 'border border-border')} onClick={() => filePick.current?.click()} data-testid="studio-upload-add">Add files…</button>
            <button type="button" className={clsx(btn, 'border border-border')} onClick={() => folderPick.current?.click()}>Add folder…</button>
            <button type="button" className={clsx(btn, 'border border-border')} disabled={!uploads.length} onClick={() => setUploads([])}>Remove all</button>
          </div>
          {progress && <div className="text-[11px] text-content-secondary">Uploading {progress.done} / {progress.total}…</div>}
          {homeProject && d?.project_name && <div className="text-[10px] text-content-tertiary">Files are kept in the project “{d.project_name}”.</div>}
        </>,
        <>
          <button type="button" className={clsx(btn, 'border border-border')} disabled={!!progress} onClick={() => setDialog(null)}>Cancel</button>
          <button type="button" className={clsx(btn, 'bg-oe-blue text-white')} disabled={busy || !uploads.length} onClick={() => doUpload(uploads, uploadTo)} data-testid="studio-upload-ok">OK</button>
        </>,
        'studio-upload-form',
      )}
    </div>
  );
}
