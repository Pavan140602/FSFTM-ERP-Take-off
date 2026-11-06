"""Revu status bar, tool-set captions, auto label name (all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-statusbar"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-statusbar'

CURSOR = r'''  /* Revu status bar cursor readout (TAGX): written straight into the
   * DOM on pointer move (rAF-throttled) so the big viewer never re-renders
   * just because the mouse moved. */
  const statusCursorRef = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    const c = containerRef.current;
    if (!c) return;
    let raf = 0;
    let last: { clientX: number; clientY: number } | null = null;
    const fmt = (units: number): string => {
      const sc = scaleForPage(pageScalesRef.current, currentPageRef.current);
      if (!sc.pixelsPerUnit || sc.pixelsPerUnit <= 0) return `${units.toFixed(0)} pt`;
      const metres = units / sc.pixelsPerUnit;
      const imperial = sc.displayUnit === 'ftin' || sc.displayUnit === 'ft' || String(measurementSystem) === 'imperial';
      if (!imperial) return `${metres.toFixed(2)} m`;
      return formatFeetInches(Math.abs(metres) / FT_TO_M) || `0'-0"`;
    };
    const paint = () => {
      raf = 0;
      const el = statusCursorRef.current;
      if (!el) return;
      const p = last ? pointerToPdf(last) : null;
      el.textContent = p ? `X ${fmt(p.x)}   Y ${fmt(p.y)}` : 'X —   Y —';
    };
    const onMove = (e: PointerEvent) => {
      last = { clientX: e.clientX, clientY: e.clientY };
      if (!raf) raf = requestAnimationFrame(paint);
    };
    const onLeave = () => {
      last = null;
      if (!raf) raf = requestAnimationFrame(paint);
    };
    c.addEventListener('pointermove', onMove);
    c.addEventListener('pointerleave', onLeave);
    return () => {
      c.removeEventListener('pointermove', onMove);
      c.removeEventListener('pointerleave', onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [pointerToPdf, pdfDoc, measurementSystem]);

'''.replace('TAGX', TAG)

STATUS = r'''              {/* Revu-style status bar (TAGX): snap, zoom, page size,
                  live cursor position in drawing units. */}
              <div className="ml-auto flex flex-wrap items-center gap-2 text-[11px] text-content-secondary" data-testid="revu-status">
                {pageMode === 'continuous' && totalPages > 1 ? (
                  <span className="text-content-tertiary">{t('takeoff_viewer.scroll_hint', { defaultValue: 'Scroll to move between pages' })}</span>
                ) : null}
                <button
                  type="button"
                  onClick={() => { setContentSnap((x) => { const next = !x; try { localStorage.setItem('oe-content-snap', next ? '1' : '0'); } catch { /* ignore */ } return next; }); setSnapPoint(null); }}
                  aria-pressed={contentSnap}
                  title="Snap to the drawing's lines and points"
                  className={clsx(
                    'rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide border',
                    contentSnap ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-tertiary',
                  )}
                  data-testid="revu-status-snap"
                >
                  SNAP
                </button>
                <span className="tabular-nums" title="Zoom">{Math.round(zoom * 100)}%</span>
                {pageSizePdfRef.current && pageSizePdfRef.current.page === currentPage && (
                  <span className="tabular-nums text-content-tertiary" title="Sheet size">
                    {(pageSizePdfRef.current.w / 72).toFixed(1)} × {(pageSizePdfRef.current.h / 72).toFixed(1)} in
                  </span>
                )}
                <span ref={statusCursorRef} className="min-w-[170px] font-mono tabular-nums text-content-primary" data-testid="revu-status-cursor">
                  X —   Y —
                </span>
              </div>
'''.replace('TAGX', TAG)

pairs = [
# cursor readout effect after the auto focus handlers (pointerToPdf exists by then)
("""  const pendingAutoFocusRef = useRef<string | null>(null);""", CURSOR + """  const pendingAutoFocusRef = useRef<string | null>(null);"""),
# status bar replaces the lone scroll hint
("""              <div className="justify-self-end text-[11px] text-content-tertiary">
                {pageMode === 'continuous' && totalPages > 1
                  ? t('takeoff_viewer.scroll_hint', { defaultValue: 'Scroll to move between pages' })
                  : null}
              </div>""", STATUS),
# Revu tool-set captions
("""              <div className={TB_GROUP} role="group" aria-label={t('takeoff_viewer.measure_tools', { defaultValue: 'Measure tools' })} data-guide="takeoff-tools">
                {([""", """              <div className={TB_GROUP} role="group" aria-label={t('takeoff_viewer.measure_tools', { defaultValue: 'Measure tools' })} data-guide="takeoff-tools">
                {/* Revu tool-set caption (""" + TAG + """) */}
                <span className="select-none px-1 text-[9px] font-bold uppercase tracking-wider text-content-tertiary">Measure</span>
                {(["""),
("""              <div className={TB_GROUP} role="group" aria-label={t('takeoff_viewer.markup_tools', { defaultValue: 'Markup tools' })}>
                {([""", """              <div className={TB_GROUP} role="group" aria-label={t('takeoff_viewer.markup_tools', { defaultValue: 'Markup tools' })}>
                <span className="select-none px-1 text-[9px] font-bold uppercase tracking-wider text-content-tertiary">Markup</span>
                {(["""),
# auto markups name themselves by their profile on the sheet
("""      const name = (m.customFields?.Subject?.trim() || m.annotation?.trim() || '');
      const material = (m.customFields?.Material?.trim() || '');""", """      // An auto markup's sheet label is its profile; its Subject ("Beam")
      // lives in the Markups list only (OE-DELIVERY 2026-11-02-revu-markups-list).
      const name = m.auto
        ? (m.annotation?.trim() || m.auto.des)
        : (m.customFields?.Subject?.trim() || m.annotation?.trim() || '');
      const material = m.auto ? '' : (m.customFields?.Material?.trim() || '');"""),
("""  rejectedFrom,
  FT_TO_M,""", """  rejectedFrom,
  FT_TO_M,
  formatFeetInches,"""),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
v.write_text(s, encoding='utf-8')
print('ok', len(pairs))
