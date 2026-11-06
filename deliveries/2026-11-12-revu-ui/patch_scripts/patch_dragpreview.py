"""Drag preview draws the real shape (Revu): solid rectangle / ellipse,
highlight fill, scalloped cloud, Cloud+ scallops + comment leader
(OE-DELIVERY 2026-11-12-revu-ui update 7)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("""        ctx.save();
        ctx.setLineDash([6 * dpr, 4 * dpr]);
        ctx.lineWidth = 1.5 * dpr;
        ctx.strokeStyle = annotationColor || '#EF4444';
        if (activeTool === 'ellipse') {
          ctx.beginPath();
          ctx.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
          ctx.stroke();
        } else {
          ctx.strokeRect(bx, by, bw, bh);
        }
        ctx.restore();""", """        // The real shape, solid, as Revu shows it while dragging (update 7).
        const col = annotationColor || '#EF4444';
        ctx.save();
        ctx.lineWidth = 1.6 * dpr;
        ctx.strokeStyle = col;
        if (activeTool === 'ellipse') {
          ctx.beginPath();
          ctx.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, 0, 0, Math.PI * 2);
          ctx.stroke();
        } else if (activeTool === 'highlight') {
          ctx.globalAlpha = 0.35;
          ctx.fillStyle = '#FDE047';
          ctx.fillRect(bx, by, bw, bh);
        } else if (activeTool === 'cloud' || activeTool === 'cloudPlus') {
          const ring = [
            { x: bx, y: by }, { x: bx + bw, y: by }, { x: bx + bw, y: by + bh }, { x: bx, y: by + bh }, { x: bx, y: by },
          ];
          const r = 6 * dpr;
          ctx.beginPath();
          for (let i = 0; i + 1 < ring.length; i++) {
            const p0 = ring[i]!;
            const p1 = ring[i + 1]!;
            const L = Math.hypot(p1.x - p0.x, p1.y - p0.y);
            if (L < 1) continue;
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
          ctx.stroke();
          if (activeTool === 'cloudPlus') {
            // Comment leader from the top-left corner, up-left then across.
            const L1 = 18 * dpr;
            ctx.strokeStyle = '#9CA3AF';
            ctx.lineWidth = 1.2 * dpr;
            ctx.beginPath();
            ctx.moveTo(bx, by);
            ctx.lineTo(bx - L1, by - L1);
            ctx.lineTo(bx - L1 - 22 * dpr, by - L1);
            ctx.stroke();
            ctx.fillStyle = '#374151';
            ctx.fillRect(bx - L1 - 60 * dpr, by - L1 - 8 * dpr, 1 * dpr, 14 * dpr);
          }
        } else {
          ctx.strokeRect(bx, by, bw, bh);
        }
        ctx.restore();""")

# Cloud+ comment sits up-left of the cloud, as in Revu.
rep("""    const maxX = Math.max(...pts.map((q) => q.x));
    const minY = Math.min(...pts.map((q) => q.y));
    const tip = { x: maxX, y: minY };
    setMarkupTextPrompt({ kind: 'callout', points: [tip, { x: tip.x + 36, y: tip.y - 36 }], value: '', groupWith: cloudId });""",
    """    const minX = Math.min(...pts.map((q) => q.x));
    const minY = Math.min(...pts.map((q) => q.y));
    const tip = { x: minX, y: minY };
    setMarkupTextPrompt({ kind: 'callout', points: [tip, { x: tip.x - 18, y: tip.y - 18 }], value: '', groupWith: cloudId });""")
p.write_text(s, encoding="utf-8")
print("ok")
