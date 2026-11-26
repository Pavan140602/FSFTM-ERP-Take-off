// OE-DELIVERY: 2026-11-26-fsftm-pdf
/**
 * Places every open drawing's viewer (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * Each drawing has exactly ONE viewer - its own markups, tools, undo and
 * saving. The viewers are rendered into host elements that are only ever
 * MOVED: the drawing on screen sits in the main stack, a drawing shown in a
 * split pane is moved into that pane's slot (published by the main viewer),
 * and the rest wait invisibly in the stack. Switching tabs or moving a
 * drawing between panes therefore never reloads, blinks or loses its view.
 */
import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import clsx from 'clsx';
import { Loader2 } from 'lucide-react';
import { useSharedState, getShared, setShared } from '@/modules/pdf-takeoff/data/shared-state';
import { useSmoothProgress } from '@/modules/pdf-takeoff/data/smooth-progress';
import {
  PANE_HOSTING_KEY,
  SPLIT_EXTRA_KEY,
  SPLIT_TABS_KEY,
  WS_FOCUS_KEY,
  PANE_SLOTS_KEY,
  type PaneHosting,
} from '@/modules/pdf-takeoff/data/workspace';

export type WorkspaceDoc = { url: string; name: string; id: string };

interface Props {
  /** Main-pane drawings whose viewers stay alive (mount order). */
  docs: WorkspaceDoc[];
  /** The main drawing on screen. */
  shownId: string | null;
  /** A newly opened drawing still loading (the previous one stays shown). */
  opening?: WorkspaceDoc;
  /** Its loading progress, percent (null = not known yet). */
  openingPct?: number | null;
  /** `pane` is the split pane the viewer sits in (compact editor), 'parked'
   *  for a pane drawing not on screen, null for a main drawing. `mirror` is
   *  set for a second editor of a drawing already open elsewhere; `key`
   *  identifies the editor. */
  renderViewer: (doc: WorkspaceDoc, visible: boolean, pane: string | null, mirror: boolean, key: string) => ReactNode;
  downloadUrl?: (id: string) => string;
}

const defaultUrl = (id: string) => `/api/v1/takeoff/documents/${encodeURIComponent(id)}/download/`;

