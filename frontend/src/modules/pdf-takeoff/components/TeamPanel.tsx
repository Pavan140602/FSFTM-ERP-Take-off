// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * Team panel (left rail > Team): who is working on which drawing and page
 * right now, and the drawing's comment thread with @mentions. A mentioned
 * person gets an in-app notification that opens this drawing.
 *
 * Presence comes from GET /takeoff/presence/ (each open viewer reports
 * itself); comments use the shared collaboration comments
 * (entity_type "takeoff_document").
 */
import { useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Send } from 'lucide-react';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';

type PresenceRow = {
  user_id: string;
  name: string;
  email: string;
  document_id: string;
  document_name: string;
  page: number;
  seconds_ago: number;
};
type Person = { id: string; name: string; email: string };
type CommentRow = {
  id: string;
  author_id: string;
  text: string;
  created_at: string;
  replies?: CommentRow[];
};

const initials = (p: { name?: string; email?: string }) =>
  ((p.name || p.email || '?').trim().split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?');
const label = (p: { name?: string; email?: string }) => (p.name || '').trim() || p.email || 'Someone';
const ago = (s: number) => (s < 30 ? 'active now' : s < 90 ? `${s}s ago` : `${Math.round(s / 60)} min ago`);
const timeOf = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

export function TeamPanel({
  projectId,
  documentId,
  onOpenDrawing,
}: {
  projectId: string | null;
  documentId: string | null;
  /** Open a drawing at a page (switches the main pane when it is another drawing). */
  onOpenDrawing: (documentId: string, page: number) => void;
}) {
  const me = useAuthStore((s) => s.userId);
  const addToast = useToastStore((s) => s.addToast);
  const qc = useQueryClient();

  const presence = useQuery({
    queryKey: ['takeoff-presence', projectId],
    queryFn: () => apiGet<{ active: PresenceRow[] }>(`/v1/takeoff/presence/${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
    refetchInterval: 15000,
  });
  const people = useQuery({
    // Only the project's people: a mention links to this drawing, which
    // someone outside the project could not open.
    queryKey: ['takeoff-people', projectId],
    queryFn: () => apiGet<{ people: Person[] }>(`/v1/takeoff/people/${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
    staleTime: 5 * 60_000,
  });
  const commentsKey = ['takeoff-comments', documentId];
  const comments = useQuery({
    queryKey: commentsKey,
    enabled: !!documentId,
    queryFn: () =>
      apiGet<{ items: CommentRow[] }>(`/v1/collaboration/comments/?entity_type=takeoff_document&entity_id=${encodeURIComponent(documentId!)}`),
    refetchInterval: 20000,
  });
  const byId = useMemo(() => new Map((people.data?.people ?? []).map((p) => [p.id, p])), [people.data]);

  // ── composer with @mention suggestions ──
  const [text, setText] = useState('');
  const [picked, setPicked] = useState<Person[]>([]);
  const [sending, setSending] = useState(false);
  const boxRef = useRef<HTMLTextAreaElement>(null);
  const atQuery = (() => {
    const el = boxRef.current;
    const upto = text.slice(0, el ? el.selectionStart ?? text.length : text.length);
    const m = /(^|\s)@([^\s@]{0,40})$/.exec(upto);
    return m ? m[2]!.toLowerCase() : null;
  })();
  const suggestions = atQuery === null
    ? []
    : (people.data?.people ?? []).filter((p) => p.id !== me && (p.name.toLowerCase().includes(atQuery) || p.email.toLowerCase().includes(atQuery))).slice(0, 6);
  const pick = (p: Person) => {
    const el = boxRef.current;
    const pos = el ? el.selectionStart ?? text.length : text.length;
    const before = text.slice(0, pos).replace(/@([^\s@]{0,40})$/, `@${label(p).replace(/\s+/g, '_')} `);
    setText(before + text.slice(pos));
    setPicked((prev) => (prev.some((x) => x.id === p.id) ? prev : [...prev, p]));
    requestAnimationFrame(() => el?.focus());
  };
  const send = async () => {
    const body = text.trim();
    if (!body || !documentId) return;
    // Mentions: people picked from the list and still named in the text,
    // plus anyone typed as @their.email.
    const mentions = new Map<string, Person>();
    for (const p of picked) if (body.includes(`@${label(p).replace(/\s+/g, '_')}`)) mentions.set(p.id, p);
    for (const m of body.matchAll(/@([^\s@]+@[^\s@]+\.[^\s@]+)/g)) {
      const hit = (people.data?.people ?? []).find((p) => p.email.toLowerCase() === m[1]!.toLowerCase());
      if (hit) mentions.set(hit.id, hit);
    }
    setSending(true);
    try {
      await apiPost('/v1/collaboration/comments/', {
        entity_type: 'takeoff_document',
        entity_id: documentId,
        text: body,
        mentions: [...mentions.keys()].map((id) => ({ mentioned_user_id: id, mention_type: 'at_notify' })),
      });
      setText('');
      setPicked([]);
      await qc.invalidateQueries({ queryKey: commentsKey });
      if (mentions.size) addToast({ type: 'success', title: `Sent - ${mentions.size} ${mentions.size === 1 ? 'person' : 'people'} notified` });
    } catch (e) {
      addToast({ type: 'error', title: 'Could not send the comment', message: e instanceof Error ? e.message : String(e) });
    } finally {
      setSending(false);
    }
  };

  const active = presence.data?.active ?? [];
  const flat = (comments.data?.items ?? []).flatMap((c) => [c, ...(c.replies ?? [])]);
  return (
    <div className="flex min-h-0 flex-1 flex-col text-[11px]" data-testid="team-panel">
      <div className="border-b border-border px-2 py-1.5 text-[11px] font-semibold">Working now</div>
      <div className="max-h-[40%] min-h-[60px] overflow-y-auto p-1.5" data-testid="team-presence">
        {active.length === 0 && <p className="px-1 py-2 text-content-tertiary">Nobody else is in this project right now.</p>}
        {active.map((r) => (
          <button
            key={`${r.user_id}:${r.document_id}`}
            type="button"
            onClick={() => onOpenDrawing(r.document_id, r.page)}
            className="mb-1 flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-surface-secondary"
            title={`Open ${r.document_name} at page ${r.page}`}
          >
            <span className={clsx('flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white', r.user_id === me ? 'bg-content-tertiary' : 'bg-oe-blue')}>
              {initials(r)}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium text-content-primary">{label(r)}{r.user_id === me ? ' (you)' : ''}</span>
              <span className="block truncate text-content-tertiary">{r.document_name} · p.{r.page}</span>
            </span>
            <span className={clsx('shrink-0 text-[10px]', r.seconds_ago < 30 ? 'text-green-600' : 'text-content-tertiary')}>{ago(r.seconds_ago)}</span>
          </button>
        ))}
      </div>
      <div className="border-y border-border px-2 py-1.5 text-[11px] font-semibold">Comments on this drawing</div>
      <div className="min-h-0 flex-1 overflow-y-auto p-1.5" data-testid="team-comments">
        {!documentId && <p className="px-1 py-2 text-content-tertiary">Save the drawing to the project to comment on it.</p>}
        {documentId && flat.length === 0 && !comments.isLoading && <p className="px-1 py-2 text-content-tertiary">No comments yet. Type @ to mention someone.</p>}
        {flat.map((c) => {
          const who = byId.get(c.author_id);
          return (
            <div key={c.id} className="mb-2 rounded border border-border/70 bg-surface-secondary/40 p-1.5">
              <div className="mb-0.5 flex items-center gap-1.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-oe-blue/80 text-[9px] font-bold text-white">{initials(who ?? {})}</span>
                <span className="font-medium">{who ? label(who) : 'Someone'}</span>
                <span className="ml-auto text-[10px] text-content-tertiary">{timeOf(c.created_at)}</span>
              </div>
              <p className="whitespace-pre-wrap break-words">
                {c.text.split(/(@[^\s]+)/g).map((part, i) =>
                  part.startsWith('@') ? <span key={i} className="font-semibold text-oe-blue">{part}</span> : <span key={i}>{part}</span>,
                )}
              </p>
            </div>
          );
        })}
      </div>
      <div className="relative border-t border-border p-1.5">
        {suggestions.length > 0 && (
          <div className="absolute bottom-full left-1.5 right-1.5 z-10 mb-1 rounded border border-border bg-surface-primary shadow-lg" data-testid="team-mention-list">
            {suggestions.map((p) => (
              <button key={p.id} type="button" onMouseDown={(e) => { e.preventDefault(); pick(p); }} className="flex w-full items-center gap-2 px-2 py-1 text-left hover:bg-surface-secondary">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-oe-blue text-[9px] font-bold text-white">{initials(p)}</span>
                <span className="min-w-0 flex-1 truncate">{label(p)}</span>
                <span className="truncate text-[10px] text-content-tertiary">{p.email}</span>
              </button>
            ))}
          </div>
        )}
        <textarea
          ref={boxRef}
          value={text}
          disabled={!documentId}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            e.stopPropagation();
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void send();
          }}
          rows={3}
          placeholder="Write a comment… type @ to mention (Ctrl+Enter sends)"
          className="w-full resize-none rounded border border-border bg-surface-secondary px-1.5 py-1 text-[11px] focus:border-oe-blue focus:outline-none"
          data-testid="team-comment-input"
        />
        <button
          type="button"
          disabled={!text.trim() || sending || !documentId}
          onClick={() => void send()}
          className="mt-1 flex w-full items-center justify-center gap-1 rounded bg-oe-blue px-2 py-1 text-[11px] font-semibold text-white disabled:opacity-40"
          data-testid="team-comment-send"
        >
          <Send size={12} /> Send
        </button>
      </div>
    </div>
  );
}
