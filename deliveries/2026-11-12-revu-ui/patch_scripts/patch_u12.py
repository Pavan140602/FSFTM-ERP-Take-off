"""Update 12: status-bar scale opens Apply Scale to Pages; Cloud / Cloud+
traced with straight ghost lines (scallops only once finished); empty
Cloud+ / callout comment kept, double-click a callout to edit its text;
magnet snap: wider reach + line intersections (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path
import re

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# 1. Status-bar scale: a button that opens the Apply Scale to Pages window.
i = s.index("                {/* Scale picker in the status bar (OE-DELIVERY 2026-11-02-revu-left-panel), like Revu. */}\n                <select")
j = s.index("                </select>\n", i) + len("                </select>\n")
s = s[:i] + """                {/* Scale in the status bar opens Revu's Apply Scale to Pages window (update 12). */}
                <button
                  type="button"
                  onClick={() => setSetScaleDlg({})}
                  title="Scale of this page - click to set it (Apply Scale to Pages)"
                  className={clsx(
                    'inline-flex h-6 max-w-[170px] items-center gap-1 rounded border bg-surface-primary px-1.5 text-[11px]',
                    isCalibrated ? 'border-border text-content-primary hover:bg-surface-secondary' : 'border-amber-400 text-amber-700 hover:bg-amber-50',
                  )}
                  data-testid="status-scale"
                >
                  <span className="truncate">{isCalibrated ? (DRAWING_SCALE_PRESETS.find((sp) => sameScale(scale, sp.scale))?.label ?? `Custom ${formatScaleRatio(scale)}`) : 'Not calibrated'}</span>
                  <ChevronDown size={11} className="shrink-0 opacity-70" />
                </button>
