/**
 * Split-pane workspace contract between the PDF viewer and TakeoffPage
 * (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * Every drawing has exactly ONE editor (its own viewer: markups, tools,
 * undo, saving). The visible main viewer lays out the split panes and
 * publishes which pane shows which project drawing; TakeoffPage then places
 * that drawing's editor into the pane's slot element. Moving a drawing
 * between panes, or switching tabs, only moves an already-running editor -
 * nothing reloads. Kept in a small module so TakeoffPage can use it without
 * loading the (lazy) viewer.
 */
import type React from 'react';

/** Drag a document tab from one pane to another. */
export const TAB_DND_MIME = 'application/x-fsftm-doc-tab';
export type TabDragPayload = { from: 'main' | 'split'; id: string; name: string; pane?: string };

export function readTabDrag(e: React.DragEvent): TabDragPayload | null {
  try {
    const raw = e.dataTransfer.getData(TAB_DND_MIME);
    const v = raw ? (JSON.parse(raw) as TabDragPayload) : null;
    return v && typeof v.id === 'string' && (v.from === 'main' || v.from === 'split') ? v : null;
  } catch {
    return null;
  }
}

export function hasTabDrag(e: React.DragEvent): boolean {
  return Array.from(e.dataTransfer.types).includes(TAB_DND_MIME);
}

/** Panes that show a project drawing as a full editor: pane -> drawing. */
export type PaneHosting = { pane: string; id: string; name: string }[];
export const PANE_HOSTING_KEY = 'ws.hosting';
/** The element each pane's editor is placed into: pane key -> element. */
export const PANE_SLOTS_KEY = 'ws.slots';
/** Drop a tab onto a pane from anywhere (set by the visible main viewer). */
export const WS_API_KEY = 'ws.api';
export type WorkspaceApi = {
  dropTabOnPane: (t: TabDragPayload, pane: string) => void;
  /** Split the pane in use ('row' = side by side, 'col' = stacked). */
  split?: (dir: 'row' | 'col') => void;
};
/** The drawing whose editor gets the keyboard (last clicked). */
export const WS_FOCUS_KEY = 'ws.focus';
/** Drawings open in split panes (ids / names; the documents themselves stay in the viewer). */
export const SPLIT_TABS_KEY = 'split.tabs';
export const SPLIT_EXTRA_KEY = 'split.extra';
