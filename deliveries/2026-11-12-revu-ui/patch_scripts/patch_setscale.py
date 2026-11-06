"""Set Scale window (Revu) opens when a measurement starts on a sheet with
no scale; calibration applies to the pages picked there
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("import { LegendPropertiesPanel } from './components/LegendPropertiesPanel';",
    "import { LegendPropertiesPanel } from './components/LegendPropertiesPanel';\n"
    "import { SetScaleDialog } from './components/SetScaleDialog';")

# State.
rep("""  const [showCalibrationDialog, setShowCalibrationDialog] = useState(false);""", """  const [showCalibrationDialog, setShowCalibrationDialog] = useState(false);
  /** Revu Set Scale window: open with an optional reason line. */
  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);
  /** Pages a running calibration applies to (picked in Set Scale). */
  const calibratePagesRef = useRef<number[] | null>(null);
  /** Sheets where the user chose Cancel: drawing carries on there with the
   *  document default, no more prompts this session. */
  const scalePromptSkipRef = useRef<Set<number>>(new Set());""")

# Calibration confirm: also the pages picked in Set Scale.
rep("""      const page = currentPage;
      setScale(nextScale);
      setShowCalibrationDialog(false);""", """      const page = currentPage;
      setScale(nextScale);
      const extra = calibratePagesRef.current;
      calibratePagesRef.current = null;
      if (extra && extra.length) {
        setPageScales((prev) => extra.reduce((acc, pg) => setPageScaleIn(acc, pg, nextScale), prev));
      }
      setShowCalibrationDialog(false);""")

# Click: a measurement on a sheet with no scale asks for one first.
rep("""      const x = (e.clientX - rect.left) / zoom;
      const y = (e.clientY - rect.top) / zoom;
      let point: Point = { x, y };""", """      const x = (e.clientX - rect.left) / zoom;
      const y = (e.clientY - rect.top) / zoom;
      // Revu: a measurement on a sheet with no scale opens Set Scale first
      // (OE-DELIVERY 2026-11-12-revu-ui).
      if (
        !settingScale &&
        !calibrationMode &&
        activePoints.length === 0 &&
        SCALE_TOOLS.has(activeTool) &&
        !pageIsCalibrated(editPageScalesRef.current, currentPage) &&
        !scalePromptSkipRef.current.has(currentPage)
      ) {
        setSetScaleDlg({ reason: `Sheet ${currentPage} has no scale yet. Set it before measuring (or Cancel to keep the default).` });
        return;
      }
      let point: Point = { x, y };""")

# Tools that measure (need a scale).
rep("""const ANNOTATION_TOOLS: AnnotationToolType[] = [""", """/** Tools whose result depends on the sheet scale (Count / Angle do not). */
const SCALE_TOOLS = new Set<string>([
  'distance', 'polyline', 'area', 'rectarea', 'volume', 'perimeter', 'diameter', 'radiusCenter', 'radius3Point',
  'arc', 'polygonCutout', 'ellipseCutout', 'dynamicFill',
]);

const ANNOTATION_TOOLS: AnnotationToolType[] = [""")

# The window.
rep("""      {showCalibrationDialog && (
        <CalibrationDialog""", """      <SetScaleDialog
        open={setScaleDlg !== null}
        currentPage={currentPage}
        totalPages={totalPages || 1}
        imperial={measurementSystem === 'imperial'}
        current={pageIsCalibrated(pageScales, currentPage) ? scaleForPage(pageScales, currentPage) : undefined}
        precision={imperialDenominator || 16}
        reason={setScaleDlg?.reason}
        onCancel={() => {
          if (setScaleDlg?.reason) scalePromptSkipRef.current.add(currentPage);
          setSetScaleDlg(null);
        }}
        onApply={({ pages, scale: sc, label, precision }) => {
          setSetScaleDlg(null);
          setPageScales((prev) => pages.reduce((acc, pg) => setPageScaleIn(acc, pg, sc), prev));
          (setPreference as (k: string, v: unknown) => void)('imperialDenominator', precision);
          addToast({
            type: 'success',
            title: `Scale set: ${label}`,
            message: pages.length === 1 ? `Page ${pages[0]}` : `${pages.length} pages (${pages[0]}-${pages[pages.length - 1]})`,
          });
        }}
        onCalibrate={(pages, precision) => {
          setSetScaleDlg(null);
          (setPreference as (k: string, v: unknown) => void)('imperialDenominator', precision);
          calibratePagesRef.current = pages;
          handleStartCalibration();
          addToast({ type: 'info', title: 'Calibrate', message: 'Click two points of a known length on the sheet.' });
        }}
      />
      {showCalibrationDialog && (
        <CalibrationDialog""")

p.write_text(s, encoding="utf-8")
print("ok")
