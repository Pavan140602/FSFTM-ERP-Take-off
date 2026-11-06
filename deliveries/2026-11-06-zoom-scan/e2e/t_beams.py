import sys, time; sys.path.insert(0, '.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A, detail_scan as Z

path, pno, out, clip = sys.argv[1], int(sys.argv[2]), sys.argv[3], [float(v) for v in sys.argv[4].split(',')]
pdf = pymupdf.open(path)
pg = pdf[pno - 1]
res = A.run_auto_takeoff(pdf, [pno], ["beams", "columns"])['pages'][0]
m = A.build_page_model(pg, pno)
cols = [(it['points'][0][0], it['points'][0][1], 12.0) for it in res['items'] if it['category'] == 'columns']
labs = [(l, i) for l, i in A.labels_by_category(m).get('beams', [])]
t = time.time()
new, st = Z.scan_beams(m, m.detail, labs, res['items'], cols)
print('scan', round(time.time() - t, 2), st)
for e in new:
    print(e['designation'], len(e['points']), round(Z.poly_len(e['points'])), [tuple(round(v) for v in p) for p in (e['points'][0], e['points'][-1])])
sh = pg.new_shape()
for it in res['items']:
    if it['kind'] == 'line':
        sh.draw_polyline(it['points']); sh.finish(color=(1, 0, 1), width=2.5, stroke_opacity=0.5, closePath=False)
    else:
        sh.draw_circle(it['points'][0], 8); sh.finish(color=(0, 0.7, 0), width=2)
for e in new:
    sh.draw_polyline(e['points']); sh.finish(color=(0, 0.5, 1) if not e["unlabeled"] else (1, 0.5, 0), width=3.5, stroke_opacity=0.8, closePath=False)
sh.commit()
pg.get_pixmap(dpi=110, clip=pymupdf.Rect(*clip)).save(out)
