"""Revu left panel (Thumbnails / Page Index / Layers), sheet index, overlay
pages, split sync, status-bar scale + units, label font (all-or-nothing).
OE-DELIVERY: 2026-11-02-revu-left-panel"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-revu-left-panel'

STATE = r'''
  /* ── Revu left panel, sheet index, overlay, sync, units, text (TAGX) ── */
  const [leftTab, setLeftTab] = useState<'thumbs' | 'index' | 'layers'>(() => {
    try {
      const v = localStorage.getItem('takeoff.leftTab');
      return v === 'index' || v === 'layers' ? v : 'thumbs';
    } catch {
      return 'thumbs';
    }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.leftTab', leftTab); } catch { /* ignore */ }
  }, [leftTab]);

  /** Sheet number + title read from each page's title block. */
  const [detectedSheets, setDetectedSheets] = useState<Record<number, SheetEntry>>({});
  /** The user's edits to the page index (win over detection). */
  const sheetKey = `takeoff.sheetIndex.${documentId ?? fileName ?? 'local'}`;
  const [sheetEdits, setSheetEdits] = useState<Record<number, SheetEntry>>({});
  useEffect(() => {
    try {
      const raw = localStorage.getItem(sheetKey);
      setSheetEdits(raw ? (JSON.parse(raw) as Record<number, SheetEntry>) : {});
    } catch {
      setSheetEdits({});
    }
  }, [sheetKey]);
  const saveSheetEdit = useCallback(
    (page: number, patch: Partial<SheetEntry>) => {
      setSheetEdits((prev) => {
        const base = prev[page] ?? detectedSheetsRef.current[page] ?? { num: '', title: '' };
        const next = { ...prev, [page]: { ...base, ...patch } };
        try { localStorage.setItem(sheetKey, JSON.stringify(next)); } catch { /* ignore */ }
        return next;
      });
    },
    [sheetKey],
  );
  const detectedSheetsRef = useRef(detectedSheets);
  detectedSheetsRef.current = detectedSheets;
  const sheetFor = useCallback(
    (page: number): SheetEntry | null => sheetEdits[page] ?? detectedSheets[page] ?? null,
    [sheetEdits, detectedSheets],
  );
  // Read every page's title block once per document, in the background.
  useEffect(() => {
    if (!pdfDoc) return;
    let cancelled = false;
    setDetectedSheets({});
    (async () => {
      const found: Record<number, SheetEntry> = {};
      const n = Math.min(pdfDoc.numPages, 400);
      for (let p = 1; p <= n; p++) {
        if (cancelled) return;
        try {
          const page = await pdfDoc.getPage(p);
          const vp = page.getViewport({ scale: 1 });
          const tc = await page.getTextContent();
          const items: TextItemLite[] = [];
          for (const raw of tc.items as Array<{ str?: string; transform?: number[]; width?: number }>) {
            if (!raw.str || !raw.transform) continue;
            const [, , c, d, e, f] = raw.transform as [number, number, number, number, number, number];
            const [x, y] = vp.convertToViewportPoint(e, f) as [number, number];
            items.push({ str: raw.str, x, y, h: Math.hypot(c, d), w: raw.width ?? 0 });
          }
          const entry = detectSheet(items, vp.width, vp.height);
          if (entry) found[p] = entry;
        } catch {
          /* unreadable page: no entry */
        }
        if (p % 8 === 0 || p === n) {
          if (cancelled) return;
          setDetectedSheets({ ...found });
          await new Promise<void>((r) => setTimeout(r, 0));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pdfDoc]);
  /** Page labels for the Markups list / legend: the PDF's own labels, else
   *  the sheet numbers read from (or typed into) the page index. */
  const displayPageLabels = useMemo<string[] | null>(() => {
    if (!totalPages) return pageLabels;
    const arr = Array.from({ length: totalPages }, (_, i) => sheetFor(i + 1)?.num || pageLabels?.[i] || '');
    return arr.some(Boolean) ? arr.map((x, i) => x || `p.${i + 1}`) : pageLabels;
  }, [totalPages, pageLabels, sheetFor]);

  /** Overlay Pages (Revu compare): another page drawn over this one in a
   *  colour, with opacity and an alignment nudge. */
  const [overlayCfg, setOverlayCfg] = useState<{ page: number; color: 'red' | 'blue' | 'green'; opacity: number; dx: number; dy: number } | null>(null);
  const [overlayPanelOpen, setOverlayPanelOpen] = useState(false);
  const [overlayImg, setOverlayImg] = useState<{ url: string; w: number; h: number } | null>(null);
  useEffect(() => {
    if (!pdfDoc || !overlayCfg) {
      setOverlayImg(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const page = await pdfDoc.getPage(overlayCfg.page);
        const vp1 = page.getViewport({ scale: 1 });
        const s = Math.min(3, 6000 / Math.max(vp1.width, vp1.height));
        const vp = page.getViewport({ scale: s });
        const off = document.createElement('canvas');
        off.width = Math.ceil(vp.width);
        off.height = Math.ceil(vp.height);
        await page.render({ canvas: off, viewport: vp }).promise;
        if (cancelled) return;
        const ctx = off.getContext('2d');
        if (!ctx) return;
        const img = ctx.getImageData(0, 0, off.width, off.height);
        const d = img.data;
        const [r, g, b] = overlayCfg.color === 'red' ? [220, 30, 30] : overlayCfg.color === 'blue' ? [30, 80, 230] : [20, 160, 60];
        for (let i = 0; i < d.length; i += 4) {
          const lum = (d[i]! * 0.3 + d[i + 1]! * 0.59 + d[i + 2]! * 0.11);
          const ink = 255 - lum;
          d[i] = r;
          d[i + 1] = g;
          d[i + 2] = b;
          d[i + 3] = ink < 24 ? 0 : Math.min(255, ink * 1.4);
        }
        ctx.putImageData(img, 0, 0);
        setOverlayImg({ url: off.toDataURL('image/png'), w: vp1.width, h: vp1.height });
      } catch {
        if (!cancelled) setOverlayImg(null);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Colour / page changes re-render; opacity and nudge are CSS only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdfDoc, overlayCfg?.page, overlayCfg?.color]);

  /** Dimension display units for every label, the legend and the lists. */
  const [displayUnitPref, setDisplayUnitPref] = useState<DisplayUnitPref>(() => {
    try {
      const v = localStorage.getItem('takeoff.displayUnit') as DisplayUnitPref | null;
      return v && ['auto', 'ftin', 'ft', 'in', 'mm', 'cm', 'm'].includes(v) ? v : 'auto';
    } catch {
      return 'auto';
    }
  });
  setGlobalDisplayUnit(displayUnitPref);
  useEffect(() => {
    try { localStorage.setItem('takeoff.displayUnit', displayUnitPref); } catch { /* ignore */ }
  }, [displayUnitPref]);
  /** Label text format: font, bold, italic (Revu caption text). */
  const [labelFont, setLabelFont] = useState<string>(() => {
    try { return localStorage.getItem('takeoff.labelFont') || 'Arial'; } catch { return 'Arial'; }
  });
  const [labelBold, setLabelBold] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.labelBold') === '1'; } catch { return false; }
  });
  const [labelItalic, setLabelItalic] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.labelItalic') === '1'; } catch { return false; }
  });
  useEffect(() => {
    try {
      localStorage.setItem('takeoff.labelFont', labelFont);
      localStorage.setItem('takeoff.labelBold', labelBold ? '1' : '0');
      localStorage.setItem('takeoff.labelItalic', labelItalic ? '1' : '0');
    } catch { /* ignore */ }
  }, [labelFont, labelBold, labelItalic]);
  const labelFontCss = `"${labelFont}", Arial, Helvetica, sans-serif`;
  const labelFontStyle = `${labelItalic ? 'italic ' : ''}${labelBold ? 'bold ' : ''}`;

  /** Revu Sync: the split pane follows the main view (page offset, zoom,
   *  scroll position) for checking two sheets / revisions together. */
  const [syncViews, setSyncViews] = useState(false);
  const syncDeltaRef = useRef(0);
  const [syncTo, setSyncTo] = useState<{ fx: number; fy: number; seq: number } | null>(null);
'''.replace('TAGX', TAG)

SYNC_EFFECTS = r'''
  /* Revu Sync effects (TAGX). */
  useEffect(() => {
    if (!syncViews || splitMode === 'off') return;
    setSplitPage(Math.min(totalPages, Math.max(1, currentPage + syncDeltaRef.current)));
  }, [syncViews, splitMode, currentPage, totalPages]);
  useEffect(() => {
    if (!syncViews || splitMode === 'off') return;
    setSplitZoom(zoom);
  }, [syncViews, splitMode, zoom]);
  useEffect(() => {
    if (!syncViews || splitMode === 'off') return;
    const c = containerRef.current;
    if (!c) return;
    let timer = 0;
    let seq = 0;
    const emit = () => {
      timer = 0;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const cr = canvas.getBoundingClientRect();
      const vr = c.getBoundingClientRect();
      if (cr.width <= 0 || cr.height <= 0) return;
      seq += 1;
      setSyncTo({ fx: (vr.left + vr.width / 2 - cr.left) / cr.width, fy: (vr.top + vr.height / 2 - cr.top) / cr.height, seq });
    };
    const onScroll = () => {
      if (!timer) timer = window.setTimeout(emit, 60);
    };
    c.addEventListener('scroll', onScroll, { passive: true });
    emit();
    return () => {
      c.removeEventListener('scroll', onScroll);
      if (timer) window.clearTimeout(timer);
    };
  }, [syncViews, splitMode, zoom, currentPage]);
'''.replace('TAGX', TAG)

LEFT_PANEL = r'''            <div
              className="shrink-0 min-h-0 flex flex-col rounded-lg border border-border bg-surface-primary overflow-hidden"
              style={{ width: leftStripWidth }}
              data-testid="revu-left-panel"
            >
              {/* Revu left panel tabs (TAGX) */}
              <div className="flex shrink-0 items-center gap-0.5 border-b border-border bg-surface-secondary/60 p-0.5" role="tablist">
                {([
                  ['thumbs', 'Thumbnails', Images],
                  ['index', 'Page Index', ListOrdered],
                  ['layers', 'Layers', Layers],
                ] as const).map(([key, label, Icon]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={leftTab === key}
                    onClick={() => setLeftTab(key)}
                    title={label}
                    data-testid={`left-tab-${key}`}
                    className={clsx(
                      'flex flex-1 items-center justify-center gap-1 rounded px-1 py-1 text-[10px] font-semibold',
                      leftTab === key ? 'bg-oe-blue text-white' : 'text-content-secondary hover:bg-surface-tertiary',
                    )}
                  >
                    <Icon size={12} />
                    {leftStripWidth >= 200 && <span className="truncate">{label}</span>}
                  </button>
                ))}
              </div>
              {leftTab === 'thumbs' && (
            <div
              className="min-h-0 flex-1 overflow-y-auto p-2 space-y-2"
              data-testid="thumbnail-strip"
            >
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => goToPage(n)}
                  data-testid="thumbnail-item"
                  data-page={n}
                  data-current={n === currentPage}
                  aria-current={n === currentPage ? 'page' : undefined}
                  className={clsx(
                    'group block w-full overflow-hidden rounded border bg-white transition-colors',
                    n === currentPage
                      ? 'ring-2 ring-oe-blue border-oe-blue'
                      : 'border-border hover:border-oe-blue/60',
                  )}
                  title={sheetCaption(sheetFor(n)) || t('takeoff_viewer.thumb_page', { defaultValue: 'Page {{n}}', n })}
                >
                  {thumbs[n] ? (
                    <img src={thumbs[n]} alt={t('takeoff_viewer.thumb_page', { defaultValue: 'Page {{n}}', n })} className="block w-full" style={{ imageRendering: 'auto' }} />
                  ) : (
                    <div className="flex aspect-[1/1.4] items-center justify-center text-content-tertiary">
                      <Loader2 size={16} className="animate-spin" />
                    </div>
                  )}
                  <span className="flex items-center justify-between gap-1 px-1 py-0.5 text-[10px] text-content-secondary">
                    <span className="min-w-0 truncate text-left">
                      <span className="tabular-nums">{n}</span>
                      {sheetFor(n)?.num ? <b className="ml-1 text-content-primary">{sheetFor(n)!.num}</b> : null}
                      {sheetFor(n)?.title ? <span className="ml-1">{sheetFor(n)!.title}</span> : null}
                    </span>
                    {countsByPage[n] ? (
                      <span className="tabular-nums rounded-full bg-purple-500/15 px-1 text-purple-500" data-testid="thumbnail-badge">
                        {countsByPage[n]}
                      </span>
                    ) : null}
                  </span>
                </button>
              ))}
            </div>
              )}
              {leftTab === 'index' && (
                <div className="min-h-0 flex-1 overflow-y-auto p-1.5 text-[11px]" data-testid="page-index">
                  <p className="px-1 pb-1 text-[10px] text-content-tertiary">
                    Sheet numbers and titles are read from each sheet's title block. Click a value to edit it.
                  </p>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => {
                    const e = sheetFor(n);
                    const edited = Boolean(sheetEdits[n]);
                    return (
                      <div
                        key={n}
                        className={clsx(
                          'flex items-center gap-1 rounded px-1 py-0.5',
                          n === currentPage ? 'bg-oe-blue/10' : 'hover:bg-surface-secondary',
                        )}
                        data-testid="page-index-row"
                      >
                        <button type="button" onClick={() => goToPage(n)} className="w-6 shrink-0 text-right tabular-nums text-content-tertiary hover:text-oe-blue" title={`Go to page ${n}`}>
                          {n}
                        </button>
                        <input
                          defaultValue={e?.num ?? ''}
                          key={`num-${n}-${e?.num ?? ''}`}
                          placeholder="Sheet"
                          onBlur={(ev) => { if (ev.target.value !== (e?.num ?? '')) saveSheetEdit(n, { num: ev.target.value.trim() }); }}
                          onKeyDown={(ev) => { ev.stopPropagation(); if (ev.key === 'Enter') (ev.target as HTMLInputElement).blur(); }}
                          className="w-[64px] shrink-0 rounded border border-transparent bg-transparent px-1 font-semibold text-content-primary hover:border-border focus:border-oe-blue focus:bg-surface-primary"
                          data-testid="page-index-num"
                        />
                        <input
                          defaultValue={e?.title ?? ''}
                          key={`title-${n}-${e?.title ?? ''}`}
                          placeholder="Title"
                          onBlur={(ev) => { if (ev.target.value !== (e?.title ?? '')) saveSheetEdit(n, { title: ev.target.value.trim() }); }}
                          onKeyDown={(ev) => { ev.stopPropagation(); if (ev.key === 'Enter') (ev.target as HTMLInputElement).blur(); }}
                          className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 text-content-secondary hover:border-border focus:border-oe-blue focus:bg-surface-primary"
                          data-testid="page-index-title"
                        />
                        {edited && <span className="shrink-0 text-[9px] text-amber-600" title="Edited by you">✎</span>}
                      </div>
                    );
                  })}
                  {Object.keys(sheetEdits).length > 0 && (
                    <button
                      type="button"
                      className="mt-1 w-full rounded border border-border px-2 py-1 text-[10px] hover:bg-surface-secondary"
                      onClick={() => {
                        setSheetEdits({});
                        try { localStorage.removeItem(sheetKey); } catch { /* ignore */ }
                      }}
                    >
                      Reset to the sheet title blocks
                    </button>
                  )}
                </div>
              )}
              {leftTab === 'layers' && (() => {
                const groups = new Map<string, number>();
                for (const m of measurements) groups.set(m.group || 'General', (groups.get(m.group || 'General') ?? 0) + 1);
                const names = [...groups.keys()].sort((a, b) => a.localeCompare(b));
                return (
                  <div className="min-h-0 flex-1 overflow-y-auto p-1.5 text-[11px]" data-testid="layers-panel">
                    <div className="flex items-center gap-1 px-1 pb-1">
                      <span className="flex-1 text-[10px] text-content-tertiary">Show or hide each group of markups.</span>
                      <button type="button" className="rounded px-1 text-[10px] text-oe-blue hover:underline" onClick={() => setHiddenGroups(new Set())}>All on</button>
                      <button type="button" className="rounded px-1 text-[10px] text-oe-blue hover:underline" onClick={() => setHiddenGroups(new Set(names))}>All off</button>
                    </div>
                    {names.map((g) => {
                      const hidden = hiddenGroups.has(g);
                      return (
                        <button
                          key={g}
                          type="button"
                          onClick={() => setHiddenGroups((prev) => { const next = new Set(prev); if (next.has(g)) next.delete(g); else next.add(g); return next; })}
                          className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left hover:bg-surface-secondary"
                          data-testid="layer-row"
                        >
                          {hidden ? <EyeOff size={12} className="text-content-tertiary" /> : <Eye size={12} className="text-oe-blue" />}
                          <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: groupColorMap[g] ?? '#3B82F6' }} />
                          <span className={clsx('min-w-0 flex-1 truncate', hidden && 'text-content-tertiary line-through')}>{g}</span>
                          <span className="tabular-nums text-content-tertiary">{groups.get(g)}</span>
                        </button>
                      );
                    })}
                    {names.length === 0 && <p className="px-1 text-content-tertiary">No markups yet.</p>}
                  </div>
                );
              })()}
            </div>
'''.replace('TAGX', TAG)

OVERLAY_IMG = r'''                  {/* Overlay Pages (TAGX): the compared page in colour. */}
                  {overlayCfg && overlayImg && pageSizePdfRef.current && (
                    <img
                      src={overlayImg.url}
                      alt=""
                      aria-hidden="true"
                      className="pointer-events-none absolute left-0 top-0"
                      style={{
                        width: overlayImg.w * zoom,
                        height: overlayImg.h * zoom,
                        opacity: overlayCfg.opacity,
                        transform: `translate(${overlayCfg.dx * zoom}px, ${overlayCfg.dy * zoom}px)`,
                        mixBlendMode: 'multiply',
                      }}
                      data-testid="overlay-page-img"
                    />
                  )}
'''.replace('TAGX', TAG)

OVERLAY_PANEL = r'''      {/* Overlay Pages panel (TAGX) */}
      {pdfDoc && overlayPanelOpen && (
        <div className="fixed right-6 top-16 z-[70] w-72 rounded-lg border border-border bg-surface-primary p-3 text-[11px] shadow-2xl" data-testid="overlay-panel">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[12px] font-semibold">Overlay Pages</span>
            <button type="button" className="text-content-tertiary hover:text-content-primary" onClick={() => setOverlayPanelOpen(false)}>✕</button>
          </div>
          <p className="mb-2 text-content-tertiary">Lay another sheet over this one in colour to compare revisions. This page stays black; the overlay shows in colour.</p>
          <label className="mb-1.5 flex items-center gap-2">
            <span className="w-16 text-content-secondary">Overlay</span>
            <select
              className="min-w-0 flex-1 rounded border border-border bg-surface-primary px-1 py-0.5"
              value={overlayCfg?.page ?? ''}
              onChange={(e) => {
                const p = Number(e.target.value);
                setOverlayCfg(p ? { page: p, color: overlayCfg?.color ?? 'red', opacity: overlayCfg?.opacity ?? 0.7, dx: 0, dy: 0 } : null);
              }}
              data-testid="overlay-page-select"
            >
              <option value="">None</option>
              {Array.from({ length: totalPages }, (_, i) => i + 1).filter((p) => p !== currentPage).map((p) => (
                <option key={p} value={p}>{`${p}  ${sheetCaption(sheetFor(p))}`.trim()}</option>
              ))}
            </select>
          </label>
          {overlayCfg && (
            <>
              <div className="mb-1.5 flex items-center gap-2">
                <span className="w-16 text-content-secondary">Colour</span>
                {(['red', 'blue', 'green'] as const).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setOverlayCfg({ ...overlayCfg, color: c })}
                    className={clsx('h-5 w-5 rounded-full border-2', overlayCfg.color === c ? 'border-content-primary' : 'border-transparent')}
                    style={{ backgroundColor: c === 'red' ? '#dc1e1e' : c === 'blue' ? '#1e50e6' : '#14a03c' }}
                    title={c}
                  />
                ))}
              </div>
              <label className="mb-1.5 flex items-center gap-2">
                <span className="w-16 text-content-secondary">Opacity</span>
                <input type="range" min={0.1} max={1} step={0.05} value={overlayCfg.opacity} onChange={(e) => setOverlayCfg({ ...overlayCfg, opacity: Number(e.target.value) })} className="flex-1" />
              </label>
              <div className="mb-1.5 flex items-center gap-1">
                <span className="w-16 text-content-secondary">Align</span>
                {([['←', -1, 0], ['→', 1, 0], ['↑', 0, -1], ['↓', 0, 1]] as const).map(([lbl, x, y]) => (
                  <button
                    key={lbl}
                    type="button"
                    className="rounded border border-border px-1.5 hover:bg-surface-secondary"
                    title="Nudge 1 pt (Shift-click: 10 pt)"
                    onClick={(e) => { const k = e.shiftKey ? 10 : 1; setOverlayCfg({ ...overlayCfg, dx: overlayCfg.dx + x * k, dy: overlayCfg.dy + y * k }); }}
                  >
                    {lbl}
                  </button>
                ))}
                <span className="ml-1 tabular-nums text-content-tertiary">{overlayCfg.dx}, {overlayCfg.dy}</span>
              </div>
              <button type="button" className="w-full rounded border border-border px-2 py-1 hover:bg-surface-secondary" onClick={() => setOverlayCfg(null)}>
                Remove overlay
              </button>
            </>
          )}
        </div>
      )}
'''.replace('TAGX', TAG)

STATUS_EXTRA = r'''                {/* Scale picker in the status bar (TAGX), like Revu. */}
                <select
                  value={(() => {
                    const p = DRAWING_SCALE_PRESETS.find((sp) => !scale.invalid && sameScale(scale, sp.scale));
                    return p ? p.label : '__current';
                  })()}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === '__calibrate') { handleStartCalibration(); return; }
                    if (v === '__current') return;
                    const p = DRAWING_SCALE_PRESETS.find((sp) => sp.label === v);
                    if (p) setScale(p.scale);
                  }}
                  title="Scale of this page"
                  className={clsx(
                    'h-6 max-w-[150px] rounded border bg-surface-primary px-1 text-[11px]',
                    isCalibrated ? 'border-border text-content-primary' : 'border-amber-400 text-amber-700',
                  )}
                  data-testid="status-scale"
                >
                  <option value="__current">{isCalibrated ? (DRAWING_SCALE_PRESETS.find((sp) => sameScale(scale, sp.scale))?.label ?? 'Custom scale') : 'Not calibrated'}</option>
                  <optgroup label="Architectural">
                    {DRAWING_SCALE_PRESETS.filter((p) => p.group === 'architectural').map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
                  </optgroup>
                  <optgroup label="Civil">
                    {DRAWING_SCALE_PRESETS.filter((p) => p.group === 'civil').map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
                  </optgroup>
                  <optgroup label="Metric">
                    {DRAWING_SCALE_PRESETS.filter((p) => p.group === 'metric').map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
                  </optgroup>
                  <option value="__calibrate">Calibrate (two clicks)…</option>
                </select>
                {/* Dimension units for every label (TAGX). */}
                <select
                  value={displayUnitPref}
                  onChange={(e) => setDisplayUnitPref(e.target.value as DisplayUnitPref)}
                  title="Units the dimensions are shown in"
                  className="h-6 rounded border border-border bg-surface-primary px-1 text-[11px]"
                  data-testid="status-units"
                >
                  <option value="auto">Units: as calibrated</option>
                  <option value="ftin">ft-in (12'-6")</option>
                  <option value="ft">feet (12.5 ft)</option>
                  <option value="in">inches</option>
                  <option value="mm">millimetres</option>
                  <option value="cm">centimetres</option>
                  <option value="m">metres</option>
                </select>
                {splitMode !== 'off' && (
                  <button
                    type="button"
                    onClick={() => {
                      setSyncViews((x) => {
                        if (!x) syncDeltaRef.current = splitPage - currentPage;
                        return !x;
                      });
                    }}
                    aria-pressed={syncViews}
                    title="Sync: the second pane follows this view's page, zoom and position"
                    className={clsx(
                      'rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide border',
                      syncViews ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-tertiary',
                    )}
                    data-testid="status-sync"
                  >
                    SYNC
                  </button>
                )}
                {overlayCfg && (
                  <button
                    type="button"
                    onClick={() => setOverlayPanelOpen(true)}
                    className="rounded border border-red-400 bg-red-50 px-1.5 py-0.5 text-[10px] font-bold text-red-700 dark:bg-red-950/30"
                    title="Overlay Pages"
                  >
                    OVERLAY p.{overlayCfg.page}
                  </button>
                )}
'''.replace('TAGX', TAG)

FONT_UI = r'''                {/* Label text format + units (TAGX) */}
                <div className="space-y-1">
                  <p className="text-[11px] font-semibold text-content-secondary">Label text</p>
                  <div className="flex items-center gap-1">
                    <select
                      value={labelFont}
                      onChange={(e) => setLabelFont(e.target.value)}
                      className="min-w-0 flex-1 rounded border border-border bg-surface-primary px-1 py-0.5 text-[11px]"
                      style={{ fontFamily: labelFontCss }}
                      data-testid="label-font"
                    >
                      {['Arial', 'Helvetica', 'Calibri', 'Segoe UI', 'Verdana', 'Tahoma', 'Times New Roman', 'Georgia', 'Courier New', 'Consolas'].map((f) => (
                        <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>
                      ))}
                    </select>
                    <button type="button" onClick={() => setLabelBold((x) => !x)} aria-pressed={labelBold} className={clsx('h-6 w-6 rounded border text-[11px] font-bold', labelBold ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border')}>B</button>
                    <button type="button" onClick={() => setLabelItalic((x) => !x)} aria-pressed={labelItalic} className={clsx('h-6 w-6 rounded border text-[11px] italic', labelItalic ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border')}>I</button>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-[11px] text-content-secondary">Dimensions in</span>
                    <select
                      value={displayUnitPref}
                      onChange={(e) => setDisplayUnitPref(e.target.value as DisplayUnitPref)}
                      className="min-w-0 flex-1 rounded border border-border bg-surface-primary px-1 py-0.5 text-[11px]"
                      data-testid="label-units"
                    >
                      <option value="auto">As calibrated</option>
                      <option value="ftin">ft-in</option>
                      <option value="ft">feet</option>
                      <option value="in">inches</option>
                      <option value="mm">mm</option>
                      <option value="cm">cm</option>
                      <option value="m">m</option>
                    </select>
                  </div>
                </div>
'''.replace('TAGX', TAG)

pairs = [
# imports
("""import {
  convertQuantity,
  formatQuantity,
  displayUnitFor,
  measurementLabel,
} from '../../features/takeoff/lib/takeoff-display-units';""", """import {
  convertQuantity,
  formatQuantity,
  displayUnitFor,
  measurementLabel,
  type DisplayUnitPref,
  setGlobalDisplayUnit,
} from '../../features/takeoff/lib/takeoff-display-units';
// Revu left panel / sheet index (""" + TAG + """).
import { type SheetEntry, type TextItemLite, detectSheet, sheetCaption } from './data/sheet-index';"""),
("""  Eye,
  EyeOff,""", """  Eye,
  EyeOff,
  Images,
  ListOrdered,"""),
# state after revuWorkspace state block (pdfDoc, documentId exist by then? place after hiddenGroups decl is safer)
("""  const [hiddenGroups, setHiddenGroups] = useState<Set<string>>(new Set());""",
 """  const [hiddenGroups, setHiddenGroups] = useState<Set<string>>(new Set());"""),
# sync effects next to the split state
("""  const [splitZoom, setSplitZoom] = useState(1);""", """  const [splitZoom, setSplitZoom] = useState(1);"""),
# left panel replaces the thumbnail strip box
("""            <div
              className="shrink-0 min-h-0 overflow-y-auto rounded-lg border border-border bg-surface-primary p-2 space-y-2"
              style={{ width: leftStripWidth }}
              data-testid="thumbnail-strip"
            >
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => goToPage(n)}
                  data-testid="thumbnail-item\"""", None),
]
# (the left-panel replacement is done below by slicing, not by the pair list)
pairs = [p for p in pairs if p[1] is not None and p[0] != p[1]]

bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)

# Left panel: slice out the old strip box.
start_marker = """            <div
              className="shrink-0 min-h-0 overflow-y-auto rounded-lg border border-border bg-surface-primary p-2 space-y-2"
              style={{ width: leftStripWidth }}
              data-testid="thumbnail-strip"
            >"""
end_marker = """            <TakeoffResizeHandle
              testId="takeoff-resize-handle-left\""""
assert s.count(start_marker) == 1 and s.count(end_marker) == 1
a = s.index(start_marker)
b = s.index(end_marker)
s = s[:a] + LEFT_PANEL + s[b:]
# show the left panel for single-page documents too
o = """          {totalPages > 1 && (
            showThumbnails ? ("""
assert s.count(o) == 1
s = s.replace(o, """          {totalPages >= 1 && (
            showThumbnails ? (""")
# thumbnails observer must re-attach when the Thumbnails tab comes back
o = """  }, [pdfDoc, showThumbnails, totalPages]);"""
assert s.count(o) == 1
s = s.replace(o, """  }, [pdfDoc, showThumbnails, totalPages, leftTab]);""")

# State block: insert right after the revuWorkspace pin effect (pdfDoc, documentId,
# fileName, pageLabels, totalPages, setHiddenGroups are declared before it?).
anchor_state = """  /* ── Bottom ledger bar: vertical resize, mirroring the side panels ─── */"""
assert s.count(anchor_state) == 1
s = s.replace(anchor_state, STATE + "\n" + anchor_state)

