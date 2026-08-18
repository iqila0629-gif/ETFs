import csv, pathlib
from collections import Counter
base = pathlib.Path(r'C:\Users\vanessacen\Desktop\新基金预测\01_数据')

def load(p):
    with open(base/p, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

print('== eip_master_status.csv ==')
ms = load('eip_master_status.csv')
print(Counter(r['status'] for r in ms))

print('== eip_api_download_log.csv ==')
log = load('eip_api_download_log.csv')
print(Counter(r['status'] for r in log))
print('--- OK symbols ---')
for r in log:
    if r['status']=='OK':
        print(' ', r['name'], '->', r['symbol'], r['rows'], r['first'], r['last'])
print('--- NOT_FOUND ---')
for r in log:
    if r['status']=='NOT_FOUND':
        print(' ', r['name'], '|', r['note'])
print('--- PENDING ---')
for r in log:
    if r['status']=='PENDING':
        print(' ', r['name'])

print('== api_download files ==')
files = sorted(p.name for p in (base/'api_download').glob('*.csv'))
print(len(files), 'files')
for f in files: print(' ', f)

print('== investing coverage ==')
cov = load('eip_investing_coverage.csv')
print(Counter(r['investing_status'] for r in cov))