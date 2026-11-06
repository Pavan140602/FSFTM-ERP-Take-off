import sys, math; sys.path.insert(0,'.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A
path=sys.argv[1]; pages=[int(x) for x in sys.argv[2].split(',')]
pdf=pymupdf.open(path)
res=A.run_auto_takeoff(pdf,pages,["beams","columns"])
for r in res['pages']:
    m=A.build_page_model(pdf[r['page']-1], r['page'])
    beams=[it for it in r['items'] if it['category']=='beams']
    labs=A.labels_by_category(m).get('beams',[])
    miss=[]
    for lab,info in labs:
        d=min((A._pt_seg_dist(lab.cx,lab.cy,(it['points'][0][0],it['points'][0][1],it['points'][-1][0],it['points'][-1][1],1)) for it in beams if it['designation']==info['designation']), default=1e9)
        if d>3*lab.size: miss.append((info['designation'], round(lab.cx), round(lab.cy), round(lab.angle), round(d) if d<1e8 else None))
    print(r['page'], 'beam labels', len(labs), 'beams', len(beams), 'labels without beam', len(miss))
    for x in miss: print('   ', x)
