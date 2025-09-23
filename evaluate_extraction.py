#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare predictions vs manual labels on a per-field basis.
Inputs:
  - data/tasks_pred.jsonl (predictions)
  - data/labels.jsonl      (manual labels)

Metrics:
  - Exact-match accuracy per field
  - Token-level F1 for 'task' field
  - Coverage: % of records with any non-null extraction
"""
import json, re
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")
PRED_PATH = DATA_DIR / "tasks_pred.jsonl"
LABEL_PATH = DATA_DIR / "labels.jsonl"

def read_jsonl(p: Path):
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def tokenize(s):
    if s is None:
        return []
    return re.findall(r"\w+", s.lower())

def f1(a_tokens, b_tokens):
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    a = Counter(a_tokens); b = Counter(b_tokens)
    inter = sum((a & b).values())
    prec = inter / max(1, sum(a.values()))
    rec  = inter / max(1, sum(b.values()))
    if prec+rec == 0:
        return 0.0
    return 2*prec*rec/(prec+rec)

def main():
    preds  = list(read_jsonl(PRED_PATH))
    labels = list(read_jsonl(LABEL_PATH))
    n = min(len(preds), len(labels))
    if n == 0:
        print("No overlapping predictions/labels. Make sure both files exist with same record order.")
        return
    acc_task = 0; acc_due = 0; acc_src = 0
    f1_task_sum = 0.0
    covered = 0
    for i in range(n):
        p = preds[i]; g = labels[i]
        acc_task += int((p.get("task") or "").strip() == (g.get("task") or "").strip())
        acc_due  += int((p.get("due_time") or "") == (g.get("due_time") or ""))
        acc_src  += int((p.get("source") or "") == (g.get("source") or ""))
        f1_task_sum += f1(tokenize(p.get("task")), tokenize(g.get("task")))
        if p.get("task") or p.get("due_time"):
            covered += 1
    print(f"Records compared: {n}")
    print(f"Exact Acc - task: {acc_task/n:.3f}, due_time: {acc_due/n:.3f}, source: {acc_src/n:.3f}")
    print(f"Token F1 (task): {f1_task_sum/n:.3f}")
    print(f"Coverage: {covered/n:.3f}")

if __name__ == "__main__":
    main()
