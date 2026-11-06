import sys, collections, math; sys.path.insert(0, r'C:/Users/ishat/Downloads/OpenConstructionERP-main (2)/OpenConstructionERP-main/backend')
import pymupdf
from app.modules.takeoff import auto_takeoff as A
path, pno, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
clip = [float(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
dpi = int(sys.argv[5]) if len(sys.argv) > 5 else 60
pdf=pymupdf.open(path); pg=pdf[pno-1]
r=A.run_auto_takeoff(pdf,[pno],list(A.CATEGORIES),rules=True)['pages'][0]
upf=r['units_per_foot'] or 9
print('scale', r['scale'], round(upf,2), r['counts'])
g=collections.defaultdict(list)
for it in r['items']: g[(it['category'], it.get('role'), it['designation'])].append(it)
for k in sorted(g, key=str):
    ws=g[k]; L=sum(math.dist(a,b) for i in ws if i['kind']=='line' for a,b in zip(i['points'],i['points'][1:]))/upf
    print(' ', k, len(ws), round(L,1),'LF', '|', ws[0].get('profile'), ws[0].get('spacing_in') or ws[0].get('stud_spacing_in'), (ws[0].get('spec') or '')[:70])
COL={'walls':(0,0.75,0.2),'joists':(0.1,0.3,1),'trusses':(0.6,0,0.8),'beams':(1,0,0),'columns':(1,0,0),'other':(1,0.5,0),'areas':(0.9,0.9,0)}
D=pg.derotation_matrix
sh=pg.new_shape()
for it in r['items']:
    col=COL.get(it['category'],(0,0,0))
    if it.get('segment')=='header': col=(1,0.5,0)
    if it['kind']=='line':
        for (ax,ay),(bx,by) in zip(it['points'],it['points'][1:]):
            L=math.hypot(bx-ax,by-ay)
            if L<=0: continue
            ux,uy=(bx-ax)/L,(by-ay)/L; nx,ny=-uy,ux; w=max(1.0,(it.get('wall_width') or 2)/2)
            poly=[pymupdf.Point(ax+nx*w,ay+ny*w)*D,pymupdf.Point(bx+nx*w,by+ny*w)*D,pymupdf.Point(bx-nx*w,by-ny*w)*D,pymupdf.Point(ax-nx*w,ay-ny*w)*D]
            sh.draw_polyline(poly+[poly[0]]); sh.finish(color=col, fill=col, fill_opacity=0.4, width=0.3)
    elif it['kind']=='count':
        for x,y in it['points']:
            sh.draw_circle(pymupdf.Point(x,y)*D, 6); sh.finish(color=col, width=1.5)
    elif it['kind']=='area':
        pts=[pymupdf.Point(x,y)*D for x,y in it['points']]
        if len(pts)>2: sh.draw_polyline(pts+[pts[0]]); sh.finish(color=col, fill=col, fill_opacity=0.12, width=1)
sh.commit()
pg.get_pixmap(dpi=dpi, clip=pymupdf.Rect(*clip) if clip else None).save(out)
