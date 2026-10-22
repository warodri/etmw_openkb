"""First collector: Project Gutenberg, public domain only. Small, polite, allow-listed.
Usage: python3 app/collector.py [--publish] [--model-check] [--max N] ID [ID ...]
Default is a DRY RUN: it fetches and runs every check but publishes nothing.
Flow per book: robots.txt -> ebook page says public domain in the USA -> (local model reads the rights text: yes/no/unclear) -> plain text ->
strip the Gutenberg licence boilerplate -> size cap -> library checks (duplicates, spam, injection, quality) -> provenance record -> publish.
Anything that fails is logged and dropped. Nothing goes to a human queue."""
import sys, os, re, time, json, urllib.request, urllib.parse, urllib.robotparser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library as L

ALLOW = {"www.gutenberg.org"}          # allow-list: a host not here is never fetched
UA = "OpenKB-collector/0.1 (+https://github.com/warodri/etmw_openkb; public-domain text only)"
DELAY = 5.0                            # seconds between requests
MAX_DOC_BYTES = 150_000                # first runs: short works only
RUN_BYTES = 600_000                    # daily byte cap per run
OLLAMA, READER = "http://127.0.0.1:11436", "qwen3.6:35b-a3b"
_last = [0.0]; _robots = {}

def get(url, limit=3_000_000):
    h = urllib.parse.urlparse(url).hostname
    if h not in ALLOW: raise ValueError("host not on the allow-list: " + str(h))
    if h not in _robots:
        rp = urllib.robotparser.RobotFileParser(); rp.set_url(f"https://{h}/robots.txt")
        try: rp.read()
        except Exception: pass
        _robots[h] = rp
    if not _robots[h].can_fetch(UA, url): raise ValueError("robots.txt disallows " + url)
    wait = DELAY - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    _last[0] = time.time()
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read(limit).decode("utf-8", "replace")

def rights_snippet(page):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", page)))
    m = re.search(r"Copyright Status\s+(.{0,80})", t) or re.search(r"(.{0,60}Public domain in the USA.{0,40})", t, re.I)
    return (m.group(0) if m else "")[:200]

def model_licence(snippet, title):
    prompt = ("Reply with exactly one word: yes, no or unclear. Question: does this rights statement from a Project Gutenberg book page say the book is in the "
              f"public domain (free to copy and reuse)?\nBook: {title}\nStatement: {snippet}\n/no_think")
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps({"model": READER, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 400}}).encode(), headers={"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=180)).get("response", "")
    out = re.sub(r"(?is)<think>.*?</think>", "", out).strip().lower()
    return "yes" if out.startswith("yes") else "no" if out.startswith("no") else "unclear"

def strip_boiler(raw):
    a = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw)
    b = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", raw)
    return raw[a.end():b.start()] if a and b else None

def collect(ebook_id, publish=False, model_check=True, spent=0):
    r = {"id": ebook_id, "ok": False, "why": "", "bytes": 0}
    page_url = f"https://www.gutenberg.org/ebooks/{ebook_id}"
    try:
        page = get(page_url)
        title = (re.search(r"<title>(.*?)(?: by .*?)?\s*\|", page, re.S) or re.search(r"<title>(.*?)</title>", page, re.S)).group(1).strip()
        title = re.sub(r"\s+", " ", title)[:120]; r["title"] = title
        snip = rights_snippet(page)
        if not re.search(r"Public domain in the USA", snip, re.I): r["why"] = "rule check failed: page does not say public domain in the USA (" + snip[:80] + ")"; return r
        if model_check:
            v = model_licence(snip, title); r["model"] = v
            if v != "yes": r["why"] = "model licence check said " + v; return r
        raw = get(f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt", limit=MAX_DOC_BYTES * 3)
        body = strip_boiler(raw)
        if body is None: r["why"] = "could not find the start/end markers"; return r
        body = re.sub(r"\r\n?", "\n", body).strip(); r["bytes"] = len(body.encode())
        if len(body.encode()) > MAX_DOC_BYTES: r["why"] = f"too long for the first runs ({len(body.encode())} bytes)"; return r
        if spent + r["bytes"] > RUN_BYTES: r["why"] = "daily byte cap reached"; return r
        res = L.submit(text=body, title=title, origin="collector", licence="Public domain", source_url=page_url, credit="Project Gutenberg (public domain in the USA)",
                       contributor="collector:gutenberg", declarations=None, **({} if publish else {"dry_run": True})) if publish else {"ok": not L.check_text(body), "reasons": L.check_text(body), "doc_id": None}
        r["ok"] = bool(res.get("ok")); r["why"] = "published " + str(res.get("doc_id")) if (publish and r["ok"]) else ("passes all checks (dry run)" if r["ok"] else "; ".join(res.get("reasons", [])))
    except Exception as e:
        r["why"] = "error: " + str(e)[:150]
    return r

if __name__ == "__main__":
    a = sys.argv[1:]; publish = "--publish" in a; mc = "--model-check" in a
    ids = [x for x in a if x.isdigit()]; spent = 0
    for i in ids:
        r = collect(int(i), publish, mc, spent); spent += r["bytes"]
        print(json.dumps(r)); 
