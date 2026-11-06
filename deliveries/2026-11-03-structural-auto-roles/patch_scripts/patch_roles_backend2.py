# OE-DELIVERY 2026-11-03-auto-takeoff-roles (tuning): plain "metal stud wall" schedules are
# partitions; header / jamb tags need a schedule row or repeats even when a line is found.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:150])
        sys.exit(1)
    s = s.replace(old, new)


rep('''    if _LB_RE.search(text):
        return "Load Bearing Wall"
    t = tag.upper()''', '''    if _LB_RE.search(text):
        return "Load Bearing Wall"
    # A wall type described only as a stud / partition wall (architectural
    # wall types) is a partition unless something says it carries load.
    if re.search(r"METAL\\s+STUD\\s+WALL|STUD\\s+PARTITION|GYP|DRYWALL|FURRING", text, re.IGNORECASE):
        return "Non-Load Bearing Wall"
    t = tag.upper()''')
rep('''    tag_marks: list[tuple[Label, dict[str, Any]]] = []''', '''    tag_marks: list[tuple[Label, dict[str, Any]]] = []
    # Header / jamb tags: a lone tag with no schedule row is more likely a
    # detail or hold-down mark than a header.
    hj_count: dict[str, int] = {}
    for _lab, _info in labels_by_cat.get("other", []):
        if _info.get("tag") and _info.get("role") in ("Header", "Jamb"):
            hj_count[_info["designation"]] = hj_count.get(_info["designation"], 0) + 1''')
rep('''            if info.get("series") or id(lab) in used_by_columns:
                continue
            seed = _member_seed(lab, model, strict=bool(info.get("tag")))''', '''            if info.get("series") or id(lab) in used_by_columns:
                continue
            if (
                info.get("tag")
                and info.get("role") in ("Header", "Jamb")
                and not (specs or {}).get(info["designation"])
                and hj_count.get(info["designation"], 0) < 2
            ):
                continue
            seed = _member_seed(lab, model, strict=bool(info.get("tag")))''')
P.write_text(s, encoding='utf-8')
print('ok')