export function ViewerWorkspace({ docs, shownId, opening, openingPct = null, renderViewer, downloadUrl = defaultUrl }: Props) {
  const smoothPct = useSmoothProgress(opening ? openingPct : null);
  const [paneHosting] = useSharedState<PaneHosting>(PANE_HOSTING_KEY, []);
  const [splitTabs] = useSharedState<{ id: string; name: string }[]>(SPLIT_TABS_KEY, []);
  const [splitExtra] = useSharedState<{ key: string; tabs: { id: string; name: string }[] }[]>(SPLIT_EXTRA_KEY, []);
  const [slots] = useSharedState<Record<string, HTMLElement>>(PANE_SLOTS_KEY, {});
  const stackRef = useRef<HTMLDivElement>(null);
  const hostsRef = useRef(new Map<string, HTMLDivElement>());
  const hostFor = (id: string) => {
    let h = hostsRef.current.get(id);
    if (!h) {
      h = document.createElement('div');
      h.dataset.viewerHost = id;
      hostsRef.current.set(id, h);
    }
    return h;
  };

  /* One OWNER editor per drawing (it saves): in the main stack when it is the
   * main drawing, else in the first pane showing it, else parked. Any other
   * pane showing the same drawing gets a MIRROR editor that shares the
   * owner's markups live. */
  type Inst = { key: string; doc: WorkspaceDoc; pane: string | null; visible: boolean; mirror: boolean };
  const instances: Inst[] = [];
  {
    const owners = new Map<string, Inst>();
    const live = paneHosting.filter((h) => slots[h.pane] && !h.id.startsWith('file:') && !h.id.startsWith('temp-'));
    const url = (id: string, name: string): WorkspaceDoc => ({ id, name, url: downloadUrl(id) });
    const addOwner = (doc: WorkspaceDoc, pane: string | null, visible: boolean) => {
      if (owners.has(doc.id) || doc.id.startsWith('file:') || doc.id.startsWith('temp-')) return;
      const inst = { key: doc.id, doc, pane, visible, mirror: false };
      owners.set(doc.id, inst);
      instances.push(inst);
    };
    for (const d of docs) {
      if (d.id === shownId) addOwner(d, null, true);
    }
    for (const h of live) {
      if (owners.has(h.id)) {
        instances.push({ key: `${h.id}@${h.pane}`, doc: url(h.id, h.name), pane: h.pane, visible: true, mirror: true });
      } else {
        const known = docs.find((d) => d.id === h.id);
        addOwner(known ?? url(h.id, h.name), h.pane, true);
      }
    }
    for (const d of docs) addOwner(d, null, d.id === shownId);
    for (const t of splitTabs) addOwner(url(t.id, t.name), 'parked', false);
    for (const xp of splitExtra) for (const t of xp.tabs) addOwner(url(t.id, t.name), 'parked', false);
  }

  // Move each host to where its drawing shows - only when that changes, so
  // canvases and scroll positions stay as they are.
  useLayoutEffect(() => {
    const stack = stackRef.current;
    const live = new Set(instances.map((v) => v.key));
    for (const v of instances) {
      const host = hostFor(v.key);
      const slot = v.pane && v.pane !== 'parked' ? slots[v.pane] : null;
      const target = slot ?? stack;
      if (!target) continue;
      if (host.parentElement !== target) target.appendChild(host);
      const cls = slot
        ? 'flex min-h-0 min-w-0 flex-1 flex-col'
        : clsx('absolute inset-0 flex min-h-0 flex-col', !v.visible && 'invisible pointer-events-none');
      if (host.className !== cls) host.className = cls;
      const tid = v.visible ? (slot ? 'viewer-pane' : 'viewer-active') : 'viewer-background';
      if (host.getAttribute('data-testid') !== tid) host.setAttribute('data-testid', tid);
    }
    for (const [id, host] of hostsRef.current) {
      if (live.has(id)) continue;
      host.remove();
      hostsRef.current.delete(id);
    }
  });
  // Unmount: drop the hosts.
  useEffect(() => {
    const hosts = hostsRef.current;
    return () => {
      for (const h of hosts.values()) h.remove();
      hosts.clear();
    };
  }, []);
  // The shown main drawing takes the keyboard when it changes.
  useEffect(() => {
    if (shownId && getShared(WS_FOCUS_KEY) !== shownId) setShared(WS_FOCUS_KEY, shownId);
  }, [shownId]);

  return (
    <>
      <div ref={stackRef} className="relative flex min-h-0 flex-1 flex-col" data-testid="viewer-stack">
        {opening && (
          <div className="pointer-events-none absolute left-1/2 top-2 z-[60] flex w-56 -translate-x-1/2 flex-col gap-1 rounded-lg bg-black/80 px-3 py-1.5 text-xs text-white shadow" data-testid="viewer-opening">
            <div className="flex items-center gap-2">
              <Loader2 size={12} className="shrink-0 animate-spin" />
              <span className="min-w-0 flex-1 truncate">Opening {opening.name}</span>
              <span className="tabular-nums">{smoothPct !== null ? `${smoothPct}%` : ''}</span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-white/20">
              {smoothPct !== null ? (
                <div className="h-full rounded-full bg-white" style={{ width: `${Math.max(3, smoothPct)}%` }} />
              ) : (
                <div className="h-full w-1/3 animate-pulse rounded-full bg-white/70" />
              )}
            </div>
          </div>
        )}
      </div>
      {instances.map((v) => createPortal(renderViewer(v.doc, v.visible, v.pane, v.mirror, v.key), hostFor(v.key), v.key))}
    </>
  );
}
