from pathlib import Path
base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend\app\modules\takeoff")
p = base / "detail_scan.py"
s = p.read_text(encoding='utf-8')
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:60])
    s = s.replace(a, b)
rep("""        if m.group(1) and m.group(2) and m.group(1) != m.group(2):
            continue  # rectangular HSS: a beam / brace size""", """        if m.group(1) and m.group(2) and m.group(1) != m.group(2):
            continue  # rectangular HSS: a beam / brace size
        if t.startswith("W") and _on_member_line(lab, ds):
            continue  # a beam size printed along its beam""")
rep("""            for sh in ds.shapes:
                if not (3.0 <= sh.w <= 30.0) or sh.aspect > 5.0:
                    continue
                if sh.filled and not sh.dark_fill and not sh.stroked:
                    continue  # text mask""", """            for sh in ds.shapes:
                if not (3.0 <= sh.w <= 20.0) or sh.aspect > 5.0:
                    continue
                if sh.filled and not sh.dark_fill and not sh.stroked:
                    continue  # text mask""")
rep("""def label_columns(""", """def _on_member_line(lab, ds: DetailSheet) -> bool:
    \"\"\"The text is printed along a long line (a beam): a member size, not
    a column callout.\"\"\"
    if ds.index is None:
        return False
    a = math.radians(lab.angle)
    ux, uy = math.cos(a), math.sin(a)
    tw = 0.55 * len(lab.text) * lab.size
    r = 2.0 * lab.size
    for j in ds.index.near(lab.cx - r, lab.cy - r, lab.cx + r, lab.cy + r):
        s = ds.segs[j]
        if s[4] < 2.6 * tw / 2.0 or _adiff(_ang(s), lab.angle) > 5.0:
            continue
        perp = abs(-(lab.cx - s[0]) * uy + (lab.cy - s[1]) * ux)
        if perp <= 1.6 * lab.size and _pt_seg(lab.cx, lab.cy, s) <= 2.0 * lab.size:
            return True
    return False


def label_columns(""")
p.write_text(s, encoding='utf-8')

p = base / "auto_takeoff.py"
s = p.read_text(encoding='utf-8')
rep("""            col_found = [c for i, c in enumerate(col_found) if i not in removed] + added
        except Exception:
            zoom_stats = {"error": True}""", """            col_found = [c for i, c in enumerate(col_found) if i not in removed] + added
            # Every column size label must have its column: follow its
            # leader (or the line it is written on) to the symbol.
            if "columns" in wanted:
                lab_cols, checked = Z.label_columns(
                    model,
                    model.detail,
                    [tuple(c["point"]) for c in col_found],
                    leader_ends=_detail_leader_ends(model),
                )
                for lc in lab_cols:
                    lab = lc["label"]
                    info = classify(lab) or {}
                    des = info.get("designation") or re.sub(r"\s+", "", lab.text.upper())
                    col_found.append({
                        "mark_obj": None,
                        "label_obj": lab,
                        "point": lc["point"],
                        "designation": des,
                        "label": des,
                        "mark": None,
                        "label_rect": list(lab.rect),
                        "size": lc["size"],
                        "zoom": True,
                    })
                zoom_stats["labels_checked"] = checked
                zoom_stats["added"] = zoom_stats.get("added", 0) + len(lab_cols)
        except Exception:
            zoom_stats = {"error": True}""")
rep("""def _column_named(""", """def _detail_leader_ends(model: PageModel):
    \"\"\"Leader ends of a callout, followed through the small pieces of the
    sheet read at full detail (also when the framing rules did not keep
    them).\"\"\"
    m2 = model
    if model.fine_index is None and model.detail is not None:
        import copy

        m2 = copy.copy(model)
        m2.fine = [s[:7] for s in model.detail.segs if s[4] >= 3.0]
        m2.fine_index = SegIndex(m2.fine)
    return lambda lab: [tip for _score, tip in leader_tips(lab, m2)]


def _column_named(""")
p.write_text(s, encoding='utf-8')
print('ok')
