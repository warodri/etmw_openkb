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
    CREATE TABLE IF NOT EXISTS verifications (id TEXT PRIMARY KEY, report_id TEXT, doc_id TEXT, to_email TEXT, holder TEXT, token TEXT UNIQUE,
        status TEXT, created_at TEXT, approved_at TEXT, sent_at TEXT, expires_at TEXT, answered_at TEXT, answer TEXT);
    CREATE TABLE IF NOT EXISTS reporters (reporter TEXT PRIMARY KEY, upheld INTEGER DEFAULT 0, dismissed INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, event TEXT, doc_id TEXT, actor TEXT, detail TEXT);
    CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
    """)
    have = [r[1] for r in c.execute("PRAGMA table_info(reports)")]
    for col in ("reporter TEXT", "claimant TEXT", "evidence_url TEXT", "triage TEXT"):
        if col.split()[0] not in have: c.execute("ALTER TABLE reports ADD COLUMN " + col)
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

def live_doc_loaders(db_path=None):
    """{doc_id: loader} for live documents. A loader returns [(chunk_dict, vector)] for that one document (read on demand)."""
    c = connect(db_path); rows = c.execute("SELECT id, title FROM documents WHERE status='live'").fetchall(); c.close()
    def mk(did, title):
        def load():
            cc = connect(db_path)
            rs = cc.execute("SELECT idx, text, vec FROM chunks WHERE doc_id=? ORDER BY idx", (did,)).fetchall(); cc.close()
            return [({"id": f"{did}#{r['idx']}", "source": title, "doc_id": did, "text": r["text"]}, json.loads(r["vec"])) for r in rs]
        return load
    return {r["id"]: mk(r["id"], r["title"]) for r in rows}

def live_titles(db_path=None):
    """[(doc_id, title)] for live documents."""
    c = connect(db_path); rows = [(r["id"], r["title"]) for r in c.execute("SELECT id, title FROM documents WHERE status='live'")]; c.close(); return rows

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

# ---- report triage: decide automatically whether a report is credible ----
import ipaddress, socket, urllib.parse, urllib.request
PII = [r"[\w.+-]+@[\w-]+\.[\w.-]+", r"(?<!\d)(?:\+?\d[\d ().-]{8,}\d)(?!\d)", r"\b\d{3}-\d{2}-\d{4}\b", r"\b[A-Z]{2}\d{6,}\b"]
NOTICE = re.compile(r"(©|\(c\)|copyright|all rights reserved)", re.I)
PERMISSIVE = re.compile(r"(creative commons|public domain|cc0|cc by|gnu free documentation|open licen)", re.I)
HIDE_AT_ONCE = ("copyright",)  # only a complete notice hides at once; see report()
MULTI_HIDE = 3                 # distinct reporters needed to hide on volume alone

def _safe_url(u):
    pr = urllib.parse.urlparse(u or "")
    if pr.scheme not in ("http", "https") or not pr.hostname: return False
    try:
        for fam, _, _, _, sa in socket.getaddrinfo(pr.hostname, None):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: return False
    except Exception: return False
    return True

def fetch_page_text(url, limit=2_000_000):
    """Fetch an evidence page as plain text. Refuses private addresses. Returns None on any failure."""
    if not _safe_url(url): return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenKB-report-check/1.0"})
        raw = urllib.request.urlopen(req, timeout=15).read(limit).decode("utf-8", "replace")
        raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
    except Exception:
        return None

def _words(t): return re.findall(r"\w+", t.lower())
def _shingles(t, n=8):
    w = _words(t); return {" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))}
def overlap(doc_text, page_text):
    """Containment of the document's text in the evidence page (0..1) and the reverse; returns the larger."""
    a, b = _shingles(doc_text), _shingles(page_text)
    if not a or not b: return 0.0
    i = len(a & b); return max(i / len(a), i / len(b))

def _doc_text(c, doc_id):
    return " ".join(r[0] for r in c.execute("SELECT text FROM chunks WHERE doc_id=? ORDER BY idx", (doc_id,)))

def _reporter_rep(c, reporter):
    r = c.execute("SELECT upheld, dismissed FROM reporters WHERE reporter=?", (reporter,)).fetchone()
    return (r[0], r[1]) if r else (0, 0)

def _bump(c, reporter, field):
    c.execute("INSERT OR IGNORE INTO reporters (reporter) VALUES (?)", (reporter,))
    c.execute(f"UPDATE reporters SET {field}={field}+1 WHERE reporter=?", (reporter,))