""" + s[j:]
if "formatScaleRatio" not in s.split("export default")[0][:20000] and not re.search(r"import \{[^}]*formatScaleRatio", s):
    rep("  DRAWING_SCALE_PRESETS,", "  DRAWING_SCALE_PRESETS,\n  formatScaleRatio,")

# 2a. Click-drawn cloud: straight dashed ghost lines while drawing.
rep("""          const ring = pts;
          const r = 7 * dpr;
          ctx.save();
          ctx.strokeStyle = annotationColor;
          ctx.lineWidth = 1.6 * dpr;
          ctx.globalAlpha = 0.9;
          ctx.beginPath();
          for (let i = 0; i + 1 < ring.length; i++) {
            const p0 = ring[i]!;
            const p1 = ring[i + 1]!;
            const L = Math.hypot(p1.x - p0.x, p1.y - p0.y);
            const n = Math.max(1, Math.round(L / (2 * r)));
            const ang = Math.atan2(p1.y - p0.y, p1.x - p0.x);
            for (let k = 0; k < n; k++) {
              const cx = p0.x + ((p1.x - p0.x) * (k + 0.5)) / n;
              const cy = p0.y + ((p1.y - p0.y) * (k + 0.5)) / n;
              const rr = L / n / 2;
              ctx.moveTo(cx + Math.cos(ang + Math.PI) * rr, cy + Math.sin(ang + Math.PI) * rr);
              ctx.arc(cx, cy, rr, ang + Math.PI, ang, false);
            }
          }
          ctx.stroke();""", """          // Straight track lines while drawing; the scallops appear once the
          // cloud is finished (Enter / double-click), as in Revu (update 12).
          ctx.save();
          ctx.strokeStyle = annotationColor;
          ctx.lineWidth = 1.6 * dpr;
          ctx.globalAlpha = 0.9;
          ctx.setLineDash([6 * dpr, 4 * dpr]);
          ctx.beginPath();
          pts.forEach((q, i) => (i === 0 ? ctx.moveTo(q.x, q.y) : ctx.lineTo(q.x, q.y)));
          ctx.stroke();
          ctx.setLineDash([]);""")

# 2b. Dragged cloud: a dashed box while dragging (no scallops, no leader yet).
i = s.index("      } else if (activeTool === 'cloud' || activeTool === 'cloudPlus') {\n        const ring = [")
j = s.index("      } else {\n        ctx.strokeRect(bx, by, bw, bh);", i)
s = s[:i] + """      } else if (activeTool === 'cloud' || activeTool === 'cloudPlus') {
        // Track box while dragging; scallops once released (update 12).
        ctx.setLineDash([6 * dpr, 4 * dpr]);
        ctx.strokeRect(bx, by, bw, bh);
""" + s[j:]

# 3. Empty comment kept; edit a callout's text later.
rep("""    { kind: 'callout' | 'stamp'; points: Point[]; value: string; groupWith?: string } | null""",
    """    { kind: 'callout' | 'stamp'; points: Point[]; value: string; groupWith?: string; editId?: string } | null""")
rep("""    const text = prompt.value.trim();
    const [tip, anchor] = prompt.points;
    if (!text || !tip) return;
    if (prompt.kind === 'stamp') {""", """    const text = prompt.value.trim();
    const [tip, anchor] = prompt.points;
    if (!tip) return;
    // Editing a placed callout's text (double-click, update 12).
    if (prompt.editId) {
      const id = prompt.editId;
      setMeasurements((prev) => prev.map((x) => {
        if (x.id !== id || x.type !== 'callout') return x;
        const sz = calloutBoxSize(text || ' ');
        const w = Math.max(sz.width, 80);
        const h = Math.max(sz.height, 22);
        const box = x.points[1]!;
        const right = box.x + (x.width ?? 0) <= (x.points[0]?.x ?? 0) + 0.5;
        const nb = { x: right ? box.x + (x.width ?? 0) - w : box.x, y: box.y + (x.height ?? 0) / 2 - h / 2 };
        const next = { ...x, text, annotation: (text.split('\\n')[0] ?? '').slice(0, 120) || x.annotation, points: [x.points[0]!, nb], width: w, height: h };
        pushUndo({ kind: 'edit_geometry', measurementId: x.id, previousMeasurement: { ...x, points: [...x.points] }, nextMeasurement: { ...next, points: [...next.points] } });
        return next;
      }));
      return;
    }
    // A callout may be left empty and filled in later (user, update 12).
    if (!text && prompt.kind !== 'callout') return;
    if (prompt.kind === 'stamp') {""")
rep("""    if (!anchor) return;
    const box = calloutBoxSize(text);""", """    if (!anchor) return;
    const box0 = calloutBoxSize(text || ' ');
    const box = { width: Math.max(box0.width, 80), height: Math.max(box0.height, 22) };""")
rep("""      annotation: (text.split('\\n')[0] ?? '').slice(0, 120),
      ...toolFieldSpread(),
      text,""", """      annotation: (text.split('\\n')[0] ?? '').slice(0, 120) || nextAnnotation('callout'),
      ...toolFieldSpread(),
      text,""")
# Inline editor: empty Enter / click-away keeps the box; Esc keeps it for Cloud+.
rep("""                          if (e.key === 'Escape') setMarkupTextPrompt(null);
                        }}
                        onBlur={() => {
                          if (markupTextPrompt.value.trim()) confirmMarkupText();
                          else setMarkupTextPrompt(null);
                        }}""", """                          if (e.key === 'Escape') {
                            // Cloud+ keeps its (empty) comment box to fill in later.
                            if (markupTextPrompt.groupWith && !markupTextPrompt.editId) confirmMarkupText();
                            else setMarkupTextPrompt(null);
                          }
                        }}
                        onBlur={() => confirmMarkupText()}""")
# Double-press a callout: edit its text in place.
rep("""        if (m.type === 'text') {
          const now = Date.now();
          const last = lastTextPressRef.current;""", """        if (m.type === 'callout' && m.points.length >= 2) {
          const now = Date.now();
          const last = lastTextPressRef.current;
          if (last && last.id === m.id && now - last.at < 400) {
            lastTextPressRef.current = null;
            setHoverInfo(null);
            const tip = m.points[0]!;
            const b = m.points[1]!;
            const w = m.width ?? 80;
            const h = m.height ?? 22;
            const left = b.x + w <= tip.x + 0.5;
            setMarkupTextPrompt({ kind: 'callout', points: [tip, { x: left ? b.x + w : b.x, y: b.y + h / 2 }], value: m.text ?? '', editId: m.id });
            e.preventDefault();
            return;
          }
          lastTextPressRef.current = { id: m.id, at: now };
        }
        if (m.type === 'text') {
          const now = Date.now();
          const last = lastTextPressRef.current;""")
p.write_text(s, encoding="utf-8")

# 4. Magnet snap: wider reach for the drawing's lines + intersections.
q = base / "data/content-snap.ts"
t = q.read_text(encoding="utf-8")


def trep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)


trep("  kind: 'endpoint' | 'midpoint' | 'edge';", "  kind: 'endpoint' | 'midpoint' | 'edge' | 'intersection';")
trep("""  const tol = tolerancePx / Math.max(zoom, 0.01);""", """  // Magnet reach (Revu-like): a little wider than the markup-vertex snap.
  const tol = (tolerancePx * 1.6) / Math.max(zoom, 0.01);""")
trep("""  const seen = new Set<number>();
  let best: ContentSnap | null = null;""", """  const seen = new Set<number>();
  const near: number[] = [];
  let best: ContentSnap | null = null;""")
trep("""        const s = segments[idx]!;
        // Endpoints first""", """        const s = segments[idx]!;
        if (near.length < 80 && distToSegmentSq(p, s).d2 < tol2 * 4) near.push(idx);
        // Endpoints first""")
trep("""  return best;
}""", """  // Line crossings (grid lines, wall corners, framing): win over a plain
  // edge or midpoint, like an endpoint (update 12).
  for (let i = 0; i < near.length; i++) {
    const s1 = segments[near[i]!]!;
    for (let j = i + 1; j < near.length; j++) {
      const s2 = segments[near[j]!]!;
      const d1x = s1.b.x - s1.a.x;
      const d1y = s1.b.y - s1.a.y;
      const d2x = s2.b.x - s2.a.x;
      const d2y = s2.b.y - s2.a.y;
      const den = d1x * d2y - d1y * d2x;
      if (Math.abs(den) < 1e-9) continue;
      const ux = s2.a.x - s1.a.x;
      const uy = s2.a.y - s1.a.y;
      const ta = (ux * d2y - uy * d2x) / den;
      const tb = (ux * d1y - uy * d1x) / den;
      if (ta < -0.001 || ta > 1.001 || tb < -0.001 || tb > 1.001) continue;
      const ix = s1.a.x + ta * d1x;
      const iy = s1.a.y + ta * d1y;
      const d2 = (p.x - ix) ** 2 + (p.y - iy) ** 2;
      if (d2 >= tol2) continue;
      if (!best || best.kind === 'edge' || best.kind === 'midpoint' || d2 < bestD2) {
        bestD2 = d2;
        best = { point: { x: ix, y: iy }, kind: 'intersection' };
      }
    }
  }
  return best;
}""")
q.write_text(t, encoding="utf-8")
print("ok")
