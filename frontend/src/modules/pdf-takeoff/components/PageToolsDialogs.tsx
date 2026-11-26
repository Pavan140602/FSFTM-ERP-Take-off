// OE-DELIVERY: 2026-11-12-fsftm-ui (update 19 - FSFTM Extract / Delete Pages windows)
/**
 * FSFTM's "Extract Pages" and "Delete Pages" windows:
 *   Pages: [Selected (13) v] of 34     (Current / Selected / All Pages / typed 1-3,5)
 * Extract also has FSFTM's options (delete after, separate files, page-label
 * names, open after extraction, keep links).
 */
import { useEffect, useRef, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import { parsePages } from './SetScaleDialog';

type Mode = 'current' | 'selected' | 'all' | 'custom';

function usePages(open: boolean, currentPage: number, selected: number[], totalPages: number) {
  const [mode, setMode] = useState<Mode>('selected');
  const [text, setText] = useState('');
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open) { wasOpen.current = false; return; }
    if (wasOpen.current) return;
    wasOpen.current = true;
    setMode(selected.length > 1 ? 'selected' : 'current');
    setText(selected.join(','));
  }, [open, selected, currentPage]);
  const pages =
    mode === 'current' ? [currentPage]
      : mode === 'selected' ? [...selected].sort((a, b) => a - b)
        : mode === 'all' ? Array.from({ length: totalPages }, (_, i) => i + 1)
          : parsePages(text, totalPages);
  const label =
    mode === 'current' ? `Current (${currentPage})`
      : mode === 'selected' ? `Selected (${selected.join(',')})`
        : mode === 'all' ? `All Pages (1-${totalPages})`
          : text;
  return { mode, setMode, text, setText, pages, label };
}

function PagesPicker({ st, currentPage, selected, totalPages }: { st: ReturnType<typeof usePages>; currentPage: number; selected: number[]; totalPages: number }) {
  const [menu, setMenu] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const sel = 'h-7 rounded border border-border bg-surface-primary px-1.5 text-xs';
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-content-secondary">Pages:</span>
      <div className="relative flex flex-1">
        <input
          ref={inputRef}
          placeholder="e.g. 3-5 or 1,5"
          value={st.label}
          onChange={(e) => { st.setMode('custom'); st.setText(e.target.value); }}
          onFocus={(e) => e.target.select()}
          className={`${sel} min-w-0 flex-1 rounded-r-none`}
          data-testid="pages-picker-input"
        />
        <button type="button" onClick={() => setMenu((v) => !v)} className="h-7 rounded-r border border-l-0 border-border px-1.5 hover:bg-surface-secondary" aria-label="Pages" data-testid="pages-picker-menu">
          <ChevronDown size={13} />
        </button>
        {menu && (
          <div className="absolute left-0 right-0 top-7 z-10 rounded border border-border bg-surface-elevated py-0.5 text-xs shadow-lg">
            {([
              ...(selected.length ? [['selected', `Selected (${selected.join(',')})`]] : []),
              ['custom', 'Custom… (type pages, e.g. 3-5 or 1,5)'],
              ['current', `Current (${currentPage})`],
              ['all', `All Pages (1-${totalPages})`],
            ] as [Mode, string][]).map(([k, txt]) => (
              <button key={k} type="button" onClick={() => {
                st.setMode(k);
                setMenu(false);
                if (k === 'custom') { st.setText(''); setTimeout(() => inputRef.current?.focus(), 0); }
              }} className="block w-full px-2 py-1 text-left hover:bg-oe-blue hover:text-white" data-testid={`pages-picker-${k}`}>
                {txt}
              </button>
            ))}
          </div>
        )}
      </div>
      <span className="text-xs text-content-secondary">of {totalPages}</span>
    </div>
  );
}

