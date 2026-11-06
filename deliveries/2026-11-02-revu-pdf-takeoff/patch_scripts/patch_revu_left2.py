"""Revu left panel v2: vertical icon tabs, sheet-number thumbnails (editable),
clean downscale, first-page-first loading, sync button, Revu defaults.
OE-DELIVERY: 2026-11-02-revu-left-panel-v2"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-left-panel-v2'


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)


# 0. clean downscale helper (module level, before SplitPane)
rep("""function SplitPane({""", """/** High-quality downscale (""" + TAG + """): halve step by step with
 *  smoothing so thin drawing lines stay crisp instead of aliasing away in
 *  one big drawImage jump - Revu-clean thumbnails. */
function downscaleCanvas(src: HTMLCanvasElement, targetW: number): HTMLCanvasElement {
  let cur: HTMLCanvasElement = src;
  while (cur.width / 2 >= targetW) {
    const half = document.createElement('canvas');
    half.width = Math.max(1, Math.round(cur.width / 2));
    half.height = Math.max(1, Math.round(cur.height / 2));
    const hc = half.getContext('2d');
    if (!hc) break;
    hc.imageSmoothingEnabled = true;
    hc.imageSmoothingQuality = 'high';
    hc.drawImage(cur, 0, 0, half.width, half.height);
    cur = half;
  }
  if (cur.width === targetW) return cur;
  const out = document.createElement('canvas');
  out.width = Math.max(1, targetW);
  out.height = Math.max(1, Math.round(targetW * (cur.height / cur.width)));
  const oc = out.getContext('2d');
  if (oc) {
    oc.fillStyle = '#ffffff';
    oc.fillRect(0, 0, out.width, out.height);
    oc.imageSmoothingEnabled = true;
    oc.imageSmoothingQuality = 'high';
    oc.drawImage(cur, 0, 0, out.width, out.height);
  }
  return out;
}

function SplitPane({""")

# 1. Revu default left panel width
rep("""const LEFT_STRIP_DEFAULT = 128;""", """const LEFT_STRIP_DEFAULT = 230; // Revu-like default panel (""" + TAG + """)""")

# 2. pdf.js thumbnails: supersample 2x, then clean downscale
rep("""      const scale = computeThumbScale(page.getViewport({ scale: 1 }).width, THUMB_MAX_WIDTH * 2);
      const vp = page.getViewport({ scale });
      const off = document.createElement('canvas');
      off.width = Math.max(1, Math.ceil(vp.width));
      off.height = Math.max(1, Math.ceil(vp.height));
      await page.render({ canvas: off, viewport: vp }).promise;
      // The document may have changed mid-render; never paint an old doc's
      // bitmap into the new doc's thumbnail map (caches reset on pdfDoc change).
      if (pdfDocRef.current !== doc) return;
      const url = off.toDataURL('image/png');""", """      // Supersample at 2x the stored size, then downscale cleanly (""" + TAG + """).
      const scale = computeThumbScale(page.getViewport({ scale: 1 }).width, THUMB_MAX_WIDTH * 4);
      const vp = page.getViewport({ scale });
      const off = document.createElement('canvas');
      off.width = Math.max(1, Math.ceil(vp.width));
      off.height = Math.max(1, Math.ceil(vp.height));
      const offCtx = off.getContext('2d');
      if (offCtx) {
        offCtx.fillStyle = '#ffffff';
        offCtx.fillRect(0, 0, off.width, off.height);
      }
      await page.render({ canvas: off, viewport: vp }).promise;
      // The document may have changed mid-render; never paint an old doc's
      // bitmap into the new doc's thumbnail map (caches reset on pdfDoc change).
      if (pdfDocRef.current !== doc) return;
      const url = downscaleCanvas(off, THUMB_MAX_WIDTH * 2).toDataURL('image/png');""")

# 3. current-page capture: clean downscale from the main canvas
rep("""      const targetW = Math.max(1, THUMB_MAX_WIDTH * 2);
      const targetH = Math.max(1, Math.round(targetW * (main.height / main.width)));
      const off = document.createElement('canvas');
      off.width = targetW;
      off.height = targetH;
      const offCtx = off.getContext('2d');
      if (!offCtx) return;
      offCtx.drawImage(main, 0, 0, targetW, targetH);
      const url = off.toDataURL('image/png');""", """      const url = downscaleCanvas(main, Math.max(1, THUMB_MAX_WIDTH * 2)).toDataURL('image/png');""")

# 4. thumbnails wait for the first page to be drawn (large files open first)
rep("""        for (;;) {
          const pending = thumbPendingRef.current;
          if (pending.size === 0) return;""", """        // Large files (""" + TAG + """): the page on screen is drawn
        // first; thumbnails only start once it is, then come one by one.
        for (let w = 0; w < 80 && mainRenderedPageRef.current !== currentPageRef.current; w++) {
          await new Promise<void>((r) => setTimeout(r, 150));
        }
        for (;;) {
          const pending = thumbPendingRef.current;
          if (pending.size === 0) return;""")

# 5. sheet reading also waits for the first page, then pages 1.. one at a time
rep("""    (async () => {
      const found: Record<number, SheetEntry> = {};
      const n = Math.min(pdfDoc.numPages, 400);
      for (let p = 1; p <= n; p++) {""", """    (async () => {
      // Never compete with the first page on screen: wait until it is drawn.
      for (let w = 0; w < 80 && mainRenderedPageRef.current === 0; w++) {
        await new Promise<void>((r) => setTimeout(r, 150));
        if (cancelled) return;
      }
      const found: Record<number, SheetEntry> = {};
      const n = Math.min(pdfDoc.numPages, 400);
      for (let p = 1; p <= n; p++) {
        // A breath between pages keeps panning / drawing smooth on big sets.
        if (p > 5) await new Promise<void>((r) => setTimeout(r, 30));""")
rep("""        if (p % 8 === 0 || p === n) {""", """        if (p <= 5 || p % 8 === 0 || p === n) {""")

# 6. left panel: vertical icon rail + content
rep("""            <div
              className="shrink-0 min-h-0 flex flex-col rounded-lg border border-border bg-surface-primary overflow-hidden"
              style={{ width: leftStripWidth }}
              data-testid="revu-left-panel"
            >""", """            <div
              className="shrink-0 min-h-0 flex flex-row rounded-lg border border-border bg-surface-primary overflow-hidden"
              style={{ width: leftStripWidth }}
              data-testid="revu-left-panel"
            >""")
rep("""              <div className="flex shrink-0 items-center gap-0.5 border-b border-border bg-surface-secondary/60 p-0.5" role="tablist">""",
    """              <div className="flex w-8 shrink-0 flex-col items-center gap-1 border-r border-border bg-surface-secondary/70 py-1" role="tablist" aria-orientation="vertical">""")
rep("""                    className={clsx(
                      'flex flex-1 items-center justify-center gap-1 rounded px-1 py-1 text-[10px] font-semibold',
                      leftTab === key ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-tertiary',
                    )}
                  >
                    <Icon size={12} />
                    {leftStripWidth >= 200 && <span className="truncate">{label}</span>}
                  </button>
                ))}
              </div>""", """                    aria-label={label}
                    className={clsx(
                      'flex h-7 w-7 items-center justify-center rounded',
                      leftTab === key ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-tertiary',
                    )}
                  >
                    <Icon size={15} />
                  </button>
                ))}
              </div>
              <div className="flex min-h-0 min-w-0 flex-1 flex-col">""")
# close the extra content wrapper: the left panel's own closing tag comes right
# before the resize handle.
rep("""            </div>
            <TakeoffResizeHandle
              testId="takeoff-resize-handle-left\"""", """              </div>
            </div>
            <TakeoffResizeHandle
              testId="takeoff-resize-handle-left\"""")

# 7. thumbnails: sheet number only (editable on the thumbnail), clean card
rep("""                  title={sheetCaption(sheetFor(n)) || t('takeoff_viewer.thumb_page', { defaultValue: 'Page {{n}}', n })}
                >""", """                  title={sheetCaption(sheetFor(n)) || `Page ${n}`}
                >""")
rep("""                    <img src={thumbs[n]} alt={t('takeoff_viewer.thumb_page', { defaultValue: 'Page {{n}}', n })} className="block w-full" style={{ imageRendering: 'auto' }} />""",
    """                    <img src={thumbs[n]} alt={sheetFor(n)?.num || `Page ${n}`} className="block w-full bg-white" style={{ imageRendering: 'auto' }} draggable={false} />""")
rep("""                  <span className="flex items-center justify-between gap-1 px-1 py-0.5 text-[10px] text-content-secondary">
                    <span className="min-w-0 truncate text-left">
                      <span className="tabular-nums">{n}</span>
                      {sheetFor(n)?.num ? <b className="ml-1 text-content-primary">{sheetFor(n)!.num}</b> : null}
                      {sheetFor(n)?.title ? <span className="ml-1">{sheetFor(n)!.title}</span> : null}
                    </span>""", """                  <span className="flex items-center justify-center gap-1 border-t border-border/60 px-1 py-0.5 text-[11px]">
                    {/* Revu-style sheet label: the sheet number only; click to
                        add or fix it (""" + TAG + """). */}
                    {editingThumb === n ? (
                      <input
                        autoFocus
                        defaultValue={sheetFor(n)?.num ?? ''}
                        placeholder="S1.00"
                        onClick={(ev) => ev.stopPropagation()}
                        onBlur={(ev) => { saveSheetEdit(n, { num: ev.target.value.trim() }); setEditingThumb(null); }}
                        onKeyDown={(ev) => {
                          ev.stopPropagation();
                          if (ev.key === 'Enter') (ev.target as HTMLInputElement).blur();
                          if (ev.key === 'Escape') setEditingThumb(null);
                        }}
                        className="w-20 rounded border border-oe-blue bg-surface-primary px-1 text-center font-semibold"
                        data-testid="thumb-sheet-input"
                      />
                    ) : (
                      <span
                        role="button"
                        tabIndex={-1}
                        title="Click to edit the sheet number"
                        onClick={(ev) => { ev.stopPropagation(); setEditingThumb(n); }}
                        className={clsx('min-w-0 truncate font-semibold hover:underline', sheetFor(n)?.num ? 'text-content-primary' : 'italic text-content-tertiary')}
                        data-testid="thumb-sheet-label"
                      >
                        {sheetFor(n)?.num || `+ sheet (${n})`}
                      </span>
                    )}""")

# 8. page index: sheet number list (title only as tooltip)
rep("""                        <input
                          defaultValue={e?.title ?? ''}
                          key={`title-${n}-${e?.title ?? ''}`}
                          placeholder="Title"
                          onBlur={(ev) => { if (ev.target.value !== (e?.title ?? '')) saveSheetEdit(n, { title: ev.target.value.trim() }); }}
                          onKeyDown={(ev) => { ev.stopPropagation(); if (ev.key === 'Enter') (ev.target as HTMLInputElement).blur(); }}
                          className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 text-content-secondary hover:border-border focus:border-oe-blue focus:bg-surface-primary"
                          data-testid="page-index-title"
                        />""", """                        <span className="min-w-0 flex-1" title={e?.title || ''} />""")
rep("""                          className="w-[64px] shrink-0 rounded border border-transparent bg-transparent px-1 font-semibold text-content-primary hover:border-border focus:border-oe-blue focus:bg-surface-primary\"""",
    """                          className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 font-semibold text-content-primary hover:border-border focus:border-oe-blue focus:bg-surface-primary\"""")
rep("""                    Sheet numbers and titles are read from each sheet's title block. Click a value to edit it.""",
    """                    Sheet numbers are read from each sheet's title block. Click one to add or fix it.""")

# 9. state for in-thumbnail editing
rep("""  /** Sheet number + title read from each page's title block. */""", """  /** Thumbnail whose sheet number is being typed (""" + TAG + """). */
  const [editingThumb, setEditingThumb] = useState<number | null>(null);
  /** Sheet number + title read from each page's title block. */""")

# 10. Sync / Compare button always in the status bar
rep("""                {splitMode !== 'off' && (
                  <button
                    type="button"
                    onClick={() => {
                      setSyncViews((x) => {
                        if (!x) syncDeltaRef.current = splitPage - currentPage;
                        return !x;
                      });
                    }}""", """                {/* Sync & compare (""" + TAG + """): one click opens the
                    next sheet beside this one and keeps both in step. */}
                <button
                  type="button"
                  onClick={() => {
                    if (splitMode === 'off') {
                      const other = currentPage < totalPages ? currentPage + 1 : Math.max(1, currentPage - 1);
                      toggleSplit('vertical');
                      setSplitPage(other);
                      syncDeltaRef.current = other - currentPage;
                      setSyncViews(true);
                    } else {
                      setSyncViews((x) => {
                        if (!x) syncDeltaRef.current = splitPage - currentPage;
                        return !x;
                      });
                    }
                  }}
                  aria-pressed={syncViews}
                  title={splitMode === 'off' ? 'Sync & compare: open the next sheet beside this one, in step' : syncViews ? 'Sync on: the second pane follows this view' : 'Sync off'}
                  className={clsx(
                    'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide border',
                    syncViews ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-tertiary',
                  )}
                  data-testid="status-sync"
                >
                  <Link2 size={11} /> SYNC
                </button>
                {false && (
                  <button
                    type="button"
                    onClick={() => {
                      setSyncViews((x) => {
                        if (!x) syncDeltaRef.current = splitPage - currentPage;
                        return !x;
                      });
                    }}""")

# drop the old split-only SYNC button kept as dead code above
i = s.index("                {false && (")
END = "                )}" + chr(10)
j = s.index(END, i) + len(END)
s = s[:i] + s[j:]
v.write_text(s, encoding='utf-8')
print('ok')
