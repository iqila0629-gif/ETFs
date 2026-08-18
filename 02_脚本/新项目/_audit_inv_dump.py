import csv
p = r'C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_investing_coverage.csv'
with open(p, encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
for r in rows:
    st = r.get('investing_status','')
    if st in ('有','需核'):
        print(f"[{st}] {r['name']}")
        print(f"       search: {r['investing_search']}")
        print(f"       note:   {r['investing_note']}")