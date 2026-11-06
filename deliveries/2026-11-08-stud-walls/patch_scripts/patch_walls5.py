from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding="utf-8")
a = """    gaps = []
    for (_lo, hi), (lo2, _hi2) in zip(merged, merged[1:]):
        g = lo2 - hi
        if 2.0 * upf <= g <= 20.0 * upf:
            gaps.append((hi, lo2))"""
b = """    gaps = []
    if merged:
        # Runs go wall to wall, so a missing face at either end is an
        # opening too (a door or window right beside a cross wall).
        edges = [(0.0, merged[0][0])] + [(hi, lo2) for (_lo, hi), (lo2, _hi2) in zip(merged, merged[1:])] + [(merged[-1][1], L)]
        for g0, g1 in edges:
            if 2.0 * upf <= g1 - g0 <= 20.0 * upf:
                gaps.append((g0, g1))"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