# Sync effects: after the split state + zoom exist -> put before the main return,
# next to the cursor readout effect (late in the component).
anchor_sync = """  const pendingAutoFocusRef = useRef<string | null>(null);"""
assert s.count(anchor_sync) == 1
s = s.replace(anchor_sync, SYNC_EFFECTS + anchor_sync)

# SplitPane sync prop
o = """                  onPageChange={(p) => setSplitPage(p)}
                  onZoomChange={(z) => setSplitZoom(z)}
                  onClose={() => setSplitMode('off')}
                />"""
assert s.count(o) == 1
s = s.replace(o, """                  onPageChange={(p) => { setSplitPage(p); if (syncViews) syncDeltaRef.current = p - currentPage; }}
                  onZoomChange={(z) => setSplitZoom(z)}
                  onClose={() => { setSplitMode('off'); setSyncViews(false); }}
                  syncTo={syncViews ? syncTo : null}
                />""")
o = """  onPageChange,
  onZoomChange,
  onClose,
}: {
  pdfDoc: PDFDocumentProxy;
  page: number;
  zoom: number;
  totalPages: number;
  measurements: Measurement[];
  groupColorMap: Record<string, string>;
  onPageChange: (p: number) => void;
  onZoomChange: (z: number) => void;
  onClose: () => void;
}) {"""
assert s.count(o) == 1
s = s.replace(o, """  onPageChange,
  onZoomChange,
  onClose,
  syncTo,
}: {
  pdfDoc: PDFDocumentProxy;
  page: number;
  zoom: number;
  totalPages: number;
  measurements: Measurement[];
  groupColorMap: Record<string, string>;
  onPageChange: (p: number) => void;
  onZoomChange: (z: number) => void;
  onClose: () => void;
  /** Revu Sync (""" + TAG + """): centre on this fraction of the sheet. */
  syncTo?: { fx: number; fy: number; seq: number } | null;
}) {""")
o = """  const anchorRef = useRef<{ fracX: number; fracY: number; clientX: number; clientY: number } | null>(null);
  const dragRef = useRef<{ x: number; y: number } | null>(null);"""
