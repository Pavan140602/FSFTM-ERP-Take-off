import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { pdfHolders, releasePdf, retainPdf } from './pdf-doc-pool';

const fakeDoc = () => ({ destroy: vi.fn(() => Promise.resolve()) }) as unknown as PDFDocumentProxy & { destroy: ReturnType<typeof vi.fn> };

describe('pdf-doc-pool (drawings shared between panes)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('keeps a drawing while any pane still shows it', () => {
    const d = fakeDoc();
    retainPdf(d);
    retainPdf(d);
    releasePdf(d);
    vi.advanceTimersByTime(5000);
    expect(d.destroy).not.toHaveBeenCalled();
    expect(pdfHolders(d)).toBe(1);
    releasePdf(d);
    vi.advanceTimersByTime(5000);
    expect(d.destroy).toHaveBeenCalledTimes(1);
  });

  it('survives a hand-over from one pane to another', () => {
    const d = fakeDoc();
    retainPdf(d);
    releasePdf(d); // dragged out of pane A ...
    retainPdf(d); // ... and dropped into pane B
    vi.advanceTimersByTime(5000);
    expect(d.destroy).not.toHaveBeenCalled();
  });
});
