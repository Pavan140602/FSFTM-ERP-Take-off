"""Update 21: clear thumbnail labels, Ctrl+C/V (and Shift+Ctrl) markups,
Combine PDFs, New PDF, Highlight snaps to words, bottom Select / Pan /
Text-select tools (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("import { SetScaleDialog } from './components/SetScaleDialog';",
    "import { SetScaleDialog } from './components/SetScaleDialog';\n"
    "import { CombineDialog, NewPdfDialog, type CombineItem } from './components/PdfCreateDialogs';\n"
    "import { wordsFromItems, wordsInRect, lineBoxes, textOf, type Word, type RawItem } from './data/text-words';")
rep("""  Hand,
""", """  Hand,
  TextCursor,
  Combine as CombineIcon,
  FilePlus2,
""")

# 1. Thumbnail label: dark pill, clearly apart from the white thumbnail.
rep("""                        className={clsx('min-w-0 truncate text-[12px] font-bold hover:underline', pageLabelOf(n) ? 'text-content-primary' : 'italic font-normal text-content-tertiary')}""",
    """                        className={clsx(
                          'min-w-0 truncate rounded px-1.5 text-[12px] font-bold leading-[18px] hover:ring-2 hover:ring-oe-blue/50',
                          pageLabelOf(n) ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900' : 'italic font-normal text-content-tertiary',
                        )}""")

# 2. Copy / paste: Ctrl+C / Ctrl+V (Shift+Ctrl too).
rep("""      if ((e.ctrlKey || e.metaKey) && e.shiftKey && !e.altKey && shouldHandleShortcut(e.target)) {""",
    """      if ((e.ctrlKey || e.metaKey) && !e.altKey && shouldHandleShortcut(e.target)) {""")
rep("""message: 'Go to any page and press Shift+Ctrl+V - they paste in the same place.' });""",
    """message: 'Go to any page and press Ctrl+V - they paste in the same place.' });""")

# 3. Combine + New PDF.
rep("""  /** Revu Extract / Delete Pages windows (update 19). */""", """  /** Combine PDFs / New PDF windows (update 21). */
  const [combineOpen, setCombineOpen] = useState(false);
  const [newPdfOpen, setNewPdfOpen] = useState(false);
  const authHeaders = (): Record<string, string> => {
    const h: Record<string, string> = {};
    const token = getAuthToken();
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  };
  const openOrDownload = async (bytes: Uint8Array, name: string, okMsg: string) => {
    const d = await uploadPdf(bytes, name).catch(() => null);
    if (d && onOpenUploadedDocument) {
      try { saveNow(); } catch { /* ignore */ }
      addToast({ type: 'success', title: okMsg, message: `${d.filename} added to the drawings and opened.` });
      onOpenUploadedDocument(d);
    } else {
      download(bytes, name);
      addToast({ type: 'success', title: okMsg, message: `${name} downloaded.` });
    }
  };
  const runCombine = async (items: CombineItem[], outName: string) => {
    setCombineOpen(false);
    try {
      const parts: Uint8Array[] = [];
      let currentAt = -1;
      for (const it of items) {
        if (it.kind === 'current') {
          currentAt = parts.length;
          parts.push(new Uint8Array(await pdfDoc!.getData()));
        } else if (it.kind === 'doc' && it.docId) {
          const res = await fetch(`/api/v1/takeoff/documents/${it.docId}/download/`, { headers: authHeaders() });
          if (!res.ok) throw new Error(`Could not read ${it.name} (${res.status})`);
          parts.push(new Uint8Array(await res.arrayBuffer()));
        } else if (it.file) {
          parts.push(new Uint8Array(await it.file.arrayBuffer()));
        }
      }
      const r = await pdfPages.combinePdfs(parts);
      let bytes = r.bytes;
      // The open drawing's markups and scales go with its pages.
      if (currentAt >= 0 && pdfDoc) {
        const map: Record<number, number> = {};
        for (let i = 1; i <= pdfDoc.numPages; i++) map[i] = r.offsets[currentAt]! + i;
        bytes = await pdfPages.withSnapshot(bytes, await snapshotFor(map));
      }
      await openOrDownload(bytes, `${outName.replace(/\\.pdf$/i, '')}.pdf`, `Combined ${items.length} files (${r.numPages} pages)`);
    } catch (err) {
      addToast({ type: 'error', title: 'Combine failed', message: err instanceof Error ? err.message : String(err) });
    }
  };
  const runNewPdf = async (o: { name: string; widthPt: number; heightPt: number; pages: number; label: string }) => {
    setNewPdfOpen(false);
    try {
      const bytes = await pdfPages.createBlankPdf(o.widthPt, o.heightPt, o.pages, o.name);
      await openOrDownload(bytes, `${o.name.replace(/\\.pdf$/i, '')}.pdf`, `New PDF: ${o.label}, ${o.pages} page${o.pages === 1 ? '' : 's'}`);
    } catch (err) {
      addToast({ type: 'error', title: 'New PDF failed', message: err instanceof Error ? err.message : String(err) });
    }
  };

  /** Revu Extract / Delete Pages windows (update 19). */""")
rep("""                { label: 'Save', shortcut: 'Ctrl+S', onClick: () => saveWorkRef.current(), testId: 'revu-file-save' },""",
    """                { label: 'New PDF…', onClick: () => setNewPdfOpen(true), testId: 'revu-file-new-pdf' },
                { label: 'Combine Files…', onClick: () => setCombineOpen(true), testId: 'revu-file-combine' },
                { label: 'Save', shortcut: 'Ctrl+S', onClick: () => saveWorkRef.current(), testId: 'revu-file-save' },""")
rep("""                {/* Save the work (update 15). */}""", """                {/* New PDF / Combine files (update 21). */}
                <button
                  onClick={() => setNewPdfOpen(true)}
                  className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-primary px-2 text-xs font-medium text-content-secondary hover:bg-surface-secondary"
                  title="New PDF - blank pages of a preset or custom size, portrait or landscape"
                  data-testid="toolbar-new-pdf"
                >
                  <FilePlus2 size={14} />
                  <span className="takeoff-toolbar-label">New</span>
                </button>
                <button
                  onClick={() => setCombineOpen(true)}
                  disabled={!pdfDoc}
                  className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-primary px-2 text-xs font-medium text-content-secondary hover:bg-surface-secondary disabled:opacity-50"
                  title="Combine this drawing with other drawings / PDF files into one"
                  data-testid="toolbar-combine"
                >
                  <CombineIcon size={14} />
                  <span className="takeoff-toolbar-label">Combine</span>
                </button>
                {/* Save the work (update 15). */}""")
rep("""      <ExtractPagesDialog""", """      <CombineDialog
        open={combineOpen}
        currentName={fileName || exportProjectName || 'drawing.pdf'}
        currentPages={totalPages || 0}
        projectDocs={(recentDocuments ?? []).filter((d) => d.id !== documentId).map((d) => ({ id: d.id, filename: d.filename, pages: d.pages }))}
        onCancel={() => setCombineOpen(false)}
        onOk={(items, name) => { void runCombine(items, name); }}
      />
      <NewPdfDialog open={newPdfOpen} onCancel={() => setNewPdfOpen(false)} onOk={(o) => { void runNewPdf(o); }} />
      <ExtractPagesDialog""")

# 4. Page words (highlight snap + text select).
rep("""  /** Combine PDFs / New PDF windows (update 21). */""", """  /** Words per page (cached) for the text highlight / Text Select tool. */
  const pageWordsRef = useRef<Map<number, Word[]>>(new Map());
  const wordsOfPage = async (n: number): Promise<Word[]> => {
    const hit = pageWordsRef.current.get(n);
    if (hit) return hit;
    if (!pdfDoc) return [];
    try {
      const page = await pdfDoc.getPage(n);
      const vp = page.getViewport({ scale: 1 });
      const tc = await page.getTextContent();
      const items: RawItem[] = [];
      for (const raw of tc.items as Array<{ str?: string; transform?: number[]; width?: number }>) {
        if (!raw.str || !raw.transform) continue;
        const [a, b, c, d, e, f] = raw.transform as [number, number, number, number, number, number];
        if (Math.abs(b) > Math.abs(a) * 0.2) continue; // rotated text: skip (boxes would be wrong)
        const [x, y] = vp.convertToViewportPoint(e, f) as [number, number];
        items.push({ str: raw.str, x, y, h: Math.hypot(c, d), w: raw.width ?? 0 });
      }
      const words = wordsFromItems(items);
      pageWordsRef.current.set(n, words);
      return words;
    } catch {
      return [];
    }
  };
  useEffect(() => { pageWordsRef.current = new Map(); }, [pdfDoc]);
  /** Text Select tool (bottom bar): drag over text, it is shown and copied. */
  const [textSelArmed, setTextSelArmed] = useState(false);
  const textSelArmedRef = useRef(false);
  textSelArmedRef.current = textSelArmed;
  const textSelStartRef = useRef<Point | null>(null);
  const [textSelBox, setTextSelBox] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const [textSel, setTextSel] = useState<{ page: number; boxes: { x: number; y: number; w: number; h: number }[]; text: string } | null>(null);

  /** Combine PDFs / New PDF windows (update 21). */""")

# Text select: mouse handling at the very start of the canvas handlers.
rep("""      {
        const ae = document.activeElement as HTMLElement | null;
        if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'SELECT')) ae.blur();
      }""", """      {
        const ae = document.activeElement as HTMLElement | null;
        if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'SELECT')) ae.blur();
      }
      // Text Select tool (update 21): start a text drag.
      if (textSelArmedRef.current && e.button === 0) {
        const tp = pointerToPdf(e);
        textSelStartRef.current = tp;
        setTextSel(null);
        if (tp) setTextSelBox({ x0: tp.x, y0: tp.y, x1: tp.x, y1: tp.y });
        e.preventDefault();
        return;
      }""")
rep("""    (e: React.MouseEvent<HTMLCanvasElement>) => {
      modsRef.current = { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey };""", """    (e: React.MouseEvent<HTMLCanvasElement>) => {
      modsRef.current = { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey };
      if (textSelArmedRef.current && textSelStartRef.current && (e.buttons & 1)) {
        const tp = pointerToPdf(e);
        const st = textSelStartRef.current;
        if (tp) setTextSelBox({ x0: st.x, y0: st.y, x1: tp.x, y1: tp.y });
        return;
      }""")
rep("""  const handleCanvasMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {""", """  const handleCanvasMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (textSelArmedRef.current && textSelStartRef.current) {
      const st = textSelStartRef.current;
      const tp = pointerToPdfRef.current?.(e) ?? st;
      textSelStartRef.current = null;
      setTextSelBox(null);
      const pg = currentPageRef.current;
      void (async () => {
        const sel = wordsInRect(await wordsOfPage(pg), { x0: st.x, y0: st.y, x1: tp.x, y1: tp.y });
        if (sel.length === 0) {
          setTextSel(null);
          addToast({ type: 'info', title: 'No text here', message: 'This part of the sheet has no selectable text (it may be drawn as lines or a scan).' });
          return;
        }
        const text = textOf(sel);
        setTextSel({ page: pg, boxes: lineBoxes(sel), text });
        try {
          await navigator.clipboard.writeText(text);
          addToast({ type: 'success', title: `${sel.length} word${sel.length === 1 ? '' : 's'} copied`, message: text.length > 80 ? `${text.slice(0, 80)}…` : text });
        } catch {
          addToast({ type: 'info', title: 'Text selected', message: text.slice(0, 120) });
        }
      })();
      return;
    }""")
rep("""  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      // Ctrl / Shift on this click decide straight vs free (update 15).""", """  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (textSelArmedRef.current) return; // the Text Select tool owns the clicks
      // Ctrl / Shift on this click decide straight vs free (update 15).""")

# Highlight snaps to the words it covers (one highlight per line).
rep("""          if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse') && !rectStartPoint) {
            const boxM: Measurement = {""", """          if (activeTool === 'highlight' && !rectStartPoint) {
            // Highlight on readable text (update 21): snap to the words the
            // drag covers - one highlight per line, like a text highlighter.
            const pg = currentPage;
            const tool = activeTool;
            const extra = toolFieldSpread();
            const col = annotationColor;
            const grp = activeGroup;
            void (async () => {
              const sel = wordsInRect(await wordsOfPage(pg), { x0: a.x, y0: a.y, x1: ep.x, y1: ep.y });
              const boxes = sel.length ? lineBoxes(sel) : [{ x: Math.min(a.x, ep.x), y: Math.min(a.y, ep.y), w: Math.abs(ep.x - a.x), h: Math.abs(ep.y - a.y) }];
              const stamp = Date.now();
              const ms: Measurement[] = boxes.map((b, i) => ({
                id: `m_${stamp}_h${i}`,
                type: tool,
                points: [{ x: b.x, y: b.y }, { x: b.x + b.w, y: b.y + b.h }],
                value: 0,
                unit: '',
                label: '',
                annotation: sel.length ? textOf(sel).split('\\n')[i]?.slice(0, 120) ?? '' : nextAnnotation(tool),
                ...extra,
                page: pg,
                group: grp,
                color: col,
                width: b.w,
                height: b.h,
              }));
              if (ms.length === 1) pushUndo({ kind: 'complete_measurement', measurement: ms[0]!, previousActivePoints: [] });
              else pushUndo({ kind: 'bulk_add', measurements: ms });
              setMeasurements((prev) => [...prev, ...ms]);
            })();
            setActivePoints([]);
            return;
          }
          if ((activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse') && !rectStartPoint) {
            const boxM: Measurement = {""")

# Bottom bar tools: Select / Pan / Text Select, beside the page navigator.
rep("""              <div className="flex min-w-0 flex-wrap items-center gap-1" data-revu-pager="1">""", """              {/* Select / Pan / Text Select (Revu bottom bar, update 21). */}
              <div className="flex items-center gap-0.5 rounded-md border border-border bg-surface-primary p-0.5" data-testid="bottom-tools">
                {([
                  ['select', 'Select (V)', MousePointer2, activeTool === 'select' && !panLock && !textSelArmed],
                  ['pan', 'Pan - drag to move the sheet', Hand, panLock],
                  ['text', 'Text Select - drag over text to select and copy it', TextCursor, textSelArmed],
                ] as [string, string, typeof Hand, boolean][]).map(([k, tip, Icon, on]) => (
                  <button
                    key={k}
                    type="button"
                    title={tip}
                    aria-pressed={on}
                    onClick={() => {
                      if (k === 'select') { setPanLock(false); setTextSelArmed(false); setTextSel(null); selectTool('select' as MeasureTool); }
                      else if (k === 'pan') { setTextSelArmed(false); setPanLock((v) => !v); }
                      else { setPanLock(false); setTextSelArmed((v) => !v); setTextSel(null); if (activeTool !== 'select') selectTool('select' as MeasureTool); }
                    }}
                    className={clsx('flex h-7 w-8 items-center justify-center rounded', on ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-secondary')}
                    data-testid={`bottom-tool-${k}`}
                  >
                    <Icon size={15} />
                  </button>
                ))}
              </div>
              <div className="flex min-w-0 flex-wrap items-center gap-1" data-revu-pager="1">""")

# Text selection drawn over the page (and the drag box).
rep("""                {/* Callout / Cloud+ comment typed in place at the box (update 10):""", """                {/* Text Select: the drag box and the selected lines (update 21). */}
                {textSelBox && (
                  <div
                    className="pointer-events-none absolute z-20 border border-dashed border-oe-blue bg-oe-blue/10"
                    style={{
                      left: `${Math.min(textSelBox.x0, textSelBox.x1) * zoom}px`,
                      top: `${Math.min(textSelBox.y0, textSelBox.y1) * zoom + overlayTop}px`,
                      width: `${Math.abs(textSelBox.x1 - textSelBox.x0) * zoom}px`,
                      height: `${Math.abs(textSelBox.y1 - textSelBox.y0) * zoom}px`,
                    }}
                  />
                )}
                {textSel && textSel.page === currentPage && textSel.boxes.map((b, i) => (
                  <div
                    key={i}
                    className="pointer-events-none absolute z-20 bg-sky-400/35 mix-blend-multiply"
                    style={{ left: `${b.x * zoom}px`, top: `${b.y * zoom + overlayTop}px`, width: `${b.w * zoom}px`, height: `${b.h * zoom}px` }}
                    data-testid="text-sel-box"
                  />
                ))}
                {/* Callout / Cloud+ comment typed in place at the box (update 10):""")
p.write_text(s, encoding="utf-8")
print("ok")
