import json, sys, urllib.request
B='http://localhost:8000/api'
def call(m,p,d=None,t=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(d).encode() if d is not None else None)
    r.add_header('Content-Type','application/json')
    if t: r.add_header('Authorization','Bearer '+t)
    with urllib.request.urlopen(r) as x:
        b=x.read(); return json.loads(b) if b else None
t=call('POST','/v1/users/auth/login/',{'email':sys.argv[1],'password':sys.argv[2]})['access_token']
rows=call('GET','/v1/takeoff/measurements/?project_id='+sys.argv[3],t=t)
rows=rows.get('items',rows) if isinstance(rows,dict) else rows
for r in rows:
    meta=r.get('metadata') or {}
    if meta.get('wall_height'):
        meta['wall_height']=None
        call('PATCH','/v1/takeoff/measurements/%s'%r['id'],{'metadata':meta},t=t)
        print('cleared',r['id'])
print('checked',len(rows))