function Shell({ title, onClose, children, testId }: { title: string; onClose: () => void; children: React.ReactNode; testId: string }) {
  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/30" onMouseDown={onClose} data-testid={testId}>
      <div className="w-[380px] max-w-[95vw] overflow-hidden rounded-md border border-border bg-surface-elevated shadow-2xl" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
        <div className="flex items-center bg-neutral-900 px-3 py-2 text-white">
          <span className="flex-1 text-[13px]">{title}</span>
          <button type="button" onClick={onClose} className="rounded p-0.5 text-white/80 hover:bg-white/10" aria-label="Close">
            <X size={15} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export interface ExtractOptions {
  pages: number[];
  deleteAfter: boolean;
  separate: boolean;
  useLabels: boolean;
  overwrite: boolean;
  openAfter: boolean;
  keepLinks: boolean;
}

interface Common {
  open: boolean;
  currentPage: number;
  selected: number[];
  totalPages: number;
  onCancel: () => void;
}

export function ExtractPagesDialog({ open, currentPage, selected, totalPages, onCancel, onOk }: Common & { onOk: (o: ExtractOptions) => void }) {
  const st = usePages(open, currentPage, selected, totalPages);
  const [deleteAfter, setDeleteAfter] = useState(false);
  const [separate, setSeparate] = useState(false);
  const [useLabels, setUseLabels] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [openAfter, setOpenAfter] = useState(true);
  const [keepLinks, setKeepLinks] = useState(true);
  if (!open) return null;
  const box = 'flex items-center gap-2 text-xs';
  const ok = st.pages.length > 0 && !(deleteAfter && st.pages.length >= totalPages);
  return (
    <Shell title="Extract Pages" onClose={onCancel} testId="extract-pages-dialog">
      <div className="space-y-3 p-4">
        <fieldset className="rounded border border-border px-3 pb-3 pt-1">
          <legend className="px-1 text-xs text-content-secondary">Page Range</legend>
          <PagesPicker st={st} currentPage={currentPage} selected={selected} totalPages={totalPages} />
        </fieldset>
        <fieldset className="space-y-1.5 rounded border border-border px-3 pb-3 pt-1">
          <legend className="px-1 text-xs text-content-secondary">Options</legend>
          <label className={box}><input type="checkbox" checked={deleteAfter} onChange={(e) => setDeleteAfter(e.target.checked)} data-testid="ex-delete-after" />Delete pages after extracting</label>
          <label className={box}><input type="checkbox" checked={separate} onChange={(e) => setSeparate(e.target.checked)} data-testid="ex-separate" />Extract pages as separate files</label>
          <label className={`${box} pl-5 ${separate ? '' : 'opacity-50'}`}><input type="checkbox" disabled={!separate} checked={useLabels} onChange={(e) => setUseLabels(e.target.checked)} data-testid="ex-use-labels" />Use page label to name files</label>
          <label className={`${box} pl-5 ${separate ? '' : 'opacity-50'}`} title="Replace a drawing of the same name in the project"><input type="checkbox" disabled={!separate} checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />Overwrite existing files</label>
          <label className={box} title="Add the extracted file(s) to the project's drawings and open them; off = download"><input type="checkbox" checked={openAfter} onChange={(e) => setOpenAfter(e.target.checked)} data-testid="ex-open-after" />Open files after extraction</label>
          <label className={box} title="Links inside the extracted pages are kept"><input type="checkbox" checked={keepLinks} onChange={(e) => setKeepLinks(e.target.checked)} />Update hyperlinks to relative paths</label>
        </fieldset>
        {deleteAfter && st.pages.length >= totalPages && <div className="text-[11px] text-semantic-error">A drawing must keep at least one page.</div>}
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={!ok} onClick={() => onOk({ pages: st.pages, deleteAfter, separate, useLabels: separate && useLabels, overwrite: separate && overwrite, openAfter, keepLinks })} className="min-w-[70px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="ex-ok">OK</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}

export function DeletePagesDialog({ open, currentPage, selected, totalPages, onCancel, onOk }: Common & { onOk: (pages: number[]) => void }) {
  const st = usePages(open, currentPage, selected, totalPages);
  if (!open) return null;
  const ok = st.pages.length > 0 && st.pages.length < totalPages;
  return (
    <Shell title="Delete Pages" onClose={onCancel} testId="delete-pages-dialog">
      <div className="p-4">
        <PagesPicker st={st} currentPage={currentPage} selected={selected} totalPages={totalPages} />
        {st.pages.length >= totalPages && <div className="mt-2 text-[11px] text-semantic-error">A drawing must keep at least one page.</div>}
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={!ok} onClick={() => onOk(st.pages)} className="min-w-[70px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="del-ok">OK</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}

// OE-DELIVERY: 2026-11-25-fsftm-pdf - Rotate Pages / Export Pages windows
// with the same page-range picker (current, selected, all, custom).

export type RotateDirection = 'cw' | 'ccw' | '180';

export function RotatePagesDialog({ open, currentPage, selected, totalPages, onCancel, onOk, fileName }: Common & { onOk: (pages: number[], dir: RotateDirection) => void; fileName?: string }) {
  const st = usePages(open, currentPage, selected, totalPages);
  const [dir, setDir] = useState<RotateDirection>('cw');
  if (!open) return null;
  const ok = st.pages.length > 0;
  const sel = 'h-7 rounded border border-border bg-surface-primary px-1.5 text-xs';
  return (
    <Shell title="Rotate Pages" onClose={onCancel} testId="rotate-pages-dialog">
      <div className="space-y-3 p-4">
        <fieldset className="rounded border border-border px-2 pb-2 pt-1">
          <legend className="px-1 text-xs text-content-secondary">Files</legend>
          <table className="w-full table-fixed text-xs">
            <thead>
              <tr className="text-left text-content-secondary">
                <th className="w-[55%] border-b border-border px-1.5 py-1 font-normal">Name</th>
                <th className="border-b border-border px-1.5 py-1 font-normal">Pages</th>
              </tr>
            </thead>
            <tbody>
              <tr className="bg-oe-blue/10">
                <td className="truncate px-1.5 py-1.5" title={fileName}>{fileName || 'Current drawing'}</td>
                <td className="px-1.5 py-1">
                  <select
                    className={`${sel} w-full`}
                    value={st.mode}
                    onChange={(e) => st.setMode(e.target.value as Mode)}
                    data-testid="rot-pages-mode"
                  >
                    {selected.length > 0 && <option value="selected">Selected ({selected.length})</option>}
                    <option value="current">Current ({currentPage})</option>
                    <option value="all">All ({totalPages})</option>
                    <option value="custom">Custom…</option>
                  </select>
                  {st.mode === 'custom' && (
                    <input
                      autoFocus
                      placeholder="e.g. 3-5 or 1,5"
                      value={st.text}
                      onChange={(e) => st.setText(e.target.value)}
                      className={`${sel} mt-1 w-full`}
                      data-testid="rot-pages-custom"
                    />
                  )}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="mt-1.5 px-1 text-[11px] text-content-tertiary">
            {st.pages.length > 0 ? `Pages ${st.pages.length > 12 ? `${st.pages.slice(0, 12).join(', ')}…` : st.pages.join(', ')} of ${totalPages}` : 'No valid pages.'}
          </p>
        </fieldset>
        <label className="flex items-center gap-2 text-xs">
          <span className="text-content-secondary">Direction:</span>
          <select className={`${sel} flex-1`} value={dir} onChange={(e) => setDir(e.target.value as RotateDirection)} data-testid="rot-direction">
            <option value="cw">Clockwise 90 degrees</option>
            <option value="180">180 degrees</option>
            <option value="ccw">Counterclockwise 90 degrees</option>
          </select>
        </label>
        <p className="text-[11px] text-content-tertiary">The pages turn in this drawing and their markups turn with them.</p>
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={!ok} onClick={() => onOk(st.pages, dir)} className="min-w-[70px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="rot-ok">OK</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}

export type ExportFormat = 'pdf' | 'png';

export function ExportPagesDialog({ open, currentPage, selected, totalPages, onCancel, onOk }: Common & { onOk: (pages: number[], format: ExportFormat) => void }) {
  const st = usePages(open, currentPage, selected, totalPages);
  const [format, setFormat] = useState<ExportFormat>('pdf');
  if (!open) return null;
  const ok = st.pages.length > 0;
  const opt = 'flex items-center gap-2 text-xs';
  return (
    <Shell title="Export Pages" onClose={onCancel} testId="export-pages-dialog">
      <div className="space-y-3 p-4">
        <fieldset className="rounded border border-border px-3 pb-3 pt-1">
          <legend className="px-1 text-xs text-content-secondary">Page Range</legend>
          <PagesPicker st={st} currentPage={currentPage} selected={selected} totalPages={totalPages} />
        </fieldset>
        <fieldset className="space-y-1.5 rounded border border-border px-3 pb-3 pt-1">
          <legend className="px-1 text-xs text-content-secondary">Format</legend>
          <label className={opt}><input type="radio" name="exp-fmt" checked={format === 'pdf'} onChange={() => setFormat('pdf')} data-testid="exp-pdf" />PDF - one file with the pages and their markups</label>
          <label className={opt}><input type="radio" name="exp-fmt" checked={format === 'png'} onChange={() => setFormat('png')} data-testid="exp-png" />PNG images - one image per page</label>
        </fieldset>
        <p className="text-[11px] text-content-tertiary">{st.pages.length} page{st.pages.length === 1 ? '' : 's'} will be exported.</p>
      </div>
      <div className="flex justify-end gap-2 px-4 pb-4">
        <button type="button" disabled={!ok} onClick={() => onOk(st.pages, format)} className="min-w-[70px] rounded bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" data-testid="exp-ok">Export</button>
        <button type="button" onClick={onCancel} className="min-w-[70px] rounded border border-border px-3 py-1.5 text-xs hover:bg-surface-secondary">Cancel</button>
      </div>
    </Shell>
  );
}
