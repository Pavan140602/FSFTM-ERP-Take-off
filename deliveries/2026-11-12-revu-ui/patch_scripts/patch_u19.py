"""Update 19: thumbnail labels (title block or the PDF's own page labels),
Revu Extract / Delete Pages windows, Ctrl+C / Ctrl+V markups to the same
position on another page (OE-DELIVERY 2026-11-12-revu-ui)."""
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
    "import { ExtractPagesDialog, DeletePagesDialog, type ExtractOptions } from './components/PageToolsDialogs';")

# ── Labels: title block, else the PDF's own page label ──
rep("""  const sheetFor = useCallback(
    (page: number): SheetEntry | null => sheetEdits[page] ?? detectedSheets[page] ?? null,
    [sheetEdits, detectedSheets],
  );""", """  const sheetFor = useCallback(
    (page: number): SheetEntry | null => sheetEdits[page] ?? detectedSheets[page] ?? null,
    [sheetEdits, detectedSheets],
  );
  /** Page label shown on a thumbnail (update 19): the edited / title-block
   *  sheet number, else the PDF's own page label (e.g. A000), else ''. */
  const pageLabelOf = (n: number): string => {
    const own = sheetFor(n)?.num;
    if (own) return own;
    const pl = pageLabels?.[n - 1]?.trim();
    return pl && pl !== String(n) ? pl : '';
  };""")
rep("""                        {sheetFor(n)?.num || `+ sheet (${n})`}""", """                        {pageLabelOf(n) || `+ label`}""")
rep("""                        className={clsx('min-w-0 truncate font-semibold hover:underline', sheetFor(n)?.num ? 'text-content-primary' : 'italic text-content-tertiary')}""",
    """                        className={clsx('min-w-0 truncate text-[12px] font-bold hover:underline', pageLabelOf(n) ? 'text-content-primary' : 'italic font-normal text-content-tertiary')}""")
rep("""                        defaultValue={sheetFor(n)?.num ?? ''}""", """                        defaultValue={pageLabelOf(n)}""")

# ── Extract / Delete windows ──
rep("""  /** Upload edited bytes as a new drawing and open it (or download). */""", """  /** Revu Extract / Delete Pages windows (update 19). */
  const [pageDlg, setPageDlg] = useState<{ kind: 'extract' | 'delete'; pages: number[] } | null>(null);
  /** Upload a PDF to the project's drawings; null when there is no project. */
  const uploadPdf = async (bytes: Uint8Array, name: string): Promise<{ id: string; filename: string } | null> => {
    const projectId = selectedProjectId || activeProjectId || '';
    if (!projectId) return null;
    const fd = new FormData();
    fd.append('file', new Blob([bytes as BlobPart], { type: 'application/pdf' }), name);
    const headers: Record<string, string> = { 'X-DDC-Client': 'OE/1.0' };
    const token = getAuthToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`/api/v1/takeoff/documents/upload/?project_id=${encodeURIComponent(projectId)}`, { method: 'POST', headers, body: fd });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
    return (await res.json()) as { id: string; filename: string };
  };
  const runExtract = async (o: ExtractOptions) => {
    setPageDlg(null);
    if (!pdfDoc || o.pages.length === 0) return;
    try {
      const safe = (t: string) => t.replace(/[\\\\/:*?"<>|]+/g, '-').trim();
      const files: { bytes: Uint8Array; name: string }[] = [];
      if (o.separate) {
        for (const pg of o.pages) {
          const lbl = o.useLabels ? pageLabelOf(pg) : '';
          files.push({ bytes: await extractToBytes([pg]), name: `${safe(lbl || `${baseName} (page ${pg})`)}.pdf` });
        }
      } else {
        files.push({ bytes: await extractToBytes(o.pages), name: `${safe(`${baseName} (pages ${o.pages.join(',')})`)}.pdf` });
      }
      let firstOpened: { id: string; filename: string } | null = null;
      if (o.openAfter && (selectedProjectId || activeProjectId)) {
        for (const f of files) {
          if (o.overwrite) {
            const same = (recentDocuments ?? []).find((d) => d.filename === f.name);
            if (same) {
              const headers: Record<string, string> = {};
              const token = getAuthToken();
              if (token) headers['Authorization'] = `Bearer ${token}`;
              await fetch(`/api/v1/takeoff/documents/${same.id}/`, { method: 'DELETE', headers }).catch(() => undefined);
            }
          }
          const d = await uploadPdf(f.bytes, f.name);
          if (d && !firstOpened) firstOpened = d;
        }
      } else {
        for (const f of files) download(f.bytes, f.name);
      }
      addToast({
        type: 'success',
        title: 'Pages extracted',
        message: `${o.pages.length} page${o.pages.length === 1 ? '' : 's'} into ${files.length} file${files.length === 1 ? '' : 's'}${o.openAfter && firstOpened ? ', added to the drawings' : ''}, with their markups.`,
      });
      if (o.deleteAfter) {
        await runPageEdit({ kind: 'delete', pages: o.pages }, 'pages extracted');
      } else if (firstOpened && onOpenUploadedDocument) {
        try { saveNow(); } catch { /* ignore */ }
        onOpenUploadedDocument(firstOpened);
      }
    } catch (err) {
      addToast({ type: 'error', title: 'Extract failed', message: err instanceof Error ? err.message : String(err) });
    }
  };
  /** Upload edited bytes as a new drawing and open it (or download). */""")
