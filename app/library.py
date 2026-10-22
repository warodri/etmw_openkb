#!/usr/bin/env python3
"""OpenKB library store: documents, chunks, reports, audit log. Stdlib only.

One shared library. Every document has a provenance record. Publishing is automatic
after automated checks (no human review before publish); safety comes from the checks,
the report-and-remove path, and an append-only audit log. See docs/COLLECTION-PLAN.md.
"""
import hashlib, json, os, re, sqlite3, time, uuid
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("OPENKB_LIBRARY_DB", os.path.join(ROOT, "data", "library.db"))
CHUNK_CHARS, OVERLAP = 3200, 480
MIN_CHARS, MAX_CHARS = 300, 2_000_000
PER_USER_DAILY_DOCS = 20

# Accepted licences (normalised key -> display). NC and ND are never accepted.
ACCEPTED = {"pd": "Public domain", "cc0": "CC0", "cc-by": "CC BY", "cc-by-sa": "CC BY-SA"}
REPORT_REASONS = ("copyright", "personal-data", "harmful", "quality", "other")
HIDE_AT_ONCE = ("copyright", "personal-data")

INJECTION = [r"ignore (all |any )?(previous|prior|above) (instructions|prompts)", r"disregard (the )?(system|previous) (prompt|instructions)",
             r"you are now (a|an|the)\b", r"(reveal|print|show) (your|the) (system )?prompt", r"\bas an ai language model\b",
             r"<\s*/?\s*(system|assistant)\s*>", r"\[\s*(system|inst)\s*\]"]
SPAM = [r"\bbuy now\b", r"\bviagra\b", r"\bcasino\b", r"click here to (win|claim)", r"\bcrypto giveaway\b"]

def now(): return datetime.now(timezone.utc).isoformat()

