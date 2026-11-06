# OE-DELIVERY 2026-11-02-revu-tool-chest + revu-markups-units (viewer)
from pathlib import Path
import re
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d want %d)\n%s' % (c, count, old[:240]))
        sys.exit(1)
    s = s.replace(old, new)


rep("import { formatInUnits } from '../../features/takeoff/lib/takeoff-display-units';\n",
    "import { formatInUnits, formatMarkupQuantity, splitQuantityText } from '../../features/takeoff/lib/takeoff-display-units';\n"
    "import { RevuToolChest } from './components/RevuToolChest';\n"
    "import {\n  addItem as chestAddItem,\n  itemFromMarkup,\n  itemSignature,\n  loadSets as loadChestSets,\n  newId as chestNewId,\n  recordRecent,\n  saveSets as saveChestSets,\n  type ChestItem,\n  type ChestSet,\n} from './data/tool-chest-sets';\n")

# ── Markups list: same figures as the sheet ──
rep("""                    lengthUnit={displayUnitPref === 'auto' ? areaLengthUnit : displayUnitPref === 'ftin' ? 'ft' : displayUnitPref}""",
    """                    lengthUnit={displayUnitPref === 'auto' ? areaLengthUnit : displayUnitPref === 'ftin' ? 'ft' : displayUnitPref}
                    formatQuantityCell={formatQuantityCell as never}""")
rep("""          if (field === 'label') {
            return { ...m, customFields: { ...m.customFields, Subject: value } };
          }""",
    """          // Revu Markups list: Subject = category, Label = the text on the sheet
          // (OE-DELIVERY 2026-11-02-revu-markups-units).
          if (field === 'subject') {
            return { ...m, customFields: { ...m.customFields, Subject: value } };
          }
          if (field === 'label') {
            const prof = normalizeProfile(value);
            if (m.auto && prof) {
              return {
                ...m,
                annotation: prof,
                group: autoGroupName(m.auto.cat, prof),
                customFields: { ...m.customFields, Material: prof },
                auto: { ...m.auto, des: prof, ud: true },
              };
            }
            return { ...m, annotation: value };
          }""")
rep("""    (id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material', value: string) => {
      // Bulk edit:""",
    """    (id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material' | 'subject', value: string) => {
      // Bulk edit:""")

# legend: Subject + Label columns, sheet units
s, n1 = re.subn(
    r"( *)case 'label':\n( *)cells\[col\.key\] = uniqJoin\(ms\.map\(\(m\) => \(m\.customFields\?\.Subject \|\| m\.annotation \|\| ''\) as string\)\);",
    lambda m: f"{m.group(1)}case 'subject':\n{m.group(2)}cells[col.key] = uniqJoin(ms.map((m) => (m.customFields?.Subject || '') as string));\n{m.group(2)}break;\n{m.group(1)}case 'label':\n{m.group(2)}cells[col.key] = uniqJoin(ms.map((m) => (m.annotation || m.customFields?.Subject || '') as string));",
    s)
s, n2 = re.subn(
    r"( *)const disp = convertQuantity\(total, first\.unit \|\| 'm', measurementSystem\);\n( *)cells\[col\.key\] = total > 0 \? formatLedgerQuantity\(disp\.value\) : '—';",
    lambda m: f"{m.group(1)}cells[col.key] = total > 0 ? legendQtyRef.current(first, total).num : '—';",
    s)
s, n3 = re.subn(
    r"( *)const dispUnit = displayUnitFor\(first\.unit \|\| 'm', measurementSystem\);\n( *)cells\[col\.key\] = dispUnit \|\| '—';",
    lambda m: f"{m.group(1)}const dispUnit = first.type === 'count' || isAnnotationType(first.type) ? displayUnitFor(first.unit || 'm', measurementSystem) : legendQtyRef.current(first, 1).unit;\n{m.group(2)}cells[col.key] = dispUnit || '—';",
    s)
