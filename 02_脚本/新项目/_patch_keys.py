# -*- coding: utf-8 -*-
import pathlib
p = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\02_脚本\新项目\eodhd_batch.py")
c = p.read_text(encoding="utf-8")

old_a = 'cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))\nEO = cfg["eodhd"]'
new_a = '''cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
KEYS = cfg["eodhd_list"]
_used = {k: 0 for k in KEYS}
_exhausted = set()

def pick_key():
    avail = [k for k in KEYS if k not in _exhausted]
    if not avail:
        return None
    return min(avail, key=lambda k: _used[k])

def mark_exhausted(k):
    _exhausted.add(k)'''
assert old_a in c, "A not found"
c = c.replace(old_a, new_a)

old_b = '''def eod_pull(symbol):
    u = f"https://eodhd.com/api/eod/{symbol}?api_token={EO}&fmt=json"
    return get(u)'''
new_b = '''def eod_pull(symbol):
    for _ in range(len(KEYS) + 1):
        k = pick_key()
        if k is None:
            return 429, "all keys exhausted"
        _used[k] += 1
        u = f"https://eodhd.com/api/eod/{symbol}?api_token={k}&fmt=json"
        st, b = get(u)
        if st in (429, 403) or "limit" in b.lower() or "daily" in b.lower():
            mark_exhausted(k)
            continue
        return st, b
    return 429, "all keys exhausted"'''
assert old_b in c, "B not found"
c = c.replace(old_b, new_b)

old_c = '''def eo_search(q):
    u = f"https://eodhd.com/api/search/{urllib.parse.quote(q)}?api_token={EO}&fmt=json"
    st, b = get(u)
    if st != 200:
        return st, []
    try:
        return st, json.loads(b)
    except Exception:
        return st, []'''
new_c = '''def eo_search(q):
    for _ in range(len(KEYS) + 1):
        k = pick_key()
        if k is None:
            return 429, []
        _used[k] += 1
        u = f"https://eodhd.com/api/search/{urllib.parse.quote(q)}?api_token={k}&fmt=json"
        st, b = get(u)
        if st in (429, 403) or "limit" in b.lower() or "daily" in b.lower():
            mark_exhausted(k)
            continue
        if st != 200:
            return st, []
        try:
            return st, json.loads(b)
        except Exception:
            return st, []
    return 429, []'''
assert old_c in c, "C not found"
c = c.replace(old_c, new_c)

p.write_text(c, encoding="utf-8")
print("patched OK, bytes:", len(c.encode("utf-8")))