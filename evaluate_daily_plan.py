#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime

DATA=Path("data"); PRED=DATA/"daily_plan_pred.jsonl"

def read_jsonl(p):
    if not p.exists(): return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def dt(s): return datetime.fromisoformat(s.replace("Z","+00:00"))

def gold_events():
    p=DATA/"calendar_sample.json"
    if not p.exists(): return {}
    by={}
    for e in json.loads(p.read_text(encoding="utf-8")):
        s=(e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date")
        en=(e.get("end")   or {}).get("dateTime") or (e.get("end")   or {}).get("date")
        if not s: continue
        sd=dt(s if "T" in s else s+"T09:00:00")
        ed=dt(en if en and "T" in en else (en+"T10:00:00" if en else s+"T10:00:00"))
        by.setdefault(sd.date().isoformat(), []).append((sd,ed))
    return by

def inter(a,b): 
    s=max(a[0],b[0]); e=min(a[1],b[1]); 
    return max(0,int((e-s).total_seconds()//60))
def uni(a,b):
    s=min(a[0],b[0]); e=max(a[1],b[1]); 
    return max(1,int((e-s).total_seconds()//60))

def main():
    gold=gold_events(); preds=read_jsonl(PRED)
    if not preds: 
        print("No predictions."); return
    for rec in preds:
        day=rec["date"]
        pred_e=[(dt(p["start"]),dt(p["end"])) for p in rec["plan"] if p["type"]=="event"]
        g=gold.get(day,[])
        if not g or not pred_e:
            print(f"{day}: No events to compare (gold={len(g)}, pred={len(pred_e)})"); 
            continue
        ious=[]
        for ge in g:
            best=0
            for pr in pred_e:
                best=max(best, inter(ge,pr)/uni(ge,pr))
            ious.append(best)
        tasks=sum(1 for p in rec["plan"] if p["type"]=="task")
        print(f"{day}: EventOverlap={sum(ious)/len(ious):.3f} | TasksScheduled={tasks}")
    print("✅ Done.")

if __name__=="__main__":
    main()
