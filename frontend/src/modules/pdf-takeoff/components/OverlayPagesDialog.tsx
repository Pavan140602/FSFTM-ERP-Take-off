// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * Overlay Pages: compare drawings by laying them over each other in colour.
 *
 * Pick two or more PDFs as layers (each with its own colour and pages - all,
 * current, selected or a custom range), align them (page align or manual
 * offset / rotation / scale), check the preview, and OK builds a NEW PDF
 * ("Overlay.pdf") with every layer drawn in its colour - opened as a new
 * document that asks to be saved. Layers that run out of pages simply add
 * nothing to the later pages; the dialog says when page counts differ.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';
import { AlertTriangle, ChevronLeft, ChevronRight, Pencil, Plus, X } from 'lucide-react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { openPdf } from '@/shared/lib/pdfjs';

export type OverlaySourceDoc = { id: string; name: string };
type PageMode = 'all' | 'current' | 'selected' | 'custom';
type Layer = {
  key: string;
  docId: string;
  name: string;
  color: string;
  mode: PageMode;
  custom: string;
  /** Manual align: offset (inches, from centre), rotation (deg), scale (x). */
  dx: number;
  dy: number;
  rot: number;
  scale: number;
};
type Defaults = { colors: string[]; blend: 'darken' | 'multiply'; opacity: number };

const DEFAULT_COLORS = ['#ff0000', '#00b400', '#0050ff', '#00c8c8', '#d200d2', '#d2c800', '#8c8c8c', '#000000'];
const DEFAULTS_KEY = 'takeoff.overlay.defaults';

function loadDefaults(): Defaults {
  try {
    const v = JSON.parse(localStorage.getItem(DEFAULTS_KEY) || 'null') as Partial<Defaults> | null;
    if (v && Array.isArray(v.colors) && v.colors.length >= 2) {
      return { colors: v.colors.slice(0, 8), blend: v.blend === 'multiply' ? 'multiply' : 'darken', opacity: Number(v.opacity) > 0 ? Number(v.opacity) : 100 };
    }
  } catch { /* ignore */ }
  return { colors: DEFAULT_COLORS, blend: 'darken', opacity: 100 };
}

/** "1-3, 5" -> [1, 2, 3, 5] within 1..n. */
export function parseRange(text: string, n: number): number[] {
  const out: number[] = [];
  for (const part of text.split(/[,;\s]+/).filter(Boolean)) {
    const m = /^(\d+)(?:-(\d+))?$/.exec(part);
    if (!m) continue;
    const a = Math.max(1, Number(m[1]));
    const b = Math.min(n, m[2] ? Number(m[2]) : a);
    for (let p = a; p <= b; p++) out.push(p);
  }
  return out;
}

const hexRgb = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  const v = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
};

