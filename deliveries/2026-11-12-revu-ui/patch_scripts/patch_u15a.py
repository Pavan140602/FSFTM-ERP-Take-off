"""Update 15a: straight lines by default (0/45/90), Ctrl+Shift = free point,
Ctrl = straight; a straight line ending on a drawing line lands square on it;
one small magnet symbol (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# State: ortho on by default (remembered), modifier refs and the rule.
rep("""  const [orthoLock, setOrthoLock] = useState(false);""", """  // On by default (Revu-style straight lines), remembered (update 15).
  const [orthoLock, setOrthoLock] = useState<boolean>(() => {
    try { return localStorage.getItem('oe-ortho-lock') !== '0'; } catch { return true; }
  });
  useEffect(() => {
    try { localStorage.setItem('oe-ortho-lock', orthoLock ? '1' : '0'); } catch { /* ignore */ }
  }, [orthoLock]);
  const orthoLockRef = useRef(orthoLock);
  orthoLockRef.current = orthoLock;
  /** Live Ctrl / Shift (keyboard and mouse events). */
  const modsRef = useRef({ ctrl: false, shift: false });
  /** Straight-line rule (update 15): straight (0/45/90) by default or with
   *  Ctrl / Shift; Ctrl+Shift places a free point. */
  const straight = (): boolean => {
    const m = modsRef.current;
    const shift = m.shift || shiftHeldRef.current;
    if (m.ctrl && shift) return false;
    return orthoLockRef.current || m.ctrl || shift;
  };""")

# Keyboard: track Ctrl too.
rep("""      // focus so it never goes stale.
      shiftHeldRef.current = e.shiftKey;
""", """      // focus so it never goes stale.
      shiftHeldRef.current = e.shiftKey;
      modsRef.current = { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey };
