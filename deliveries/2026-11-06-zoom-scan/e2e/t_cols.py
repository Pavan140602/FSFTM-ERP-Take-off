import sys, time; sys.path.insert(0,'.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A, detail_scan as Z
path, pno = sys.argv[1], int(sys.argv[2]); rules = sys.argv[3]=='1'; out=sys.argv[4]
pdf=pymupdf.open(path); pg=pdf[pno-1]
res=A.run_auto_takeoff(pdf,[pno],["beams","columns"],rules=rules)['pages'][0]
models,_=A.build_models(pdf,[pno],want_specs=False,rules=rules); m=models[0]
t=time.time(); ds=Z.read_sheet(pg, index_cls=A.SegIndex); print('read', round(time.time()-t,2),'s shapes',len(ds.shapes),'segs',len(ds.segs))
found=[{'point':tuple(it['points'][0])} for it in res['items'] if it['category']=='columns']
members=[(it['points'][0][0],it['points'][0][1],it['points'][-1][0],it['points'][-1][1]) for it in res['items'] if it['kind']=='line']
t=time.time()
add,rem,st=Z.scan_columns(m,ds,found,members,lambda x,y:{'designation':'?'},seeded_only=(m.kind=='foundation' and rules),col_mark_re=A._COL_MARK_RE)
print('scan',round(time.time()-t,2),'s',st, 'found before',len(found))
sh=pg.new_shape()
for i,c in enumerate(found):
    sh.draw_circle(c['point'],9); sh.finish(color=(1,0.5,0) if i in rem else (0,0.75,0),width=2.5)
for c in add:
    sh.draw_circle(c['point'],11); sh.finish(color=(0,0.3,1),width=3)
sh.commit()
pg.get_pixmap(dpi=60).save(out)
for c in add: print('add', [round(v) for v in c['point']], c['size'])
