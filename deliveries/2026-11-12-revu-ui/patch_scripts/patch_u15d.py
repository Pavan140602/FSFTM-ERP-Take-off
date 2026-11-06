"""Update 15d: vector Save PDF (pdf-lib annotations + snapshot with scales),
own annotations hidden on reopen, thumbnails (page no., scale line, multi-
select, right-click page menu with working page tools)
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src")
p = base / "modules/pdf-takeoff/TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("import { SetScaleDialog } from './components/SetScaleDialog';",
    "import { SetScaleDialog } from './components/SetScaleDialog';\n"
    "import * as pdfPages from './data/pdf-pages';")

# Props: open an uploaded (edited) document.
rep("""  /** Close the open PDF (parent clears it; the viewer saves first, update 15). */
  onCloseDocument?: () => void;
}""", """  /** Close the open PDF (parent clears it; the viewer saves first, update 15). */
  onCloseDocument?: () => void;
  /** Open a document the viewer just uploaded (page tools, update 15). */
  onOpenUploadedDocument?: (doc: { id: string; filename: string }) => void;
}""")
rep("""  onOpenRecentDocument,
  onCloseDocument,""", """  onOpenRecentDocument,
  onCloseDocument,
  onOpenUploadedDocument,""")

# ── Hide our own written annotations on a reopened ERP PDF ──
rep("""  useEffect(() => {
    if (!pdfDoc) return;
    let cancelled = false;
    (async () => {
      const snapshot = await readTakeoffSnapshot(pdfDoc);
      if (cancelled || !snapshot) return;""", """  useEffect(() => {
    if (!pdfDoc) return;
    let cancelled = false;
    (async () => {
      const snapshot = await readTakeoffSnapshot(pdfDoc);
      if (cancelled || !snapshot) return;
      // The file also carries these markups as PDF annotations (Revu-style
      // save, update 15): draw the pages without annotations so the editable
      // markups are not doubled, and restore the saved page scales.
      {
        const docAny = pdfDoc as unknown as { getPage: (n: number) => Promise<unknown>; __oeNoAnn?: boolean };
        if (!docAny.__oeNoAnn) {
          docAny.__oeNoAnn = true;
          const og = docAny.getPage.bind(pdfDoc);
          docAny.getPage = async (n: number) => {
            const pg = (await og(n)) as { render: (p: Record<string, unknown>) => unknown; __oeNoAnn?: boolean };
            if (!pg.__oeNoAnn) {
              pg.__oeNoAnn = true;
              const r = pg.render.bind(pg);
              pg.render = (prm: Record<string, unknown>) => r({ ...prm, annotationMode: 0 });
            }
            return pg;
          };
          pageCacheRef.current.clear();
          for (const c of continuousCanvasesRef.current) if (c) delete c.dataset.rz;
          setThumbs({});
          setAnnRev((x) => x + 1);
        }
        const sc = (snapshot as pdfPages.TakeoffSnapshotV).scales;
        if (sc) {
          setPageScales((prev) => Object.entries(sc).reduce((acc, [orig, cfg]) => {
            const to = snapshot.pageMap[orig] ?? Number(orig);
            return pageIsCalibrated(acc, to) ? acc : setPageScaleIn(acc, to, cfg);
          }, prev));
        }
      }""")
rep("""  }, [pdfDoc, canvasReady, currentPage, renderZoom, pageMode, lineWeightsOff]);""",
    """  }, [pdfDoc, canvasReady, currentPage, renderZoom, pageMode, lineWeightsOff, annRev]);""")
rep("""  const [lineWeightsOff, setLineWeightsOff] = useState(() => {""", """  /** Bumped to redraw the pages (annotations hidden on a reopened save, update 15). */
  const [annRev, setAnnRev] = useState(0);
  const [lineWeightsOff, setLineWeightsOff] = useState(() => {""")

# ── Page tools + vector save ──
anchor = "  // Export to Proposal+Quotation dialog state (OE-DELIVERY 2026-10-27-export-proposal)."
assert s.count(anchor) == 1
s = s.replace(anchor, r"""  /* ── Revu page tools + vector Save PDF (update 15) ───────────────── */
  const [thumbSel, setThumbSel] = useState<Set<number>>(new Set());
  const thumbAnchorRef = useRef<number | null>(null);
  const [thumbMenu, setThumbMenu] = useState<{ x: number; y: number; pages: number[] } | null>(null);
  const [thumbSub, setThumbSub] = useState<string | null>(null);
  const pageClipRef = useRef<Uint8Array | null>(null);
  const filePickRef = useRef<HTMLInputElement | null>(null);
  const filePickActionRef = useRef<((bytes: Uint8Array) => void) | null>(null);
  const baseName = (fileName || exportProjectName || 'drawing').replace(/\.pdf$/i, '');
  const download = (bytes: Uint8Array | Blob, name: string) => {
    const blob = bytes instanceof Blob ? bytes : new Blob([bytes as BlobPart], { type: 'application/pdf' });
    triggerDownload(blob, name);
  };
  const viewportOf = async (n: number) => (await pdfDoc!.getPage(n)).getViewport({ scale: 1 });
  /** Snapshot of the visible markups + page scales for the given page map. */
  const snapshotFor = async (pageMap: Record<number, number>, rotate?: { pages: Set<number>; deg: 90 | 180 | 270 }) => {
    const keep = measurements.filter((m) => pageMap[m.page] !== undefined && !hiddenMeasurements.has(m.id) && !hiddenGroups.has(m.group));
    const sizes: Record<string, { w: number; h: number }> = {};
    const scales: Record<string, ScaleConfig> = {};
    const pm: Record<string, number> = {};
    const out: Measurement[] = [];
    for (const k of Object.keys(pageMap)) {
      const pg = Number(k);
      pm[k] = pageMap[pg]!;
      const vp = await viewportOf(pg);
      const rot = rotate && rotate.pages.has(pg) && rotate.deg !== 180;
      sizes[k] = rot ? { w: vp.height, h: vp.width } : { w: vp.width, h: vp.height };
      if (pageIsCalibrated(pageScales, pg)) scales[k] = scaleForPage(pageScales, pg);
    }
    for (const m of keep) {
      if (rotate && rotate.pages.has(m.page)) {
        const vp = await viewportOf(m.page);
        out.push({ ...m, points: m.points.map((q) => pdfPages.rotatePoint(q, rotate.deg, vp.width, vp.height)) });
      } else out.push(m);
    }
    return pdfPages.makeSnapshot(out, pm, sizes, scales);
  };
  /** Upload edited bytes as a new drawing and open it (or download). */
  const saveEditedPdf = async (bytes: Uint8Array, suffix: string) => {
    const name = `${baseName} (${suffix}).pdf`;
    const projectId = selectedProjectId || activeProjectId || '';
    if (!onOpenUploadedDocument || !projectId) {
      download(bytes, name);
      addToast({ type: 'success', title: 'Edited PDF downloaded', message: name });
      return;
    }
    const fd = new FormData();
    fd.append('file', new Blob([bytes as BlobPart], { type: 'application/pdf' }), name);
    const headers: Record<string, string> = { 'X-DDC-Client': 'OE/1.0' };
    const token = getAuthToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`/api/v1/takeoff/documents/upload/?project_id=${encodeURIComponent(projectId)}`, { method: 'POST', headers, body: fd });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
    const doc = (await res.json()) as { id: string; filename: string };
    try { saveNow(); } catch { /* ignore */ }
    addToast({ type: 'success', title: 'Pages updated', message: `Saved as ${doc.filename} - opening it with your markups.` });
    onOpenUploadedDocument({ id: doc.id, filename: doc.filename });
  };
  /** Run a page edit on the real file, carry the markups, save as a new drawing. */
  const runPageEdit = async (edit: pdfPages.PageEdit, suffix: string, rotate?: { pages: Set<number>; deg: 90 | 180 | 270 }) => {
    if (!pdfDoc) return;
    try {
      const orig = await pdfDoc.getData();
      const r = await pdfPages.editPages(orig, edit);
      const snap = await snapshotFor(r.pageMap, rotate);
      const bytes = await pdfPages.withSnapshot(r.bytes, snap);
      await saveEditedPdf(bytes, suffix);
    } catch (err) {
      addToast({ type: 'error', title: 'Page tool failed', message: err instanceof Error ? err.message : String(err) });
    }
  };
  const extractToBytes = async (pages: number[]) => {
    const orig = await pdfDoc!.getData();
    const bytes = await pdfPages.extractPages(orig, pages);
    const map: Record<number, number> = {};
    pages.forEach((pg, i) => { map[pg] = i + 1; });
    return pdfPages.withSnapshot(bytes, await snapshotFor(map));
  };
  const renderPagePng = async (n: number, scaleX = 2): Promise<Blob> => {
    const page = await pdfDoc!.getPage(n);
    const vp = page.getViewport({ scale: scaleX });
    const c = document.createElement('canvas');
    c.width = Math.ceil(vp.width);
    c.height = Math.ceil(vp.height);
    await page.render({ canvas: c, viewport: vp }).promise;
    const cx = c.getContext('2d');
    if (cx) {
      renderMeasurementsOnCanvas(cx, measurements, { pageNumber: n, dpr: 1, zoom: scaleX, scale, groupColorMap, hiddenGroups, hiddenMeasurements, measurementSystem });
    }
    return new Promise((res) => c.toBlob((b) => res(b ?? new Blob()), 'image/png'));
  };
  const pickPdf = (then: (bytes: Uint8Array) => void) => {
    filePickActionRef.current = then;
    filePickRef.current?.click();
  };
  /** Revu-style Save PDF: the original file + markups as PDF annotations +
   *  the editable ERP snapshot (markups and page scales). */
  const handleSaveVectorPdf = async () => {
    if (!pdfDoc) return;
    setIsExportingPdf(true);
    try {
      const orig = await pdfDoc.getData();
      const visible = measurements.filter((m) => !hiddenMeasurements.has(m.id) && !hiddenGroups.has(m.group) && !hiddenTypes.has(m.type));
      const byPage = new Map<number, pdfPages.AnnotInput[]>();
      const pages = [...new Set(visible.map((m) => m.page))];
      for (const pg of pages) {
        const vp = await viewportOf(pg);
        const toPdf = (q: Point) => {
          const [x, y] = vp.convertToPdfPoint(q.x, q.y) as [number, number];
          return { x, y };
        };
        byPage.set(pg, visible.filter((m) => m.page === pg).map((m) => ({
          m,
          color: resolveMeasurementColor(m, groupColorMap),
          toPdf,
          text: [m.customFields?.Subject, m.annotation, m.label].filter(Boolean).join(' - '),
        })));
      }
      const all: Record<number, number> = {};
      for (let i = 1; i <= pdfDoc.numPages; i++) all[i] = i;
      const snap = await snapshotFor(all);
      const r = await pdfPages.saveVectorPdf(orig, byPage, snap);
      download(r.bytes, `${baseName}.pdf`);
      addToast({ type: 'success', title: 'PDF saved', message: `${pdfDoc.numPages} pages, ${r.annots} markups as PDF annotations. Opening this file in the ERP again gives editable markups.` });
    } catch (err) {
      addToast({ type: 'error', title: 'Save PDF failed', message: err instanceof Error ? err.message : String(err) });
    } finally {
      setIsExportingPdf(false);
    }
  };
  const handleSaveVectorPdfRef = useRef(handleSaveVectorPdf);
  handleSaveVectorPdfRef.current = handleSaveVectorPdf;
  /** Thumbnail menu actions (Revu's page menu). */
  const thumbAction = async (key: string, pages: number[]) => {
    setThumbMenu(null);
    setThumbSub(null);
    if (!pdfDoc || pages.length === 0) return;
    const first = pages[0]!;
    const last = pages[pages.length - 1]!;
    const sel = new Set(pages);
    try {
      switch (key) {
        case 'setup': {
          const vp = await viewportOf(first);
          const page = await pdfDoc.getPage(first);
          addToast({ type: 'info', title: `Page ${first} setup`, message: `${(vp.width / 72).toFixed(2)} x ${(vp.height / 72).toFixed(2)} in (${Math.round(vp.width)} x ${Math.round(vp.height)} pt), rotation ${page.rotate} deg` });
          break;
        }
        case 'scale':
          goToPage(first);
          setSetScaleDlg({ pages });
          break;
        case 'copy':
        case 'cut': {
          pageClipRef.current = await pdfPages.extractPages(await pdfDoc.getData(), pages);
          if (key === 'cut') await runPageEdit({ kind: 'delete', pages }, 'pages cut');
          else addToast({ type: 'success', title: `${pages.length} page${pages.length === 1 ? '' : 's'} copied`, message: 'Right-click a page > Paste Pages to put them after it.' });
          break;
        }
        case 'paste':
          if (pageClipRef.current) await runPageEdit({ kind: 'insertPdf', after: last, other: pageClipRef.current }, 'pages pasted');
          break;
        case 'snapshot': {
          const png = await renderPagePng(first, 2);
          try {
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })]);
            addToast({ type: 'success', title: 'Page copied as a picture', message: `Page ${first} is on the clipboard.` });
          } catch {
            triggerDownload(png, `${baseName}-p${first}.png`);
          }
          break;
        }
        case 'stamp':
          goToPage(first);
          selectTool('stamp' as MeasureTool);
          break;
        case 'insertBlank':
          await runPageEdit({ kind: 'insertBlank', after: last, count: 1 }, 'blank page inserted');
          break;
        case 'insertPages':
          pickPdf((other) => { void runPageEdit({ kind: 'insertPdf', after: last, other }, 'pages inserted'); });
          break;
        case 'replace':
          pickPdf((other) => { void runPageEdit({ kind: 'replace', pages, other }, 'pages replaced'); });
          break;
        case 'extract':
          download(await extractToBytes(pages), `${baseName} (pages ${pages.join(',')}).pdf`);
          addToast({ type: 'success', title: 'Pages extracted', message: `${pages.length} page${pages.length === 1 ? '' : 's'} with their markups.` });
          break;
        case 'delete':
          if (pages.length >= pdfDoc.numPages) { addToast({ type: 'warning', title: 'Keep at least one page' }); break; }
          if (!window.confirm(`Delete page${pages.length === 1 ? '' : 's'} ${pages.join(', ')}? A new copy of the drawing is saved without them; the original stays.`)) break;
          await runPageEdit({ kind: 'delete', pages }, 'pages deleted');
          break;
        case 'rotateCw':
        case 'rotateCcw':
        case 'rotate180': {
          const deg = key === 'rotateCw' ? 90 : key === 'rotateCcw' ? 270 : 180;
          await runPageEdit({ kind: 'rotate', pages, deg }, 'pages rotated', { pages: sel, deg });
          break;
        }
        case 'number': {
          const prefix = window.prompt('Number pages - label prefix (e.g. S-, A-, or leave empty):', '') ?? null;
          if (prefix === null) break;
          const start = Number(window.prompt('Start at number:', '1') ?? '1') || 1;
          pages.forEach((pg, i) => saveSheetEdit(pg, { num: `${prefix}${start + i}` }));
          addToast({ type: 'success', title: 'Pages numbered', message: `${pages.length} page labels set.` });
          break;
        }
        case 'rename':
          setLeftTab('thumbs');
          setEditingThumb(first);
          break;
        case 'resetLabels':
          setSheetEdits({});
          try { localStorage.removeItem(sheetKey); } catch { /* ignore */ }
          addToast({ type: 'success', title: 'Page labels reset', message: 'Labels read from the title blocks again.' });
          break;
        case 'exportPdf':
          download(await extractToBytes(pages), `${baseName} (pages ${pages.join(',')}).pdf`);
          break;
        case 'exportPng':
          for (const pg of pages) triggerDownload(await renderPagePng(pg, 2), `${baseName}-p${pg}.png`);
          break;
        case 'email': {
          const nm = `${baseName} (pages ${pages.join(',')}).pdf`;
          download(await extractToBytes(pages), nm);
          window.location.href = `mailto:?subject=${encodeURIComponent(nm)}&body=${encodeURIComponent(`Attached: ${nm} (downloaded - attach it to this email).`)}`;
          break;
        }
        case 'print': {
          const url = URL.createObjectURL(new Blob([await extractToBytes(pages) as BlobPart], { type: 'application/pdf' }));
          const fr = document.createElement('iframe');
          fr.style.position = 'fixed';
          fr.style.width = '0';
          fr.style.height = '0';
          fr.src = url;
          document.body.appendChild(fr);
          fr.onload = () => { try { fr.contentWindow?.print(); } catch { window.open(url); } };
          break;
        }
        case 'repair':
          await runPageEdit({ kind: 'repair' }, 'repaired');
          break;
        case 'flatten': {
          const keep = measurements.filter((m) => sel.has(m.page));
          if (keep.length === 0) { addToast({ type: 'warning', title: 'No markups on these pages' }); break; }
          const pdf = await buildTakeoffPdf({ pdfDoc, measurements: keep, hiddenGroups, hiddenMeasurements, scale, groupColorMap, projectName: exportProjectName, measurementSystem });
          triggerDownload(pdf.output('blob'), `${baseName} (flattened ${pages.join(',')}).pdf`);
          break;
        }
        case 'summaryCsv': {
          const rows = [['Page', 'Sheet', 'Type', 'Subject', 'Label', 'Value', 'Unit', 'Group']];
          for (const m of measurements.filter((x) => sel.has(x.page))) {
            rows.push([String(m.page), sheetFor(m.page)?.num ?? '', TYPE_LABELS[m.type] ?? m.type, m.customFields?.Subject ?? '', m.annotation ?? '', String(+Number(m.value || 0).toFixed(4)), m.unit ?? '', m.group ?? '']);
          }
          const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
          triggerDownload(new Blob([csv], { type: 'text/csv' }), `${baseName} markup summary.csv`);
          break;
        }
        default:
          break;
      }
    } catch (err) {
      addToast({ type: 'error', title: 'Page tool failed', message: err instanceof Error ? err.message : String(err) });
    }
  };

""" + anchor)

# Save PDF button = vector save; old raster export stays in the File menu.
rep("""                <button
                  onClick={handleExportPdf}
                  disabled={isExportingPdf || !pdfDoc}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md bg-emerald-600""", """                <button
                  onClick={() => { void handleSaveVectorPdfRef.current(); }}
                  disabled={isExportingPdf || !pdfDoc}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md bg-emerald-600""")
rep("""title={t('takeoff_viewer.save_pdf_hint', { defaultValue: 'Save this drawing as a PDF with your measurements and markups' })}""",
    """title="Save the PDF (all pages, vector) with your markups as PDF annotations - Revu / Acrobat show them, and the ERP reopens them editable\"""")
rep("""                { label: 'Export PDF with markups…', onClick: () => { void handleExportPdf(); } },""",
    """                { label: 'Save PDF (markups as annotations)', onClick: () => { void handleSaveVectorPdfRef.current(); }, testId: 'revu-file-save-pdf' },
                { label: 'Export flattened PDF (picture + summary)…', onClick: () => { void handleExportPdf(); } },""")

# ── Thumbnail item: selection, page no. + scale line, right-click ──
rep("""                <button
                  key={n}
                  type="button"
                  onClick={() => goToPage(n)}
                  data-testid="thumbnail-item\"""", """                <button
                  key={n}
                  type="button"
                  onClick={(ev) => {
                    // Revu: Ctrl toggles, Shift adds a range; a plain click goes to the page.
                    if (ev.ctrlKey || ev.metaKey) {
                      setThumbSel((prev) => { const nx = new Set(prev.size ? prev : [currentPage]); if (nx.has(n)) nx.delete(n); else nx.add(n); return nx; });
                      thumbAnchorRef.current = n;
                      return;
                    }
                    if (ev.shiftKey) {
                      const a = thumbAnchorRef.current ?? currentPage;
                      const nx = new Set<number>();
                      for (let k = Math.min(a, n); k <= Math.max(a, n); k++) nx.add(k);
                      setThumbSel(nx);
                      return;
                    }
                    thumbAnchorRef.current = n;
                    setThumbSel(new Set());
                    goToPage(n);
                  }}
                  onContextMenu={(ev) => {
                    ev.preventDefault();
                    const pagesSel = thumbSel.size && thumbSel.has(n) ? [...thumbSel].sort((a, b) => a - b) : [n];
                    if (!thumbSel.has(n)) setThumbSel(new Set([n]));
                    setThumbSub(null);
                    setThumbMenu({ x: Math.min(ev.clientX, window.innerWidth - 270), y: Math.min(ev.clientY, window.innerHeight - 560), pages: pagesSel });
                  }}
                  data-selected={thumbSel.has(n) ? 'true' : undefined}
                  data-testid="thumbnail-item\"""")
rep("""                    n === currentPage
                      ? 'ring-2 ring-oe-blue border-oe-blue'
                      : 'border-border hover:border-oe-blue/60',
                  )}
                  title={sheetCaption(sheetFor(n)) || `Page ${n}`}""", """                    n === currentPage
                      ? 'ring-2 ring-oe-blue border-oe-blue'
                      : thumbSel.has(n)
                        ? 'ring-2 ring-sky-300 border-sky-400'
                        : 'border-border hover:border-oe-blue/60',
                  )}
                  title={sheetCaption(sheetFor(n)) || `Page ${n}`}""")
rep("""                    {countsByPage[n] ? (
                      <span className="tabular-nums rounded-full bg-purple-500/15 px-1 text-purple-500" data-testid="thumbnail-badge">
                        {countsByPage[n]}
                      </span>
                    ) : null}
                  </span>""", """                    {countsByPage[n] ? (
                      <span className="tabular-nums rounded-full bg-purple-500/15 px-1 text-purple-500" data-testid="thumbnail-badge">
                        {countsByPage[n]}
                      </span>
                    ) : null}
                  </span>
                  {/* Revu: page number, then the page's scale - click it to set the scale (update 15). */}
                  <span className="flex items-center justify-center gap-1 px-1 pb-0.5 text-[10px] leading-3">
                    <span className="font-semibold tabular-nums text-content-secondary" data-testid="thumb-page-no">{n}</span>
                    <span className="text-content-tertiary">·</span>
                    <span
                      role="button"
                      tabIndex={-1}
                      onClick={(ev) => { ev.stopPropagation(); goToPage(n); setSetScaleDlg({ pages: [n] }); }}
                      className={clsx('truncate hover:underline', pageIsCalibrated(pageScales, n) ? 'text-content-secondary' : 'text-amber-600')}
                      title="Set the scale of this page"
                      data-testid="thumb-scale"
                    >
                      {pageIsCalibrated(pageScales, n)
                        ? (DRAWING_SCALE_PRESETS.find((sp) => sameScale(scaleForPage(pageScales, n), sp.scale))?.label ?? formatScaleRatio(scaleForPage(pageScales, n)))
                        : 'Scale Not Set'}
                    </span>
                  </span>""")

# Set Scale window: pages picked from the thumbnails.
rep("""  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);""",
    """  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string; pages?: number[] } | null>(null);""")
rep("""        reason={setScaleDlg?.reason}
        extraPresets=""", """        reason={setScaleDlg?.reason}
        initialPages={setScaleDlg?.pages}
        extraPresets=""")

# Menu + hidden file input, next to the Set Scale window.
rep("""      {/* Revu's Calibrate window (update 14):""", """      {/* Thumbnail page menu (Revu, update 15). */}
      <input
        ref={filePickRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={async (ev) => {
          const f = ev.target.files?.[0];
          ev.target.value = '';
          if (!f) return;
          const act = filePickActionRef.current;
          filePickActionRef.current = null;
          act?.(new Uint8Array(await f.arrayBuffer()));
        }}
        data-testid="page-tools-file"
      />
      {thumbMenu && (
        <div className="fixed inset-0 z-[80]" onMouseDown={() => { setThumbMenu(null); setThumbSub(null); }} onContextMenu={(e) => { e.preventDefault(); setThumbMenu(null); }}>
          <div
            className="absolute w-64 rounded-md border border-border bg-surface-elevated py-1 text-[12px] shadow-2xl"
            style={{ left: thumbMenu.x, top: thumbMenu.y }}
            onMouseDown={(e) => e.stopPropagation()}
            data-testid="thumb-menu"
          >
            <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-content-tertiary">
              {thumbMenu.pages.length === 1 ? `Page ${thumbMenu.pages[0]}` : `${thumbMenu.pages.length} pages (${thumbMenu.pages.join(', ')})`}
            </div>
            {([
              ['setup', 'Page Setup…', ''],
              ['scale', 'Set Scale…', ''],
              ['-'],
              ['cut', 'Cut Pages', ''],
              ['copy', 'Copy Pages', ''],
              ['snapshot', 'Copy Page to Snapshot', 'Ctrl+Alt+C'],
              ['paste', 'Paste Pages', '', !pageClipRef.current],
              ['-'],
              ['stamp', 'Apply Stamp…', ''],
              ['-'],
              ['insertBlank', 'Insert Blank Page…', 'Ctrl+Shift+N'],
              ['insertPages', 'Insert Pages…', 'Ctrl+Shift+I'],
              ['extract', 'Extract Pages…', 'Ctrl+Shift+X'],
              ['replace', 'Replace Pages…', 'Ctrl+Shift+Y'],
              ['delete', 'Delete Pages…', 'Ctrl+Shift+D'],
              ['rotate', 'Rotate Pages', '>'],
              ['number', 'Number Pages…', ''],
              ['rename', 'Rename Page Label', ''],
              ['resetLabels', 'Reset All Page Labels', ''],
              ['-'],
              ['export', 'Export Pages', '>'],
              ['email', 'Email Pages…', ''],
              ['print', 'Print Pages…', ''],
              ['-'],
              ['repair', 'Repair PDF', ''],
              ['flatten', 'Flatten…', 'Ctrl+Shift+M'],
              ['-'],
              ['summary', 'Markup Summary', '>'],
            ] as [string, string?, string?, boolean?][]).map(([k, label, hint, disabled], i) =>
              k === '-' ? (
                <div key={`s${i}`} className="my-1 border-t border-border" />
              ) : (
                <div key={k} className="relative">
                  <button
                    type="button"
                    disabled={disabled}
                    onMouseEnter={() => setThumbSub(hint === '>' ? k : null)}
                    onClick={() => { if (hint === '>') setThumbSub(k); else void thumbAction(k, thumbMenu.pages); }}
                    className="flex w-full items-center justify-between px-3 py-1 text-left hover:bg-oe-blue hover:text-white disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-inherit"
                    data-testid={`thumb-menu-${k}`}
                  >
                    <span>{label}</span>
                    <span className="text-[10px] opacity-70">{hint === '>' ? '▸' : hint}</span>
                  </button>
                  {thumbSub === k && hint === '>' && (
                    <div className="absolute left-full top-0 ml-0.5 w-48 rounded-md border border-border bg-surface-elevated py-1 shadow-xl" data-testid={`thumb-sub-${k}`}>
                      {(k === 'rotate'
                        ? [['rotateCw', 'Clockwise 90°'], ['rotateCcw', 'Counter-clockwise 90°'], ['rotate180', '180°']]
                        : k === 'export'
                          ? [['exportPdf', 'PDF'], ['exportPng', 'Image (PNG)']]
                          : [['summaryCsv', 'CSV (Excel)']]
                      ).map(([sk, sl]) => (
                        <button key={sk} type="button" onClick={() => void thumbAction(sk!, thumbMenu.pages)} className="block w-full px-3 py-1 text-left hover:bg-oe-blue hover:text-white" data-testid={`thumb-menu-${sk}`}>
                          {sl}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ),
            )}
          </div>
        </div>
      )}
      {/* Revu's Calibrate window (update 14):""")
p.write_text(s, encoding="utf-8")

# Parent: open an uploaded (edited) drawing.
q = base / "features/takeoff/TakeoffPage.tsx"
t = q.read_text(encoding="utf-8")
a = """                  onCloseDocument={() => {"""
assert t.count(a) == 1
t = t.replace(a, """                  onOpenUploadedDocument={(d) => {
                    // A page tool saved an edited copy (update 15): list it and open it.
                    void refetchServerDocuments();
                    setActiveDocId(d.id);
                    setViewerDoc({ url: `/api/v1/takeoff/documents/${d.id}/download/`, name: d.filename, id: d.id });
                    setSearchParams(
                      (prev) => {
                        const next = new URLSearchParams(prev);
                        next.set('doc', d.id);
                        next.set('tab', 'measurements');
                        next.delete('page');
                        return next;
                      },
                      { replace: true },
                    );
                  }}
                  onCloseDocument={() => {""")
q.write_text(t, encoding="utf-8")
print("ok")
