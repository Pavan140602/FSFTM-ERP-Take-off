from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding='utf-8')
a = """        for x, y in ((s[0], s[1]), (s[2], s[3])):
            t = ux * x + uy * y - c_u
            if abs(t) > half + 2.0:
                out.append((x, y))
    return out"""
b = """        if s[4] > 8.0 * max(half, 1.0):
            continue  # a long member line, not a callout's leader
        # The text often fills the whole leader: its ends are where it points.
        out.extend([(s[0], s[1]), (s[2], s[3])])
    return out"""
assert s.count(a) == 1
s = s.replace(a, b)
a = """        if s[4] < 1.2 * half or _adiff(_ang(s), lab.angle) > 5.0:"""
b = """        if s[4] < 0.8 * half or _adiff(_ang(s), lab.angle) > 5.0:"""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('ok')
