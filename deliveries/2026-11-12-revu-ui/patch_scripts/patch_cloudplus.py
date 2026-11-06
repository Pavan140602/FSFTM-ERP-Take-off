"""Cloud+ (Revu): a cloud with a comment - cloud, then a callout box with a
leader to it, grouped (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src")
p = base / "modules/pdf-takeoff/TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# Types.
rep("""  // Revu Polyline markup: a line through any number of points, no measure.
  | 'polylineMarkup';""", """  // Revu Polyline markup: a line through any number of points, no measure.
  | 'polylineMarkup'
  // Revu Cloud+: a cloud with a comment (callout) beside it.
  | 'cloudPlus';""")
rep("""  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp' | 'polylineMarkup';""",
    """  | 'line' | 'polygon' | 'ellipse' | 'pen' | 'callout' | 'stamp' | 'polylineMarkup' | 'cloudPlus';""")
rep("""  'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp', 'polylineMarkup',
];""", """  'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp', 'polylineMarkup', 'cloudPlus',
];""")
rep("""  polylineMarkup: '#EF4444',""", """  polylineMarkup: '#EF4444',
  cloudPlus: '#EF4444',""")
rep("""  polylineMarkup: 'Polyline',
  area: 'Area',""", """  polylineMarkup: 'Polyline',
  cloudPlus: 'Cloud+',
  area: 'Area',""")

# Prompt can group the callout with its cloud.
rep("""    { kind: 'callout' | 'stamp'; points: Point[]; value: string } | null""",
    """    { kind: 'callout' | 'stamp'; points: Point[]; value: string; groupWith?: string } | null""")
rep("""    pushUndo({ kind: 'complete_measurement', measurement: newMeasurement, previousActivePoints: [] });
    setMeasurements((prev) => [...prev, newMeasurement]);
  }, [markupTextPrompt, placeStamp, annotationColor, currentPage, activeGroup, pushUndo]);""",
    """    // Cloud+: the comment box and its cloud move together (one group).
    const gid = prompt.groupWith ? `cloudplus_${Date.now()}` : undefined;
    if (gid) newMeasurement.markupGroupId = gid;
    pushUndo({ kind: 'complete_measurement', measurement: newMeasurement, previousActivePoints: [] });
    setMeasurements((prev) => [
      ...prev.map((x) => (gid && x.id === prompt.groupWith ? { ...x, markupGroupId: gid, text } : x)),
      newMeasurement,
    ]);
  }, [markupTextPrompt, placeStamp, annotationColor, currentPage, activeGroup, pushUndo]);""")

# Helper: after a Cloud+ cloud, ask for the comment.
rep("""  const confirmMarkupText = useCallback(() => {""", """  /** Cloud+ - once its cloud is drawn, ask for the comment; the callout's
   *  tip sits on the cloud's top-right corner. */
  const askCloudComment = (cloudId: string, pts: Point[]) => {
    const maxX = Math.max(...pts.map((q) => q.x));
    const minY = Math.min(...pts.map((q) => q.y));
    const tip = { x: maxX, y: minY };
    setMarkupTextPrompt({ kind: 'callout', points: [tip, { x: tip.x + 36, y: tip.y - 36 }], value: '', groupWith: cloudId });
  };
  const confirmMarkupText = useCallback(() => {""")

# Clicks / drags / finish: Cloud+ behaves as Cloud.
rep("""      if (activeTool === 'cloud') {
        pushUndo({ kind: 'add_point', tool: 'cloud', point });""", """      if (activeTool === 'cloud' || activeTool === 'cloudPlus') {
        pushUndo({ kind: 'add_point', tool: 'cloud', point });""")
rep("""        (activeTool === 'cloud' || activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse')
      ) {
        const bp = pointerToPdf(e);""", """        (activeTool === 'cloud' || activeTool === 'cloudPlus' || activeTool === 'rectangle' || activeTool === 'highlight' || activeTool === 'ellipse')
      ) {
        const bp = pointerToPdf(e);""")
