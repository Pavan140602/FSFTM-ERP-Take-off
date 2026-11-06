// OE-DELIVERY: 2026-11-05-upload-progress
/**
 * Upload with progress for the takeoff drawings strip.
 *
 * ``fetch`` cannot report upload progress, so the PDF goes up through
 * XMLHttpRequest and reports bytes sent; ``uploadStats`` turns that into
 * percent, MB sent and time left for the progress bar.
 */

export interface UploadProgress {
  loaded: number;
  total: number;
  /** ms timestamp the upload started. */
  startedAt: number;
}

export interface UploadStats {
  percent: number;
  sentMB: number;
  totalMB: number;
  /** Seconds left at the current average speed (null until measurable). */
  secondsLeft: number | null;
  /** All bytes sent: the server is reading the drawing. */
  processing: boolean;
}

const MB = 1024 * 1024;

export function uploadStats(p: UploadProgress, now: number = Date.now()): UploadStats {
  const total = Math.max(p.total, 0);
  const loaded = Math.min(Math.max(p.loaded, 0), total || p.loaded);
  const percent = total > 0 ? Math.min(100, Math.floor((loaded / total) * 100)) : 0;
  const elapsed = (now - p.startedAt) / 1000;
  let secondsLeft: number | null = null;
  if (loaded > 0 && total > 0 && elapsed >= 0.4 && loaded < total) {
    const speed = loaded / elapsed;
    secondsLeft = speed > 0 ? Math.max(0, Math.ceil((total - loaded) / speed)) : null;
  }
  return {
    percent,
    sentMB: Math.round((loaded / MB) * 10) / 10,
    totalMB: Math.round((total / MB) * 10) / 10,
    secondsLeft,
    processing: total > 0 && loaded >= total,
  };
}

/** 75 -> "1 min 15 s left", 8 -> "8 s left". */
export function formatTimeLeft(seconds: number | null): string {
  if (seconds === null) return 'estimating time…';
  if (seconds < 1) return 'almost done';
  if (seconds < 60) return `${seconds} s left`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m} min ${s} s left` : `${m} min left`;
}

export class UploadHttpError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** POST ``body`` with progress callbacks; resolves with the JSON reply.
 *  Error replies surface FastAPI's ``detail`` like the old fetch code. */
export function xhrUpload<T>(
  url: string,
  body: FormData,
  headers: Record<string, string>,
  onProgress?: (loaded: number, total: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    xhr.responseType = 'text';
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded, e.total);
      };
      xhr.upload.onload = () => onProgress(1, 1);
    }
    xhr.onload = () => {
      let parsed: unknown = null;
      try {
        parsed = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        parsed = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(parsed as T);
        return;
      }
      const detail = (parsed as { detail?: unknown } | null)?.detail;
      reject(new UploadHttpError(typeof detail === 'string' && detail ? detail : xhr.statusText || `HTTP ${xhr.status}`, xhr.status));
    };
    xhr.onerror = () => reject(new Error('Network error - check the connection and try again.'));
    xhr.onabort = () => reject(new Error('Upload cancelled.'));
    xhr.send(body);
  });
}
