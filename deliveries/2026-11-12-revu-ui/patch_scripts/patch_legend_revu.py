"""Revu-style legend: one row per Subject + appearance, columns Count /
Subject / total / Unit; the earlier detailed legend stays one click away
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)


rep('''  const [legendColsOpen, setLegendColsOpen] = useState(false);''', '''  const [legendColsOpen, setLegendColsOpen] = useState(false);
  /** Legend layout: 'revu' = one row per Subject + appearance (symbol,
   *  count, subject, total) like Bluebeam Revu; 'detailed' = the earlier
   *  per-length rows with every list column (OE-DELIVERY 2026-11-12-revu-ui). */
  const [legendStyle, setLegendStyle] = useState<'revu' | 'detailed'>(() => {
    try {
      return localStorage.getItem('takeoff.legendStyle') === 'detailed' ? 'detailed' : 'revu';
    } catch {
      return 'revu';
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem('takeoff.legendStyle', legendStyle);
    } catch { /* ignore */ }
  }, [legendStyle]);''')

rep('''  const legendVisibleColumns = useMemo(
    () => legendColumnDefs.filter((c) => !legendHiddenColumns.has(c.key)),
    [legendColumnDefs, legendHiddenColumns],
  );''', '''  const legendVisibleColumns = useMemo(
    () =>
      legendStyle === 'revu'
        ? (['count', 'subject', 'length', 'area', 'unit'] as const)
            .map((k) => legendColumnDefs.find((c) => c.key === k))
            .filter((c): c is (typeof legendColumnDefs)[number] => Boolean(c))
            .map((c) => (c.key === 'count' ? { ...c, label: 'Qty' } : c.key === 'subject' ? { ...c, label: 'Description' } : c))
        : legendColumnDefs.filter((c) => !legendHiddenColumns.has(c.key)),
    [legendColumnDefs, legendHiddenColumns, legendStyle],
  );''')

rep('''  const groupLegendRows = (relevant: Measurement[]): LegendRowGroup[] => {
    const byMerge = new Map<string, Measurement[]>();''', '''  const groupLegendRows = (relevant: Measurement[]): LegendRowGroup[] => {
    if (legendStyle === 'revu') {
      // Revu: one row per Subject and look (type + colour), totals summed.
      const bySubject = new Map<string, Measurement[]>();
      for (const m of relevant) {
        const subj = (m.customFields?.Subject?.trim() || m.annotation?.trim() || '').toLowerCase();
        const key = `${m.type}||${subj}||${resolveMeasurementColor(m, groupColorMap).toLowerCase()}||${(m.unit || '').toLowerCase()}`;
        const arr = bySubject.get(key) ?? [];
        arr.push(m);
        bySubject.set(key, arr);
      }
      return [...bySubject.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([key, ms]) => ({ key, ms }));
    }
    const byMerge = new Map<string, Measurement[]>();''')

rep('''cells[col.key] = uniqJoin(ms.map((m) => (m.customFields?.Subject || '') as string));''',
    '''cells[col.key] = uniqJoin(ms.map((m) => (m.customFields?.Subject || (legendStyle === 'revu' ? m.annotation : '') || '') as string));''', 2)

rep('''    [groupColorMap, legendColumnDefs, measurementSystem, displayPageLabels, displayUnitPref],''',
    '''    [groupColorMap, legendColumnDefs, measurementSystem, displayPageLabels, displayUnitPref, legendStyle],''')
rep('''    [measurements, legendColumnDefs, groupColorMap, measurementSystem, displayPageLabels, displayUnitPref],''',
    '''    [measurements, legendColumnDefs, groupColorMap, measurementSystem, displayPageLabels, displayUnitPref, legendStyle],''')
rep('''legendTextColor, legendBgColor, legendBorderStyle,''', '''legendTextColor, legendBgColor, legendBorderStyle, legendStyle,''')

# Layout switch in the legend panel header.
rep('''                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setLegendColsOpen((v) => !v)}''', '''                    <div className="flex overflow-hidden rounded border border-border text-[10px]" role="group" aria-label="Legend layout" data-testid="legend-style">
                      {(['revu', 'detailed'] as const).map((st) => (
                        <button
                          key={st}
                          type="button"
                          onClick={() => setLegendStyle(st)}
                          className={legendStyle === st ? 'bg-oe-blue px-1.5 py-0.5 text-white' : 'px-1.5 py-0.5 text-content-secondary hover:bg-surface-secondary'}
                          title={st === 'revu' ? 'Revu style: one row per Subject (symbol, quantity, description, total)' : 'Detailed: a row per length with every list column'}
                          aria-pressed={legendStyle === st}
                          data-testid={`legend-style-${st}`}
                        >
                          {st === 'revu' ? 'Revu' : 'Detailed'}
                        </button>
                      ))}
                    </div>
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setLegendColsOpen((v) => !v)}''')

p.write_text(s, encoding="utf-8")
print("ok")
