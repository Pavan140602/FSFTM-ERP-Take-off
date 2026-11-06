import json, sys
for s in sys.argv[1:]:
    try:
        o=json.load(open(f'old_{s}.json')); n=json.load(open(f'new_{s}.json'))
    except Exception as e:
        print(s, 'missing', e); continue
    same=0
    for k in sorted(set(o)|set(n), key=lambda x:(x.split(':')[0], int(x.split(':')[1]))):
        if o.get(k)==n.get(k): same+=1; continue
        print(k, 'OLD', o.get(k)); print(' '*len(k), 'NEW', n.get(k))
    print(s, 'unchanged pages', same)
