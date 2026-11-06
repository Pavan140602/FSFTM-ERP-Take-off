import sys, collections, math; sys.path.insert(0,'.')
import pymupdf
from app.modules.takeoff import auto_takeoff as A
path, pno, out, clip, rules = sys.argv[1], int(sys.argv[2]), sys.argv[3], [float(v) for v in sys.argv[4].split(',')], sys.argv[5]=='1'
pdf=pymupdf.open(path); pg=pdf[pno-1]
r=A.run_auto_takeoff(pdf,[pno],list(A.CATEGORIES),rules=rules)['pages'][0]
walls=[it for it in r['items'] if it['category']=='walls']
upf=r['units_per_foot'] or 9
print(r['counts'], collections.Counter(it.get('segment') for it in walls), 'studs', sum(it.get('stud_count') or 0 for it in walls), 'LF', round(sum(math.dist(*it['points']) for it in walls)/upf,1))
sh=pg.new_shape()
for it in walls:
    (ax,ay),(bx,by)=it['points']; L=math.hypot(bx-ax,by-ay)
    if L<=0 or not it.get('wall_width'): continue
    ux,uy=(bx-ax)/L,(by-ay)/L; nx,ny=-uy,ux; w=it['wall_width']/2
    poly=[pymupdf.Point(ax+nx*w,ay+ny*w),pymupdf.Point(bx+nx*w,by+ny*w),pymupdf.Point(bx-nx*w,by-ny*w),pymupdf.Point(ax-nx*w,ay-ny*w)]
    hdr=it.get('segment')=='header'
    sh.draw_polyline(poly+[poly[0]]); sh.finish(color=(0.9,0.5,0) if hdr else (0.75,0.1,0.55), fill=(1,0.75,0.2) if hdr else (0.9,0.3,0.7), fill_opacity=0.3, width=0.6)
    if not hdr:
        sd=it['stud_spacing']; n=it['stud_count']
        for k in range(n):
            t=min(k*sd,L); cx,cy=ax+ux*t,ay+uy*t
            sh.draw_line(pymupdf.Point(cx+nx*w,cy+ny*w),pymupdf.Point(cx-nx*w,cy-ny*w)); sh.finish(color=(0.4,0,0.3),width=0.8)
sh.commit()
pg.get_pixmap(dpi=200,clip=pymupdf.Rect(*clip)).save(out)
for it in [w for w in walls if w.get('segment')=='header'][:3]: print('  HDR', it['designation'], it.get('header'), it['spec'][:80])