assert s.count(o) == 1
s = s.replace(o, o + """
  // Revu Sync: follow the main view's position (""" + TAG + """).
  useEffect(() => {
    if (!syncTo) return;
    const id = window.setTimeout(() => {
      const sc = scrollRef.current;
      const sheet = sheetRef.current;
      if (!sc || !sheet) return;
      const sr = sheet.getBoundingClientRect();
      const vr = sc.getBoundingClientRect();
      sc.scrollLeft += sr.left + syncTo.fx * sr.width - (vr.left + vr.width / 2);
      sc.scrollTop += sr.top + syncTo.fy * sr.height - (vr.top + vr.height / 2);
    }, 140);
    return () => window.clearTimeout(id);
  }, [syncTo, zoom]);""")

# Overlay image above the PDF bitmap
o = """                  {/* Deep-zoom sharp tile of the visible region (OE-DELIVERY 2026-11-02-revu-zoom). */}
                  <canvas
                    ref={detailCanvasRef}
                    className="pointer-events-none absolute"
                    style={{ display: 'none' }}
                    aria-hidden="true"
                  />
                  </>"""
assert s.count(o) == 1
s = s.replace(o, o[:-len('                  </>')] + OVERLAY_IMG + """                  </>""")

# Overlay panel near the menu bar
o = """      {isTakeoffFullscreen && <FullscreenToastStack />}
"""
assert s.count(o) == 1
s = s.replace(o, o + OVERLAY_PANEL)