rep("""        case 'extract':
          download(await extractToBytes(pages), `${baseName} (pages ${pages.join(',')}).pdf`);
          addToast({ type: 'success', title: 'Pages extracted', message: `${pages.length} page${pages.length === 1 ? '' : 's'} with their markups.` });
          break;
        case 'delete':
          if (pages.length >= pdfDoc.numPages) { addToast({ type: 'warning', title: 'Keep at least one page' }); break; }
          if (!window.confirm(`Delete page${pages.length === 1 ? '' : 's'} ${pages.join(', ')}? A new copy of the drawing is saved without them; the original stays.`)) break;
          await runPageEdit({ kind: 'delete', pages }, 'pages deleted');
          break;""", """        case 'extract':
          setPageDlg({ kind: 'extract', pages });
          break;
        case 'delete':
          setPageDlg({ kind: 'delete', pages });
          break;""")
rep("""      {/* Thumbnail page menu (Revu, update 15). */}""", """      <ExtractPagesDialog
        open={pageDlg?.kind === 'extract'}
        currentPage={currentPage}
        selected={pageDlg?.pages ?? []}
        totalPages={totalPages || 1}
        onCancel={() => setPageDlg(null)}
        onOk={(o) => { void runExtract(o); }}
      />
      <DeletePagesDialog
        open={pageDlg?.kind === 'delete'}
        currentPage={currentPage}
        selected={pageDlg?.pages ?? []}
        totalPages={totalPages || 1}
        onCancel={() => setPageDlg(null)}
        onOk={(pages) => { setPageDlg(null); void runPageEdit({ kind: 'delete', pages }, 'pages deleted'); }}
      />
      {/* Thumbnail page menu (Revu, update 15). */}""")

# ── Ctrl+C / Ctrl+V markups ──
rep("""      // Ctrl+S saves the work (update 15).""", """      // Ctrl+C / Ctrl+V markups (update 19): copy the selected markups, paste
      // them on the page on screen at the SAME position (Revu).
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && shouldHandleShortcut(e.target)) {
        const k = e.key.toLowerCase();
        if (k === 'c') {
          const ids = selectedLedgerIdsRef.current.size
            ? [...selectedLedgerIdsRef.current]
            : selectedMeasurementIdRef.current ? [selectedMeasurementIdRef.current] : [];
          const picked = measurementsRef.current.filter((m) => ids.includes(m.id));
          if (picked.length) {
            e.preventDefault();
            markupClipRef.current = picked.map((m) => JSON.parse(JSON.stringify(m)) as Measurement);
            addToast({ type: 'success', title: `${picked.length} markup${picked.length === 1 ? '' : 's'} copied`, message: 'Go to any page and press Ctrl+V - they paste in the same place.' });
            return;
          }
        }
        if (k === 'v' && markupClipRef.current?.length) {
          e.preventDefault();
          pasteMarkupsRef.current();
          return;
        }
      }

      // Ctrl+S saves the work (update 15).""")
rep("""  /** Save the work now (button, File > Save, Ctrl+S - update 15). */""", """  /** Copied markups (Ctrl+C) and the paste routine (Ctrl+V), update 19. */
  const markupClipRef = useRef<Measurement[] | null>(null);
  const pasteMarkupsRef = useRef<() => void>(() => {});
  pasteMarkupsRef.current = () => {
    const clip = markupClipRef.current;
    if (!clip || clip.length === 0) return;
    const page = currentPageRef.current;
    const sc = scaleForPage(pageScalesRef.current, page);
    const stamp = Date.now();
    const idMap = new Map<string, string>();
    clip.forEach((m, i) => idMap.set(m.id, `m_${stamp}_p${i}_${Math.random().toString(36).slice(2, 6)}`));
    const groupMap = new Map<string, string>();
    const clones: Measurement[] = clip.map((m) => {
      const id = idMap.get(m.id)!;
      let next: Measurement = {
        ...m,
        id,
        page,
        serverId: undefined,
        suggested: undefined,
        linkedPositionId: undefined,
        linkedPositionOrdinal: undefined,
        linkedBoqId: undefined,
        linkedPositionLabel: undefined,
        points: m.points.map((q) => ({ ...q })),
        createdAt: new Date().toISOString(),
      };
      if (m.markupGroupId) {
        if (!groupMap.has(m.markupGroupId)) groupMap.set(m.markupGroupId, `${m.markupGroupId}_p${stamp}`);
        next.markupGroupId = groupMap.get(m.markupGroupId);
      }
      if (m.cutoutOf) next.cutoutOf = idMap.get(m.cutoutOf);
      // Re-measured with the target page's scale.
      if (!isAnnotationType(m.type) && m.type !== 'count' && sc.pixelsPerUnit > 0) {
        try {
          const patch = recomputeMeasurement(next as never, next.points, sc) as Partial<Measurement> | null;
          if (patch) next = { ...next, ...patch };
        } catch { /* keep the copied values */ }
      }
      return next;
    });
    pushUndo({ kind: 'bulk_add', measurements: clones });
    setMeasurements((prev) => [...prev, ...clones]);
    setSelectedLedgerIds(new Set(clones.map((c) => c.id)));
    addToast({ type: 'success', title: `${clones.length} markup${clones.length === 1 ? '' : 's'} pasted`, message: `Page ${page}, same position.` });
  };

  /** Save the work now (button, File > Save, Ctrl+S - update 15). */""")
p.write_text(s, encoding="utf-8")
print("ok")
