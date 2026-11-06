from pathlib import Path

root = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main")
s = ""


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


p = root / "frontend/src/modules/pdf-takeoff/data/auto-takeoff.ts"
s = p.read_text(encoding="utf-8")
rep("""      const dupIdx = onPage.find((i) => {
        const m = next[i]!;
        return LINE_TYPES.has(m.type) && segmentsOf(m).some((s) => segs.some((seg) => linesOverlap(s, seg) || linesOverlap(seg, s)));
      });""", """      const dupIdx = onPage.find((i) => {
        const m = next[i]!;
        // A shear / strap-braced panel lies on its bearing wall on purpose:
        // walls of another tag on the same line are not copies
        // (OE-DELIVERY 2026-11-08-stud-walls).
        if (item.category === 'walls' && m.auto?.cat === 'walls' && m.auto.des !== item.designation) return false;
        return LINE_TYPES.has(m.type) && segmentsOf(m).some((s) => segs.some((seg) => linesOverlap(s, seg) || linesOverlap(seg, s)));
      });""")
p.write_text(s, encoding="utf-8")

p = root / "backend/app/modules/takeoff/auto_takeoff.py"
s = p.read_text(encoding="utf-8")
rep('''    out: list[dict[str, Any]] = []
    for k, it in enumerate(items):
        if k in replace:
            out.extend(replace[k])
        else:
            out.append(it)
    return out


''', '''    out: list[dict[str, Any]] = []
    for k, it in enumerate(items):
        if k in replace:
            out.extend(replace[k])
        else:
            out.append(it)
    # A shear / strap-braced panel drawn on a bearing wall is part of that
    # wall: the wall's studs already cover it, so the panel counts none of
    # its own (its chord studs are in its spec) - the two are shown together,
    # and either can be picked out with the role filter.
    plain = [w for w in out if w.get("category") == "walls" and w.get("kind") == "line" and w.get("segment") == "wall"]
    for w in plain:
        if w.get("role") not in ("Shear Wall", "Strap Braced Wall"):
            continue
        (ax, ay), (bx, by) = w["points"]
        L = math.hypot(bx - ax, by - ay)
        if L <= 0:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        for o in plain:
            if o is w or o.get("role") in ("Shear Wall", "Strap Braced Wall"):
                continue
            (cx, cy), (dx, dy) = o["points"]
            if abs((cx - ax) * -uy + (cy - ay) * ux) > 2.0 or abs((dx - ax) * -uy + (dy - ay) * ux) > 2.0:
                continue
            t1, t2 = (cx - ax) * ux + (cy - ay) * uy, (dx - ax) * ux + (dy - ay) * uy
            ov = min(L, max(t1, t2)) - max(0.0, min(t1, t2))
            if ov >= 0.6 * L:
                w["stud_count"] = 0
                w["stud_spacing"] = None  # the viewer counts / draws none for it
                w["studs_in"] = o.get("designation")
                w["spec"] = f"{w.get('spec') or ''}; field studs counted in wall {o.get('designation')}".lstrip("; ")
                break
    return out


''')
p.write_text(s, encoding="utf-8")
print("ok")