# Status bar: scale, units, sync, overlay
o = """                <span className="tabular-nums" title="Zoom">{Math.round(zoom * 100)}%</span>"""
assert s.count(o) == 1
s = s.replace(o, STATUS_EXTRA + o)

# Ledger page labels + length unit follow the new settings
o = """                    pageLabels={pageLabels}"""
assert s.count(o) == 1
s = s.replace(o, """                    pageLabels={displayPageLabels}""")
o = """                    lengthUnit={areaLengthUnit}"""
assert s.count(o) == 1
s = s.replace(o, """                    lengthUnit={displayUnitPref === 'auto' ? areaLengthUnit : displayUnitPref === 'ftin' ? 'ft' : displayUnitPref}""")

# Label fonts
o = """        ctx.font = `${fsRevu}px Arial, Helvetica, sans-serif`;"""
assert s.count(o) == 1
s = s.replace(o, """        ctx.font = `${labelFontStyle}${fsRevu}px ${labelFontCss}`;""")
o = """      const fontFamily = revu ? 'Arial, Helvetica, sans-serif' : 'sans-serif';
      const weight = revu ? '' : 'bold ';"""
assert s.count(o) == 1
s = s.replace(o, """      const fontFamily = revu ? labelFontCss : 'sans-serif';
      const weight = revu ? labelFontStyle : 'bold ';""")
