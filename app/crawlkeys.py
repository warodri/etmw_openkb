"""Step 2: accounts for user crawl agents. An account sets a MANDATORY default licence and accepts the terms, then makes up to 3 keys.
An agent sends page addresses with its key; each goes through app/intake.py. Keys are stored as hashes only; the key itself is shown once."""
import hashlib, secrets, time, json, collections, threading
import library as L, intake as I

TERMS_VERSION = "draft-1"   # the terms text is a proposal until Walter approves it (private draft)
MAX_KEYS = 3
DAILY_CAP = 200            # new entries per account per UTC day (3 keys share it)
RATE_PER_MIN = 6            # submissions per key per minute (each costs one polite fetch and a few embeddings)
_recent, _rl = collections.defaultdict(collections.deque), threading.Lock()
DECL = {"own_or_licensed": True, "ok_with_cc_by_sa": True, "may_be_edited": True}   # recorded as accepted through the terms

def _h(s): return hashlib.sha256(s.encode()).hexdigest()

def _c(db_path=None):
    c = L.connect(db_path)
    c.execute("CREATE TABLE IF NOT EXISTS crawl_accounts (owner TEXT PRIMARY KEY, default_licence TEXT, terms_version TEXT, terms_accepted_at TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS crawl_keys (id TEXT PRIMARY KEY, key_hash TEXT UNIQUE, owner TEXT, label TEXT, created_at TEXT, revoked_at TEXT, last_used TEXT, submissions INTEGER DEFAULT 0)")
    return c

def contributor_id(owner): return "crawler:" + _h("owner:" + owner)[:10]

def set_account(owner, default_licence, accept_terms, db_path=None):
    """The default licence is mandatory and must be one we accept. Returns {ok, reasons}."""
    k = L.norm_licence(default_licence)
    if k is None: return {"ok": False, "reasons": ["the default licence must be one of: public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0, BSD"]}
    if not accept_terms: return {"ok": False, "reasons": ["the crawler terms must be accepted"]}
    c = _c(db_path); lic = L.ACCEPTED[k]
    c.execute("INSERT INTO crawl_accounts (owner, default_licence, terms_version, terms_accepted_at, created_at) VALUES (?,?,?,?,?) ON CONFLICT(owner) DO UPDATE SET default_licence=excluded.default_licence, terms_version=excluded.terms_version, terms_accepted_at=excluded.terms_accepted_at",
              (owner, lic, TERMS_VERSION, L.now(), L.now()))
    L.log(c, "crawler-default-set", None, contributor_id(owner), json.dumps({"default_licence": lic, "terms_version": TERMS_VERSION})); c.commit(); c.close()
    return {"ok": True, "default_licence": lic, "reasons": []}

def account(owner, db_path=None):
    c = _c(db_path); a = c.execute("SELECT default_licence, terms_version, terms_accepted_at FROM crawl_accounts WHERE owner=?", (owner,)).fetchone()
    keys = [dict(r) for r in c.execute("SELECT id, label, created_at, revoked_at, last_used, submissions FROM crawl_keys WHERE owner=? ORDER BY created_at", (owner,))]
    c.close()
    return {"has_account": bool(a), "default_licence": a["default_licence"] if a else "", "terms_version": a["terms_version"] if a else "", "keys": keys}

def create_key(owner, label="", db_path=None):
    c = _c(db_path)
    if not c.execute("SELECT 1 FROM crawl_accounts WHERE owner=?", (owner,)).fetchone(): c.close(); return {"ok": False, "reasons": ["set the default licence and accept the terms first"]}
    if c.execute("SELECT count(*) FROM crawl_keys WHERE owner=? AND revoked_at IS NULL", (owner,)).fetchone()[0] >= MAX_KEYS: c.close(); return {"ok": False, "reasons": ["at most %d active keys; revoke one first" % MAX_KEYS]}
    token = "okc_" + secrets.token_hex(24); kid = "key-" + secrets.token_hex(4)
    c.execute("INSERT INTO crawl_keys (id, key_hash, owner, label, created_at) VALUES (?,?,?,?,?)", (kid, _h(token), owner, (label or "")[:60], L.now()))
    L.log(c, "crawler-key-created", None, contributor_id(owner), json.dumps({"id": kid, "label": (label or "")[:60]})); c.commit(); c.close()
    return {"ok": True, "id": kid, "key": token, "reasons": []}   # the key is shown once; only its hash is kept

def revoke_key(owner, kid, db_path=None):
    c = _c(db_path); n = c.execute("UPDATE crawl_keys SET revoked_at=? WHERE id=? AND owner=? AND revoked_at IS NULL", (L.now(), kid, owner)).rowcount
    if n: L.log(c, "crawler-key-revoked", None, contributor_id(owner), json.dumps({"id": kid}))
    c.commit(); c.close(); return {"ok": bool(n)}

def auth(token, db_path=None):
    if not (token or "").startswith("okc_") or len(token) != 52: return None
    c = _c(db_path)
    r = c.execute("SELECT k.id, k.owner, a.default_licence FROM crawl_keys k JOIN crawl_accounts a ON a.owner=k.owner WHERE k.key_hash=? AND k.revoked_at IS NULL", (_h(token),)).fetchone()
    c.close()
    return {"key_id": r["id"], "owner": r["owner"], "default_licence": r["default_licence"], "contributor": contributor_id(r["owner"])} if r else None

def submit(token, url, embed=None, delay=None, db_path=None):
    """Returns {status, ok, doc_id, licence, basis, reasons}. status is an HTTP-style code."""
    a = auth(token, db_path)
    if not a: return {"status": 401, "ok": False, "reasons": ["invalid or revoked key"]}
    with _rl:
        q = _recent[a["key_id"]]; now = time.time()
        while q and now - q[0] > 60: q.popleft()
        if len(q) >= RATE_PER_MIN: return {"status": 429, "ok": False, "reasons": ["too many submissions, at most %d per minute per key" % RATE_PER_MIN]}
        q.append(now)
    c = _c(db_path)
    c.execute("CREATE TABLE IF NOT EXISTS crawl_adds (owner TEXT, day TEXT, n INTEGER DEFAULT 0, PRIMARY KEY (owner, day))")
    day = time.strftime("%Y-%m-%d", time.gmtime()); row = c.execute("SELECT n FROM crawl_adds WHERE owner=? AND day=?", (a["owner"], day)).fetchone(); c.close()
    if row and row["n"] >= DAILY_CAP: return {"status": 429, "ok": False, "reasons": ["daily limit reached: %d new entries per account per day; try again tomorrow (UTC)" % DAILY_CAP]}
    kw = {} if delay is None else {"delay": delay}
    r = I.ingest(url, a["contributor"], a["default_licence"], DECL, embed=embed, db_path=db_path, **kw)
    c = _c(db_path)
    if r["ok"]: c.execute("INSERT INTO crawl_adds (owner, day, n) VALUES (?,?,1) ON CONFLICT(owner, day) DO UPDATE SET n=n+1", (a["owner"], day))
    c.execute("UPDATE crawl_keys SET last_used=?, submissions=submissions+1 WHERE id=?", (L.now(), a["key_id"])); c.commit(); c.close()
    return {"status": 200 if r["ok"] else 422, "ok": r["ok"], "doc_id": r["doc_id"], "licence": r["licence"] if r["ok"] else "", "basis": r["basis"] if r["ok"] else "", "title": r["title"], "reasons": r["reasons"]}
