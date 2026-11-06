# Undo the test-run edits on the QA beam (label, styles) so the QA data is as before.
import json
import sys
import urllib.request

BASE = 'http://localhost:8000/api'
email, pw, project, doc = sys.argv[1:5]


def call(method, path, data=None, tok=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(data).encode() if data is not None else None)
    req.add_header('Content-Type', 'application/json')
    if tok:
        req.add_header('Authorization', 'Bearer ' + tok)
    with urllib.request.urlopen(req) as r:
        body = r.read()
        return json.loads(body) if body else None


tok = call('POST', '/v1/users/auth/login/', {'email': email, 'password': pw})['access_token']
rows = call('GET', '/v1/takeoff/measurements/?project_id=%s' % project, tok=tok)
rows = rows.get('items', rows) if isinstance(rows, dict) else rows
fixed = 0
for r in rows:
    if str(r.get('document_id')) != doc:
        continue
    meta = dict(r.get('metadata') or r.get('metadata_') or {})
    cf = dict(meta.get('custom_fields') or {})
    dirty = False
    if cf.get('Subject') == 'B-101 test':
        cf['Subject'] = 'Beam'
        meta['custom_fields'] = cf
        dirty = True
    if meta.get('label_style'):
        meta['label_style'] = None
        dirty = True
    for k, v in (('line_style', None), ('stroke_width', None), ('stroke_alpha', None)):
        if meta.get(k) is not None and meta.get('label_style', 1) is None:
            meta[k] = v
    ann = r.get('annotation')
    patch = {'metadata': meta}
    if ann == 'B-101 test':
        auto = meta.get('auto_takeoff') or {}
        patch['annotation'] = auto.get('des') or 'W12X26'
        dirty = True
    if dirty:
        call('PATCH', '/v1/takeoff/measurements/%s' % r['id'], patch, tok=tok)
        fixed += 1
        print('restored', r['id'], patch.get('annotation'), list(meta.keys())[:6])
print('fixed', fixed, 'of', len(rows))
