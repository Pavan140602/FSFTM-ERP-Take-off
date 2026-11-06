# OE-DELIVERY 2026-11-03-takeoff-workarea: compact header (more drawing), drawing stays open
# across modules (also via /takeoff with no tab), same page on return, Current + Recent list.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    if s.count(old) != count:
        print('ANCHOR FAIL', s.count(old), old[:160])
        sys.exit(1)
    s = s.replace(old, new)


# ── recent (last opened) order + Current badge in the bottom strip ──
rep("""function TakeoffDocFilmstrip({
  documents,
  activeDocId,
  isLoading,
  onSelectDoc,
  onDeleteDoc,
  onUploadNew,
}: {
  documents: UploadedDocument[];
  activeDocId: string | null;""", """function TakeoffDocFilmstrip({
  documents,
  activeDocId,
  isLoading,
  onSelectDoc,
  onDeleteDoc,
  onUploadNew,
  recentIds = [],
}: {
  documents: UploadedDocument[];
  /** Last-opened order, most recent first (OE-DELIVERY 2026-11-03-takeoff-workarea). */
  recentIds?: string[];
  activeDocId: string | null;""")
rep("""      if (sortBy === 'size') return b.size_bytes - a.size_bytes;
      // 'recent' — newest uploaded_at first.
      const at = new Date(a.uploaded_at || 0).getTime();""", """      if (sortBy === 'size') return b.size_bytes - a.size_bytes;
      // 'recent' - the drawing open now, then the ones opened most recently,
      // then the rest by upload date.
      const ra = a.id === activeDocId ? -1 : recentIds.indexOf(a.id);
      const rb = b.id === activeDocId ? -1 : recentIds.indexOf(b.id);
      const ka = ra === -1 && a.id !== activeDocId ? 1e6 : ra;
      const kb = rb === -1 && b.id !== activeDocId ? 1e6 : rb;
      if (ka !== kb) return ka - kb;
      const at = new Date(a.uploaded_at || 0).getTime();""")
rep("""  }, [documents, sortBy, pinned]);""", """  }, [documents, sortBy, pinned, recentIds, activeDocId]);""")
rep("""        <span className="text-xs font-semibold text-content-primary">
          {t('takeoff.documents_panel', { defaultValue: 'Documents' })}
        </span>""", """        <span className="text-xs font-semibold text-content-primary">
          {t('takeoff.documents_panel_recent', { defaultValue: 'Current & recent drawings' })}
        </span>""")
rep("""                        {doc.filename}
                      </span>
                      {isPinned && (""", """                        {doc.filename}
                      </span>
                      {isActive && (
                        <span className="shrink-0 rounded bg-oe-blue px-1 text-[8px] font-bold uppercase leading-[13px] text-white" data-testid="filmstrip-current">
                          {t('takeoff.current', { defaultValue: 'Current' })}
                        </span>
                      )}
                      {isPinned && (""")

# ── default tab: back on the drawing when one was open ──
rep("""  const initialTab: TakeoffTab =
    tabFromUrl === 'measurements' || tabFromUrl === 'documents' ? tabFromUrl : 'documents';""",
    """  // With no ?tab=, land on the drawing that was open last time instead of
  // the documents list (OE-DELIVERY 2026-11-03-takeoff-workarea).
  const initialTab: TakeoffTab =
    tabFromUrl === 'measurements' || tabFromUrl === 'documents'
      ? tabFromUrl
      : (() => {
          try {
            for (let i = 0; i < localStorage.length; i++) {
              const k = localStorage.key(i);
              if (k && k.startsWith('takeoff.lastOpenDoc.') && localStorage.getItem(k)) return 'measurements';
            }
          } catch { /* ignore */ }
          return 'documents';
        })();""")

# ── remember recent + page; compact header state ──
rep("""  useEffect(() => {
    if (!viewerDoc) return;
    try {
      localStorage.setItem(`takeoff.lastOpenDoc.${selectedProjectId || 'noproject'}`, viewerDoc.id);
    } catch { /* ignore */ }
  }, [viewerDoc, selectedProjectId]);""", """  useEffect(() => {
    if (!viewerDoc) return;
    try {
      localStorage.setItem(`takeoff.lastOpenDoc.${selectedProjectId || 'noproject'}`, viewerDoc.id);
    } catch { /* ignore */ }
  }, [viewerDoc, selectedProjectId]);

  /* Recently opened drawings, most recent first (OE-DELIVERY 2026-11-03-takeoff-workarea). */
  const recentKey = `takeoff.recentDocs.${selectedProjectId || 'noproject'}`;
  const [recentIds, setRecentIds] = useState<string[]>(() => {
    try {
      const v = JSON.parse(localStorage.getItem(`takeoff.recentDocs.${activeProjectId || 'noproject'}`) || '[]');
      return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
    } catch { return []; }
  });
  useEffect(() => {
    if (!viewerDoc) return;
    setRecentIds((prev) => {
      const next = [viewerDoc.id, ...prev.filter((x) => x !== viewerDoc.id)].slice(0, 12);
      try { localStorage.setItem(recentKey, JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    });
  }, [viewerDoc, recentKey]);
  /** Page each drawing was left on, so coming back opens the same sheet. */
  const storedPageFor = (docId: string): number | undefined => {
    try {
      const v = parseInt(localStorage.getItem(`takeoff.lastPage.${docId}`) || '', 10);
      return Number.isFinite(v) && v > 0 ? v : undefined;
    } catch { return undefined; }
  };
  /** Compact header: the page header, info card and tabs shrink to one slim
   *  bar so the drawing gets the room. */
  const [compactHeader, setCompactHeader] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.compactHeader') !== '0'; } catch { return true; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.compactHeader', compactHeader ? '1' : '0'); } catch { /* ignore */ }
  }, [compactHeader]);""")

