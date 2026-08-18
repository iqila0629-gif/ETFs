import csv
p = r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_api_download_log.csv'
with open(p, encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
print('cols:', list(rows[0].keys()))
for r in rows:
    nm = r.get('name','')
    if 'ALLIANCE' in nm.upper() or 'AB ' in nm.upper() or nm.upper().startswith('AB'):
        print(r)