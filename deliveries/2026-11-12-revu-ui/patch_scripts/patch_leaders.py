"""Update 10: Cloud+ leader slides round the cloud with the mouse, a click
drops the box and you type in place; Callout shows a live arrow (head on
the called-out point) and is typed in place after the second click
(OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# Helper: nearest point on a closed outline.
rep("""/** Tools whose result depends on the sheet scale (Count / Angle do not). */""",
    """/** Nearest point on a closed outline (Cloud+ leader, update 10). */
function nearestOnRing(ring: Point[], q: Point): Point {
  let best = ring[0] ?? q;
  let bd = Infinity;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i]!;
    const b = ring[(i + 1) % ring.length]!;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const L2 = dx * dx + dy * dy || 1;
    const t = Math.max(0, Math.min(1, ((q.x - a.x) * dx + (q.y - a.y) * dy) / L2));
    const pt = { x: a.x + t * dx, y: a.y + t * dy };
    const d = Math.hypot(pt.x - q.x, pt.y - q.y);
    if (d < bd) {
      bd = d;
      best = pt;
    }
  }
  return best;
}

/** Leader + arrow head at `tip` (callout / Cloud+ previews, update 10). */
function drawLeader(ctx: CanvasRenderingContext2D, from: Point, tip: Point, k: number, dpr: number, color: string): void {
  const F = { x: from.x * k, y: from.y * k };
  const T = { x: tip.x * k, y: tip.y * k };
  ctx.save();
  ctx.setLineDash([]);
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1.6 * dpr;
  ctx.beginPath();
  ctx.moveTo(F.x, F.y);
  ctx.lineTo(T.x, T.y);
  ctx.stroke();
  const ang = Math.atan2(T.y - F.y, T.x - F.x);
  const h = 10 * dpr;
  ctx.beginPath();
  ctx.moveTo(T.x, T.y);
  ctx.lineTo(T.x - h * Math.cos(ang - 0.42), T.y - h * Math.sin(ang - 0.42));
  ctx.lineTo(T.x - h * Math.cos(ang + 0.42), T.y - h * Math.sin(ang + 0.42));
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** Tools whose result depends on the sheet scale (Count / Angle do not). */""")

# State: Cloud+ leader phase.
rep("""  const askCloudComment = (cloudId: string, pts: Point[]) => {
    const minX = Math.min(...pts.map((q) => q.x));
    const minY = Math.min(...pts.map((q) => q.y));
    const tip = { x: minX, y: minY };
    setMarkupTextPrompt({ kind: 'callout', points: [tip, { x: tip.x - 18, y: tip.y - 18 }], value: '', groupWith: cloudId });
  };""", """  const askCloudComment = (cloudId: string, pts: Point[]) => {
    // Leader phase: the line rides round the cloud with the mouse; the next
    // click drops the comment box there (update 10).
    cloudLeaderRef.current = { cloudId, pts };
    setCloudLeader({ cloudId, pts });
  };""")
rep("""  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);""",
    """  const [setScaleDlg, setSetScaleDlg] = useState<{ reason?: string } | null>(null);
  /** Cloud+ leader phase (update 10): the cloud just drawn, waiting for the box click. */
  const [cloudLeader, setCloudLeader] = useState<{ cloudId: string; pts: Point[] } | null>(null);
  const cloudLeaderRef = useRef<{ cloudId: string; pts: Point[] } | null>(null);
  useEffect(() => {
    if (!cloudLeader) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        cloudLeaderRef.current = null;
        setCloudLeader(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cloudLeader]);""")

# The tool must stay on during the leader phase / typing.
rep("""  exitToolRef.current = () => {
    const tl = activeToolRef.current;
    if (tl === 'select' || tl === 'count' || offsetToolRef.current) return;""", """  exitToolRef.current = () => {
    const tl = activeToolRef.current;
    if (tl === 'select' || tl === 'count' || offsetToolRef.current) return;
    if (cloudLeaderRef.current) return; // Cloud+: still placing its comment""")

# Click in the leader phase: drop the box.
rep("""      if (activeTool === 'select') return;

      // Rectangle area / volume / perimeter / cutout drawn by press-and-drag""", """      if (activeTool === 'select') return;

      // Cloud+ leader phase: this click drops the comment box; type in place.
      if (cloudLeaderRef.current) {
        const cl = cloudLeaderRef.current;
        cloudLeaderRef.current = null;
        setCloudLeader(null);
        boxDragRef.current = null;
        setBoxDragRect(null);
        const tip = nearestOnRing(cl.pts, point);
        setMarkupTextPrompt({ kind: 'callout', points: [tip, point], value: '', groupWith: cl.cloudId });
        return;
      }

      // Rectangle area / volume / perimeter / cutout drawn by press-and-drag""")

# Previews: callout live arrow; Cloud+ leader; leader while typing.
rep("""      if (activeTool === 'line' || activeTool === 'polygon' || activeTool === 'callout' || activeTool === 'arc' || activeTool === 'pen' || activeTool === 'polylineMarkup') {""",
    """      if (activeTool === 'line' || activeTool === 'polygon' || activeTool === 'arc' || activeTool === 'pen' || activeTool === 'polylineMarkup') {""")
rep("""    // Live tracing (update 9): the shape follows the mouse as in Revu.""", """    // Callout / Cloud+ leaders (update 10): arrow head on the called-out
    // point, box end on the mouse; while typing, the leader to the box.
    {
      const k = dpr * zoom;
      const col = annotationColor || '#EF4444';
      if (activeTool === 'callout' && activePoints.length === 1 && liveCursor && !panning && !markupTextPrompt) {
        drawLeader(ctx, liveCursor, activePoints[0]!, k, dpr, col);
        ctx.save();
        ctx.setLineDash([4 * dpr, 3 * dpr]);
        ctx.strokeStyle = col;
        ctx.strokeRect(liveCursor.x * k, liveCursor.y * k - 10 * dpr, 90 * dpr, 20 * dpr);
        ctx.restore();
      }
      if (cloudLeader && liveCursor && !panning) {
        const tip = nearestOnRing(cloudLeader.pts, liveCursor);
        drawLeader(ctx, liveCursor, tip, k, dpr, col);
        ctx.save();
        ctx.setLineDash([4 * dpr, 3 * dpr]);
        ctx.strokeStyle = col;
        ctx.strokeRect(liveCursor.x * k, liveCursor.y * k - 10 * dpr, 90 * dpr, 20 * dpr);
        ctx.restore();
      }
      if (markupTextPrompt?.kind === 'callout' && markupTextPrompt.points.length >= 2) {
        drawLeader(ctx, markupTextPrompt.points[1]!, markupTextPrompt.points[0]!, k, dpr, col);
      }
    }

    // Live tracing (update 9): the shape follows the mouse as in Revu.""")

# Track the cursor in the leader phase too.
rep("""          activeTool === 'arrow' ||
          activeTool === 'rectarea')
      ) {""", """          activeTool === 'arrow' ||
          activeTool === 'rectarea' ||
          cloudLeaderRef.current)
      ) {""")

# Render deps.
i = s.index("displayUnitPref, autoRoleFilter]);")
s = s[:i] + "displayUnitPref, autoRoleFilter, markupTextPrompt, cloudLeader]);" + s[i + len("displayUnitPref, autoRoleFilter]);"):]

# In-place callout editor (no dialog).
rep("""      {markupTextPrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">""",
    """      {markupTextPrompt && markupTextPrompt.kind !== 'callout' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">""")
rep("""                {showTextInput && (() => {
                  const est = textInputStyle""", """                {/* Callout / Cloud+ comment typed in place at the box (update 10):
                    Enter places it, Shift+Enter is a new line, Esc cancels. */}
                {markupTextPrompt?.kind === 'callout' && markupTextPrompt.points.length >= 2 && (() => {
                  const [tip, anchor] = markupTextPrompt.points as [Point, Point];
                  const left = anchor.x < tip.x;
                  return (
                    <div
                      className="absolute z-20"
                      style={{
                        left: `${anchor.x * zoom}px`,
                        top: `${anchor.y * zoom + overlayTop}px`,
                        transform: `translate(${left ? '-100%' : '0'}, -50%)`,
                      }}
                      data-testid="callout-inline-editor"
                    >
                      <textarea
                        value={markupTextPrompt.value}
                        onChange={(e) => {
                          const value = e.target.value;
                          setMarkupTextPrompt((cur) => (cur ? { ...cur, value } : cur));
                        }}
                        onInput={(e) => {
                          const el = e.currentTarget;
                          el.style.height = 'auto';
                          el.style.height = `${el.scrollHeight}px`;
                        }}
                        rows={1}
                        autoFocus
                        placeholder="Type…"
                        onKeyDown={(e) => {
                          e.stopPropagation();
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            confirmMarkupText();
                          }
                          if (e.key === 'Escape') setMarkupTextPrompt(null);
                        }}
                        onBlur={() => {
                          if (markupTextPrompt.value.trim()) confirmMarkupText();
                          else setMarkupTextPrompt(null);
                        }}
                        className="block w-44 resize-none overflow-hidden border bg-white px-1.5 py-1 text-[12px] leading-4 outline-none"
                        style={{ borderColor: annotationColor || '#EF4444', color: annotationColor || '#EF4444' }}
                      />
                    </div>
                  );
                })()}
                {showTextInput && (() => {
                  const est = textInputStyle""")
p.write_text(s, encoding="utf-8")
print("ok")
