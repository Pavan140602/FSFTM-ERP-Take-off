// OE-DELIVERY: 2026-10-20-pdf-grid-thumbnail-v1
// PdfThumbnail — renders the first page of a PDF as a grid-card thumbnail.
//
// The file-list API returns thumbnail_url only for photos/drawings, so PDF
// documents used to show a plain icon on their cards. This component fills
// that gap on the frontend: when the card scrolls into view it opens the
// PDF through the shared pdf.js binding (range requests + auth header, so
// only the bytes page 1 needs are fetched), paints page 1 to an offscreen
// canvas and keeps the resulting image in a module-level cache keyed by
// URL, so scrolling and re-renders never fetch or render twice. Any
// failure (not a PDF, network, render error) falls back to the caller's
// placeholder icon.

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { openPdfUrl, closePdf } from '@/shared/lib/pdfjs';
import { useAuthStore } from '@/stores/useAuthStore';

const THUMB_WIDTH = 480;

const cache = new Map<string, string>();
const inflight = new Map<string, Promise<string | null>>();

async function renderFirstPage(url: string): Promise<string | null> {
  const token = useAuthStore.getState().accessToken;
  const httpHeaders: Record<string, string> = {};
  if (token) httpHeaders['Authorization'] = `Bearer ${token}`;
  const loadingTask = openPdfUrl(url, httpHeaders);
  try {
    const doc = await loadingTask.promise;
    try {
      const page = await doc.getPage(1);
      const base = page.getViewport({ scale: 1 });
      const viewport = page.getViewport({ scale: THUMB_WIDTH / base.width });
      const canvas = document.createElement('canvas');
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      // PDF pages can be transparent; thumbnails read best on white.
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      await page.render({ canvas, viewport }).promise;
      return canvas.toDataURL('image/jpeg', 0.82);
    } finally {
      closePdf(doc);
    }
  } catch {
    return null;
  }
}

function loadThumbnail(url: string): Promise<string | null> {
  const hit = cache.get(url);
  if (hit) return Promise.resolve(hit);
  const pending = inflight.get(url);
  if (pending) return pending;
  const p = renderFirstPage(url).then((dataUrl) => {
    inflight.delete(url);
    if (dataUrl) cache.set(url, dataUrl);
    return dataUrl;
  });
  inflight.set(url, p);
  return p;
}

export function PdfThumbnail({ url, fallback }: { url: string; fallback: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [dataUrl, setDataUrl] = useState<string | null>(() => cache.get(url) ?? null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (dataUrl || failed) return;
    const el = ref.current;
    if (!el) return;
    let cancelled = false;
    const start = () => {
      void loadThumbnail(url).then((result) => {
        if (cancelled) return;
        if (result) setDataUrl(result);
        else setFailed(true);
      });
    };
    if (typeof IntersectionObserver === 'undefined') {
      start();
      return () => {
        cancelled = true;
      };
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect();
          start();
        }
      },
      { rootMargin: '240px' },
    );
    observer.observe(el);
    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [url, dataUrl, failed]);

  if (dataUrl) {
    return <img src={dataUrl} alt="" className="h-full w-full object-cover" />;
  }
  return (
    <div ref={ref} className="flex h-full w-full items-center justify-center">
      {fallback}
    </div>
  );
}
