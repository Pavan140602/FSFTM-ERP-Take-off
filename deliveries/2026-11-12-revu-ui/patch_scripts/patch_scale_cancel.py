"""Scale ask: Cancel / close without a scale removes the markup just drawn
(user rule, OE-DELIVERY 2026-11-12-revu-ui update 7)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("""  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);""",
    """  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);
  /** Markups drawn on a sheet with no scale, waiting for one: removed when
   *  the scale window is cancelled (user rule, update 7). */
  const unscaledPendingRef = useRef<string[]>([]);
  const dropUnscaledPending = () => {
    const ids = new Set(unscaledPendingRef.current);
    unscaledPendingRef.current = [];
    if (ids.size) setMeasurements((prev) => prev.filter((m) => !ids.has(m.id)));
  };""")

rep("""      const pg = op.measurement.page;
      setTimeout(() => {
        if (pageIsCalibrated(editPageScalesRef.current, pg)) return;
        setSetScaleDlg({
          reason: `Sheet ${pg} has no scale yet, so this measurement is not to scale. Set the scale and it is re-measured. This asks after each measurement until the sheet has a scale.`,
        });""", """      const pg = op.measurement.page;
      const mid = op.measurement.id;
      setTimeout(() => {
        if (pageIsCalibrated(editPageScalesRef.current, pg)) return;
        unscaledPendingRef.current = [...unscaledPendingRef.current, mid];
        setSetScaleDlg({
          reason: `Sheet ${pg} has no scale yet. Apply a scale to keep this measurement - Cancel removes it.`,
        });""")

rep("""        onCancel={() => {
          // Cancel just closes: the next measurement on a sheet with no scale asks again (user rule).
          setSetScaleDlg(null);
        }}
        onApply={({ pages, scale: sc, label, precision }) => {
          setSetScaleDlg(null);""", """        onCancel={() => {
          // Cancel: the markup drawn without a scale is removed, and the next
          // one asks again (user rule).
          setSetScaleDlg(null);
          dropUnscaledPending();
        }}
        onApply={({ pages, scale: sc, label, precision }) => {
          setSetScaleDlg(null);
          unscaledPendingRef.current = [];""")

rep("""      calibratePagesRef.current = null;""", """      calibratePagesRef.current = null;
      unscaledPendingRef.current = [];""")
rep("""  const handleCalibrationCancel = useCallback(() => {
    setShowCalibrationDialog(false);""", """  const handleCalibrationCancel = useCallback(() => {
    setShowCalibrationDialog(false);
    dropUnscaledPending();""")
p.write_text(s, encoding="utf-8")
print("ok")
