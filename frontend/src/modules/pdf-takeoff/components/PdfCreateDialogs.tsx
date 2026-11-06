// OE-DELIVERY: 2026-11-12-revu-ui (update 21 - Combine PDFs + New PDF)
/**
 * Combine: pick the open drawing, other project drawings and / or files from
 * the computer, put them in order, combine into one new drawing.
 * New PDF: Preset page size (ANSI / ARCH / ISO) or Custom X x Y (in / mm),
 * Portrait / Landscape, number of pages.
 */
import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, FilePlus2, Trash2, X } from 'lucide-react';

function Shell({ title, onClose, children, testId, width = 460 }: { title: string; onClose: () => void; children: React.ReactNode; testId: string; width?: number }) {
  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/30" onMouseDown={onClose} data-testid={testId}>
      <div className="max-w-[95vw] overflow-hidden rounded-md border border-border bg-surface-elevated shadow-2xl" style={{ width }} onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
        <div className="flex items-center bg-neutral-900 px-3 py-2 text-white">
          <span className="flex-1 text-[13px]">{title}</span>
          <button type="button" onClick={onClose} className="rounded p-0.5 text-white/80 hover:bg-white/10" aria-label="Close"><X size={15} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ── Combine ── */
export interface CombineItem {
  key: string;
  name: string;
  /** 'current' = the open drawing, 'doc' = a project drawing, 'file' = from the computer. */
  kind: 'current' | 'doc' | 'file';
  docId?: string;
  file?: File;
  pages?: number;
}

export function CombineDialog({
  open, currentName, currentPages, projectDocs, onCancel, onOk,
}: {
  open: boolean;
  currentName: string;
  currentPages: number;
  projectDocs: { id: string; filename: string; pages: number }[];
  onCancel: () => void;
  onOk: (items: CombineItem[], outName: string) => void;
}) {
  const [items, setItems] = useState<CombineItem[]>([]);
  const [outName, setOutName] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const was = useRef(false);
  useEffect(() => {
    if (!open) { was.current = false; return; }
    if (was.current) return;
    was.current = true;
    setItems([{ key: 'current', name: currentName, kind: 'current', pages: currentPages }]);
    setOutName(`${currentName.replace(/\.pdf$/i, '')} (combined)`);
  }, [open, currentName, currentPages]);
  if (!open) return null;
  const move = (i: number, d: number) => setItems((arr) => {
    const j = i + d;
    if (j < 0 || j >= arr.length) return arr;
    const n = [...arr];
    [n[i], n[j]] = [n[j]!, n[i]!];
    return n;
  });
  const has = (id: string) => items.some((x) => x.docId === id);
  const total = items.reduce((s, x) => s + (x.pages ?? 0), 0);
  return (
    <Shell title="Combine Files" onClose={onCancel} testId="combine-dialog" width={560}>
      <div className="grid grid-cols-2 gap-3 p-4 text-xs">
        <div>
          <div className="mb-1 font-semibold text-content-secondary">Add drawings</div>
          <div className="max-h-56 overflow-y-auto rounded border border-border">
            {projectDocs.length === 0 && <div className="p-2 text-content-tertiary">No other drawings in this project.</div>}
            {projectDocs.map((d) => (
              <button
                key={d.id}
                type="button"
                disabled={has(d.id)}
                onClick={() => setItems((arr) => [...arr, { key: `doc-${d.id}`, name: d.filename, kind: 'doc', docId: d.id, pages: d.pages }])}
                className="flex w-full items-center justify-between gap-2 border-b border-border/50 px-2 py-1 text-left hover:bg-oe-blue/10 disabled:opacity-40"
                data-testid="combine-add-doc"
              >
                <span className="truncate">{d.filename}</span>
                <span className="shrink-0 text-content-tertiary">{d.pages || ''} p</span>
              </button>
            ))}
          </div>
          <button type="button" onClick={() => fileRef.current?.click()} className="mt-2 flex items-center gap-1 rounded border border-border px-2 py-1 hover:bg-surface-secondary" data-testid="combine-add-files">
            <FilePlus2 size={13} /> Add files from computer…
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="hidden"
            data-testid="combine-file-input"
            onChange={(e) => {
              const fs = Array.from(e.target.files ?? []);
              e.target.value = '';
              setItems((arr) => [...arr, ...fs.map((f, i) => ({ key: `file-${Date.now()}-${i}`, name: f.name, kind: 'file' as const, file: f }))]);
            }}
          />
        </div>
        <div>
          <div className="mb-1 font-semibold text-content-secondary">Files to combine (in this order)</div>
          <div className="max-h-56 overflow-y-auto rounded border border-border" data-testid="combine-list">
            {items.map((it, i) => (
              <div key={it.key} className="flex items-center gap-1 border-b border-border/50 px-2 py-1">
                <span className="w-4 text-content-tertiary">{i + 1}</span>
                <span className="min-w-0 flex-1 truncate" title={it.name}>{it.name}{it.kind === 'current' ? ' (open)' : ''}</span>
                <button type="button" onClick={() => move(i, -1)} className="rounded p-0.5 hover:bg-surface-secondary" aria-label="Up"><ArrowUp size={12} /></button>
                <button type="button" onClick={() => move(i, 1)} className="rounded p-0.5 hover:bg-surface-secondary" aria-label="Down"><ArrowDown size={12} /></button>
                <button type="button" onClick={() => setItems((arr) => arr.filter((x) => x.key !== it.key))} className="rounded p-0.5 text-red-600 hover:bg-red-50" aria-label="Remove"><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
          <div className="mt-1 text-[10px] text-content-tertiary">{items.length} file{items.length === 1 ? '' : 's'}{total ? ` · ${total}+ pages` : ''}</div>
        </div>
        <label className="col-span-2 flex items-center gap-2">
          <span className="text-content-secondary">New drawing name:</span>
          <input value={outName} onChange={(e) => setOutName(e.target.value)} className="h-7 flex-1 rounded border border-border bg-surface-primary px-1.5" data-testid="combine-name" />
          <span className="text-content-tertiary">.pdf</span>
        </label>
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={items.length < 2 || !outName.trim()} onClick={() => onOk(items, outName.trim())} className="min-w-[90px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="combine-ok">Combine</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}

/* ── New PDF ── */
type Unit = 'in' | 'mm';
export const PAGE_PRESETS: { group: string; name: string; w: number; h: number; unit: Unit }[] = [
  { group: 'ANSI', name: 'Letter (ANSI A)', w: 8.5, h: 11, unit: 'in' },
  { group: 'ANSI', name: 'Legal', w: 8.5, h: 14, unit: 'in' },
  { group: 'ANSI', name: 'Tabloid (ANSI B)', w: 11, h: 17, unit: 'in' },
  { group: 'ANSI', name: 'ANSI C', w: 17, h: 22, unit: 'in' },
  { group: 'ANSI', name: 'ANSI D', w: 22, h: 34, unit: 'in' },
  { group: 'ANSI', name: 'ANSI E', w: 34, h: 44, unit: 'in' },
  { group: 'ARCH', name: 'ARCH A', w: 9, h: 12, unit: 'in' },
  { group: 'ARCH', name: 'ARCH B', w: 12, h: 18, unit: 'in' },
  { group: 'ARCH', name: 'ARCH C', w: 18, h: 24, unit: 'in' },
  { group: 'ARCH', name: 'ARCH D', w: 24, h: 36, unit: 'in' },
  { group: 'ARCH', name: 'ARCH E1', w: 30, h: 42, unit: 'in' },
  { group: 'ARCH', name: 'ARCH E', w: 36, h: 48, unit: 'in' },
  { group: 'ISO', name: 'A4', w: 210, h: 297, unit: 'mm' },
  { group: 'ISO', name: 'A3', w: 297, h: 420, unit: 'mm' },
  { group: 'ISO', name: 'A2', w: 420, h: 594, unit: 'mm' },
  { group: 'ISO', name: 'A1', w: 594, h: 841, unit: 'mm' },
  { group: 'ISO', name: 'A0', w: 841, h: 1189, unit: 'mm' },
];
const PT = { in: 72, mm: 72 / 25.4 } as const;
const SAME = '__same__';

export function NewPdfDialog({ open, onCancel, onOk, current, scaleLabel }: {
  open: boolean;
  onCancel: () => void;
  onOk: (r: { name: string; widthPt: number; heightPt: number; pages: number; label: string; keepScale: boolean }) => void;
  /** The open drawing's sheet size (points) - the default (update 22). */
  current?: { w: number; h: number };
  /** The open sheet's scale, e.g. 1/8" = 1'-0" - put on the new pages. */
  scaleLabel?: string;
}) {
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');
  const [preset, setPreset] = useState('ARCH D');
  const [keepScale, setKeepScale] = useState(true);
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open) { wasOpen.current = false; return; }
    if (wasOpen.current) return;
    wasOpen.current = true;
    // Default: the same sheet as the drawing on screen.
    if (current) {
      setMode('preset');
      setPreset(SAME);
      setOrient(current.w >= current.h ? 'landscape' : 'portrait');
    }
    setKeepScale(true);
  }, [open, current]);
  const [cw, setCw] = useState('24');
  const [ch, setCh] = useState('36');
  const [unit, setUnit] = useState<Unit>('in');
  const [orient, setOrient] = useState<'portrait' | 'landscape'>('landscape');
  const [pages, setPages] = useState(1);
  const [name, setName] = useState('New drawing');
  if (!open) return null;
  const same = preset === SAME && current;
  const p = PAGE_PRESETS.find((x) => x.name === preset) ?? PAGE_PRESETS[0]!;
  const w0 = mode === 'preset' ? (same ? current!.w : p.w * PT[p.unit]) : Number(cw) * PT[unit];
  const h0 = mode === 'preset' ? (same ? current!.h : p.h * PT[p.unit]) : Number(ch) * PT[unit];
  const ok = w0 > 0 && h0 > 0 && w0 <= 14400 && h0 <= 14400 && pages >= 1 && name.trim();
  const short = Math.min(w0, h0);
  const long = Math.max(w0, h0);
  const widthPt = orient === 'landscape' ? long : short;
  const heightPt = orient === 'landscape' ? short : long;
  const fmt = (v: number) => (unit === 'mm' && mode === 'custom' ? `${(v / PT.mm).toFixed(0)} mm` : `${+(v / 72).toFixed(2)}"`);
  const sel = 'h-7 rounded border border-border bg-surface-primary px-1.5 text-xs';
  const lab = 'w-[78px] shrink-0 text-right text-xs text-content-secondary';
  return (
    <Shell title="New PDF" onClose={onCancel} testId="new-pdf-dialog">
      <div className="space-y-3 p-4 text-xs">
        <div className="flex items-center gap-2">
          <span className={lab}>Name:</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className={`${sel} flex-1`} data-testid="newpdf-name" />
        </div>
        <div className="flex items-start gap-2">
          <span className={`${lab} pt-1`}>Page size:</span>
          <div className="flex flex-1 flex-col gap-2">
            <div className="flex gap-4">
              <label className="flex items-center gap-1.5"><input type="radio" checked={mode === 'preset'} onChange={() => setMode('preset')} data-testid="newpdf-preset-mode" />Preset</label>
              <label className="flex items-center gap-1.5"><input type="radio" checked={mode === 'custom'} onChange={() => setMode('custom')} data-testid="newpdf-custom-mode" />Custom</label>
            </div>
            {mode === 'preset' ? (
              <select value={preset} onChange={(e) => setPreset(e.target.value)} className={`${sel} w-full`} data-testid="newpdf-preset">
                {current && (
                  <option value={SAME}>Same as this drawing - {+(Math.max(current.w, current.h) / 72).toFixed(2)} x {+(Math.min(current.w, current.h) / 72).toFixed(2)} in</option>
                )}
                {['ANSI', 'ARCH', 'ISO'].map((g) => (
                  <optgroup key={g} label={g}>
                    {PAGE_PRESETS.filter((x) => x.group === g).map((x) => (
                      <option key={x.name} value={x.name}>{x.name} - {x.w} x {x.h} {x.unit === 'in' ? 'in' : 'mm'}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            ) : (
              <div className="flex items-center gap-1.5">
                <span>X</span>
                <input value={cw} onChange={(e) => setCw(e.target.value)} inputMode="decimal" className={`${sel} w-20`} data-testid="newpdf-w" />
                <span>Y</span>
                <input value={ch} onChange={(e) => setCh(e.target.value)} inputMode="decimal" className={`${sel} w-20`} data-testid="newpdf-h" />
                <select value={unit} onChange={(e) => setUnit(e.target.value as Unit)} className={sel} data-testid="newpdf-unit">
                  <option value="in">in</option>
                  <option value="mm">mm</option>
                </select>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={lab}>Orientation:</span>
          <label className="flex items-center gap-1.5"><input type="radio" checked={orient === 'portrait'} onChange={() => setOrient('portrait')} data-testid="newpdf-portrait" />Portrait</label>
          <label className="ml-3 flex items-center gap-1.5"><input type="radio" checked={orient === 'landscape'} onChange={() => setOrient('landscape')} data-testid="newpdf-landscape" />Landscape</label>
        </div>
        {scaleLabel && (
          <label className="flex items-center gap-2 pl-[86px]" data-testid="newpdf-keep-scale-row">
            <input type="checkbox" checked={keepScale} onChange={(e) => setKeepScale(e.target.checked)} data-testid="newpdf-keep-scale" />
            Use this drawing's scale on the new pages ({scaleLabel})
          </label>
        )}
        <div className="flex items-center gap-2">
          <span className={lab}>Pages:</span>
          <input type="number" min={1} max={500} value={pages} onChange={(e) => setPages(Math.max(1, Math.min(500, Number(e.target.value) || 1)))} className={`${sel} w-20`} data-testid="newpdf-pages" />
          <span className="ml-auto text-content-tertiary" data-testid="newpdf-size">{fmt(widthPt)} x {fmt(heightPt)}</span>
        </div>
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={!ok} onClick={() => onOk({ name: name.trim(), widthPt, heightPt, pages, label: mode === 'preset' ? (same ? 'same size as the drawing' : preset) : `${cw} x ${ch} ${unit}`, keepScale: Boolean(scaleLabel) && keepScale })} className="min-w-[90px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="newpdf-ok">Create</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}
