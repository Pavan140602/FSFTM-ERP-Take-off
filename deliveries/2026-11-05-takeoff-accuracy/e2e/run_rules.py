import sys, time, json, collections
sys.path.insert(0, ".")
import pymupdf
from app.modules.takeoff import auto_takeoff as A

path = r"C:\Users\ishat\Downloads\Pages from 01) StudioRes PCB - Building Drawings.pdf"
pages = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [3, 4, 7, 8, 9]
pdf = pymupdf.open(path)
t = time.time()
res = A.run_auto_takeoff(pdf, pages, ["beams", "columns", "joists", "trusses", "walls", "areas", "other"], rules=True)
print("secs", round(time.time() - t, 1))
print("read", json.dumps(res["read"])[:900])
for pg in res["pages"]:
    print("\n== page", pg["page"], pg.get("sheet_kind"), pg.get("level"), pg["counts"], pg.get("note"))
    by = collections.Counter()
    sample = {}
    for it in pg["items"]:
        k = (it["category"], it.get("role"), it["designation"], it.get("profile"), it.get("level"), it.get("height_ft"))
        by[k] += 1
        sample.setdefault(k, it.get("spec"))
    for k, n in sorted(by.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][2]))):
        print("  ", n, k, "|", (sample[k] or "")[:90])