def connect(path=None):
    c = sqlite3.connect(path or DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, title TEXT, origin TEXT, source_url TEXT, licence TEXT,
        credit TEXT, contributor TEXT, status TEXT, hash TEXT, head_hash TEXT, chars INTEGER, created_at TEXT, removed_at TEXT, removed_reason TEXT);
    CREATE INDEX IF NOT EXISTS docs_hash ON documents(hash); CREATE INDEX IF NOT EXISTS docs_head ON documents(head_hash);
    CREATE TABLE IF NOT EXISTS chunks (doc_id TEXT, idx INTEGER, text TEXT, vec TEXT, PRIMARY KEY (doc_id, idx));
    CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, doc_id TEXT, reason TEXT, details TEXT, email TEXT, status TEXT,
        created_at TEXT, decided_at TEXT, decision TEXT);
    CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, event TEXT, doc_id TEXT, actor TEXT, detail TEXT);
    CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
    """)
    return c

def log(c, event, doc_id=None, actor="system", detail=""):
    c.execute("INSERT INTO audit_log (ts, event, doc_id, actor, detail) VALUES (?,?,?,?,?)", (now(), event, doc_id, actor, detail))

def norm_licence(s):
    t = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    if not t: return None
    if re.search(r"\b(nc|nd|noncommercial|non commercial|noderivs|no derivatives)\b", t) or "sa nc" in t: return None
    if t in ("pd", "public domain", "public domain mark", "pdm"): return "pd"
    if "cc0" in t or "public domain dedication" in t: return "cc0"
    m = re.match(r"^(cc )?by( sa)?( \d( \d)?)?( international| intl| unported)?$", t)
    if m: return "cc-by-sa" if m.group(2) else "cc-by"
    return None

def check_text(text):
    """Automated quality / spam / injection checks. Returns list of reasons (empty = pass)."""
    r = []
    n = len(text)
    if n < MIN_CHARS: r.append(f"too short ({n} chars, minimum {MIN_CHARS})")
    if n > MAX_CHARS: r.append("too long")
    if n:
        letters = sum(ch.isalpha() or ch.isspace() for ch in text) / n
        if letters < 0.7: r.append("mostly non-text characters (garbage or encoding problem)")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) > 20 and len(set(lines)) / len(lines) < 0.3: r.append("highly repetitive")
        words = re.findall(r"\w+", text.lower())
        if len(words) > 100 and len(set(words)) / len(words) < 0.08: r.append("highly repetitive vocabulary")
        urls = len(re.findall(r"https?://", text))
        if urls > 20 and urls / max(1, len(words)) > 0.05: r.append("too many links (spam pattern)")
    low = text.lower()
    for p in INJECTION:
        if re.search(p, low): r.append("prompt-injection pattern found"); break
    for p in SPAM:
        if re.search(p, low): r.append("spam pattern found"); break
    return r

def chunk_text(text):
    text = text.strip(); out, start = [], 0
    while start < len(text):
        out.append(text[start:start + CHUNK_CHARS]); start += CHUNK_CHARS - OVERLAP
    return out

def _hash(t): return hashlib.sha256(re.sub(r"\s+", " ", t.lower()).strip().encode()).hexdigest()

def ollama_embed(text, host="http://127.0.0.1:11436", model="qwen3-embedding:4b"):
    import urllib.request
    req = urllib.request.Request(host + "/api/embed", data=json.dumps({"model": model, "input": text}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["embeddings"][0]

def submit(*a, **k):
    db_path = k.get('db_path'); c = connect(db_path)
    try: return _submit(c, *a, **k)
    finally: c.close()

def _submit(c, text, title, origin, licence, source_url="", credit="", contributor="", declarations=None, embed=ollama_embed, db_path=None):
    """Run checks; publish if all pass. Returns {ok, doc_id, reasons}. No human review step."""
    reasons = []
    key = norm_licence(licence)
    if key is None: reasons.append("licence missing, unclear, or not accepted (accepted: public domain, CC0, CC BY, CC BY-SA; NC/ND excluded)")
    if origin not in ("manual", "collector", "user-crawler"): reasons.append("unknown origin")
    if origin in ("manual", "user-crawler"):
        need = ("own_or_licensed", "ok_with_cc_by_sa", "may_be_edited")
        if not declarations or not all(declarations.get(k) for k in need): reasons.append("the three declarations were not all accepted")
    if origin in ("collector", "user-crawler") and not re.match(r"^https?://", source_url or ""): reasons.append("source URL required")
    if not (title or "").strip(): reasons.append("title required")
    text = (text or "").strip()
    reasons += check_text(text)
    h, hh = _hash(text), _hash(text[:2000])
    if c.execute("SELECT 1 FROM documents WHERE status IN ('live','hidden') AND (hash=? OR head_hash=?)", (h, hh)).fetchone():
        reasons.append("duplicate of a document already in the library")
    if contributor and origin != "collector":
        since = datetime.fromtimestamp(time.time() - 86400, timezone.utc).isoformat()
        if c.execute("SELECT count(*) FROM documents WHERE contributor=? AND created_at>?", (contributor, since)).fetchone()[0] >= PER_USER_DAILY_DOCS:
            reasons.append(f"daily limit of {PER_USER_DAILY_DOCS} documents reached")
    did = "doc-" + uuid.uuid4().hex[:12]
    if reasons:
        log(c, "rejected", None, contributor or origin, json.dumps({"title": title, "origin": origin, "reasons": reasons}))
        c.commit(); return {"ok": False, "doc_id": None, "reasons": reasons}
    parts = chunk_text(text)
    vecs = [embed(p) for p in parts]  # may raise: nothing is written yet
    c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
              (did, title.strip(), origin, source_url, ACCEPTED[key], credit, contributor, "live", h, hh, len(text), now()))
    for i, (p, v) in enumerate(zip(parts, vecs)):
        c.execute("INSERT INTO chunks VALUES (?,?,?,?)", (did, i, p, json.dumps(v)))
    log(c, "published", did, contributor or origin, json.dumps({"title": title, "origin": origin, "licence": ACCEPTED[key], "source_url": source_url, "chunks": len(parts)}))
    c.commit(); return {"ok": True, "doc_id": did, "reasons": []}

def live_chunks(db_path=None):
    """[(chunk_dict, vector)] for live documents only, in the shape the server's retrieve() uses."""
    c = connect(db_path)
    rows = c.execute("SELECT d.id, d.title, ch.idx, ch.text, ch.vec FROM chunks ch JOIN documents d ON d.id=ch.doc_id WHERE d.status='live' ORDER BY d.id, ch.idx").fetchall()
    c.close()
    return [({"id": f"{r['id']}#{r['idx']}", "source": r["title"], "doc_id": r["id"], "text": r["text"]}, json.loads(r["vec"])) for r in rows]

def get_document(doc_id, db_path=None):
    c = connect(db_path); r = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone(); c.close()
    return dict(r) if r else None

