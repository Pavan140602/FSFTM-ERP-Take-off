import sys, math, collections, json, importlib.util, time
sys.path.insert(0, r'C:/Users/ishat/Downloads/OpenConstructionERP-main (2)/OpenConstructionERP-main/backend')
OLD = sys.argv[1] == 'old'
import app.modules.takeoff as PK
if OLD:
    for name in ('detail_scan', 'framing_rules', 'auto_takeoff'):
        sp = importlib.util.spec_from_file_location(f'app.modules.takeoff.{name}', f'backup_div5/{name}.py')
        mod = importlib.util.module_from_spec(sp); sys.modules[sp.name] = mod; setattr(PK, name, mod); sp.loader.exec_module(mod)
from app.modules.takeoff import auto_takeoff as A
import pymupdf
SETS = {
 'studio': (r'C:/Users/ishat/Downloads/Pages from 01) StudioRes PCB - Building Drawings.pdf', None),
 'home2': (r'C:/Users/ishat/Downloads/2026-10-22_25090 Mobile Home2Suites _STR_V25.pdf', None),
 'ac': (r'C:/Users/ishat/Downloads/2026-11-03_AC RETREAT, BY MARIOTT_STR_V25.pdf', None),
 'cfs': (r'C:/Users/ishat/OneDrive/Desktop/Pavan/CFS Standards/Structural Approval Drawings REV-014 17th April 2020.pdf', None),
}
out = {}
for key in sys.argv[3].split(','):
    path, _ = SETS[key]
    pdf = pymupdf.open(path)
    pages = list(range(1, len(pdf) + 1))
    t = time.time()
    r = A.run_auto_takeoff(pdf, pages, list(A.CATEGORIES), rules=True)
    for p in r['pages']:
        upf = p.get('units_per_foot') or 0
        c = collections.Counter(); lf = collections.Counter()
        for it in p['items']:
            k = f"{it['category']}/{it.get('role') or ''}"
            c[k] += len(it['points']) if it['kind'] == 'count' else 1
            if it['kind'] == 'line' and upf:
                lf[k] += sum(math.dist(a, b) for a, b in zip(it['points'], it['points'][1:])) / upf
        out[f"{key}:{p['page']}"] = {k: [c[k], round(lf[k])] for k in c}
    print(key, len(pages), 'pages', round(time.time() - t), 's', flush=True)
json.dump(out, open(sys.argv[2], 'w'), indent=0)
