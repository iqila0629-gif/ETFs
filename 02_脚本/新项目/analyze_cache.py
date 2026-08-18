# -*- coding: utf-8 -*-
import json, pathlib, re
cache = json.loads(pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_yahoo_search_cache.json").read_text(encoding="utf-8"))
print("names in cache:", len(cache))
hits_dist = {}
for nm, v in cache.items():
    n = len(v["hits"])
    hits_dist[n] = hits_dist.get(n, 0) + 1
print("hits distribution:", dict(sorted(hits_dist.items())))
shown = 0
for nm, v in cache.items():
    if v["hits"] and shown < 12:
        shown += 1
        print("\nNAME:", nm[:65])
        print("  q_used:", v["query_used"][:75])
        for h in v["hits"][:4]:
            print("   ", h["symbol"], "|", (h["shortname"] or "")[:55], "|", h["exch"], "|", h["type"])