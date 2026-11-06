from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:90])
    s = s.replace(a, b)


# ── data/auto-takeoff.ts ───────────────────────────────────────────────
p = base / "data" / "auto-takeoff.ts"
s = p.read_text(encoding="utf-8")
rep("""  level?: string | null;
  height_ft?: number | null;
}""", """  level?: string | null;
  height_ft?: number | null;
  /** Column symbol on the sheet: [long side, short side, angle deg] in
   *  drawing units (OE-DELIVERY 2026-11-07-column-shapes). */
  symbol?: number[] | null;
}""")
rep("""  /** Column mark text and its quad on the sheet. */
  mk?: string;
  mq?: [number, number][];
}""", """  /** Column mark text and its quad on the sheet. */
  mk?: string;
  mq?: [number, number][];
  /** Column symbol [long side, short side, angle deg] (OE-DELIVERY 2026-11-07-column-shapes). */
  sy?: [number, number, number];
}""")
rep("""    ...(Array.isArray(item.mark_quad) && item.mark_quad.length === 4
      ? { mq: item.mark_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
  };
}""", """    ...(Array.isArray(item.mark_quad) && item.mark_quad.length === 4
      ? { mq: item.mark_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
    ...(Array.isArray(item.symbol) && item.symbol.length === 3
      ? { sy: [item.symbol[0]!, item.symbol[1]!, item.symbol[2]!] as [number, number, number] }
      : {}),
  };
}""")
p.write_text(s, encoding="utf-8")

# ── TakeoffViewerModule.tsx ────────────────────────────────────────────
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")

# import
rep("""  type AutoListRow,""", """  type AutoListRow,""")  # sanity (exists once)
first_import_end = s.index("\n", s.index("import "))
s = s[: first_import_end + 1] + "import { columnShape, columnProfileOf, isColumnMarkup, isManualColumn, profileKey, drawColumnSymbol } from './data/column-shape';\n" + s[first_import_end + 1 :]

# 1. Column symbols by shape, for auto and hand-placed columns.
rep("""      for (const m of measurements) {
        if (m.auto?.cat !== 'columns' || m.page !== currentPage) continue;
        if (hiddenGroups.has(m.group) || hiddenMeasurements.has(m.id) || hiddenTypes.has(m.type)) continue;
        const colour = resolveMeasurementColor(m, groupColorMap);
        const mq = m.auto.mq;""", """      for (const m of measurements) {
        // Every column - found by Auto Takeoff or placed by hand with a
        // profile - drawn as its section (OE-DELIVERY 2026-11-07-column-shapes).
        if (m.page !== currentPage || !isColumnMarkup(m)) continue;
        if (hiddenGroups.has(m.group) || hiddenMeasurements.has(m.id) || hiddenTypes.has(m.type)) continue;
        const colour = resolveMeasurementColor(m, groupColorMap);
        const manual = !m.auto;
        const profile = columnProfileOf(m);
        const shape = columnShape(profile);
        const sy = m.auto?.sy;
        const mq = m.auto?.mq;""")
rep("""        const text = m.auto.mk || '';
        for (const pt of m.points) {
          const x = pt.x * k;
          const y = pt.y * k;
          const r = Math.max(5 * dpr, 4.5 * k);
          ctx.globalAlpha = 1;
          if (!autoShowColumns) {
            // Column symbol: a ring with a cross, in the column colour.
            ctx.strokeStyle = colour;
            ctx.lineWidth = Math.max(1.5 * dpr, 0.9 * k);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.moveTo(x - r * 0.7, y - r * 0.7);
            ctx.lineTo(x + r * 0.7, y + r * 0.7);
            ctx.moveTo(x + r * 0.7, y - r * 0.7);
            ctx.lineTo(x - r * 0.7, y + r * 0.7);
            ctx.stroke();
          }""", """        const text = m.auto?.mk || (manual ? profile : '');
        for (const pt of m.points) {
          const x = pt.x * k;
          const y = pt.y * k;
          const r = Math.max(5 * dpr, 4.5 * k);
          ctx.globalAlpha = 1;
          // "Highlight all": every column taken off (found or added by hand)
          // gets a soft green disc, so what is covered shows at a glance.
          if (autoHighlightAll) {
            ctx.save();
            ctx.globalAlpha = 0.28;
            ctx.fillStyle = '#16A34A';
            ctx.beginPath();
            ctx.arc(x, y, Math.max(r * 1.9, (sy ? sy[0] * 0.8 : 0) * k), 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
          }
          if (!autoShowColumns || manual) {
            // Size and turn of the symbol drawn on the sheet when known,
            // else the section's own proportions at a readable size.
            const long = sy ? Math.max(sy[0] * k, 2 * r) : 2.2 * r;
            const shortSide = sy
              ? Math.max(sy[1] * k, long * 0.3)
              : shape.d && shape.b
                ? long * (shape.b / shape.d)
                : long;
            const ang = sy ? (sy[2] * Math.PI) / 180 : 0;
            drawColumnSymbol(ctx, x, y, shape, long, shortSide, ang, colour, Math.max(1.5 * dpr, 0.9 * k));
          }""")
rep("""          if (text) {
            const fs = Math.max(9 * dpr, 6 * k);""", """          if (text && (!manual || m.points.length <= 40)) {
            const fs = Math.max(9 * dpr, 6 * k);""")

