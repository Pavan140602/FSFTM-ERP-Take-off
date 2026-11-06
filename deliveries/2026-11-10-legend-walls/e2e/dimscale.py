"""Probe: sheet scale from dimension strings (dimension text vs. the line it sits on)."""
import collections
import math
import re
import sys

import pymupdf

FT_IN = re.compile(r"^(\d{1,3})\s*'\s*-?\s*(\d{1,2})?(?:\s+(\d{1,2})/(\d{1,2}))?\s*(?:(\d)/(\d))?\s*[\"”]?$")
FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75}


def parse_ft(t: str):
    t = t.strip().replace("’", "'").replace("″", '"')
    extra = 0.0
    for k, v in FRAC.items():
        if k in t:
            extra += v
            t = t.replace(k, "")
    m = FT_IN.match(t)
    if not m:
        return None
    ft = int(m.group(1))
    inch = int(m.group(2) or 0)
    fr = 0.0
    if m.group(3):
        fr = int(m.group(3)) / max(1, int(m.group(4)))
    elif m.group(5):
        fr = int(m.group(5)) / max(1, int(m.group(6)))
    v = ft + (inch + fr + extra) / 12.0
    return v if v >= 1.0 else None


def probe(path, pno):
    pdf = pymupdf.open(path)
    page = pdf[pno - 1]
    segs = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                L = math.hypot(b.x - a.x, b.y - a.y)
                if L > 8:
                    segs.append((a.x, a.y, b.x, b.y, L))
    ratios = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            txt = "".join(s["text"] for s in l["spans"]).strip()
            v = parse_ft(txt)
            if v is None:
                continue
            dx, dy = l["dir"]
            x0, y0, x1, y1 = l["bbox"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            h = min(x1 - x0, y1 - y0) if abs(dx) < 0.5 or abs(dy) < 0.5 else 8
            best = None
            for s in segs:
                ux, uy = (s[2] - s[0]) / s[4], (s[3] - s[1]) / s[4]
                if abs(ux * dx + uy * dy) < 0.995:
                    continue
                # perpendicular distance of text centre to the line, and along-line position
                px, py = cx - s[0], cy - s[1]
                t = px * ux + py * uy
                d = abs(px * -uy + py * ux)
                if d > 2.5 * h or t < 0 or t > s[4]:
                    continue
                if abs(t - s[4] / 2) > 0.35 * s[4] + 4:
                    continue
                if best is None or d < best[0]:
                    best = (d, s[4])
            if best:
                ratios.append((best[1] / v, txt, round(best[1], 1)))
    return ratios


if __name__ == "__main__":
    r = probe(sys.argv[1], int(sys.argv[2]))
    hist = collections.Counter(round(x[0], 1) for x in r)
    print(len(r), hist.most_common(8))
    for x in r[:15]:
        print(x)