rep("""  const handleViewerPageChange = useCallback(
    (page: number) => {
      setSearchParams(""", """  const handleViewerPageChange = useCallback(
    (page: number) => {
      if (viewerDocIdRef.current) {
        try { localStorage.setItem(`takeoff.lastPage.${viewerDocIdRef.current}`, String(page)); } catch { /* ignore */ }
      }
      setSearchParams(""")
rep("""  /** True while a cross-module `?doc=X&source=document` open is resolving""",
    """  const viewerDocIdRef = useRef<string | null>(null);
  viewerDocIdRef.current = viewerDoc?.id ?? null;

  /** True while a cross-module `?doc=X&source=document` open is resolving""")
rep("""                  initialPage={
                    viewerDoc && viewerDoc.id === deepLinkedDocIdRef.current
                      ? (initialPage ?? undefined)
                      : undefined
                  }""", """                  initialPage={
                    viewerDoc && viewerDoc.id === deepLinkedDocIdRef.current && initialPage
                      ? initialPage
                      : viewerDoc
                        ? storedPageFor(viewerDoc.id)
                        : undefined
                  }""")
rep("""            onUploadNew={() => filmstripUploadRef.current?.click()}
          />
          {/* Hidden file input shared between Documents tab and Measurements filmstrip. */}""",
    """            onUploadNew={() => filmstripUploadRef.current?.click()}
            recentIds={recentIds}
          />
          {/* Hidden file input shared between Documents tab and Measurements filmstrip. */}""")

# ── compact header ──
COMPACT = "compactHeader && activeTab === 'measurements'"
rep("""      <div className="shrink-0 space-y-5">""", """      <div className={clsx('shrink-0', """ + COMPACT + """ ? 'space-y-1' : 'space-y-5')}>
      {!(""" + COMPACT + """) && (<>""")
rep("""        {t('takeoff.intro_body', {
          defaultValue:
            'Upload PDF drawings to measure areas, lengths and counts by hand, or let AI extract elements with quantities. Selected measurements flow straight into your BOQ and stay linked to the project cost and schedule.',
        })}
      </DismissibleInfo>""", """        {t('takeoff.intro_body', {
          defaultValue:
            'Upload PDF drawings to measure areas, lengths and counts by hand, or let AI extract elements with quantities. Selected measurements flow straight into your BOQ and stay linked to the project cost and schedule.',
        })}
      </DismissibleInfo>
      </>)}""")
rep("""      <div className="flex items-stretch gap-2">
      <div
        className="flex flex-1 gap-1 rounded-md border border-border-light/80 bg-surface-secondary/40 p-1\"""",
    """      <div className="flex items-stretch gap-2">
      <div
        className={clsx('flex flex-1 gap-1 rounded-md border border-border-light/80 bg-surface-secondary/40', """ + COMPACT + """ ? 'p-0.5' : 'p-1')}""")
s = s.replace("""            'flex flex-1 items-center justify-center gap-2 rounded-sm px-4 py-2 text-sm font-semibold transition-colors',""",
              """            'flex flex-1 items-center justify-center gap-2 rounded-sm px-4 font-semibold transition-colors',
            """ + COMPACT + """ ? 'py-0.5 text-xs' : 'py-2 text-sm',""")
rep("""        <GitCompare size={15} strokeWidth={2.1} aria-hidden />
        <span className="hidden sm:inline">
          {t('takeoff_compare.compare_short', { defaultValue: 'Compare' })}
        </span>
      </button>
      </div>""", """        <GitCompare size={15} strokeWidth={2.1} aria-hidden />
        <span className="hidden sm:inline">
          {t('takeoff_compare.compare_short', { defaultValue: 'Compare' })}
        </span>
      </button>
      {activeTab === 'measurements' && (
        <button
          type="button"
          onClick={() => setCompactHeader((v) => !v)}
          className="inline-flex items-center rounded-md border border-border-light/80 bg-surface-secondary/40 px-2 text-content-secondary hover:bg-surface-primary/60 hover:text-oe-blue"
          title={compactHeader ? t('takeoff.expand_header', { defaultValue: 'Show the page header' }) : t('takeoff.compact_header', { defaultValue: 'Minimise the header - more room for the drawing' })}
          aria-pressed={compactHeader}
          data-testid="takeoff-compact-toggle"
        >
          <ChevronDown size={14} className={clsx('transition-transform', compactHeader ? '' : 'rotate-180')} />
        </button>
      )}
      </div>""")
rep("""          className="mt-5 flex flex-1 min-h-0 flex-col overflow-x-hidden"
          role="tabpanel"
          id="takeoff-tabpanel-measurements\"""", """          className={clsx('flex flex-1 min-h-0 flex-col overflow-x-hidden', compactHeader ? 'mt-1.5' : 'mt-5')}
          role="tabpanel"
          id="takeoff-tabpanel-measurements\"""")
P.write_text(s, encoding='utf-8')
print('ok', s.count(COMPACT))
