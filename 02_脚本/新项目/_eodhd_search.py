import json, sys, urllib.request, urllib.parse

keys = json.load(open(r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\api_keys.json', encoding='utf-8'))
eodhd_list = keys.get('eodhd_list', [])

def search(q, key):
    url = 'https://eodhd.com/api/search/' + urllib.parse.quote(q) + '?api_token=' + key + '&type=fund'
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

queries = sys.argv[1:]
for q in queries:
    print('===== QUERY:', q)
    for key in eodhd_list:
        res = search(q, key)
        if isinstance(res, list) and len(res) > 0:
            print('key used:', key[:12] + '...')
            for it in res:
                print('  ', it.get('Code'), '|', it.get('Name'), '|', it.get('Exchange'), '|', it.get('Type'))
            break
        else:
            print('  key', key[:12], '->', res if isinstance(res, dict) else 'empty')