def report(doc_id, reason, details="", email="", reporter="anon", claimant="", evidence_url="", statement=False, holder_contact="", fetch=fetch_page_text, db_path=None):
    """Public report with automatic triage. Returns {id, outcome, hidden, message} or None if refused.
    outcome: removed (obviously valid) | dismissed (bogus or unsupported) | queued (ambiguous, maintainer looks) |
             needs-evidence (not enough to act on; the reporter is told what to add)."""
    if reason not in REPORT_REASONS: return None
    details = (details or "").strip()[:2000]
    c = connect(db_path)
    fixture = (doc_id or "").startswith(("fixture:", "general"))
    doc = None
    if not fixture:
        doc = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc: c.close(); return None
    rid = "rep-" + uuid.uuid4().hex[:10]
    def finish(outcome, why, message, hide=None, remove=False):
        c.execute("INSERT INTO reports (id, doc_id, reason, details, email, status, created_at, decided_at, decision, reporter, claimant, evidence_url, triage) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (rid, doc_id, reason, details, (email or "")[:200], "open" if outcome == "queued" else ("waiting" if outcome == "awaiting-source" else "closed"), now(), None if outcome in ("queued", "awaiting-source") else now(), None if outcome in ("queued", "awaiting-source") else outcome, reporter, (claimant or "")[:200], (evidence_url or "")[:500], why))
        log(c, "reported", doc_id, "public:" + reporter, json.dumps({"report": rid, "reason": reason, "outcome": outcome, "why": why}))
        if outcome == "dismissed": _bump(c, reporter, "dismissed")
        if remove and doc: _bump(c, reporter, "upheld")
        c.commit(); c.close()
        if remove: takedown(doc_id, "auto:" + rid, f"removed automatically after report {rid}: {why}", hard=True, db_path=db_path)
        elif hide is True: takedown(doc_id, "auto:" + rid, f"hidden pending decision ({why})", hard=False, db_path=db_path)
        elif hide is False and doc and doc["status"] == "hidden": restore(doc_id, "auto:" + rid, why, db_path=db_path)
        return {"id": rid, "outcome": outcome, "hidden": bool(hide) and not remove, "message": message}
    # abuse: repeats and low reputation
    if not fixture and c.execute("SELECT 1 FROM reports WHERE doc_id=? AND reporter=?", (doc_id, reporter)).fetchone():
        return finish("dismissed", "duplicate report from the same reporter", "You already reported this document. It is being handled.")
    up, dis = _reporter_rep(c, reporter)
    if dis >= 3 and up == 0: return finish("dismissed", "reporter has several earlier reports that did not hold up", "We could not accept this report automatically.")
    if len(re.sub(r"\W+", "", details)) < 8 and reason != "copyright" and reason != "quality": return finish("needs-evidence", "no details", "Please say what is wrong, and for personal information quote the exact text.")
    if re.search(r"https?://\S+.*https?://\S+.*https?://\S+", details) or any(re.search(p, details.lower()) for p in SPAM):
        return finish("dismissed", "report text looks like spam", "We could not accept this report automatically.")
    text = _doc_text(c, doc_id) if doc else ""
    if fixture:
        ok = len(details) >= 30
        return finish("queued" if ok else "dismissed", "test-corpus or site-level report", "Thank you. We will look at this." if ok else "Please add more detail.")
    # ---- by reason ----
    if reason == "copyright":
        contact = (holder_contact or "").strip()
        if not (claimant.strip() and re.match(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", contact) and re.match(r"^https?://", evidence_url or "") and statement):
            return finish("needs-evidence", "copyright notice incomplete", "To act on a copyright report we need: who the work belongs to (the rights holder), an email address for them, a link to where the original is, and your confirmation that you are the owner or authorised to act. Please add them and send again.")
        page = fetch(evidence_url)
        strong = False; note = "evidence page could not be fetched"
        if page is not None:
            ov = overlap(text, page)
            dom_doc = urllib.parse.urlparse(doc["source_url"] or "").hostname
            dom_ev = urllib.parse.urlparse(evidence_url).hostname
            if ov < 0.10: return finish("dismissed", f"evidence page does not contain the document (overlap {ov:.2f})", "We checked your link and it does not contain this document's text, so we could not act. If you meant another link, send it again.", hide=False)
            permissive, notice = bool(PERMISSIVE.search(page)), bool(NOTICE.search(page))
            strong = ov >= 0.5 and notice and not permissive and dom_ev != dom_doc and doc["origin"] != "collector"
            note = f"overlap {ov:.2f}, notice={notice}, permissive licence on page={permissive}"
        cd, ed = contact.split("@")[1].lower(), (urllib.parse.urlparse(evidence_url).hostname or "").lower()
        # the named contact must be tied to the evidence: its email or domain appears on the page, or the page lives on that domain
        low = (page or "").lower()
        tied = page is not None and (contact.lower() in low or cd in low or ed == cd or ed.endswith("." + cd))
        if not tied:
            return finish("queued", f"holder contact is not tied to the evidence page ({note}); no email sent", "Received. We could not tie the contact you gave to your link, so a person will look. We have not emailed anyone.", hide=False)
        note += "; contact tied to the evidence page"
        res = finish("awaiting-source", note, "Thank you. We are asking the rights holder you named to confirm. Nothing is removed unless they confirm. " + ("The document is hidden until they answer, for up to 7 days." if strong else "The document stays up while we wait, for up to 7 days."), hide=strong)
        c2 = connect(db_path)
        c2.execute("INSERT INTO verifications (id, report_id, doc_id, to_email, holder, token, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   ("ver-" + uuid.uuid4().hex[:10], rid, doc_id, contact[:200], claimant[:200], uuid.uuid4().hex, "draft", now()))
        log(c2, "verification-drafted", doc_id, "system", json.dumps({"report": rid, "to": contact}))
        c2.commit(); c2.close()
        return res
    if reason == "personal-data":
        sn = details
        norm = lambda t: re.sub(r"\s+", " ", t.lower())
        found = len(sn) >= 12 and norm(sn) in norm(text)
        if not found:
            q = re.findall(r"\"([^\"]{12,})\"", details)
            found = any(norm(x) in norm(text) for x in q)
            if not q and len(sn) < 12: return finish("needs-evidence", "no quoted text", "Please quote the exact text that contains the personal information.")
        if not found: return finish("dismissed", "quoted text not found in the document", "We could not find that text in the document, so we could not act. Please quote it exactly.")
        if any(re.search(p, sn) for p in PII): return finish("removed", "quoted text is in the document and is a personal identifier", "Thank you. The text is in the document and the document has been removed.", remove=True)
        return finish("queued", "quoted text found but not an obvious identifier", "Received. A person will decide.", hide=_multi(c, doc_id, reporter))
    # harmful / quality / other
    bad = check_text(text) if text else []
    if reason in ("harmful", "quality") and bad:
        return finish("removed", "document now fails the automatic checks: " + "; ".join(bad), "Thank you. The document failed our automatic checks and has been removed.", remove=True)
    n = c.execute("SELECT count(DISTINCT reporter) FROM reports WHERE doc_id=? AND reason=? AND created_at>?", (doc_id, reason, datetime.fromtimestamp(time.time() - 7 * 86400, timezone.utc).isoformat())).fetchone()[0] + 1
    if reason == "quality":
        if n >= MULTI_HIDE: return finish("queued", f"{n} separate quality reports", "Received. A person will look.")
        return finish("dismissed", "single quality report, noted", "Thanks. Noted. If several people report it, it gets looked at.")
    if reason == "harmful":
        return finish("queued", "harmful report with details", "Received. A person will decide.", hide=_multi(c, doc_id, reporter))
    return finish("queued" if len(details) >= 30 else "dismissed", "other", "Received." if len(details) >= 30 else "Please add more detail.")

def _multi(c, doc_id, reporter):
    """True when enough distinct reporters (including this one) have reported the document in 7 days."""
    since = datetime.fromtimestamp(time.time() - 7 * 86400, timezone.utc).isoformat()
    n = c.execute("SELECT count(DISTINCT reporter) FROM reports WHERE doc_id=? AND created_at>? AND (triage NOT LIKE 'duplicate%' AND triage NOT LIKE '%spam%')", (doc_id, since)).fetchone()[0] + 1
    return n >= MULTI_HIDE

def decide_report(rid, decision, actor, db_path=None):
    """Maintainer decision on a queued report: 'remove' (hard takedown), 'restore', or 'dismiss' (keep as is)."""
    c = connect(db_path); r = c.execute("SELECT * FROM reports WHERE id=? AND status='open'", (rid,)).fetchone()
    if not r or decision not in ("remove", "restore", "dismiss"): c.close(); return False
    c.execute("UPDATE reports SET status='closed', decided_at=?, decision=? WHERE id=?", (now(), decision, rid))
    _bump(c, r["reporter"] or "anon", "upheld" if decision == "remove" else "dismissed")
    log(c, "report-decided", r["doc_id"], actor, json.dumps({"report": rid, "decision": decision}))
    c.commit(); c.close()
    if decision == "remove": takedown(r["doc_id"], actor, f"removed after report {rid}", hard=True, db_path=db_path)
    else: restore(r["doc_id"], actor, f"report {rid} {decision}", db_path=db_path)
    return True

VERIFY_DAYS = 7
def verification_mail(v, doc_title, base_url):
    link = base_url.rstrip("/") + "/verify/" + v["token"]
    subj = "Please confirm: is this your work? (OpenKB copyright check)"
    body = (f"Hello {v['holder']},\n\n"
            "Someone has told the OpenKB library (an open, CC BY-SA knowledge library) that a document in it belongs to you or to the organisation you run, "
            "and was added without permission:\n\n"
            f"  {doc_title or v['doc_id']}\n\n"
            "We do not remove documents on a stranger's say-so, so we are asking you directly. One click is enough:\n\n"
            f"  {link}\n\n"
            "On that page you can say 'Yes, this is ours and it is used without permission' (we then remove the document at once) "
            "or 'No, this is not ours / we do not object' (we keep it). If we hear nothing within "
            f"{VERIFY_DAYS} days we keep the document and close the report. You can also reply to this email.\n\n"
            "We will never ask you for money or personal documents. If you did not expect this message, ignore it.\n\n"
            "OpenKB, https://openkb--warodri.entertomyworld.com/report")
    return subj, body

def outbox(db_path=None):
    c = connect(db_path)
    rows = [dict(r) for r in c.execute("SELECT v.*, d.title FROM verifications v LEFT JOIN documents d ON d.id=v.doc_id WHERE v.status IN ('draft','approved') ORDER BY v.created_at").fetchall()]
    c.close(); return rows

def approve_outbox(vid, actor="maintainer-cli", db_path=None):
    """Approve ONE drafted verification email for sending. Nothing is sent without this."""
    c = connect(db_path)
    n = c.execute("UPDATE verifications SET status='approved', approved_at=? WHERE id=? AND status='draft'", (now(), vid)).rowcount
    if n: log(c, "verification-approved", None, actor, vid)
    c.commit(); c.close(); return bool(n)

def send_approved(sender, base_url, db_path=None):
    """Send approved verification emails through sender(to, subject, body). Returns count sent."""
    c = connect(db_path); sent = 0
    for v in c.execute("SELECT v.*, d.title FROM verifications v LEFT JOIN documents d ON d.id=v.doc_id WHERE v.status='approved'").fetchall():
        subj, body = verification_mail(dict(v), v["title"], base_url)
        if sender(v["to_email"], subj, body):
            c.execute("UPDATE verifications SET status='sent', sent_at=?, expires_at=? WHERE id=?", (now(), datetime.fromtimestamp(time.time() + VERIFY_DAYS * 86400, timezone.utc).isoformat(), v["id"]))
            log(c, "verification-sent", v["doc_id"], "system", v["id"]); sent += 1
    c.commit(); c.close(); return sent

def mark_sent(vid, actor="mail-task", db_path=None):
    """Record that an APPROVED verification was sent (by the mail route outside this repo). Starts the 7-day clock."""
    c = connect(db_path)
    n = c.execute("UPDATE verifications SET status='sent', sent_at=?, expires_at=? WHERE id=? AND status='approved'", (now(), datetime.fromtimestamp(time.time() + VERIFY_DAYS * 86400, timezone.utc).isoformat(), vid)).rowcount
    if n: log(c, "verification-sent", None, actor, vid)
    c.commit(); c.close(); return bool(n)

def outbox_json(base_url="https://openkb--warodri.entertomyworld.com", status=("draft", "approved"), db_path=None):
    """Machine-readable drafts: [{id, report_id, status, to, subject, body, doc_title}]"""
    out = []
    for v in outbox(db_path):
        if v["status"] not in status: continue
        subj, body = verification_mail(v, v["title"], base_url)
        out.append({"id": v["id"], "report_id": v["report_id"], "status": v["status"], "to": v["to_email"], "subject": subj, "body": body, "doc_title": v["title"]})
    return out

def get_verification(token, db_path=None):
    c = connect(db_path); v = c.execute("SELECT v.*, d.title FROM verifications v LEFT JOIN documents d ON d.id=v.doc_id WHERE v.token=?", (token or "",)).fetchone(); c.close()
    return dict(v) if v else None

def answer_verification(token, answer, db_path=None):
    """The named rights holder answers: 'yes' (ours, used without permission: remove) or 'no' (keep). Only a sent, unanswered, unexpired request counts."""
    if answer not in ("yes", "no"): return False
    c = connect(db_path); v = c.execute("SELECT * FROM verifications WHERE token=? AND status='sent'", (token or "",)).fetchone()
    if not v or (v["expires_at"] and v["expires_at"] < now()): c.close(); return False
    c.execute("UPDATE verifications SET status='answered', answer=?, answered_at=? WHERE id=?", (answer, now(), v["id"]))
    dec = "remove" if answer == "yes" else "dismiss"
    c.execute("UPDATE reports SET status='closed', decided_at=?, decision=? WHERE id=?", (now(), "removed" if answer == "yes" else "dismissed", v["report_id"]))
    r = c.execute("SELECT reporter FROM reports WHERE id=?", (v["report_id"],)).fetchone()
    _bump(c, (r["reporter"] if r else None) or "anon", "upheld" if answer == "yes" else "dismissed")
    log(c, "verification-answered", v["doc_id"], "rights-holder:" + v["to_email"], json.dumps({"verification": v["id"], "answer": answer}))
    c.commit(); c.close()
    if answer == "yes": takedown(v["doc_id"], "source-confirmed:" + v["id"], f"removed: rights holder {v['holder']} confirmed (report {v['report_id']})", hard=True, db_path=db_path)
    else: restore(v["doc_id"], "source-answered:" + v["id"], f"rights holder did not confirm (report {v['report_id']})", db_path=db_path)
    return True

def expire_verifications(db_path=None):
    """No answer in VERIFY_DAYS (or never approved in 14 days): close the report, keep or restore the document. Nothing is removed."""
    c = connect(db_path); n = 0
    old = datetime.fromtimestamp(time.time() - 14 * 86400, timezone.utc).isoformat()
    rows = c.execute("SELECT * FROM verifications WHERE (status='sent' AND expires_at<?) OR (status IN ('draft','approved') AND created_at<?)", (now(), old)).fetchall()
    for v in rows:
        c.execute("UPDATE verifications SET status='expired' WHERE id=?", (v["id"],))
        c.execute("UPDATE reports SET status='closed', decided_at=?, decision='dismissed' WHERE id=?", (now(), v["report_id"]))
        log(c, "verification-expired", v["doc_id"], "system", json.dumps({"verification": v["id"], "report": v["report_id"]})); n += 1
    c.commit(); c.close()
    for v in rows:
        d = get_document(v["doc_id"], db_path)
        if d and d["status"] == "hidden": restore(v["doc_id"], "system", "no answer from the named rights holder, report closed", db_path=db_path)
    return n

def open_reports(db_path=None):
    c = connect(db_path)
    rows = [dict(r) for r in c.execute("SELECT r.*, d.title, d.status AS doc_status FROM reports r LEFT JOIN documents d ON d.id=r.doc_id WHERE r.status='open' ORDER BY r.created_at").fetchall()]
    c.close(); return rows

def public_stats(db_path=None):
    """Honest numbers for the welcome-page counter. A crawler counts as active if it published something in the last 48 hours."""
    c = connect(db_path)
    since = datetime.fromtimestamp(time.time() - 48 * 3600, timezone.utc).isoformat()
    day = datetime.fromtimestamp(time.time() - 24 * 3600, timezone.utc).isoformat()
    active = c.execute("SELECT count(DISTINCT actor) FROM audit_log WHERE event='published' AND (actor LIKE 'collector:%' OR actor LIKE 'crawler:%') AND ts>?", (since,)).fetchone()[0]
    last = c.execute("SELECT max(ts) FROM audit_log WHERE event='published' AND (actor LIKE 'collector:%' OR actor LIKE 'crawler:%')").fetchone()[0]
    added = c.execute("SELECT count(*) FROM audit_log WHERE event='published' AND (actor LIKE 'collector:%' OR actor LIKE 'crawler:%') AND ts>?", (day,)).fetchone()[0]
    docs = c.execute("SELECT count(*) FROM documents WHERE status='live'").fetchone()[0]
    c.close()
    return {"active_crawlers": active, "documents": docs, "added_24h": added, "last_active": last}

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
    elif a[:1] == ["outbox-json"]: print(json.dumps(outbox_json(), indent=1))
    elif a[:1] == ["mark-sent"] and len(a) == 2: print(mark_sent(a[1]))
    elif a[:1] == ["outbox"]:
        for v in outbox(): print(v["id"], v["status"], v["to_email"], v["holder"], v["doc_id"], v["title"])
    elif a[:1] == ["approve"] and len(a) == 2: print(approve_outbox(a[1]))
    elif a[:1] == ["expire"]: print(expire_verifications())
    elif a[:1] == ["log"]:
        c = connect()
        for r in c.execute("SELECT ts, event, doc_id, actor, detail FROM audit_log ORDER BY id DESC LIMIT 30"): print(tuple(r))
    else: print("usage: library.py stats | reports | decide <report-id> remove|restore|dismiss | remove <doc-id> [reason] | log")
