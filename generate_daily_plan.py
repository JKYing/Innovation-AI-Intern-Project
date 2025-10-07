#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime, timedelta

DATA = Path("data")
OUT  = DATA / "daily_plan_pred.jsonl"
OUT.parent.mkdir(exist_ok=True, parents=True)

def read_calendar(p=DATA/"calendar_sample.json"):
    evts=[]
    if p.exists():
        for e in json.loads(p.read_text(encoding="utf-8")):
            s=(e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date")
            en=(e.get("end")   or {}).get("dateTime") or (e.get("end")   or {}).get("date")
            if not s: continue
            evts.append({"start":s,"end":en or s,"item":(e.get("summary") or "Event"),"type":"event","priority":"None"})
    return evts

def read_tasks():
    p = DATA/"tasks_pred_llm.jsonl"
    if not p.exists(): p = DATA/"tasks_pred.jsonl"
    tasks=[]
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try: j=json.loads(line)
            except: continue
            name=(j.get("task") or "Task").strip()
            lo=name.lower()
            dur=60 if any(k in lo for k in["submit","present","deadline","final"]) else 45 if any(k in lo for k in["read","check","review"]) else 30
            pri="High" if any(k in lo for k in["urgent","by ","due","submit","deadline"]) else "Low" if any(k in lo for k in["optional","later","someday"]) else "Medium"
            tasks.append({"name":name,"duration":dur,"priority":pri})
    return tasks

def to_dt(s,defdate=None):
    try: return datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except: 
        try: return datetime.fromisoformat((s or "")+"T09:00:00")
        except: return defdate

def group_by_date(events):
    by={}
    for e in events:
        sd=to_dt(e["start"]); ed=to_dt(e["end"],sd)
        if not sd: continue
        d=sd.date().isoformat()
        by.setdefault(d,[]).append({**e,"start_dt":sd,"end_dt":ed})
    for d in by: by[d].sort(key=lambda x:x["start_dt"])
    return by

def schedule_day(day, evts, tasks, start=8, end=20, pad=15):
    tasks=sorted(tasks, key=lambda t: {"High":0,"Medium":1,"Low":2}.get(t["priority"],1))
    day_start=datetime.fromisoformat(f"{day}T{start:02d}:00:00")
    day_end  =datetime.fromisoformat(f"{day}T{end:02d}:00:00")
    blocks=[{"start":e["start_dt"],"end":e["end_dt"],"item":e["item"],"type":"event","priority":"None"} for e in evts]
    blocks+=[{"start":day_start,"end":day_start,"item":"_start","type":"sentinel","priority":"None"},
             {"start":day_end,"end":day_end,"item":"_end","type":"sentinel","priority":"None"}]
    blocks.sort(key=lambda x:x["start"])
    plan=[b for b in blocks if b["type"]=="event"]
    for i in range(len(blocks)-1):
        gap_start=blocks[i]["end"]+timedelta(minutes=pad)
        gap_end  =blocks[i+1]["start"]-timedelta(minutes=pad)
        if gap_end<=gap_start: continue
        avail=(gap_end-gap_start).total_seconds()/60
        j=0
        while j<len(tasks) and avail>=15:
            t=tasks[j]
            if avail<t["duration"]: j+=1; continue
            plan.append({"start":gap_start,"end":gap_start+timedelta(minutes=t["duration"]),
                         "item":t["name"],"type":"task","priority":t["priority"]})
            gap_start+=timedelta(minutes=t["duration"]+pad)
            avail=(gap_end-gap_start).total_seconds()/60
            tasks.pop(j)
    plan.sort(key=lambda x:x["start"])
    for p in plan: p.update(start=p["start"].isoformat(), end=p["end"].isoformat())
    return {"date":day,"plan":plan,"meta":{"source":"heuristic"}}

def main():
    evts=read_calendar(); tasks=read_tasks(); by=group_by_date(evts)
    if not by: by[datetime.now().date().isoformat()]=[]
    with OUT.open("w",encoding="utf-8") as w:
        for day in sorted(by): w.write(json.dumps(schedule_day(day,by[day],tasks))+"\n")
    print(f"✅ wrote {OUT}")

if __name__=="__main__":
    main()
