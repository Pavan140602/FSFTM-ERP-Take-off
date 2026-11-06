import sys, math, collections; sys.path.insert(0,'.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A, framing_rules as FR
pdf=pymupdf.open(r"C:\Users\ishat\Downloads\Pages from 01) StudioRes PCB - Building Drawings.pdf")
pages=[int(x) for x in sys.argv[1].split(',')]
res=A.run_auto_takeoff(pdf,pages,["beams","columns","joists","trusses","walls","areas","other"],rules=True)
def dist_item(x,y,it):
    p=it['points']
    if len(p)==1: return math.hypot(p[0][0]-x,p[0][1]-y)
    return A._pt_seg_dist(x,y,(p[0][0],p[0][1],p[1][0],p[1][1],1))
for r in res['pages']:
    pg=r['page']; m=A.build_page_model(pdf[pg-1],pg); A.apply_framing_rules(pdf,[m])
    upf=m.units_per_foot or 9
    miss=[]
    for l in m.labels:
        if A._in_rects(l.cx,l.cy,m.schedule_rects,4) or len(l.text)>14: continue
        ri=FR.rule_classify(l.text,(m.kind,m.level,m.fsched))
        if ri=='skip' or not isinstance(ri,dict): continue
        if ri['category'] not in FR.ALLOWED.get(m.kind,set()): continue
        des=[ri['designation']]+([ri['wall_type']] if ri.get('wall_type') else [])
        for d in des:
            same=[it for it in r['items'] if it['designation'].replace('-','')==d.replace('-','')]
            dm=min((dist_item(l.cx,l.cy,it) for it in same),default=1e9)
            if dm>4*upf: miss.append((d,round(l.cx),round(l.cy),round(dm/upf,1) if dm<1e8 else None))
    print(pg, m.kind, 'missing:', len(miss), miss[:12])
