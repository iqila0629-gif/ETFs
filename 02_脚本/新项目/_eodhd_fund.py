import json, sys, urllib.request

keys = json.load(open(r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\api_keys.json', encoding='utf-8'))
eodhd_list = keys.get('eodhd_list', [])

def fund(symbol, key):
    u = f'https://eodhd.com/api/fundamentals/{symbol}?api_token={key}&fmt=json'
    try:
        with urllib.request.urlopen(u, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

for sym in sys.argv[1:]:
    print('===== FUNDAMENTALS:', sym)
    ok = False
    for key in eodhd_list:
        d = fund(sym, key)
        if isinstance(d, dict) and 'error' not in d and d.get('General'):
            g = d.get('General', {})
            print('  Name:', g.get('Name'))
            print('  ISIN:', g.get('ISIN'))
            print('  CUSIP:', g.get('CUSIP'))
            print('  Currency:', g.get('Currency'))
            print('  Type:', g.get('Type'))
            print('  Exchange:', g.get('Exchange'))
            print('  Fund_Type:', g.get('Fund_Type'))
            ok = True
            break
        else:
            print('  key', key[:12], '->', (d.get('error') if isinstance(d, dict) else d)[:120] if isinstance(d, dict) else str(d)[:120])
    if not ok:
        print('  NOT resolved')