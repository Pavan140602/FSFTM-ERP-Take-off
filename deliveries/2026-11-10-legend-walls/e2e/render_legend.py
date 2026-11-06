import sys, collections, math; sys.path.insert(0,'.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A
path, pno, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
clip = [float(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
pdf=pymupdf.open(path); pg=pdf[pno-1]
r=A.run_auto_takeoff(pdf,[pno],list(A.CATEGORIES),rules=True)['pages'][0]
walls=[it for it in r['items'] if it['category']=='walls']
upf=r['units_per_foot'] or 9
print('scale', r['scale'], round(upf,2), r['counts'])
for d in sorted(set(i['designation'] for i in walls)):
    ws=[i for i in walls if i['designation']==d]
    print(' ', d, len(ws), ws[0].get('role'), round(sum(math.dist(*i['points']) for i in ws)/upf,1),'LF', sum(i.get('stud_count') or 0 for i in ws),'studs |', ws[0].get('profile'), ws[0].get('wall_width_in'), ws[0].get('stud_spacing_in'))
sh=pg.new_shape()
for it in walls:
    (ax,ay),(bx,by)=it['points']; L=math.hypot(bx-ax,by-ay)
    if L<=0: continue
    ux,uy=(bx-ax)/L,(by-ay)/L; nx,ny=-uy,ux; w=max(1.5,(it.get('wall_width') or 3)/2)
    poly=[pymupdf.Point(ax+nx*w,ay+ny*w),pymupdf.Point(bx+nx*w,by+ny*w),pymupdf.Point(bx-nx*w,by-ny*w),pymupdf.Point(ax-nx*w,ay-ny*w)]
    hdr=it.get('segment')=='header'
    col=(1,0.5,0) if hdr else (0,0.75,0.2)
    sh.draw_polyline(poly+[poly[0]]); sh.finish(color=(0,0,0), fill=col, fill_opacity=0.45, width=0.5)
sh.commit()
pg.get_pixmap(dpi=int(sys.argv[5]) if len(sys.argv)>5 else 60, clip=pymupdf.Rect(*clip) if clip else None).save(out)
