"""Multiply / Offset distance accepts any length form (12'-6 1/2", 1 1/2",
12 ft 6 in ...); offset ghost label shows the real typed distance
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("import { SetScaleDialog } from './components/SetScaleDialog';",
    "import { SetScaleDialog } from './components/SetScaleDialog';\n"
    "import { parseLengthInches, formatFtIn } from './data/length-input';")

rep("""  const v = parseFloat(s);
  if (!Number.isFinite(v) || v <= 0) return null;
  // A bare number is interpreted in the selected unit.""", """  // Any other estimator form: 12'-6 1/2", 1 1/2", 12 ft 6 in, 3/4" ...
  const anyIn = parseLengthInches(s, fallbackUnit === 'ft-in' ? 'ft' : fallbackUnit);
  if (anyIn !== null) return anyIn > 0 ? anyIn * 0.0254 : null;
  const v = parseFloat(s);
  if (!Number.isFinite(v) || v <= 0) return null;
  // A bare number is interpreted in the selected unit.""")

rep("""          const distVal = parseFloat(offsetDistance);
          const unit = displayUnitFor('', measurementSystem);
          const label = !(distVal > 0) ? '' : `${formatMeasurement(distVal, unit)}`;""", """          const distM = parseDistanceToMeters(offsetDistance, offsetUnitRef.current);
          const label = !(distM && distM > 0)
            ? ''
            : measurementSystem === 'imperial'
              ? formatFtIn(distM / 0.0254)
              : `${(distM * 1000).toFixed(0)} mm`;""")
p.write_text(s, encoding="utf-8")
print("ok")
