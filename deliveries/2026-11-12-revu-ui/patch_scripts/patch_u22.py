"""Update 22: thumbnail scale as a clear pill, Chrome-style close tab top
right, New PDF follows the open drawing's size + scale, dimensions in the
saved PDF (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# 1. Thumbnail scale: a pill like the label (amber when not set).
rep("""                      className={clsx('truncate font-medium hover:underline', pageIsCalibrated(pageScales, n) ? 'text-content-primary' : 'text-amber-700')}""",
    """                      className={clsx(
                        'truncate rounded px-1.5 text-[11px] font-semibold leading-[18px] hover:ring-2 hover:ring-oe-blue/50',
                        pageIsCalibrated(pageScales, n) ? 'bg-emerald-700 text-white' : 'bg-amber-500 text-white',
                      )}""")

# 2. Close: a Chrome-style tab with x at the top right (menu bar).
rep("""          right={
            <button
              type="button"
              onClick={() => setRevuWorkspace((w) => !w)}""", """          right={
            <div className="flex items-center gap-2">
            {pdfDoc && onCloseDocument && (
              <div
                className="flex max-w-[320px] items-center gap-1 rounded-t-md border border-b-0 border-border bg-surface-primary py-0.5 pl-2.5 pr-0.5 text-[11px] text-content-primary shadow-sm"
                title={fileName || ''}
                data-testid="doc-tab"
              >
                <span className="truncate">{fileName || 'Drawing'}</span>
                <button
                  type="button"
                  onClick={closePdf}
                  className="ml-1 flex h-5 w-5 shrink-0 items-center justify-center rounded text-content-secondary transition-colors hover:bg-red-600 hover:text-white"
                  title="Close PDF (your work is saved first)"
                  aria-label="Close PDF"
                  data-testid="toolbar-close-pdf"
                >
                  <X size={13} />
                </button>
              </div>
            )}
            <button
              type="button"
              onClick={() => setRevuWorkspace((w) => !w)}""")
rep("""              {revuWorkspace ? 'Exit workspace' : 'Workspace'}
            </button>
          }""", """              {revuWorkspace ? 'Exit workspace' : 'Workspace'}
            </button>
            </div>
          }""")
i = s.index("                {onCloseDocument && (\n                  <button\n                    onClick={closePdf}")
j = s.index("                )}\n", i) + len("                )}\n")
s = s[:i] + s[j:]

# 3. New PDF: follow the open drawing's sheet size and scale.
rep("""      <NewPdfDialog open={newPdfOpen} onCancel={() => setNewPdfOpen(false)} onOk={(o) => { void runNewPdf(o); }} />""",
    """      <NewPdfDialog
        open={newPdfOpen}
        current={pageSizePdfRef.current ? { w: pageSizePdfRef.current.w, h: pageSizePdfRef.current.h } : undefined}
        scaleLabel={pdfDoc && pageIsCalibrated(pageScales, currentPage)
          ? (DRAWING_SCALE_PRESETS.find((sp) => sameScale(scaleForPage(pageScales, currentPage), sp.scale))?.label ?? formatScaleRatio(scaleForPage(pageScales, currentPage)))
          : undefined}
        onCancel={() => setNewPdfOpen(false)}
        onOk={(o) => { void runNewPdf(o); }}
      />""")
rep("""  const runNewPdf = async (o: { name: string; widthPt: number; heightPt: number; pages: number; label: string }) => {
    setNewPdfOpen(false);
    try {
      const bytes = await pdfPages.createBlankPdf(o.widthPt, o.heightPt, o.pages, o.name);""", """  const runNewPdf = async (o: { name: string; widthPt: number; heightPt: number; pages: number; label: string; keepScale?: boolean }) => {
    setNewPdfOpen(false);
    try {
      let bytes = await pdfPages.createBlankPdf(o.widthPt, o.heightPt, o.pages, o.name);
      // Same scale as the sheet on screen, set on every new page (update 22).
      if (o.keepScale && pdfDoc && pageIsCalibrated(pageScales, currentPage)) {
        const sc = scaleForPage(pageScales, currentPage);
        const pm: Record<string, number> = {};
        const sizes: Record<string, { w: number; h: number }> = {};
        const scales: Record<string, ScaleConfig> = {};
        for (let k = 1; k <= o.pages; k++) {
          pm[String(k)] = k;
          sizes[String(k)] = { w: o.widthPt, h: o.heightPt };
          scales[String(k)] = sc;
        }
        bytes = await pdfPages.withSnapshot(bytes, pdfPages.makeSnapshot([], pm, sizes, scales));
      }""")
# Scales from a file: apply again once the drawing's own (empty) server data has loaded.
rep("""        const sc = (snapshot as pdfPages.TakeoffSnapshotV).scales;
        if (sc) {
          setPageScales((prev) => Object.entries(sc).reduce((acc, [orig, cfg]) => {
            const to = snapshot.pageMap[orig] ?? Number(orig);
            return pageIsCalibrated(acc, to) ? acc : setPageScaleIn(acc, to, cfg);
          }, prev));
        }""", """        const sc = (snapshot as pdfPages.TakeoffSnapshotV).scales;
        if (sc) {
          const applyScales = () => setPageScales((prev) => Object.entries(sc).reduce((acc, [orig, cfg]) => {
            const to = snapshot.pageMap[orig] ?? Number(orig);
            return pageIsCalibrated(acc, to) ? acc : setPageScaleIn(acc, to, cfg);
          }, prev));
          applyScales();
          // A new server copy loads its (empty) page scales after this; set them again.
          for (const ms of [1500, 4000]) setTimeout(() => { if (!cancelled) applyScales(); }, ms);
        }""")

# 4. Dimensions written into the saved PDF.
rep("""          text: [m.customFields?.Subject, m.annotation, m.label].filter(Boolean).join(' - '),""", """          text: [m.customFields?.Subject, m.annotation].filter(Boolean).join(' - '),
          // The dimension as the sheet caption shows it (update 22).
          dim: (() => {
            if (m.type === 'count') return `${m.points.length} ea`;
            if (isAnnotationType(m.type) || m.type === 'angle' || !(Number(m.value) > 0)) return undefined;
            const u = String(m.unit || '');
            const kind: 'length' | 'area' | 'volume' = u.includes('\\u00B3') || u.includes('³') ? 'volume' : u.includes('\\u00B2') || u.includes('²') ? 'area' : 'length';
            try {
              return formatMarkupQuantity(m, Number(m.value), kind, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem);
            } catch {
              return m.label || undefined;
            }
          })(),""")
p.write_text(s, encoding="utf-8")

# New PDF dialog: "Same as this drawing" preset + keep-scale option.
q = base / "components/PdfCreateDialogs.tsx"
t = q.read_text(encoding="utf-8")


def trep(a, b):
    global t
    assert t.count(a) == 1, a[:90]
    t = t.replace(a, b)


trep("""export function NewPdfDialog({ open, onCancel, onOk }: {
  open: boolean;
  onCancel: () => void;
  onOk: (r: { name: string; widthPt: number; heightPt: number; pages: number; label: string }) => void;
}) {
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');
  const [preset, setPreset] = useState('ARCH D');""", """export function NewPdfDialog({ open, onCancel, onOk, current, scaleLabel }: {
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
  }, [open, current]);""")
trep("""  const p = PAGE_PRESETS.find((x) => x.name === preset)!;
  const w0 = mode === 'preset' ? p.w * PT[p.unit] : Number(cw) * PT[unit];
  const h0 = mode === 'preset' ? p.h * PT[p.unit] : Number(ch) * PT[unit];""", """  const same = preset === SAME && current;
  const p = PAGE_PRESETS.find((x) => x.name === preset) ?? PAGE_PRESETS[0]!;
  const w0 = mode === 'preset' ? (same ? current!.w : p.w * PT[p.unit]) : Number(cw) * PT[unit];
  const h0 = mode === 'preset' ? (same ? current!.h : p.h * PT[p.unit]) : Number(ch) * PT[unit];""")
trep("""              <select value={preset} onChange={(e) => setPreset(e.target.value)} className={`${sel} w-full`} data-testid="newpdf-preset">
                {['ANSI', 'ARCH', 'ISO'].map((g) => (""", """              <select value={preset} onChange={(e) => setPreset(e.target.value)} className={`${sel} w-full`} data-testid="newpdf-preset">
                {current && (
                  <option value={SAME}>Same as this drawing - {+(Math.max(current.w, current.h) / 72).toFixed(2)} x {+(Math.min(current.w, current.h) / 72).toFixed(2)} in</option>
                )}
                {['ANSI', 'ARCH', 'ISO'].map((g) => (""")
trep("""        <div className="flex items-center gap-2">
          <span className={lab}>Pages:</span>""", """        {scaleLabel && (
          <label className="flex items-center gap-2 pl-[86px]" data-testid="newpdf-keep-scale-row">
            <input type="checkbox" checked={keepScale} onChange={(e) => setKeepScale(e.target.checked)} data-testid="newpdf-keep-scale" />
            Use this drawing's scale on the new pages ({scaleLabel})
          </label>
        )}
        <div className="flex items-center gap-2">
          <span className={lab}>Pages:</span>""")
trep("""onOk({ name: name.trim(), widthPt, heightPt, pages, label: mode === 'preset' ? preset : `${cw} x ${ch} ${unit}` })""",
     """onOk({ name: name.trim(), widthPt, heightPt, pages, label: mode === 'preset' ? (same ? 'same size as the drawing' : preset) : `${cw} x ${ch} ${unit}`, keepScale: Boolean(scaleLabel) && keepScale })""")
trep("""const PT = { in: 72, mm: 72 / 25.4 } as const;""", """const PT = { in: 72, mm: 72 / 25.4 } as const;
const SAME = '__same__';""")
q.write_text(t, encoding="utf-8")
print("ok")