# 2. Ctrl / Cmd + click toggles a markup in the multi-selection too.
rep("""        // Shift+press: a plain release toggles this markup in the
        // multi-select set (the long-standing Shift+click); a drag""", """        // Ctrl / Cmd + click: add or remove this markup from the selection
        // (OE-DELIVERY 2026-11-07-column-shapes) - like Shift+click, without
        // the Shift+drag copy.
        if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
          e.preventDefault();
          setHoverInfo(null);
          toggleMarqueeSelection(m.id);
          return;
        }
        // Shift+press: a plain release toggles this markup in the
        // multi-select set (the long-standing Shift+click); a drag""")

# 3. Select every markup of the same profile.
rep("""  /** Clear the canvas multi-select set. */
  const clearMarqueeSelection = useCallback(() => {""", """  /** Select every markup with the same profile as ``id`` (columns: every
   *  column of that size, found or placed by hand), on this sheet or all
   *  sheets (OE-DELIVERY 2026-11-07-column-shapes). */
  const selectSameProfile = useCallback((id: string, allPages: boolean) => {
    const all = measurementsRef.current;
    const ref = all.find((x) => x.id === id);
    if (!ref) return;
    const refCol = isColumnMarkup(ref);
    const key = profileKey(columnProfileOf(ref) || ref.group || '');
    const ids = all
      .filter((x) => (allPages || x.page === ref.page) && x.type === ref.type)
      .filter((x) => isColumnMarkup(x) === refCol && profileKey(columnProfileOf(x) || x.group || '') === key)
      .map((x) => x.id);
    setSelectedLedgerIds(new Set(ids));
    setSelectedMeasurementId(id);
  }, []);

  /** Clear the canvas multi-select set. */
  const clearMarqueeSelection = useCallback(() => {""")
rep("""                { label: 'Deselect', shortcut: 'Esc', onClick: () => { setSelectedLedgerIds(new Set()); setSelectedMeasurementId(null); } },""", """                {
                  label: 'Select same profile (this sheet)',
                  disabled: !selectedMeasurementId,
                  onClick: () => { if (selectedMeasurementId) selectSameProfile(selectedMeasurementId, false); },
                },
                {
                  label: 'Select same profile (all sheets)',
                  disabled: !selectedMeasurementId,
                  onClick: () => { if (selectedMeasurementId) selectSameProfile(selectedMeasurementId, true); },
                },
                { label: 'Deselect', shortcut: 'Esc', onClick: () => { setSelectedLedgerIds(new Set()); setSelectedMeasurementId(null); } },""")
rep("""            <button
              type="button"
              onClick={() => duplicateMeasurement(contextMenu.measurementId)}""", """            <button
              type="button"
              onClick={() => { selectSameProfile(contextMenu.measurementId, false); setContextMenu(null); }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors"
              role="menuitem"
              data-testid="context-select-same-profile"
              title="Select every markup with this profile on this sheet (Ctrl+click adds or removes one)"
            >
              <Copy size={13} className="opacity-0" />
              <span className="flex-1">Select same profile</span>
            </button>
            <button
              type="button"
              onClick={() => { selectSameProfile(contextMenu.measurementId, true); setContextMenu(null); }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-content-primary hover:bg-surface-secondary transition-colors"
              role="menuitem"
              data-testid="context-select-same-profile-all"
            >
              <Copy size={13} className="opacity-0" />
              <span className="flex-1">Select same profile, all sheets</span>
            </button>
            <button
              type="button"
              onClick={() => duplicateMeasurement(contextMenu.measurementId)}""")

# 4. Columns placed by hand show in the Detected list with the found ones.
rep("""      measurements
        .filter((m) => m.auto)
        .map((m) => ({
          id: m.id,
          cat: m.auto!.cat,
          des: m.auto!.des,
          page: m.page,
          valueText:
            m.type === 'count'
              ? String(m.points.length)
              : measurementLabel(m, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnitRef.current),
          value: m.type === 'count' ? m.points.length : m.value || 0,
          edited: isAutoEdited(m),
          generated: Boolean(m.auto!.gen),
          label: m.annotation || m.auto!.des,
          heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
        })),""", """      measurements
        .filter((m) => m.auto || isManualColumn(m))
        .map((m) => {
          if (!m.auto) {
            // A column placed by hand with its profile (OE-DELIVERY 2026-11-07-column-shapes).
            const prof = columnProfileOf(m) || 'COLUMN';
            return {
              id: m.id,
              cat: 'columns' as const,
              des: prof.toUpperCase().replace(/\\s+/g, ''),
              page: m.page,
              valueText: String(m.points.length),
              value: m.points.length,
              edited: true,
              generated: false,
              label: `${prof} · added by you`,
              heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
            };
          }
          return {
            id: m.id,
            cat: m.auto.cat,
            des: m.auto.des,
            page: m.page,
            valueText:
              m.type === 'count'
                ? String(m.points.length)
                : measurementLabel(m, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnitRef.current),
            value: m.type === 'count' ? m.points.length : m.value || 0,
            edited: isAutoEdited(m),
            generated: Boolean(m.auto.gen),
            label: m.annotation || m.auto.des,
            heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
          };
        }),""")
p.write_text(s, encoding="utf-8")
print("ok")