if (n1, n2, n3) != (2, 2, 2):
    print('legend regex counts', n1, n2, n3)
    sys.exit(1)

rep("""  const buildLegendRows = useCallback(""",
    """  /** Sheet-caption formatting for the Markups list and the legend
   *  (OE-DELIVERY 2026-11-02-revu-markups-units). */
  const formatQuantityCell = useCallback(
    (m: Measurement, kind: 'length' | 'area' | 'volume', metricValue: number) =>
      splitQuantityText(
        formatMarkupQuantity(m, metricValue, kind, scaleForMeasurement(pageScales, m.page, m.points), measurementSystem, areaAreaUnit),
      ),
    // displayUnitPref feeds the module-level display unit the formatter reads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pageScales, measurementSystem, areaAreaUnit, displayUnitPref],
  );
  const legendQtyRef = useRef<(m: Measurement, total: number) => { num: string; unit: string }>(() => ({ num: '', unit: '' }));
  legendQtyRef.current = (m, total) =>
    formatQuantityCell(m, m.type === 'area' ? 'area' : m.type === 'volume' ? 'volume' : 'length', total);
  const buildLegendRows = useCallback(""")

# ── Tool Chest (Revu) ──
rep("""  /** Extra measurement fields from the active chest tool. Spread into every""",
    """  /* Revu Tool Chest (OE-DELIVERY 2026-11-02-revu-tool-chest): tool sets in
   * localStorage; the armed chest tool's properties ride on every new markup;
   * tools you draw with land in Recent Tools. */
  const [chestSets, setChestSets] = useState<ChestSet[]>(() => loadChestSets());
  useEffect(() => { saveChestSets(chestSets); }, [chestSets]);
  const [activeChestItemId, setActiveChestItemId] = useState<string | null>(null);
  const chestStyleRef = useRef<ToolStyle | null>(null);
  const pendingRecentRef = useRef<ChestItem[]>([]);

  /** Extra measurement fields from the active chest tool. Spread into every""")
rep("""      ...styleFieldsFor(toolStylesRef.current, sketchCtxRef.current.activeTool),
      author: useAuthStore.getState().userFullName || undefined,""",
    """      ...styleFieldsFor(toolStylesRef.current, sketchCtxRef.current.activeTool),
      // An armed Tool Chest tool's own properties win (Revu).
      ...(chestStyleRef.current ?? {}),
      author: useAuthStore.getState().userFullName || undefined,""")
rep("""    if (!subject && !material) return stamp;
    return {
      ...stamp,""",
    """    {
      // Remember the tool for Recent Tools (flushed after the markup lands).
      const tool = sketchCtxRef.current.activeTool;
      const style = { ...styleFieldsFor(toolStylesRef.current, tool), ...(chestStyleRef.current ?? {}) };
      if (!style.color && isAnnotationTool(tool)) style.color = annotationColor;
      pendingRecentRef.current.push({
        id: chestNewId('tool'),
        name: material?.trim() || subject?.trim() || (TYPE_LABELS[tool] ?? tool),
        tool,
        subject: subject?.trim() || undefined,
        label: material?.trim() || undefined,
        group: activeGroup || undefined,
        style,
      });
    }
    if (!subject && !material) return stamp;
    return {
      ...stamp,""")
rep("""    // A manual tool switch drops the chest tool's sticky label + subject.
    toolLabelRef.current = null;
    toolSubjectRef.current = null;
    toolSetRef.current = null;
  }, [activeTool, finishDrag]);""",
    """    // A manual tool switch drops the chest tool's sticky label + subject.
    toolLabelRef.current = null;
    toolSubjectRef.current = null;
    toolSetRef.current = null;
    chestStyleRef.current = null;
    setActiveChestItemId(null);
  }, [activeTool, finishDrag]);""")