def takedown(doc_id, actor, reason, hard=True, db_path=None):
    """hard=True removes text and vectors for good (record stays). hard=False hides (soft takedown, reversible)."""
    c = connect(db_path); d = c.execute("SELECT status FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not d: c.close(); return False
    if hard:
        c.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        c.execute("UPDATE documents SET status='removed', removed_at=?, removed_reason=? WHERE id=?", (now(), reason, doc_id))
        log(c, "removed", doc_id, actor, reason)
    else:
        c.execute("UPDATE documents SET status='hidden', removed_reason=? WHERE id=? AND status='live'", (reason, doc_id))
        log(c, "hidden", doc_id, actor, reason)
    c.commit(); c.close(); return True

def restore(doc_id, actor, note="", db_path=None):
    c = connect(db_path)
    n = c.execute("UPDATE documents SET status='live', removed_reason=NULL WHERE id=? AND status='hidden'", (doc_id,)).rowcount
    if n: log(c, "restored", doc_id, actor, note)
    c.commit(); c.close(); return bool(n)

def report(doc_id, reason, details="", email="", db_path=None):
    """Public report. Copyright and personal-data reports hide the document at once (soft takedown)."""
    if reason not in REPORT_REASONS: return None
    c = connect(db_path)
    fixture = (doc_id or "").startswith("fixture:")  # test-corpus documents are not in the library table
    if not fixture and not c.execute("SELECT 1 FROM documents WHERE id=?", (doc_id,)).fetchone(): c.close(); return None
    rid = "rep-" + uuid.uuid4().hex[:10]
    c.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?,NULL,NULL)", (rid, doc_id, reason, (details or "")[:2000], (email or "")[:200], "open", now()))
    log(c, "reported", doc_id, "public", json.dumps({"report": rid, "reason": reason}))
    c.commit(); c.close()
    if reason in HIDE_AT_ONCE and not fixture: takedown(doc_id, "auto:" + rid, f"hidden pending decision ({reason})", hard=False, db_path=db_path)
    return rid

def decide_report(rid, decision, actor, db_path=None):
    """decision: 'remove' (hard takedown), 'restore', or 'dismiss' (keep as is)."""
    c = connect(db_path); r = c.execute("SELECT * FROM reports WHERE id=? AND status='open'", (rid,)).fetchone()
    if not r or decision not in ("remove", "restore", "dismiss"): c.close(); return False
    c.execute("UPDATE reports SET status='closed', decided_at=?, decision=? WHERE id=?", (now(), decision, rid))
    log(c, "report-decided", r["doc_id"], actor, json.dumps({"report": rid, "decision": decision}))
    c.commit(); c.close()
    if decision == "remove": takedown(r["doc_id"], actor, f"removed after report {rid}", hard=True, db_path=db_path)
    elif decision == "restore" or decision == "dismiss": restore(r["doc_id"], actor, f"report {rid} {decision}", db_path=db_path)
    return True

def open_reports(db_path=None):
    c = connect(db_path)
    rows = [dict(r) for r in c.execute("SELECT r.*, d.title, d.status AS doc_status FROM reports r LEFT JOIN documents d ON d.id=r.doc_id WHERE r.status='open' ORDER BY r.created_at").fetchall()]
    c.close(); return rows

def stats(db_path=None):
    c = connect(db_path)
    out = {"documents": dict(c.execute("SELECT status, count(*) FROM documents GROUP BY status").fetchall()),
           "open_reports": c.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0]}
    c.close(); return out

if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if a[:1] == ["stats"]: print(json.dumps(stats(), indent=1))
    elif a[:1] == ["reports"]:
        for r in open_reports(): print(r["id"], r["doc_id"], r["reason"], r["doc_status"], (r["title"] or ""), "|", r["details"][:120])
    elif a[:2] == ["decide"] and len(a) == 3 + 0 or (a[:1] == ["decide"] and len(a) == 3): print(decide_report(a[1], a[2], "maintainer-cli"))
    elif a[:1] == ["remove"] and len(a) >= 2: print(takedown(a[1], "maintainer-cli", " ".join(a[2:]) or "removed by maintainer", hard=True))
    elif a[:1] == ["log"]:
        c = connect()
        for r in c.execute("SELECT ts, event, doc_id, actor, detail FROM audit_log ORDER BY id DESC LIMIT 30"): print(tuple(r))
    else: print("usage: library.py stats | reports | decide <report-id> remove|restore|dismiss | remove <doc-id> [reason] | log")
