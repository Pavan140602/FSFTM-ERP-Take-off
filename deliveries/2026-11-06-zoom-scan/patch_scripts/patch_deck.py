from pathlib import Path
import os

os.chdir(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
SP = r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad"
p = Path('detail_scan.py')
s = p.read_text(encoding='utf-8')
if 'def deck_legend' not in s:
    s += Path(SP, 'deck_legend_part.py').read_text(encoding='utf-8')
    p.write_text(s, encoding='utf-8')

p = Path('auto_takeoff.py')
s = p.read_text(encoding='utf-8')


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('''            d_added = 0
            for lab, info in labels_by_cat.get("areas", []):
                if info.get("role") != "Deck":
                    continue
                if any(''', '''            d_added = 0
            # Deck tags keyed to a deck legend (AD / BD / CD ...): each tag
            # on the plan marks the bay that gets that deck.
            legend_tags, legend_boxes = Z.deck_legend(model, deck_info)
            deck_labs: list[tuple[Label, dict[str, Any]]] = []
            for lab, info in labels_by_cat.get("areas", []):
                if info.get("role") == "Deck" and not _in_rects(lab.cx, lab.cy, legend_boxes, 2):
                    deck_labs.append((lab, info))
            if legend_tags:
                for lab in model.labels:
                    t = "".join(lab.text.split()).upper()
                    if t in legend_tags and not _in_rects(lab.cx, lab.cy, legend_boxes, 2) and not _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
                        info = dict(legend_tags[t])
                        info["designation"] = f"{t} - {info['designation']}"
                        deck_labs.append((lab, info))
            zoom_stats = zoom_stats or {}
            zoom_stats["deck_legend"] = sorted(legend_tags)
            model_deck_legend = legend_boxes
            for lab, info in deck_labs:
                if any(''')
rep('''                    "spec": lab.text,
                    "points": [[_r(x), _r(y)] for x, y in poly],
                    "anchor": [_r(lab.cx), _r(lab.cy)],
                    "label_rect": [_r(v) for v in lab.rect],
                    "label_quad": label_quad(lab),
                    "page": p,
                    "series": None,
                    "index": None,
                    "generated": False,
                    "confidence": 0.55,''', '''                    "spec": info.get("legend_text") or lab.text,
                    "points": [[_r(x), _r(y)] for x, y in poly],
                    "anchor": [_r(lab.cx), _r(lab.cy)],
                    "label_rect": [_r(v) for v in lab.rect],
                    "label_quad": label_quad(lab),
                    "page": p,
                    "series": None,
                    "index": None,
                    "generated": False,
                    "confidence": 0.55,''')
# legend boxes excluded from missed: keep them on the model for generic_missed
rep('''            model_deck_legend = legend_boxes
''', '''            model.schedule_rects = list(model.schedule_rects) + [b for b in legend_boxes if b not in model.schedule_rects]
''')
rep('''        for lab, info in labels_by_cat.get(cat, []):
            if id(lab) in used_by_columns:
                continue
            if cat == "areas" and info.get("role") != "Deck":
                continue''', '''        for lab, info in labels_by_cat.get(cat, []):
            if id(lab) in used_by_columns or _in_rects(lab.cx, lab.cy, model.schedule_rects, 4):
                continue
            if cat == "areas" and info.get("role") != "Deck":
                continue''')
p.write_text(s, encoding='utf-8')
print('ok')
