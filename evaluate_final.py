#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
from collections import Counter
from datetime import datetime

DATA = Path("data")

def read_jsonl(p: Path):
    if not p.exists(): return []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line: yield json.loads(line)

def tok(s): 
    return re.findall(r"\w+", (s or "").lower())

def f1(a, b):
    if not a and not b: return 1.0
    if not a or not b:  return 0.0
    A, B = Counter(a), Counter(b)
    inter = sum((A & B).values())
    prec  = inter / max(1, sum(A.values()))
    rec   = inter / max(1, sum(B.values()))
    return 0.0 if prec+rec == 0 else 2*prec*rec/(prec+rec)

def extraction_report(pred_path, label_path):
    preds, labels = list(read_jsonl(pred_path)), list(read_jsonl(label_path))
    n = min(len(preds), len(labels))
    if n == 0: return {"n": 0}
    acc_task = acc_due = acc_src = 0; f1_task_sum = 0.0
    for i in range(n):
        p, g = preds[i], labels[i]
        acc_task += int((p.get("task") or "").strip() == (g.get("task") or "").strip())
        acc_due  += int((p.get("due_time") or "") == (g.get("due_time") or ""))
        acc_src  += int((p.get("source") or "") == (g.get("source") or ""))
        f1_task_sum += f1(tok(p.get("task")), tok(g.get("task")))
    return {
        "n": n,
        "acc_task": round(acc_task/n,3),
        "acc_due": round(acc_due/n,3),
        "acc_source": round(acc_src/n,3),
        "f1_task": round(f1_task_sum/n,3)
    }

def to_dt(s): 
    return datetime.fromisoformat((s or "").replace("Z","+00:00"))

def planning_report(plan_path, calendar_path):
    def minutes_overlap(a,b):
        s=max(a[0],b[0]); e=min(a[1],b[1]); return max(0,int((e-s).total_seconds()//60))
    def minutes_union(a,b):
        s=min(a[0],b[0]); e=max(a[1],b[1]); return max(1,int((e-s).total_seconds()//60))

    plans = list(read_jsonl(plan_path))
    if not Path(calendar_path).exists(): return {"days": 0}

    gold = {}
    for e in json.loads(Path(calendar_path).read_text(encoding="utf-8")):
        s = (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date")
        en= (e.get("end")   or {}).get("dateTime") or (e.get("end")   or {}).get("date")
        if not s: continue
        sd = to_dt(s if "T" in s else s+"T09:00:00")
        ed = to_dt(en if en and "T" in en else (en+"T10:00:00" if en else s+"T10:00:00"))
        gold.setdefault(sd.date().isoformat(), []).append((sd, ed))

    by_day=[]
    for rec in plans:
        day = rec["date"]
        pred_events = [(to_dt(p["start"]), to_dt(p["end"])) for p in rec["plan"] if p["type"]=="event"]
        tasks = [p for p in rec["plan"] if p["type"]=="task"]
        gold_events = gold.get(day, [])
        if not gold_events or not pred_events:
            by_day.append({"day":day, "event_overlap": None, "tasks_scheduled": len(tasks)})
            continue
        ious=[]
        for g in gold_events:
            best=0
            for pr in pred_events:
                inter=minutes_overlap(g,pr); uni=minutes_union(g,pr)
                best=max(best, inter/uni)
            ious.append(best)
        by_day.append({"day":day, "event_overlap": round(sum(ious)/len(ious),3), "tasks_scheduled": len(tasks)})
    return {"days": len(by_day), "by_day": by_day}

def main():
    report = {
        "extraction_heuristic": extraction_report(DATA/"tasks_pred.jsonl", DATA/"labels.jsonl"),
        "extraction_llm":       extraction_report(DATA/"tasks_pred_llm.jsonl", DATA/"labels.jsonl"),
        "planning":             planning_report(DATA/"daily_plan_pred.jsonl", DATA/"calendar_sample.json")
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
