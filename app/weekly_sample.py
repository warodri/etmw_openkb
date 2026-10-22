"""Weekly sample for the maintainer: 20 random auto-published documents from the last 7 days (titles, source, size).
Not a gate. Writes data/weekly_sample.md and prints it. Usage: python3 app/weekly_sample.py"""
import sys, os, random, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library as L
from datetime import datetime, timezone
c = L.connect()
since = datetime.fromtimestamp(time.time() - 7 * 86400, timezone.utc).isoformat()
rows = c.execute("SELECT id, title, origin, source_url, licence FROM documents WHERE status='live' AND created_at>?", (since,)).fetchall() if "created_at" in [r[1] for r in c.execute("PRAGMA table_info(documents)")] else c.execute("SELECT id, title, origin, source_url, licence FROM documents WHERE status='live'").fetchall()
pick = random.sample(rows, min(20, len(rows)))
out = [f"# Weekly sample ({len(pick)} of {len(rows)} live documents)", ""] + [f"- {r['title']} | {r['origin']} | {r['source_url']} | {r['id']}" for r in pick]
txt = "\n".join(out); open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "weekly_sample.md"), "w").write(txt); print(txt)