rep("""          if (activeTool === 'cloud' && activePoints.length === 0) {""", """          if ((activeTool === 'cloud' || activeTool === 'cloudPlus') && activePoints.length === 0) {""")
rep("""            pushUndo({ kind: 'complete_measurement', measurement: cloudM, previousActivePoints: [] });
            setMeasurements((prev) => [...prev, cloudM]);
            setActivePoints([]);
            return;""", """            pushUndo({ kind: 'complete_measurement', measurement: cloudM, previousActivePoints: [] });
            setMeasurements((prev) => [...prev, cloudM]);
            setActivePoints([]);
            if (activeTool === 'cloudPlus') askCloudComment(cloudM.id, corners);
            return;""")
rep("""    if (activeTool === 'cloud' && pts.length >= 3) {""", """    if ((activeTool === 'cloud' || activeTool === 'cloudPlus') && pts.length >= 3) {""")
# the dbl-click cloud measurement creation: add comment ask after it lands
i = s.index("    if ((activeTool === 'cloud' || activeTool === 'cloudPlus') && pts.length >= 3) {")
j = s.index("      setActivePoints([]);\n      return;\n    }", i)
s = s[:j] + "      if (activeTool === 'cloudPlus') askCloudComment(newMeasurement.id, pts);\n" + s[j:]
rep("""        ((activeTool === 'cloud' || activeTool === 'polygon') && activePoints.length >= 3) ||""",
    """        ((activeTool === 'cloud' || activeTool === 'cloudPlus' || activeTool === 'polygon') && activePoints.length >= 3) ||""")

# Tool strip + menu.
rep("""      T('cloud', 'Cloud', RevuCloud, 'markup'),""", """      T('cloud', 'Cloud', RevuCloud, 'markup'),
      T('cloudPlus', 'Cloud+', RevuCloudPlus, 'markup'),""")
rep("""['Callout', 'callout'], ['Cloud', 'cloud'],""", """['Callout', 'callout'], ['Cloud', 'cloud'], ['Cloud+', 'cloudPlus'],""")
rep("""  RevuPolylineMarkup, RevuAngle,""", """  RevuPolylineMarkup, RevuCloudPlus, RevuAngle,""")
p.write_text(s, encoding="utf-8")

# Shared tool type + labels.
q = base / "features/takeoff/lib/takeoff-types.ts"
t = q.read_text(encoding="utf-8")
t = t.replace("""  | 'polylineMarkup';

export type MeasurementType =""", """  | 'polylineMarkup'
  | 'cloudPlus';

export type MeasurementType =""")
q.write_text(t, encoding="utf-8")
q = base / "modules/pdf-takeoff/data/revu-style.ts"
t = q.read_text(encoding="utf-8")
t = t.replace("  polylineMarkup: 'Polyline',\n", "  polylineMarkup: 'Polyline',\n  cloudPlus: 'Cloud+',\n", 1)
q.write_text(t, encoding="utf-8")
q = base / "modules/pdf-takeoff/components/revu-icons.tsx"
t = q.read_text(encoding="utf-8")
t += """
export const RevuCloudPlus = make('cloudplus', (
  <>
    <path d="M3 11a2 2 0 0 1 3.4-1.5 2.2 2.2 0 0 1 4.2 0 2 2 0 0 1 3.4 1.4 2 2 0 0 1-.4 3.6 2.2 2.2 0 0 1-4.2.5A2 2 0 0 1 6 15.6 2 2 0 0 1 3 11z" fill={FILL_RED} stroke={RED} strokeWidth={1.5} />
    <path d="M13.5 9.5L17 6" stroke={RED} strokeWidth={1.3} />
    <rect x="16.5" y="2.5" width="5" height="4.5" stroke={RED} strokeWidth={1.3} />
  </>
));
"""
q.write_text(t, encoding="utf-8")
print("ok")
