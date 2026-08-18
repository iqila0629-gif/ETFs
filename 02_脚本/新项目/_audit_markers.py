import csv, re

cov_p = r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_investing_coverage.csv'
log_p = r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_api_download_log.csv'

with open(cov_p, encoding='utf-8-sig') as f:
    cov = list(csv.DictReader(f))
with open(log_p, encoding='utf-8-sig') as f:
    log = list(csv.DictReader(f))
logmap = {r['name']: r for r in log}

MARK = re.compile(r'\b(ACC|ACCUMULATION|AC|CAP|INC|INCOME|DIS|DIST|MDIS|QDIS)\b', re.I)

def markers(s):
    if not s: return []
    return [m.group(0).upper() for m in MARK.finditer(s)]

print(f"{'fund name':<58} {'nameMark':<14} {'status':<5} {'searchMark':<18} {'eodhd->symbol':<28}")
print('-'*130)
for r in cov:
    if r.get('investing_status','') not in ('有','需核'):
        continue
    nm = r['name']
    nmk = markers(nm)
    smk = markers(r.get('investing_search',''))
    eod = logmap.get(nm,{})
    sym = eod.get('symbol','')
    print(f"{nm:<58} {','.join(nmk):<14} {r['investing_status']:<5} {','.join(smk):<18} {sym:<28} | {r.get('investing_note','')[:60]}")