o = """        ctx.font = labelStyle === 'revu' ? `${12 * dpr * zoom}px Arial, Helvetica, sans-serif` : `${12 * dpr}px sans-serif`;"""
assert s.count(o) == 1
s = s.replace(o, """        ctx.font = labelStyle === 'revu' ? `${labelFontStyle}${12 * dpr * zoom}px ${labelFontCss}` : `${12 * dpr}px sans-serif`;""")
# draw deps
o = """hiddenTypes, labelStyle, autoHighlightAll, autoShowColumns]);"""
assert s.count(o) == 1
s = s.replace(o, """hiddenTypes, labelStyle, autoHighlightAll, autoShowColumns, labelFontCss, labelFontStyle, displayUnitPref]);""")

# Colours tab: font + units under the Label style block
o = """                <div className="space-y-2">
                  <p className="text-[11px] font-semibold text-content-secondary">
                    {t('takeoff_viewer.label_show_lines', { defaultValue: 'Show in label' })}
                  </p>"""
assert s.count(o) == 1
s = s.replace(o, FONT_UI + o)

# Menus: Document > Overlay Pages, View > Units submenu
o = """                { label: 'Viewports…', checked: showViewportPanel, onClick: () => setShowViewportPanel((x) => !x) },"""
assert s.count(o) == 1
s = s.replace(o, o + """
                { separator: true },
                { label: 'Overlay Pages…', checked: Boolean(overlayCfg), onClick: () => setOverlayPanelOpen(true), testId: 'revu-doc-overlay' },
                { label: 'Page Index', onClick: () => { setShowThumbnails(true); setLeftTab('index'); } },""")
