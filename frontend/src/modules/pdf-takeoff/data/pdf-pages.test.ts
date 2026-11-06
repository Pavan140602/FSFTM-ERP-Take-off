import { describe, expect, it } from 'vitest';
import { PDFArray, PDFDocument, PDFName } from 'pdf-lib';
import { editPages, extractPages, makeSnapshot, saveVectorPdf, rotatePoint, type AnnotInput } from './pdf-pages';
import type { Measurement } from '../../../features/takeoff/lib/takeoff-types';

async function threePages(): Promise<Uint8Array> {
  const d = await PDFDocument.create();
  d.addPage([600, 400]);
  d.addPage([600, 400]);
  d.addPage([300, 300]);
  return d.save();
}
const sizes = async (b: Uint8Array) => (await PDFDocument.load(b)).getPages().map((p) => Math.round(p.getWidth()));

describe('pdf-pages', () => {
  it('extracts pages in order', async () => {
    const out = await extractPages(await threePages(), [3, 1]);
    expect(await sizes(out)).toEqual([300, 600]);
  });
  it('deletes and maps', async () => {
    const r = await editPages(await threePages(), { kind: 'delete', pages: [2] });
    expect(r.numPages).toBe(2);
    expect(r.pageMap).toEqual({ 1: 1, 3: 2 });
  });
  it('inserts blank after a page and at the start', async () => {
    const r = await editPages(await threePages(), { kind: 'insertBlank', after: 1, count: 2 });
    expect(r.numPages).toBe(5);
    expect(r.pageMap).toEqual({ 1: 1, 2: 4, 3: 5 });
    const r0 = await editPages(await threePages(), { kind: 'insertBlank', after: 0, count: 1 });
    expect(r0.pageMap).toEqual({ 1: 2, 2: 3, 3: 4 });
  });
  it('inserts and replaces from another PDF', async () => {
    const other = await extractPages(await threePages(), [3]);
    const ins = await editPages(await threePages(), { kind: 'insertPdf', after: 3, other });
    expect(await sizes(ins.bytes)).toEqual([600, 600, 300, 300]);
    const rep = await editPages(await threePages(), { kind: 'replace', pages: [1], other });
    expect(await sizes(rep.bytes)).toEqual([300, 600, 300]);
    expect(rep.pageMap).toEqual({ 2: 2, 3: 3 });
  });
  it('rotates', async () => {
    const r = await editPages(await threePages(), { kind: 'rotate', pages: [1], deg: 90 });
    const d = await PDFDocument.load(r.bytes);
    expect(d.getPage(0).getRotation().angle).toBe(90);
    expect(rotatePoint({ x: 10, y: 20 }, 90, 600, 400)).toEqual({ x: 380, y: 10 });
  });
  it('saves markups as annotations + snapshot, and a re-save does not stack them', async () => {
    const m = { id: 'a1', type: 'polyline', page: 1, points: [{ x: 10, y: 10 }, { x: 100, y: 50 }, { x: 200, y: 10 }], value: 1, unit: 'm', label: '', annotation: 'W12x26', group: 'General' } as unknown as Measurement;
    const c = { id: 'c1', type: 'cloud', page: 2, points: [{ x: 10, y: 10 }, { x: 100, y: 10 }, { x: 100, y: 80 }], value: 0, unit: '', label: '', annotation: '', group: 'General' } as unknown as Measurement;
    const toPdf = (p: { x: number; y: number }) => ({ x: p.x, y: 400 - p.y });
    const byPage = new Map<number, AnnotInput[]>([
      [1, [{ m, color: '#00ff00', toPdf, text: 'W12x26' }]],
      [2, [{ m: c, color: '#ff0000', toPdf, text: '' }]],
    ]);
    const snap = makeSnapshot([m, c], { 1: 1, 2: 2 }, { 1: { w: 600, h: 400 }, 2: { w: 600, h: 400 } });
    const first = await saveVectorPdf(await threePages(), byPage, snap);
    expect(first.annots).toBe(2);
    const again = await saveVectorPdf(first.bytes, byPage, snap);
    const d = await PDFDocument.load(again.bytes);
    const a1 = d.getPage(0).node.lookup(PDFName.of('Annots'), PDFArray);
    expect(a1.size()).toBe(1);
    expect(d.getPageCount()).toBe(3);
    expect(d.getKeywords()?.startsWith('OE-TAKEOFF:')).toBe(true);
  });
});

describe('combine + blank (u21)', () => {
  it('combines in order with offsets', async () => {
    const { combinePdfs, createBlankPdf } = await import('./pdf-pages');
    const a = await createBlankPdf(612, 792, 2);
    const b = await createBlankPdf(1224, 792, 3);
    const r = await combinePdfs([a, b]);
    expect(r.numPages).toBe(5);
    expect(r.offsets).toEqual([0, 2]);
    const d = await PDFDocument.load(r.bytes);
    expect(Math.round(d.getPage(2).getWidth())).toBe(1224);
  });
});
