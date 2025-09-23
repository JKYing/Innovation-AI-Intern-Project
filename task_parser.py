#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 2 — Task Extraction Parser
Reads JSON exports from Week 1 and produces:
  - data/tasks_pred.jsonl  (one JSON per line; fields: task, due_time, source, context, meta)

Heuristics:
  - From email subject/body snippets, look for verbs like "submit", "review", "schedule", "call", "meet", "pay"
  - Extract due/when phrases using simple regexes (today, tomorrow, dates like 2025-09-30, Oct 3, 3pm, 15:00, 'by Friday')
  - Source = "gmail" or "calendar"
  - Context keeps the raw text for traceability
This is intentionally lightweight so you can compare vs GPT outputs later.
"""
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser as dateparser

DATA_DIR = Path("data")
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True, parents=True)

# --- Basic patterns ---
DATE_PAT = re.compile(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?)\b", re.I)
TIME_PAT = re.compile(r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|noon|midnight)\b", re.I)
REL_PAT  = re.compile(r"\b(today|tomorrow|tmrw|next\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|week)|by\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|EOD|end of day|Friday)|by\s+[\w/:-]+)\b", re.I)

# Task-like verbs / phrases
TASK_CUES = re.compile(r"\b(submit|review|respond|reply|schedule|call|meet|pay|send|prepare|draft|finish|complete|follow\s*up|confirm|share|update|fix|deploy|ship|present)\b", re.I)

def normalize_due(text, ref=None):
    """
    Try to parse a due/when from text.
    Returns ISO8601 datetime string if datetime found, else None.
    """
    if not text:
        return None
    ref = ref or datetime.now()
    # quick hits: explicit date/time combo in the same window
    try:
        dt = dateparser.parse(text, default=ref, fuzzy=True)
        # Heuristic: if text is too generic, dateparser may just return 'now'; guard against that
        if dt and (DATE_PAT.search(text) or TIME_PAT.search(text) or REL_PAT.search(text)):
            return dt.isoformat()
    except Exception:
        pass
    # fallbacks: look for date or relative expressions then time
    m_date = DATE_PAT.search(text) or REL_PAT.search(text)
    m_time = TIME_PAT.search(text)
    if m_date or m_time:
        join_txt = " ".join(x.group(0) for x in [m_date, m_time] if x)
        try:
            dt2 = dateparser.parse(join_txt, default=ref, fuzzy=True)
            if dt2:
                return dt2.isoformat()
        except Exception:
            return None
    return None

def guess_task(text):
    """
    Return a short imperative-like task if cues appear.
    """
    if not text:
        return None
    m = TASK_CUES.search(text)
    if not m:
        return None
    cue = m.group(0).lower()
    # naive transformation: take +/- few words around cue
    tokens = re.findall(r"\w+|\S", text)
    idxs = [i for i,t in enumerate(tokens) if cue in t.lower()]
    if idxs:
        i = idxs[0]
        lo = max(0, i-3); hi = min(len(tokens), i+12)
        phrase = " ".join(tokens[lo:hi])
        # clean minor artifacts
        phrase = re.sub(r"\s+", " ", phrase).strip(" ,.;:-")
        return phrase
    return None

def load_json_if_exists(path: Path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def iter_gmail():
    gmail = load_json_if_exists(DATA_DIR / "gmail_sample.json")
    for g in gmail:
        src = "gmail"
        subject = (g.get("subject") or "").strip()
        snippet = (g.get("snippet") or "").strip()
        context = f"Subject: {subject}\nSnippet: {snippet}\nFrom: {g.get('from')}\nDate: {g.get('date')}"
        yield {
            "source": src,
            "context": context,
            "primary_text": " ".join([subject, snippet]).strip(),
            "meta": {"id": g.get("id"), "from": g.get("from"), "date": g.get("date")}
        }

def iter_calendar():
    cal = load_json_if_exists(DATA_DIR / "calendar_sample.json")
    for e in cal:
        src = "calendar"
        summary = (e.get("summary") or "").strip()
        # flatten start info
        start = e.get("start") or {}
        start_iso = start.get("dateTime") or start.get("date") or None
        context = f"Summary: {summary}\nStart: {start_iso}\nEnd: {(e.get('end') or {}).get('dateTime') or (e.get('end') or {}).get('date')}\nLocation: {e.get('location')}"
        yield {
            "source": src,
            "context": context,
            "primary_text": summary,
            "meta": {"id": e.get("id"), "start": start_iso}
        }

def main():
    out_path = OUT_DIR / "tasks_pred.jsonl"
    n = 0
    with open(out_path, "w", encoding="utf-8") as w:
        for item in list(iter_gmail()) + list(iter_calendar()):
            text = item["primary_text"]
            task = guess_task(text) or (text[:120] if text else None)
            due = normalize_due(text) or normalize_due(item.get("context", "")) or item["meta"].get("start")
            rec = {
                "task": task,
                "due_time": due,
                "source": item["source"],
                "context": item["context"],
                "meta": item["meta"]
            }
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"✅ Wrote {n} lines -> {out_path}")

if __name__ == "__main__":
    main()
