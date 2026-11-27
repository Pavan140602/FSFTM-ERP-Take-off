// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * One full screen for the whole PDF Measurements workspace.
 *
 * Every open drawing and every split pane is its own viewer. Each used to
 * put ITS OWN element in full screen and listen for the change itself, so:
 *  - clicking Workspace while a split pane had the controls put only that
 *    pane in full screen (the layout jumped when moving between panes);
 *  - the other viewers saw "I am not full screen" and released the Esc key
 *    lock the first one had just taken, so a plain Esc dropped out of full
 *    screen;
 *  - the button read "Workspace" in a pane while the screen was full.
 *
 * Now the PAGE goes full screen (document.documentElement) and the
 * workspace, pinned to the window, simply fills it. One listener keeps the
 * shared state (`ws.fullscreen`) and holds the Esc lock for as long as full
 * screen lasts; F11 is handled once. A plain Esc press stays with the page
 * (tools use it); only the browser's "hold Esc" safety exit leaves full
 * screen, and the Workspace button does.
 */
import { getShared, setShared } from './shared-state';

export const FS_KEY = 'ws.fullscreen';
export const WORKSPACE_KEY = 'ws.workspace';
export const VIEW_PREF_KEY = 'ws.viewPref';
export type ViewPref = 'fullscreen' | 'normal';

type Keyboard = { lock?: (keys?: string[]) => Promise<void>; unlock?: () => void };
const keyboard = (): Keyboard | undefined => (navigator as unknown as { keyboard?: Keyboard }).keyboard;

let ourExit = false;
let viewers = 0;
let installed = false;

export function isPageFullscreen(): boolean {
  return typeof document !== 'undefined' && !!document.fullscreenElement;
}

export function readViewPref(): ViewPref {
  try {
    return localStorage.getItem('takeoff.viewMode') === 'normal' ? 'normal' : 'fullscreen';
  } catch {
    return 'fullscreen';
  }
}

export function readWorkspace(): boolean {
  try {
    return localStorage.getItem('takeoff.fsftmWorkspace') !== '0';
  } catch {
    return true;
  }
}

function setPref(pref: ViewPref) {
  setShared<ViewPref>(VIEW_PREF_KEY, () => pref);
  try { localStorage.setItem('takeoff.viewMode', pref); } catch { /* ignore */ }
}

export function setWorkspace(on: boolean) {
  setShared<boolean>(WORKSPACE_KEY, () => on);
  try { localStorage.setItem('takeoff.fsftmWorkspace', on ? '1' : '0'); } catch { /* ignore */ }
}

/** Can this page keep Esc from leaving full screen? The browser allows the
 *  Esc lock only on a secure address (https://, or localhost); on a plain
 *  http:// server address Esc always leaves full screen. */
export function escLockSupported(): boolean {
  return typeof window !== 'undefined' && window.isSecureContext && !!keyboard()?.lock;
}

let escNoticeShown = false;
/** True once per page load: show the "Esc lock needs https" notice. */
export function takeEscNotice(): boolean {
  if (escNoticeShown || escLockSupported()) return false;
  escNoticeShown = true;
  return true;
}

function lockEsc() {
  try { void keyboard()?.lock?.(['Escape'])?.catch?.(() => undefined); } catch { /* not supported */ }
}

/** Full screen for the whole workspace (keeps the choice). */
export function enterFullscreen(): void {
  setPref('fullscreen');
  setWorkspace(true);
  if (isPageFullscreen()) {
    lockEsc();
    return;
  }
  const el = document.documentElement;
  try {
    const p = el.requestFullscreen?.({ navigationUI: 'hide' });
    void p?.then(lockEsc).catch(() => undefined);
  } catch { /* not allowed now */ }
}

/** Back to the normal page (keeps the choice). */
export function exitFullscreen(): void {
  setPref('normal');
  setWorkspace(false);
  try { keyboard()?.unlock?.(); } catch { /* ignore */ }
  if (isPageFullscreen()) {
    ourExit = true;
    void document.exitFullscreen?.()?.catch?.(() => undefined);
  }
}

export function toggleFullscreen(): void {
  if (isPageFullscreen()) exitFullscreen();
  else enterFullscreen();
}

/** Called by each viewer while it is mounted; the first one installs the
 *  page-wide listeners. Returns the cleanup. */
export function registerFullscreenViewer(): () => void {
  viewers++;
  if (!installed && typeof document !== 'undefined') {
    installed = true;
    setShared<boolean>(FS_KEY, () => isPageFullscreen());
    document.addEventListener('fullscreenchange', () => {
      const on = isPageFullscreen();
      setShared<boolean>(FS_KEY, () => on);
      if (on) {
        lockEsc();
      } else {
        try { keyboard()?.unlock?.(); } catch { /* ignore */ }
        // Left by the browser itself (holding Esc, or a browser without the
        // Esc lock): keep the big full-window workspace - never drop to the
        // small normal page by surprise. Workspace goes full screen again;
        // only Exit workspace returns to the normal page.
        if (!ourExit && getShared<ViewPref>(VIEW_PREF_KEY) === 'fullscreen') {
          setWorkspace(true);
        }
        ourExit = false;
      }
    });
    window.addEventListener('keydown', (e) => {
      if (viewers <= 0 || e.key !== 'F11') return;
      e.preventDefault();
      toggleFullscreen();
    });
  }
  return () => {
    viewers = Math.max(0, viewers - 1);
  };
}
