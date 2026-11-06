# OE-DELIVERY 2026-11-05-detail-scan: "Not taken off" list in the Auto Takeoff panel.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) / "frontend/src/modules/pdf-takeoff"
V = ROOT / "TakeoffViewerModule.tsx"
P = ROOT / "AutoTakeoffPanel.tsx"
S = {V: V.read_text(encoding="utf-8"), P: P.read_text(encoding="utf-8")}


def rep(f, old, new):
    if S[f].count(old) != 1:
        print("ANCHOR FAIL", f.name, S[f].count(old), old[:120])
        sys.exit(1)
    S[f] = S[f].replace(old, new)


# â”€â”€ panel types + prop â”€â”€
rep(P, '''  items: AutoItem[];
  note: string | null;
}''', '''  items: AutoItem[];
  note: string | null;
  /** Tags no markup answers, for review (OE-DELIVERY 2026-11-05-detail-scan). */
  missed?: AutoMissed[];
}

export interface AutoMissed {
  designation: string;
  category: string | null;
  role?: string | null;
  at: [number, number];
  page: number;
  reason: string;
}''')
rep(P, '''  onJumpToPage: (page: number) => void;''', '''  onJumpToPage: (page: number) => void;
  /** Zoom to a spot on a page (tags not taken off). */
  onFocusSpot?: (page: number, x: number, y: number) => void;''')
rep(P, '''  const { documentId, currentPage, pageCount, stats, onApply, onRestyle, onRemove, onJumpToPage, list, rejectedCount, onForgetRejected, highlightAll, onToggleHighlight, showColumns, onToggleColumns } = props;''',
    '''  const { documentId, currentPage, pageCount, stats, onApply, onRestyle, onRemove, onJumpToPage, onFocusSpot, list, rejectedCount, onForgetRejected, highlightAll, onToggleHighlight, showColumns, onToggleColumns } = props;
  const [showAllMissed, setShowAllMissed] = useState(false);''')
rep(P, '''          {last.res.read?.framing_rules && (''', '''          {(() => {
            const missed = last.res.pages.flatMap((pg) => pg.missed ?? []);
            if (missed.length === 0) {
              return last.res.read?.framing_rules ? (
                <p className="text-content-secondary" data-testid="auto-missed-none">
                  Every tag on the plans read was taken off.
                </p>
              ) : null;
            }
            const shown = showAllMissed ? missed : missed.slice(0, 8);
            return (
              <div className="rounded border border-amber-300 bg-amber-50/60 p-1.5 space-y-0.5" data-testid="auto-missed">
                <p className="font-semibold text-amber-700">
                  Not taken off ({missed.length}) â€” check these tags on the sheet
                </p>
                {shown.map((m, i) => (
                  <button
                    key={`${m.page}-${m.designation}-${i}`}
                    type="button"
                    className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-start hover:bg-amber-100"
                    title={m.reason}
                    onClick={() => (onFocusSpot ? onFocusSpot(m.page, m.at[0], m.at[1]) : onJumpToPage(m.page))}
                    data-testid="auto-missed-row"
                  >
                    <span className="font-semibold">{m.designation}</span>
                    <span className="text-content-tertiary">{m.role ?? m.category ?? ''}</span>
                    <span className="ms-auto text-content-tertiary">p.{m.page}</span>
                  </button>
                ))}
                {missed.length > 8 && (
                  <button type="button" className="text-oe-blue underline" onClick={() => setShowAllMissed((v) => !v)}>
                    {showAllMissed ? 'Show fewer' : `Show all ${missed.length}`}
                  </button>
                )}
              </div>
            );
          })()}
          {last.res.read?.framing_rules && (''')

# â”€â”€ viewer: zoom to a spot â”€â”€
rep(V, '''  const focusAutoMarkup = useCallback(''', '''  /** Zoom to a spot (a tag Auto Takeoff could not take off), changing page
   *  first when needed (OE-DELIVERY 2026-11-05-detail-scan). */
  const pendingSpotRef = useRef<{ page: number; x: number; y: number } | null>(null);
  const zoomToSpot = useCallback(
    (cx: number, cy: number) => {
      const vp = viewportSize();
      const res = computeZoomToBox({ minX: cx - 110, minY: cy - 110, maxX: cx + 110, maxY: cy + 110 }, vp.width, vp.height, {
        fallbackZoom: zoomRef.current || 1,
      });
      zoomTo(res.zoom);
      const centre = (tries: number) => {
        const c = containerRef.current;
        const canvas = canvasRef.current;
        if (!c || !canvas) return;
        const z = zoomRef.current || 1;
        const cr = canvas.getBoundingClientRect();
        const vr = c.getBoundingClientRect();
        const dx = cr.left + cx * z - (vr.left + vr.width / 2);
        const dy = cr.top + cy * z - (vr.top + vr.height / 2);
        c.scrollLeft += dx;
        c.scrollTop += dy;
        if (tries > 0 && (Math.abs(dx) > 2 || Math.abs(dy) > 2)) window.setTimeout(() => centre(tries - 1), 120);
      };
      window.setTimeout(() => requestAnimationFrame(() => centre(3)), 80);
    },
    [viewportSize, zoomTo],
  );
  const focusSpot = useCallback(
    (page: number, x: number, y: number) => {
      if (page !== currentPageRef.current) {
        pendingSpotRef.current = { page, x, y };
        goToPage(page);
        return;
      }
      zoomToSpot(x, y);
    },
    [goToPage, zoomToSpot],
  );
  useEffect(() => {
    const sp = pendingSpotRef.current;
    if (!sp || sp.page !== currentPage) return;
    pendingSpotRef.current = null;
    const timer = window.setTimeout(() => zoomToSpot(sp.x, sp.y), 350);
    return () => window.clearTimeout(timer);
  }, [currentPage, zoomToSpot]);

  const focusAutoMarkup = useCallback(''')
rep(V, '''                onJumpToPage={goToPage}
                rejectedCount={autoRejected.length}''', '''                onJumpToPage={goToPage}
                onFocusSpot={focusSpot}
                rejectedCount={autoRejected.length}''')

for f, t in S.items():
    f.write_text(t, encoding="utf-8")
print("ok")
