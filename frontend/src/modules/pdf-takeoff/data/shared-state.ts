/**
 * State shared by every mounted PDF viewer (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * Each open drawing keeps its own viewer alive in the background so that
 * switching drawings never reloads or blinks. The split layout (panes, the
 * drawings open in them, their pages and zoom) belongs to the WORKSPACE, not
 * to one drawing, so it lives here: whichever viewer is showing renders the
 * same panes. Works like `useState`, keyed by name.
 */
import { useCallback, useRef, useSyncExternalStore } from 'react';

type Setter<T> = (v: T | ((prev: T) => T)) => void;

const values = new Map<string, unknown>();
const subs = new Map<string, Set<() => void>>();

function emit(key: string) {
  subs.get(key)?.forEach((cb) => cb());
}

export function getShared<T>(key: string): T | undefined {
  return values.get(key) as T | undefined;
}

export function setShared<T>(key: string, v: T | ((prev: T) => T)): void {
  const prev = values.get(key) as T;
  const next = typeof v === 'function' ? (v as (p: T) => T)(prev) : v;
  if (Object.is(prev, next)) return;
  values.set(key, next);
  emit(key);
}

/** Forget every shared value whose key starts with `prefix`. */
export function clearShared(prefix: string): void {
  for (const key of [...values.keys()]) {
    if (!key.startsWith(prefix)) continue;
    values.delete(key);
    emit(key);
  }
}

export function useSharedState<T>(key: string, init: T | (() => T), paused = false): [T, Setter<T>] {
  if (!values.has(key)) values.set(key, typeof init === 'function' ? (init as () => T)() : init);
  // A paused reader (a viewer kept alive in the background) keeps the value
  // it last saw and is not re-rendered by changes; it catches up on resume.
  const frozen = useRef<T>(values.get(key) as T);
  const subscribe = useCallback(
    (cb: () => void) => {
      if (paused) return () => undefined;
      let s = subs.get(key);
      if (!s) {
        s = new Set();
        subs.set(key, s);
      }
      s.add(cb);
      return () => {
        s!.delete(cb);
      };
    },
    [key, paused],
  );
  const read = useCallback(() => {
    if (paused) return frozen.current;
    if (!values.has(key)) values.set(key, typeof init === 'function' ? (init as () => T)() : init);
    return values.get(key) as T;
    // `init` only seeds a missing value; it never changes the key's identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, paused]);
  const value = useSyncExternalStore(subscribe, read, read);
  if (!paused) frozen.current = value;
  const set = useCallback<Setter<T>>((v) => setShared(key, v), [key]);
  return [value, set];
}