CHEST_FNS = """  /** Recent Tools: fold in the tools that just drew markups. */
  useEffect(() => {
    const pending = pendingRecentRef.current;
    if (pending.length === 0) return;
    pendingRecentRef.current = [];
    setChestSets((prev) => pending.reduce((acc, it) => recordRecent(acc, it), prev));
  }, [measurements.length]);
  /** Draw with a Tool Chest tool: its type, Subject, Label, group and properties. */
  const useChestItem = useCallback(
    (item: ChestItem) => {
      selectTool(item.tool as MeasureTool);
      toolSubjectRef.current = item.subject ?? null;
      toolLabelRef.current = item.label ?? null;
      toolSetRef.current = null;
      chestStyleRef.current = item.style;
      if (item.style.color && isAnnotationTool(item.tool as MeasureTool)) setAnnotationColor(item.style.color);
      if (item.group) setActiveGroup(item.group);
      setActiveChestItemId(item.id);
    },
    [selectTool],
  );
  /** Properties mode: apply a tool's properties (and Subject) to the selection. */
  const applyChestItem = useCallback(
    (item: ChestItem) => {
      if (propsSelectedIds.size === 0) return;
      setMeasurements((prev) =>
        prev.map((m) =>
          propsSelectedIds.has(m.id) && !m.locked && !m.flattened
            ? {
                ...m,
                ...(item.style as Partial<Measurement>),
                ...(item.subject ? { customFields: { ...(m.customFields ?? {}), Subject: item.subject } } : {}),
              }
            : m,
        ),
      );
      addToast({ type: 'success', title: `Applied "${item.name}"`, message: `${propsSelectedIds.size} markup${propsSelectedIds.size === 1 ? '' : 's'} updated.` });
    },
    [propsSelectedIds, addToast],
  );
  /** Revu "Add to Tool Chest": each selected markup becomes a tool in the set. */
  const addSelectionToChest = useCallback(
    (setId: string) => {
      if (propsSelected.length === 0) return;
      setChestSets((prev) => {
        let next = prev;
        const target = prev.find((x) => x.id === setId);
        const have = new Set((target?.items ?? []).map(itemSignature));
        for (const m of propsSelected) {
          const it = itemFromMarkup(m as unknown as Parameters<typeof itemFromMarkup>[0]);
          if (have.has(itemSignature(it))) continue;
          have.add(itemSignature(it));
          next = chestAddItem(next, setId, it);
        }
        return next;
      });
      const name = chestSets.find((x) => x.id === setId)?.name ?? 'Tool Chest';
      addToast({ type: 'success', title: `Added to ${name}`, message: `${propsSelected.length} tool${propsSelected.length === 1 ? '' : 's'}` });
    },
    [propsSelected, chestSets, addToast],
  );
  const chestIconFor = useCallback((tool: string) => stripTools.find((x) => x.tool === tool)?.icon, [stripTools]);

  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts)."""
rep("""  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts).""", CHEST_FNS)

# panel JSX
start_marker = """            {sidebarTab === 'tools' && (
              <div className="space-y-2">
"""
rep(start_marker, """            {sidebarTab === 'tools' && (
              <RevuToolChest
                sets={chestSets}
                onChange={setChestSets}
                onUse={useChestItem}
                onApply={applyChestItem}
                onAddSelection={addSelectionToChest}
                selectionCount={propsSelected.length}
                activeItemId={activeChestItemId}
                iconFor={chestIconFor}
                typeLabel={(tool) => TYPE_LABELS[tool] ?? tool}
              >
""")
a = s.index("""                <button
                  type="button"
                  onClick={saveCurrentTool}""")
b = s.index("""            {/* Colours panel""", a)
s = s[:a] + """              </RevuToolChest>
            )}

""" + s[b:]

# Properties bar: Add to Tool Chest
rep("""                totals={propsBar.totals}
                defaults={propsBar.defaults}
              />""", """                totals={propsBar.totals}
                defaults={propsBar.defaults}
                onAddToChest={() => addSelectionToChest(chestSets.find((x) => !x.recent)?.id ?? 'my-tools')}
              />""")

P.write_text(s, encoding='utf-8')
print('ok')
