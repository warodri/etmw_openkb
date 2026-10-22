"""Reference-only text access. The library stores NO document text: per chunk it keeps start offset, hash and vector.
At question time the needed chunks are cut from the source page, which is fetched from its URL and kept in a
TEMPORARY COPY cache (24 hours, capped). If the source is gone or has changed, the chunk is dropped."""
import os, re, time, hashlib, threading, urllib.parse
import library as L

CACHE_DIR = os.path.join(os.path.dirname(L.DB_PATH), "cache")
TTL = 24 * 3600          # a cached source page is a temporary copy: it expires after 24 hours
MAX_FILES = 300          # and the cache holds at most this many pages
QUERY_DELAY = 1.0        # seconds between fetches to one host at question time (the crawl rule stays 5 s)
_lock = threading.Lock()

def chash(t): return hashlib.sha256(t.encode("utf-8")).hexdigest()[:32]

def _norm(raw): return re.sub(r"\r\n?", "\n", raw).strip()

def transform(raw, recipe):
    """The same pure function is used at index time and at question time, so offsets stay valid."""
    if recipe == "gutenberg":
        a = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw)
        b = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", raw)
        if not (a and b): return None
        return _norm(raw[a.end():b.start()])
    if recipe in ("ia", "plain"): return _norm(raw)
    return None

MIN_READABLE = 800   # a page with less readable text than this is treated as empty (JavaScript-only shell, login wall)
_TAG = re.compile(r"\[\s*(source|sources|system|assistant|user|context)\b[^\]\n]{0,120}\]", re.I)
_URL = re.compile(r"(?i)\b(?:https?://|www\.)[^\s)>\]\"']+")

def readable(text): return len((text or "").strip()) >= MIN_READABLE

def sanitize(text):
    """Page text is data. Remove lookalikes of the source tags we put in the reader prompt, so a page cannot pose as another source."""
    return _TAG.sub("(tag removed)", text or "")

def clean_answer(ans):
    """The reader may not send people to links. Only the entry's own source link (shown by the app, not by the reader) is allowed."""
    return _URL.sub("(link removed)", ans or "")

READING = [0]   # how many source pages are being read right now (the app shows "Reading the source")

def _fetch_raw(url):
    READING[0] += 1
    try: return _fetch_raw2(url)
    finally: READING[0] -= 1

def _fetch_raw2(url):
    import collector as C
    C.ALLOW.add("archive.org")   # hosts our collectors take from; text_url values come only from them
    with _lock:   # one fetch at a time, polite spacing between requests
        return C.get(url, limit=C.MAX_DOC_BYTES * 3, delay=QUERY_DELAY)

def _evict():
    try:
        fs = sorted((os.path.getmtime(os.path.join(CACHE_DIR, f)), f) for f in os.listdir(CACHE_DIR) if f.endswith(".txt"))
        for _, f in fs[:max(0, len(fs) - MAX_FILES)]: os.remove(os.path.join(CACHE_DIR, f))
    except OSError: pass

def source_text(doc_id, text_url, recipe, fetch=_fetch_raw, now=time.time):
    """Text of the source page (stripped, transformed), from the temporary cache or the live source. None if unavailable."""
    os.makedirs(CACHE_DIR, exist_ok=True); p = os.path.join(CACHE_DIR, doc_id + ".txt")
    try:
        if now() - os.path.getmtime(p) < TTL: return open(p, encoding="utf-8").read()
    except OSError: pass
    try:
        t = transform(fetch(text_url), recipe)
    except Exception:
        return None
    if not t: return None
    open(p, "w", encoding="utf-8").write(t); _evict()
    return t

def hydrate(hits, db_path=None, fetch=_fetch_raw):
    """hits: [(score, chunk_dict)] from the vector index. Fills in chunk text from the sources and drops chunks whose source
    is gone or changed. Returns (hits_with_text, dropped_count). Chunks that still carry stored text pass through unchanged."""
    c = L.connect(db_path); out, dropped, cache = [], 0, {}
    for score, ch in hits:
        if ch.get("text"): out.append((score, ch)); continue
        did, _, idx = ch["id"].rpartition("#")
        row = c.execute("SELECT ch.start, ch.chash, d.text_url, d.recipe FROM chunks ch JOIN documents d ON d.id=ch.doc_id WHERE ch.doc_id=? AND ch.idx=?", (did, int(idx or 0))).fetchone()
        if not row or not row["text_url"]: dropped += 1; continue
        if did not in cache: cache[did] = source_text(did, row["text_url"], row["recipe"], fetch=fetch)
        t = cache[did]
        piece = t[row["start"]:row["start"] + L.CHUNK_CHARS] if t else None
        if not piece or chash(piece) != row["chash"]:
            dropped += 1
            if t: _log_changed(c, did)
            continue
        out.append((score, dict(ch, text=sanitize(piece))))
    c.close(); return out, dropped

def _log_changed(c, did):
    try:
        L.log(c, "source_changed", did, "reader", "chunk hash differs from the source page; chunk dropped"); c.commit()
    except Exception: pass