export function OverlayPagesDialog({
  sources,
  selfId,
  selfDoc,
  currentPage,
  selectedPages,
  loadDoc,
  releaseDoc,
  onCreate,
  onClose,
}: {
  /** Drawings that can be layers (this one first). */
  sources: OverlaySourceDoc[];
  selfId: string;
  selfDoc: PDFDocumentProxy;
  currentPage: number;
  selectedPages: number[];
  loadDoc: (id: string, name: string) => Promise<PDFDocumentProxy | null>;
  releaseDoc: (doc: PDFDocumentProxy) => void;
  /** The finished overlay PDF. */
  onCreate: (file: File) => void;
  onClose: () => void;
}) {
  const [defaults, setDefaults] = useState<Defaults>(loadDefaults);
  const [layers, setLayers] = useState<Layer[]>(() => [
    { key: 'l0', docId: selfId, name: sources.find((s) => s.id === selfId)?.name ?? 'This drawing', color: loadDefaults().colors[0]!, mode: 'all', custom: '', dx: 0, dy: 0, rot: 0, scale: 1 },
  ]);
  const [docs, setDocs] = useState<Map<string, PDFDocumentProxy>>(() => new Map([[selfId, selfDoc]]));
  const heldRef = useRef<PDFDocumentProxy[]>([]);
  const [sel, setSel] = useState<string>('l0');
  const [align, setAlign] = useState<'page' | 'manual'>('page');
  const [addOpen, setAddOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [defaultsOpen, setDefaultsOpen] = useState(false);
  const [previewIdx, setPreviewIdx] = useState(0);
  const [progress, setProgress] = useState<number | null>(null);
  const cancelRef = useRef(false);
  const previewRef = useRef<HTMLCanvasElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => { for (const d of heldRef.current) releaseDoc(d); }, [releaseDoc]);

  const pagesOf = (l: Layer): number[] => {
    const d = docs.get(l.docId);
    const n = d?.numPages ?? 0;
    if (!n) return [];
    if (l.mode === 'all') return Array.from({ length: n }, (_, i) => i + 1);
    if (l.mode === 'current') return [l.docId === selfId ? Math.min(currentPage, n) : 1];
    if (l.mode === 'selected') {
      const s = l.docId === selfId ? selectedPages.filter((p) => p <= n) : [];
      return s.length ? s : [l.docId === selfId ? Math.min(currentPage, n) : 1];
    }
    return parseRange(l.custom, n);
  };
  const lists = layers.map(pagesOf);
  const outCount = Math.max(0, ...lists.map((x) => x.length));
  const ready = layers.length >= 2 && layers.every((l) => docs.has(l.docId)) && outCount > 0;
  const uneven = layers.length >= 2 && new Set(lists.map((x) => x.length)).size > 1;

  const addLayer = async (id: string, name: string, preloaded?: PDFDocumentProxy) => {
    setAddOpen(false);
    const key = `l${Date.now()}${Math.random().toString(36).slice(2, 5)}`;
    setLayers((prev) => [
      ...prev,
      { key, docId: id, name, color: defaults.colors[prev.length % defaults.colors.length]!, mode: id === selfId ? 'current' : 'all', custom: '', dx: 0, dy: 0, rot: 0, scale: 1 },
    ]);
    setSel(key);
    if (docs.has(id)) return;
    const d = preloaded ?? (await loadDoc(id, name));
    if (!d) {
      setLayers((prev) => prev.filter((l) => l.key !== key));
      return;
    }
    if (!preloaded) heldRef.current.push(d);
    setDocs((prev) => new Map(prev).set(id, d));
  };

  /** One output page: every layer's page in its colour, aligned on the first layer's page. */
  const compose = async (idx: number, maxPx: number, quick = false): Promise<{ canvas: HTMLCanvasElement; w: number; h: number } | null> => {
    const parts: { l: Layer; doc: PDFDocumentProxy; page: number }[] = [];
    layers.forEach((l, i) => {
      const doc = docs.get(l.docId);
      const pg = lists[i]?.[idx];
      if (doc && pg) parts.push({ l, doc, page: pg });
    });
    if (!parts.length) return null;
    const basePage = await parts[0]!.doc.getPage(parts[0]!.page);
    const bv = basePage.getViewport({ scale: 1 });
    const pxPerPt = maxPx / Math.max(bv.width, bv.height);
    const out = document.createElement('canvas');
    out.width = Math.round(bv.width * pxPerPt);
    out.height = Math.round(bv.height * pxPerPt);
    const octx = out.getContext('2d')!;
    octx.fillStyle = '#ffffff';
    octx.fillRect(0, 0, out.width, out.height);
    for (const { l, doc, page } of parts) {
      const pg = await doc.getPage(page);
      const v1 = pg.getViewport({ scale: 1 });
      const fit = Math.min(bv.width / v1.width, bv.height / v1.height) * (align === 'manual' ? l.scale : 1);
      const vp = pg.getViewport({ scale: fit * pxPerPt });
      const tmp = document.createElement('canvas');
      tmp.width = Math.ceil(vp.width);
      tmp.height = Math.ceil(vp.height);
      await pg.render({ canvas: tmp, viewport: vp, ...(quick ? { intent: 'display' } : {}) }).promise;
      const tctx = tmp.getContext('2d')!;
      const img = tctx.getImageData(0, 0, tmp.width, tmp.height);
      const d = img.data;
      const [r, g, b] = hexRgb(l.color);
      for (let i = 0; i < d.length; i += 4) {
        const ink = 255 - (d[i]! * 0.3 + d[i + 1]! * 0.59 + d[i + 2]! * 0.11);
        d[i] = r;
        d[i + 1] = g;
        d[i + 2] = b;
        d[i + 3] = ink < 20 ? 0 : Math.min(255, ink * 1.4);
      }
      tctx.putImageData(img, 0, 0);
      octx.save();
      octx.globalCompositeOperation = defaults.blend;
      octx.globalAlpha = Math.max(0.05, Math.min(1, defaults.opacity / 100));
      const m = align === 'manual';
      octx.translate(out.width / 2 + (m ? l.dx * 72 * pxPerPt : 0), out.height / 2 + (m ? l.dy * 72 * pxPerPt : 0));
      if (m && l.rot) octx.rotate((l.rot * Math.PI) / 180);
      octx.drawImage(tmp, -tmp.width / 2, -tmp.height / 2);
      octx.restore();
    }
    return { canvas: out, w: bv.width, h: bv.height };
  };

  // Live preview of the page in view.
  const previewSig = JSON.stringify([layers, align, defaults, previewIdx, [...docs.keys()]]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const c = previewRef.current;
      if (!c) return;
      const res = await compose(Math.min(previewIdx, Math.max(0, outCount - 1)), 900, true).catch(() => null);
      if (cancelled) return;
      const ctx = c.getContext('2d')!;
      if (!res) {
        c.width = 10;
        c.height = 10;
        ctx.clearRect(0, 0, 10, 10);
        return;
      }
      c.width = res.canvas.width;
      c.height = res.canvas.height;
      ctx.drawImage(res.canvas, 0, 0);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewSig, outCount]);

  const run = async () => {
    if (!ready) return;
    cancelRef.current = false;
    setProgress(0);
    try {
      const { PDFDocument } = await import('pdf-lib');
      const pdf = await PDFDocument.create();
      for (let i = 0; i < outCount; i++) {
        if (cancelRef.current) {
          setProgress(null);
          return;
        }
        const res = await compose(i, 4200);
        if (res) {
          const blob: Blob = await new Promise((ok) => res.canvas.toBlob((b) => ok(b!), 'image/jpeg', 0.9));
          const jpg = await pdf.embedJpg(new Uint8Array(await blob.arrayBuffer()));
          const page = pdf.addPage([res.w, res.h]);
          page.drawImage(jpg, { x: 0, y: 0, width: res.w, height: res.h });
        }
        setProgress(Math.round(((i + 1) / outCount) * 100));
      }
      const bytes = await pdf.save();
      onCreate(new File([bytes as unknown as BlobPart], 'Overlay.pdf', { type: 'application/pdf' }));
    } finally {
      setProgress(null);
    }
  };

  const selLayer = layers.find((l) => l.key === sel) ?? null;
  const setLayer = (key: string, patch: Partial<Layer>) => setLayers((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  const notAdded = useMemo(() => sources.filter((s) => !layers.some((l) => l.docId === s.id)), [sources, layers]);
  const input = 'h-6 rounded border border-white/15 bg-[#1e1e1e] px-1 text-[12px] text-white';

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center bg-black/50" data-testid="overlay-dialog">
      <div className="flex max-h-[94vh] w-[960px] max-w-[96vw] flex-col rounded-md border border-white/10 bg-[#2b2b2b] text-[12px] text-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
          <span className="text-[13px]">Overlay Pages</span>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded p-0.5 hover:bg-white/10"><X size={15} /></button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
          {layers.length < 2 && (
            <div className="flex items-center gap-2 rounded bg-[#7a5a14] px-3 py-1.5" data-testid="overlay-warn-layers">
              <AlertTriangle size={14} /> Overlay requires at least 2 layers to continue. Please select files to add layers.
              <button type="button" className="font-semibold underline" onClick={() => setAddOpen(true)}>[+]</button>
            </div>
          )}
          {uneven && (
            <div className="flex items-center gap-2 rounded bg-[#7a5a14] px-3 py-1.5" data-testid="overlay-warn-pages">
              <AlertTriangle size={14} /> All layers don&apos;t have the same amount of pages.
            </div>
          )}
          <div className="rounded border border-white/10">
            <div className="grid grid-cols-[1.6fr_70px_1.4fr_220px] border-b border-white/10 bg-[#333] px-2 py-1 text-white/70">
              <span>Document</span><span>Color</span><span>Layer</span><span>Pages</span>
            </div>
            <div className="max-h-44 min-h-[110px] overflow-y-auto">
              {layers.map((l, i) => {
                const d = docs.get(l.docId);
                const n = d?.numPages ?? 0;
                return (
                  <div
                    key={l.key}
                    onClick={() => setSel(l.key)}
                    className={clsx('grid grid-cols-[1.6fr_70px_1.4fr_220px] items-center gap-1 px-2 py-1', sel === l.key && 'bg-[#1f6fd1]/40')}
                    data-testid="overlay-layer"
                  >
                    <span className="truncate" title={l.name}>{l.name}{!d && ' (opening…)'}</span>
                    <label className="flex items-center">
                      <span className="h-4 w-4 rounded-sm border border-white/50" style={{ backgroundColor: l.color }} />
                      <input type="color" value={l.color} onChange={(e) => setLayer(l.key, { color: e.target.value })} className="ml-1 h-5 w-6 cursor-pointer bg-transparent" aria-label={`Colour of layer ${i + 1}`} />
                    </label>
                    <input value={l.name} onChange={(e) => setLayer(l.key, { name: e.target.value })} className={clsx(input, 'min-w-0')} />
                    <span className="flex items-center gap-1">
                      <select
                        value={l.mode}
                        onChange={(e) => setLayer(l.key, { mode: e.target.value as PageMode })}
                        className={clsx(input, 'flex-1')}
                        data-testid="overlay-layer-pages"
                      >
                        <option value="all">All Pages (1 - {n || '…'})</option>
                        <option value="current">Current ({l.docId === selfId ? currentPage : 1})</option>
                        <option value="selected">Selected ({l.docId === selfId ? selectedPages.length || 1 : 1})</option>
                        <option value="custom">Custom Range</option>
                      </select>
                      {l.mode === 'custom' ? (
                        <input value={l.custom} placeholder="1-3,5" onChange={(e) => setLayer(l.key, { custom: e.target.value })} className={clsx(input, 'w-16')} />
                      ) : (
                        <span className="w-10 rounded border border-white/15 px-1 text-right tabular-nums">{lists[i]?.length ?? 0}</span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="relative flex items-center gap-1">
            <button type="button" onClick={() => setAddOpen((v) => !v)} className="rounded p-1 hover:bg-white/10" title="Add layer" data-testid="overlay-add"><Plus size={15} /></button>
            <button type="button" disabled={!selLayer || align !== 'manual'} onClick={() => setEditOpen(true)} className="rounded p-1 hover:bg-white/10 disabled:opacity-30" title="Position of the selected layer (Manual Align)"><Pencil size={14} /></button>
            <button type="button" disabled={!selLayer || layers.length <= 1} onClick={() => selLayer && setLayers((prev) => prev.filter((x) => x.key !== selLayer.key))} className="rounded p-1 hover:bg-white/10 disabled:opacity-30" title="Remove layer"><X size={15} /></button>
            <select value={align} onChange={(e) => setAlign(e.target.value as 'page' | 'manual')} className={clsx(input, 'ml-auto')} data-testid="overlay-align">
              <option value="page">Page Align</option>
              <option value="manual">Manual Align</option>
            </select>
            {addOpen && (
              <div className="absolute left-0 top-full z-10 mt-1 w-80 rounded border border-white/15 bg-[#252525] py-1 shadow-xl" data-testid="overlay-add-menu">
                <button type="button" className="block w-full px-3 py-1 text-left hover:bg-[#1f6fd1]" onClick={() => fileRef.current?.click()}>Add Files…</button>
                <button
                  type="button"
                  className="block w-full px-3 py-1 text-left hover:bg-[#1f6fd1]"
                  onClick={() => { for (const s of notAdded) void addLayer(s.id, s.name); }}
                >
                  Add Open Files
                </button>
                <div className="my-1 border-t border-white/10" />
                {notAdded.length === 0 && <div className="px-3 py-1 text-white/50">No other drawings open</div>}
                {notAdded.map((s) => (
                  <button key={s.id} type="button" className="block w-full truncate px-3 py-1 text-left hover:bg-[#1f6fd1]" onClick={() => void addLayer(s.id, s.name)} title={s.name}>
                    {s.name}
                  </button>
                ))}
              </div>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                e.target.value = '';
                if (!f) return;
                const d = await openPdf(await f.arrayBuffer(), { fastImages: true }).promise;
                heldRef.current.push(d);
                await addLayer(`file:${f.name}:${Date.now()}`, f.name, d);
                setDocs((prev) => new Map(prev));
              }}
            />
          </div>
          <fieldset className="rounded border border-white/10 px-2 pb-2">
            <legend className="px-1 text-white/70">Preview</legend>
            <div className="relative flex h-[380px] items-center justify-center bg-white/5">
              <canvas ref={previewRef} className="max-h-full max-w-full bg-white" data-testid="overlay-preview" />
              {outCount > 1 && (
                <>
                  <button type="button" onClick={() => setPreviewIdx((i) => Math.max(0, i - 1))} className="absolute left-2 rounded border border-white/20 bg-black/40 p-1"><ChevronLeft size={16} /></button>
                  <button type="button" onClick={() => setPreviewIdx((i) => Math.min(outCount - 1, i + 1))} className="absolute right-2 rounded border border-white/20 bg-black/40 p-1"><ChevronRight size={16} /></button>
                  <span className="absolute bottom-1 rounded bg-black/50 px-2 text-[11px]">Page {Math.min(previewIdx, outCount - 1) + 1} of {outCount}</span>
                </>
              )}
            </div>
          </fieldset>
        </div>
        <div className="flex items-center gap-2 border-t border-white/10 px-3 py-2">
          <button type="button" onClick={() => setDefaultsOpen(true)} className="rounded border border-white/20 px-3 py-1 hover:bg-white/10">Edit Defaults</button>
          <span className="flex-1" />
          <button type="button" disabled={!ready} onClick={() => void run()} className="rounded bg-[#1f6fd1] px-6 py-1 font-semibold disabled:opacity-40" data-testid="overlay-ok">OK</button>
          <button type="button" onClick={onClose} className="rounded border border-white/20 px-4 py-1 hover:bg-white/10">Cancel</button>
        </div>
      </div>

      {editOpen && selLayer && (
        <div className="fixed inset-0 z-[96] flex items-center justify-center bg-black/40">
          <div className="w-[380px] rounded-md border border-white/10 bg-[#2b2b2b] p-3 text-[12px] text-white shadow-2xl">
            <div className="mb-2 font-semibold">Position - {selLayer.name}</div>
            {([['Rotation (deg)', 'rot', 1], ['Scale (x)', 'scale', 0.01], ['Offset X (in, from centre)', 'dx', 0.05], ['Offset Y (in, from centre)', 'dy', 0.05]] as const).map(([lbl, k, step]) => (
              <label key={k} className="mb-1.5 flex items-center gap-2">
                <span className="w-44 text-white/70">{lbl}</span>
                <input type="number" step={step} value={selLayer[k]} onChange={(e) => setLayer(selLayer.key, { [k]: Number(e.target.value) || (k === 'scale' ? 1 : 0) })} className={clsx(input, 'w-24 text-right')} />
              </label>
            ))}
            <div className="mt-2 flex justify-end gap-2">
              <button type="button" onClick={() => setLayer(selLayer.key, { rot: 0, scale: 1, dx: 0, dy: 0 })} className="rounded border border-white/20 px-3 py-1">Reset</button>
              <button type="button" onClick={() => setEditOpen(false)} className="rounded bg-[#1f6fd1] px-4 py-1 font-semibold">OK</button>
            </div>
          </div>
        </div>
      )}

      {defaultsOpen && (
        <div className="fixed inset-0 z-[96] flex items-center justify-center bg-black/40">
          <div className="w-[440px] rounded-md border border-white/10 bg-[#2b2b2b] p-3 text-[12px] text-white shadow-2xl" data-testid="overlay-defaults">
            <div className="mb-2 font-semibold">Appearance</div>
            <div className="mb-2 grid grid-cols-2 gap-1">
              {defaults.colors.map((c, i) => (
                <label key={i} className="flex items-center gap-2">
                  <span className="w-14 text-white/70">Layer {i + 1}:</span>
                  <input type="color" value={c} onChange={(e) => setDefaults((d) => ({ ...d, colors: d.colors.map((x, j) => (j === i ? e.target.value : x)) }))} className="h-5 w-8 bg-transparent" />
                </label>
              ))}
            </div>
            <label className="mb-1.5 flex items-center gap-2">
              <span className="w-32 text-white/70">Default Blend:</span>
              <select value={defaults.blend} onChange={(e) => setDefaults((d) => ({ ...d, blend: e.target.value as Defaults['blend'] }))} className={input}>
                <option value="darken">Darken</option>
                <option value="multiply">Multiply</option>
              </select>
            </label>
            <label className="mb-1.5 flex items-center gap-2">
              <span className="w-32 text-white/70">Default Opacity:</span>
              <input type="number" min={5} max={100} value={defaults.opacity} onChange={(e) => setDefaults((d) => ({ ...d, opacity: Number(e.target.value) || 100 }))} className={clsx(input, 'w-20 text-right')} /> %
            </label>
            <div className="mt-2 flex justify-end gap-2">
              <button type="button" onClick={() => setDefaults({ colors: DEFAULT_COLORS, blend: 'darken', opacity: 100 })} className="rounded border border-white/20 px-3 py-1">Reset</button>
              <button
                type="button"
                onClick={() => {
                  try { localStorage.setItem(DEFAULTS_KEY, JSON.stringify(defaults)); } catch { /* ignore */ }
                  setDefaultsOpen(false);
                }}
                className="rounded bg-[#1f6fd1] px-4 py-1 font-semibold"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}

      {progress !== null && (
        <div className="fixed inset-0 z-[97] flex items-center justify-center bg-black/30" data-testid="overlay-progress">
          <div className="w-[460px] rounded-md border border-white/10 bg-[#2b2b2b] p-3 text-white shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <span>Overlaying Pages</span>
              <span className="tabular-nums text-white/70">{progress}%</span>
            </div>
            <div className="mb-3 h-2 overflow-hidden rounded bg-white/10">
              <div className="h-full bg-[#1f6fd1] transition-[width]" style={{ width: `${progress}%` }} />
            </div>
            <div className="flex justify-end">
              <button type="button" onClick={() => { cancelRef.current = true; }} className="rounded bg-[#1f6fd1] px-4 py-1 font-semibold">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
