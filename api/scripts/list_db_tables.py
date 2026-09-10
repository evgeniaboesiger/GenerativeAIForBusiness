import os
import sqlite3
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings

url = settings.database_url or "sqlite:///./fraumatch_demo.db"
if url.startswith("sqlite:///"):
    path = url.replace("sqlite:///", "", 1)
else:
    print(f"Do not know how to inspect non-SQLite URL: {url}")
    sys.exit(1)

conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())
conn.close()