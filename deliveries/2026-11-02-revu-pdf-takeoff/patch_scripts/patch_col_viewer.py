"""Column height, profile highlight on the sheet (all-or-nothing).
OE-DELIVERY: 2026-11-02-auto-takeoff-columns"""
import sys
from pathlib import Path

v = Path(sys.argv[1])
s = v.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-auto-takeoff-columns'

DRAW = r'''    // Auto Takeoff (TAGX): light up the profile text each auto markup
    // was read from (all of them when "Highlight profile text" is on, strong
    // for the selected ones) and ring selected columns so one is easy to find.
    {
      const sel = new Set<string>(selectedLedgerIds);
      if (selectedMeasurementId) sel.add(selectedMeasurementId);
      const k = dpr * zoom;
      ctx.save();
      ctx.setLineDash([]);
      for (const m of measurements) {
        if (!m.auto || m.page !== currentPage) continue;
        if (hiddenGroups.has(m.group) || hiddenMeasurements.has(m.id) || hiddenTypes.has(m.type)) continue;
        const isSel = sel.has(m.id);
        if (!isSel && !autoHighlightAll) continue;
        const lr = m.auto.lr;
        if (lr) {
          const pad = 1.5;
          const x = (lr[0] - pad) * k;
          const y = (lr[1] - pad) * k;
          const w = (lr[2] - lr[0] + 2 * pad) * k;
          const h = (lr[3] - lr[1] + 2 * pad) * k;
          ctx.globalAlpha = isSel ? 0.45 : 0.22;
          ctx.fillStyle = '#FACC15';
          ctx.fillRect(x, y, w, h);
          if (isSel) {
            ctx.globalAlpha = 1;
            ctx.strokeStyle = '#CA8A04';
            ctx.lineWidth = 1.5 * dpr;
            ctx.strokeRect(x, y, w, h);
          }
        }
        if (isSel && m.type === 'count') {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = '#2563EB';
          ctx.lineWidth = 2.5 * dpr;
          for (const p of m.points) {
            ctx.beginPath();
            ctx.arc(p.x * k, p.y * k, Math.max(14 * dpr, 9 * k), 0, Math.PI * 2);
            ctx.stroke();
          }
        }
      }
      ctx.restore();
    }

'''.replace('TAGX', TAG)

pairs = [
("""  auto?: AutoTag;
  /** Author display name""", """  auto?: AutoTag;
  /** Column height in metres, entered in the Auto Takeoff list (""" + TAG + """). */
  columnHeight?: number;
  /** Author display name"""),
("""  const [labelStyle, setLabelStyle] = useState<'revu' | 'badge'>(() => {""",
 """  /** Highlight the profile text of every auto markup on the sheet (""" + TAG + """). */
  const [autoHighlightAll, setAutoHighlightAll] = useState<boolean>(() => {
    try { return localStorage.getItem('takeoff.autoHighlight') !== '0'; } catch { return true; }
  });
  useEffect(() => {
    try { localStorage.setItem('takeoff.autoHighlight', autoHighlightAll ? '1' : '0'); } catch { /* ignore */ }
  }, [autoHighlightAll]);
  const [labelStyle, setLabelStyle] = useState<'revu' | 'badge'>(() => {"""),
("""    if (activeTool === 'select') {
      const selected = measurements.find(""", DRAW + """    if (activeTool === 'select') {
      const selected = measurements.find("""),
("""showTextInput, editingTextId, viewportDraft, hiddenTypes, labelStyle]);""",
 """showTextInput, editingTextId, viewportDraft, hiddenTypes, labelStyle, autoHighlightAll]);"""),
("""          edited: isAutoEdited(m),
          generated: Boolean(m.auto!.gen),
        })),""", """          edited: isAutoEdited(m),
          generated: Boolean(m.auto!.gen),
          label: m.annotation || m.auto!.des,
          heightFt: m.columnHeight ? m.columnHeight / FT_TO_M : null,
        })),"""),
("""  const selectAutoIds = useCallback((ids: string[]) => {""", """  const setAutoColumnHeight = useCallback((ids: string[], ft: number | null) => {
    const set = new Set(ids);
    setMeasurements((prev) =>
      prev.map((m) => (set.has(m.id) ? { ...m, columnHeight: ft == null ? undefined : ft * FT_TO_M } : m)),
    );
  }, []);

  const selectAutoIds = useCallback((ids: string[]) => {"""),
("""                  onDelete: deleteAutoMarkups,
                }}""", """                  onDelete: deleteAutoMarkups,
                  onSetHeight: setAutoColumnHeight,
                }}
                highlightAll={autoHighlightAll}
                onToggleHighlight={setAutoHighlightAll}"""),
("""  hasCombinedAutoCounts,
  rejectedFrom,""", """  hasCombinedAutoCounts,
  rejectedFrom,
  FT_TO_M,"""),
]
bad = [(o[:90], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
v.write_text(s, encoding='utf-8')
print('ok', len(pairs))
