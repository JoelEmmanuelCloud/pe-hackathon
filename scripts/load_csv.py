import csv
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.database import database_proxy, get_db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event
from peewee import chunked

db = get_db()
database_proxy.initialize(db)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

if len(sys.argv) > 1:
    DATA_DIR = sys.argv[1]


def parse_dt(s):
    if not s:
        return datetime.now()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return datetime.now()


def load_users(filepath):
    print(f"Loading users from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with db.atomic():
        for batch in chunked(rows, 100):
            data = [
                {
                    "id": int(r["id"]),
                    "username": r["username"],
                    "email": r["email"],
                    "created_at": parse_dt(r["created_at"]),
                }
                for r in batch
            ]
            User.insert_many(data).on_conflict_ignore().execute()
    print(f"  Loaded {len(rows)} users.")


def load_urls(filepath):
    print(f"Loading URLs from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with db.atomic():
        for batch in chunked(rows, 100):
            data = [
                {
                    "id": int(r["id"]),
                    "user_id": int(r["user_id"]) if r.get("user_id") else None,
                    "short_code": r["short_code"],
                    "original_url": r["original_url"],
                    "title": r.get("title", ""),
                    "is_active": r.get("is_active", "True").strip().lower() in ("true", "1", "yes"),
                    "created_at": parse_dt(r["created_at"]),
                    "updated_at": parse_dt(r["updated_at"]),
                }
                for r in batch
            ]
            Url.insert_many(data).on_conflict_ignore().execute()
    print(f"  Loaded {len(rows)} URLs.")


def load_events(filepath):
    print(f"Loading events from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with db.atomic():
        for batch in chunked(rows, 100):
            data = [
                {
                    "id": int(r["id"]),
                    "url_id": int(r["url_id"]),
                    "user_id": int(r["user_id"]) if r.get("user_id") else None,
                    "event_type": r["event_type"],
                    "timestamp": parse_dt(r["timestamp"]),
                    "details": r.get("details", ""),
                }
                for r in batch
            ]
            Event.insert_many(data).on_conflict_ignore().execute()
    print(f"  Loaded {len(rows)} events.")


if __name__ == "__main__":
    users_csv = os.path.join(DATA_DIR, "users.csv")
    urls_csv = os.path.join(DATA_DIR, "urls.csv")
    events_csv = os.path.join(DATA_DIR, "events.csv")

    with db:
        db.create_tables([User, Url, Event], safe=True)
        load_users(users_csv)
        load_urls(urls_csv)
        load_events(events_csv)

    print("Done! Seed data loaded.")
