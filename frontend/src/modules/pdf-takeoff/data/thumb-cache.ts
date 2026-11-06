// OE-DELIVERY: 2026-11-12-revu-ui (thumbnail speed fix)
/**
 * Page thumbnails kept in the browser (IndexedDB), so reopening a drawing
 * shows its thumbnails at once instead of rendering every page again.
 * Best-effort: any storage error just means "not cached".
 */
const DB = 'oe-takeoff-thumbs';
const STORE = 'thumbs';
const MAX_ENTRIES = 3000;

let dbp: Promise<IDBDatabase | null> | null = null;
function db(): Promise<IDBDatabase | null> {
  if (dbp) return dbp;
  dbp = new Promise((resolve) => {
    try {
      if (typeof indexedDB === 'undefined') return resolve(null);
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => {
        const d = req.result;
        if (!d.objectStoreNames.contains(STORE)) d.createObjectStore(STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbp;
}

export async function thumbCacheGet(key: string): Promise<string | null> {
  const d = await db();
  if (!d) return null;
  return new Promise((resolve) => {
    try {
      const req = d.transaction(STORE, 'readonly').objectStore(STORE).get(key);
      req.onsuccess = () => resolve(typeof req.result === 'string' ? req.result : null);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

let writes = 0;
export async function thumbCachePut(key: string, url: string): Promise<void> {
  const d = await db();
  if (!d) return;
  try {
    const tx = d.transaction(STORE, 'readwrite');
    const st = tx.objectStore(STORE);
    st.put(url, key);
    // Now and then keep the store bounded (oldest keys go first).
    if (++writes % 200 === 0) {
      const cnt = st.count();
      cnt.onsuccess = () => {
        const over = cnt.result - MAX_ENTRIES;
        if (over <= 0) return;
        let left = over;
        const cur = st.openCursor();
        cur.onsuccess = () => {
          const c = cur.result;
          if (!c || left <= 0) return;
          c.delete();
          left--;
          c.continue();
        };
      };
    }
  } catch {
    /* quota / private mode: not cached */
  }
}
