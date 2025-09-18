# week1_collect_data.py
# 一次性拉取 Gmail / Calendar / Plaid（Sandbox）样例数据并保存为 JSON

import os
import json
import datetime as dt
from pathlib import Path
from time import sleep

from dotenv import load_dotenv

# ---------------- 通用工具 ----------------
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def save_json(obj, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)  # ← 加上 default=str
    print(f"✅ Saved -> {path} ({len(obj) if isinstance(obj, list) else 'object'})")


# ---------------- Google: Gmail ----------------
def pull_gmail(creds_path: str):
    print("▶ Pulling Gmail...")
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    token_file = "token_gmail.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token_file).write_text(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    res = service.users().messages().list(
        userId="me", maxResults=10, q="newer_than:30d"
    ).execute()

    messages = res.get("messages", [])
    out = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        out.append({
            "id": m["id"],
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
            "snippet": msg.get("snippet")
        })

    save_json(out, DATA_DIR / "gmail_sample.json")


# ---------------- Google: Calendar ----------------
def pull_calendar(creds_path: str):
    print("▶ Pulling Calendar...")
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    token_file = "token_calendar.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token_file).write_text(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    now = dt.datetime.utcnow().isoformat() + "Z"
    end = (dt.datetime.utcnow() + dt.timedelta(days=7)).isoformat() + "Z"

    events = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
        maxResults=50
    ).execute().get("items", [])

    out = [{
        "id": e.get("id"),
        "summary": e.get("summary"),
        "start": e.get("start"),
        "end": e.get("end"),
        "location": e.get("location")
    } for e in events]

    save_json(out, DATA_DIR / "calendar_sample.json")



# ---------------- 主流程 ----------------
if __name__ == "__main__":
    load_dotenv()
    creds_path = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
    assert os.path.exists(creds_path), f"找不到 {creds_path}，请把 credentials.json 放到项目根目录或设置 GOOGLE_CREDENTIALS"

    pull_gmail(creds_path)
    pull_calendar(creds_path)
    pull_plaid()

    print("🎉 All done. Check the data/ folder.")
