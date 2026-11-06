// OE-DELIVERY: 2026-11-05-upload-progress
import { useEffect, useState } from 'react';
import { formatTimeLeft, uploadStats, type UploadProgress } from '../lib/upload-progress';

/** Upload progress: bar + "42% · 12.4 / 30.1 MB · 9 s left", then
 *  "Reading drawing…" while the server opens the PDF. */
export function UploadProgressBar({ progress, compact = false }: { progress?: UploadProgress; compact?: boolean }) {
  // Re-render each second so the time left keeps moving between events.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const s = progress ? uploadStats(progress, Math.max(now, Date.now())) : null;
  const processing = !s || s.processing;
  const text = !s
    ? 'Starting upload…'
    : s.processing
      ? 'Uploaded · reading drawing…'
      : `${s.percent}% · ${s.sentMB} / ${s.totalMB} MB · ${formatTimeLeft(s.secondsLeft)}`;
  return (
    <div className={compact ? 'mt-1' : 'mt-2'} data-testid="upload-progress">
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-surface-tertiary"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={s ? s.percent : 0}
        aria-label="Upload progress"
      >
        <div
          className={processing && s ? 'h-full w-full animate-pulse bg-oe-blue/70' : 'h-full bg-oe-blue transition-[width] duration-200'}
          style={processing && s ? undefined : { width: `${s ? Math.max(2, s.percent) : 2}%` }}
        />
      </div>
      <p className={compact ? 'mt-0.5 text-[10px] text-content-tertiary truncate' : 'mt-1 text-xs text-content-tertiary'} data-testid="upload-progress-text">
        {text}
      </p>
    </div>
  );
}
