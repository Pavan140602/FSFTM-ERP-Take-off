/**
 * Smooth, honest progress for loading a drawing (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * pdf.js reports progress in bursts (and, with range loading, may finish
 * long before every byte arrived), so the raw number jumps. The shown value
 * eases toward the real one each frame and never goes backwards; it shows
 * no number at all until real progress is known.
 */
import { useEffect, useRef, useState } from 'react';

export function useSmoothProgress(target: number | null): number | null {
  const [shown, setShown] = useState<number | null>(target);
  const ref = useRef({ shown: target ?? 0, target: target ?? 0, known: target !== null });
  useEffect(() => {
    const r = ref.current;
    if (target === null) {
      r.known = false;
      r.shown = 0;
      r.target = 0;
      setShown(null);
      return;
    }
    r.known = true;
    r.target = Math.max(r.target, Math.min(100, target)); // never backwards
    let raf = 0;
    const tick = () => {
      const d = r.target - r.shown;
      r.shown = Math.abs(d) < 0.4 ? r.target : r.shown + d * 0.18;
      setShown(Math.round(r.shown));
      if (r.shown !== r.target) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return shown;
}
