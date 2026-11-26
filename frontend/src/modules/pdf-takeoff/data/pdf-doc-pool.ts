/**
 * Shared ownership of open PDF documents (OE-DELIVERY 2026-11-26-fsftm-pdf).
 *
 * One loaded drawing can be shown in several places at once: the main viewer,
 * a split pane, the quick-switch cache. Moving a drawing between panes hands
 * the SAME loaded document over instead of downloading it again, so nobody
 * may destroy it while another place still shows it. Every holder retains
 * the document and releases it when done; the last release frees it (after a
 * short grace period, so a hand-over - release here, retain there - never
 * destroys it in between).
 */
import type { PDFDocumentProxy } from 'pdfjs-dist';

const refs = new Map<PDFDocumentProxy, number>();
const GRACE_MS = 1500;

export function retainPdf(doc: PDFDocumentProxy | null | undefined): void {
  if (!doc) return;
  refs.set(doc, (refs.get(doc) ?? 0) + 1);
}

export function releasePdf(doc: PDFDocumentProxy | null | undefined): void {
  if (!doc) return;
  const n = (refs.get(doc) ?? 0) - 1;
  if (n > 0) {
    refs.set(doc, n);
    return;
  }
  refs.delete(doc);
  window.setTimeout(() => {
    if (refs.has(doc)) return; // picked up again in the meantime
    try {
      void (doc as unknown as { destroy?: () => Promise<void> }).destroy?.();
    } catch {
      /* already gone */
    }
  }, GRACE_MS);
}

/** How many holders a document has (tests / diagnostics). */
export function pdfHolders(doc: PDFDocumentProxy): number {
  return refs.get(doc) ?? 0;
}