""")
rep("""    const upHandler = (e: KeyboardEvent) => {
      shiftHeldRef.current = e.shiftKey;""", """    const upHandler = (e: KeyboardEvent) => {
      shiftHeldRef.current = e.shiftKey;
      modsRef.current = { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey };""")
rep("""    const blurHandler = () => {
      shiftHeldRef.current = false;""", """    const blurHandler = () => {
      shiftHeldRef.current = false;
      modsRef.current = { ctrl: false, shift: false };""")

# Mouse: keep the modifiers fresh.
rep("""  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {""", """  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      modsRef.current = { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey };""")

# Click path: straight rule + square onto a snapped drawing line.
rep("""        if (csnap) {
          point = csnap.point;
          setSnapIsContent(true);
          setSnapKind(csnap.kind);
        } else {
          setSnapIsContent(false);
          setSnapKind(null);
        }
      }""", """        if (csnap) {
          const anchorPt = activePoints[activePoints.length - 1];
          // Straight line onto a drawing line: keep the 0/45/90 direction and
          // land where it meets that line (draw between two lines square).
          point = csnap.kind === 'edge' && csnap.seg && anchorPt && !settingScale && straight()
            ? orthoOntoSegment(anchorPt, point, csnap.seg)
            : csnap.point;
          contentLockedRef.current = true;
          setSnapIsContent(true);
          setSnapKind(csnap.kind);
        } else {
          setSnapIsContent(false);
          setSnapKind(null);
        }
      }""")
rep("""      if (
        !settingScale &&
        !vsnap &&
        !exactPoint &&
        (orthoLock || shiftHeldRef.current) &&
        activePoints.length > 0 &&
        (activeTool === 'distance' ||""", """      const lockedOnContent = contentLockedRef.current;
      contentLockedRef.current = false;
      if (
        !settingScale &&
        !vsnap &&
        !exactPoint &&
        !lockedOnContent &&
        straight() &&
        activePoints.length > 0 &&
        (activeTool === 'perimeter' ||
          activeTool === 'polygonCutout' ||
          activeTool === 'polylineMarkup' ||
          activeTool === 'cloudPlus' ||
          activeTool === 'diameter' ||
          activeTool === 'radiusCenter' ||
          activeTool === 'angle' ||
          activeTool === 'distance' ||""")
rep("""          scalePoints.length === 1 && (orthoLock || shiftHeldRef.current)
            ? orthoSnap(scalePoints[0]!, point)
            : point;""", """          scalePoints.length === 1 && straight() && !contentLockedRef.current
            ? orthoSnap(scalePoints[0]!, point)
            : point;""")
rep("""          setLiveCursor(csnapCal ? csnapCal.point : orthoLock || shiftHeldRef.current ? orthoSnap(a, pt) : pt);""",
    """          setLiveCursor(csnapCal ? csnapCal.point : straight() ? orthoSnap(a, pt) : pt);""")
# Hover path.
rep("""          if (csnap) {
            setSnapPoint(csnap.point);
            setSnapIsContent(true);
            setSnapKind(csnap.kind);
            setLiveCursor(csnap.point);
          } else {""", """          if (csnap) {
            const anchorH = activePoints[activePoints.length - 1];
            const shown = csnap.kind === 'edge' && csnap.seg && anchorH && straight()
              ? orthoOntoSegment(anchorH, pt, csnap.seg)
              : csnap.point;
            setSnapPoint(shown);
            setSnapIsContent(true);
            setSnapKind(csnap.kind);
            setLiveCursor(shown);
          } else {""")
rep("""            const snapped =
              anchor && (orthoLock || shiftHeldRef.current) ? orthoSnap(anchor, pt) : pt;""", """            const snapped =
              anchor && straight() ? orthoSnap(anchor, pt) : pt;""")
# Edits: only Shift / Ctrl square a dragged vertex (the default lock is for drawing).
rep("""      const ortho = orthoLock || shiftHeldRef.current;""", """      const ortho = (shiftHeldRef.current || modsRef.current.ctrl) && !(shiftHeldRef.current && modsRef.current.ctrl);""")
rep("""  const handleCanvasDblClickRef = useRef<(() => void) | null>(null);""", """  const handleCanvasDblClickRef = useRef<(() => void) | null>(null);
  /** The click point came from a drawing snap: no further ortho on it. */
  const contentLockedRef = useRef(false);""")
# Ortho toggle tooltip.
rep("""title={t('takeoff_viewer.ortho_lock_hint', { defaultValue: 'Constrain new segments to 0, 45 or 90 degrees (hold Shift, or toggle here)' })}""",
    """title={t('takeoff_viewer.ortho_lock_hint2', { defaultValue: 'Straight lines (0 / 45 / 90 degrees) - on by default. Ctrl+Shift while clicking = free point; Ctrl = straight.' })}""")

# Helper.
rep("""/** Nearest point on a closed outline (Cloud+ leader, update 10). */""", """/** A straight (0/45/90) line from `anchor` towards `cursor`, landing where it
 *  meets the drawing line `seg` (update 15). Falls back to the plain ortho
 *  point when the line is parallel or the meet is far from the cursor. */
function orthoOntoSegment(anchor: Point, cursor: Point, seg: { a: Point; b: Point }): Point {
  const o = orthoSnap(anchor, cursor);
  const dx = o.x - anchor.x;
  const dy = o.y - anchor.y;
  const sx = seg.b.x - seg.a.x;
  const sy = seg.b.y - seg.a.y;
  const den = dx * sy - dy * sx;
  if (Math.abs(den) < 1e-9) return o;
  const t = ((seg.a.x - anchor.x) * sy - (seg.a.y - anchor.y) * sx) / den;
  const q = { x: anchor.x + t * dx, y: anchor.y + t * dy };
  return Math.hypot(q.x - cursor.x, q.y - cursor.y) < 40 ? q : o;
}

/** Nearest point on a closed outline (Cloud+ leader, update 10). */""")

# One small magnet symbol.
i = s.index("      if (snapKind === 'intersection') {\n        ctx.beginPath();\n        ctx.moveTo(sx - 6 * dpr")
j = s.index("      ctx.restore();\n    }\n  }, [measurements, orderedMeasurements", i)
s = s[:i] + """      // One small magnet mark for every snap (update 15): a 4 px ring.
      ctx.lineWidth = 1.5 * dpr;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(sx, sy, 3.5 * dpr, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
""" + s[j:]
p.write_text(s, encoding="utf-8")

# Content snap returns the line it snapped to.
q = base / "data/content-snap.ts"
t = q.read_text(encoding="utf-8")
t = t.replace("  kind: 'endpoint' | 'midpoint' | 'edge' | 'intersection';", "  kind: 'endpoint' | 'midpoint' | 'edge' | 'intersection';\n  /** The drawing line, for an edge snap (straight-onto-line, update 15). */\n  seg?: Segment;", 1)
a = """              kind: 'edge',
            };"""
assert t.count(a) == 1
t = t.replace(a, """              kind: 'edge',
              seg: s,
            };""")
q.write_text(t, encoding="utf-8")
print("ok")
