from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff\detail_scan.py")
s = p.read_text(encoding="utf-8")
a = """        if best is None:
            # No symbol where it points: unless a column already stands at
            # one of its ends, list it for the estimator."""
b = """        if best is None:
            # A column found already at the end of the line the text is
            # written on (an I-shaped W column has no closed box): this
            # label names it.
            near_k = min(
                (
                    (math.hypot(x - ex, y - ey), k)
                    for k, (x, y) in enumerate(taken[:n_found])
                    for ex, ey, pn in ends
                    if pn == 0.0
                ),
                default=None,
            )
            if near_k is not None and near_k[0] <= 14.0:
                claims.append((lab, near_k[1]))
                continue
            # No symbol where it points: unless a column already stands at
            # one of its ends, list it for the estimator."""
assert s.count(a) == 1
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("ok")
