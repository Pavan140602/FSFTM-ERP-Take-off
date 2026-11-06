# OE-DELIVERY 2026-11-04-framing-layout: wire "Lay out framing" into the viewer.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:140])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('components/RevuPropertiesBar.tsx', [
    ("""  /** Revu "Add to Tool Chest" for the selection. */
  onAddToChest?: () => void;""", """  /** Revu "Add to Tool Chest" for the selection. */
  onAddToChest?: () => void;
  /** Lay out framing across the selected outline (OE-DELIVERY 2026-11-04-framing-layout). */
  onLayoutFraming?: () => void;"""),
    ("""totals, defaults, onAddToChest }: Props) {""", """totals, defaults, onAddToChest, onLayoutFraming }: Props) {"""),
    ("""      {onAddToChest && mode === 'selection' && (""", """      {onLayoutFraming && mode === 'selection' && (type === 'area' || type === 'polygon') && (
        <button
          type="button"
          onClick={onLayoutFraming}
          className="flex h-6 shrink-0 items-center gap-1 rounded border border-oe-blue/50 bg-oe-blue/5 px-2 text-[10px] font-semibold text-oe-blue hover:bg-oe-blue/10"
          title="Place trusses / joists / hat channels across this outline at a spacing"
          data-testid="props-layout-framing"
        >
          Lay out framing
        </button>
      )}
      {onAddToChest && mode === 'selection' && ("""),
])

V = 'TakeoffViewerModule.tsx'
patch(V, [
    ("""import { RevuToolChest } from './components/RevuToolChest';""", """import { RevuToolChest } from './components/RevuToolChest';
import { FramingLayoutDialog, type FramingRequest } from './components/FramingLayoutDialog';
import { layoutMembers } from './data/framing-layout';"""),
    ("""                onAddToChest={() => addSelectionToChest(chestSets.find((x) => !x.recent)?.id ?? 'my-tools')}""",
     """                onAddToChest={() => addSelectionToChest(chestSets.find((x) => !x.recent)?.id ?? 'my-tools')}
                onLayoutFraming={() => setShowFraming(true)}"""),
    ("""                { label: 'Auto Takeoff…', onClick: () => showRevuPanel('auto'), testId: 'revu-tools-auto' },""",
     """                { label: 'Auto Takeoff…', onClick: () => showRevuPanel('auto'), testId: 'revu-tools-auto' },
                { label: 'Lay out framing…', onClick: () => setShowFraming(true), testId: 'revu-tools-framing' },"""),
    ("""  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts).""", """  /* Lay out framing (OE-DELIVERY 2026-11-04-framing-layout): members across a
   * selected outline at a spacing, for framing that is not drawn. */
  const [showFraming, setShowFraming] = useState(false);
  const framingArea = propsSelected.find((m) => (m.type === 'area' || m.type === 'polygon') && m.points.length >= 3) ?? null;
  const framingLine = propsSelected.find((m) => (m.type === 'distance' || m.type === 'line' || m.type === 'polyline') && m.points.length >= 2) ?? null;
  const layoutFraming = useCallback(
    (req: FramingRequest) => {
      const area = framingArea;
      if (!area) return;
      let angle = 0;
      if (req.direction === 'vertical') angle = Math.PI / 2;
      else if (req.direction === 'custom') angle = (-req.customDeg * Math.PI) / 180;
      else if (framingLine && (req.direction === 'along-line' || req.direction === 'across-line')) {
        const a = framingLine.points[0]!;
        const b = framingLine.points[framingLine.points.length - 1]!;
        angle = Math.atan2(b.y - a.y, b.x - a.x) + (req.direction === 'across-line' ? Math.PI / 2 : 0);
      }
      const sc = scaleForMeasurement(pageScales, area.page, area.points);
      const spacingPts = req.spacingM * sc.pixelsPerUnit;
      const lines = layoutMembers(area.points, angle, spacingPts, req.startAt, req.includeEnd);
      if (lines.length === 0) {
        addToast({ type: 'info', title: 'No members fit', message: 'Check the spacing and that the page scale is set.' });
        return;
      }
      if (lines.length > 600) {
        addToast({ type: 'error', title: `${lines.length} members is too many`, message: 'Check the spacing and the page scale.' });
        return;
      }
      const it = req.item;
      const subject = it?.subject || req.subject || 'Member';
      const label = it?.label || it?.name || req.label || subject;
      const style = it?.style ?? {};
      const stamp = Date.now();
      const author = useAuthStore.getState().userFullName || undefined;
      const created: Measurement[] = lines.map(([a, b], i) => {
        const pts: Point[] = [{ x: a.x, y: a.y }, { x: b.x, y: b.y }];
        const base: Measurement = {
          id: `frame_${stamp}_${i}`,
          type: 'distance',
          points: pts,
          value: 0,
          unit: 'm',
          label: '',
          annotation: label,
          page: area.page,
          group: it?.group || `${subject}: ${label}`,
          ...(style as Partial<Measurement>),
          labelMode: 'all',
          author,
          createdAt: new Date().toISOString(),
          notes: `Laid out at ${req.spacingText} O.C. across ${area.annotation || 'the outline'} - check against the drawings.`,
          customFields: { Subject: subject, Material: label },
        };
        const patch = recomputeMeasurement(base, pts, sc);
        return { ...base, value: patch.value, label: patch.label, unit: patch.unit ?? base.unit };
      });
      setMeasurements((prev) => [...prev, ...created]);
      pushUndo({ kind: 'bulk_add', measurements: created });
      setShowFraming(false);
      addToast({ type: 'success', title: `${created.length} ${subject} members laid out`, message: `${label} at ${req.spacingText} O.C.` });
    },
    [framingArea, framingLine, pageScales, addToast, pushUndo],
  );

  /** Revu default keyboard shortcuts (OE-DELIVERY 2026-11-02-revu-shortcuts)."""),
    ("""      {showShortcutSheet && (""", """      {showFraming && (
        <FramingLayoutDialog
          onClose={() => setShowFraming(false)}
          onCreate={layoutFraming}
          sets={chestSets}
          areaName={framingArea ? (framingArea.annotation || framingArea.customFields?.Subject || 'Selected area') : null}
          hasLine={Boolean(framingLine)}
        />
      )}
      {showShortcutSheet && ("""),
])
print('ok')