o = """                { label: 'Show Labels', checked: showLabels, onClick: () => setShowLabels((x) => !x) },"""
assert s.count(o) == 1
s = s.replace(o, """                {
                  label: 'Dimension Units',
                  submenu: ([
                    ['As calibrated', 'auto'], ['ft-in', 'ftin'], ['Feet', 'ft'], ['Inches', 'in'], ['Millimetres', 'mm'], ['Centimetres', 'cm'], ['Metres', 'm'],
                  ] as [string, DisplayUnitPref][]).map(([label, u]) => ({ label, checked: displayUnitPref === u, onClick: () => setDisplayUnitPref(u) })),
                },
                { label: 'Sync Split Views', checked: syncViews, disabled: splitMode === 'off', onClick: () => setSyncViews((x) => { if (!x) syncDeltaRef.current = splitPage - currentPage; return !x; }) },
""" + o)
o = """                { label: 'Thumbnails', checked: showThumbnails, onClick: () => setShowThumbnails((x) => !x) },"""
assert s.count(o) == 1
s = s.replace(o, """                { label: 'Thumbnails', checked: showThumbnails && leftTab === 'thumbs', onClick: () => { setShowThumbnails(true); setLeftTab('thumbs'); } },
                { label: 'Page Index', checked: showThumbnails && leftTab === 'index', onClick: () => { setShowThumbnails(true); setLeftTab('index'); } },
                { label: 'Layers', checked: showThumbnails && leftTab === 'layers', onClick: () => { setShowThumbnails(true); setLeftTab('layers'); } },
                { label: 'Left Panel', checked: showThumbnails, onClick: () => setShowThumbnails((x) => !x) },""")

v.write_text(s, encoding='utf-8')
print('ok')
