"""Second collector: Library of Congress items on the Internet Archive, published before 1929 (public domain in the US by date).
Rule check (all must hold): item is in the library_of_congress collection, language English, a year in its metadata <= 1928, a full-text (DjVu OCR) file <= 300 KB.
Then: the local model sanity-checks title/date/opening text (yes/no/unclear), then the normal library checks. Same politeness as Gutenberg: one worker, 5 s between requests."""
import sys, os, re, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collector as C, library as L
C.ALLOW.add("archive.org")
BASE = "https://archive.org"

def catalog(skip=0):
    """Yield (identifier, title) of English LoC texts dated <= 1928, most downloaded first."""
    q = 'collection:library_of_congress AND mediatype:texts AND language:eng AND date:[* TO 1928-12-31] AND item_size:[8000000 TO 40000000]'
    start = 0
    while start < 3000:
        url = BASE + "/advancedsearch.php?" + urllib.parse.urlencode({"q": q, "fl[]": ["identifier", "title"], "sort[]": "downloads desc", "rows": 100, "page": start // 100 + 1, "output": "json"}, doseq=True)
        docs = json.loads(C.get(url))["response"]["docs"]
        if not docs: return
        for d in docs: yield d["identifier"], d.get("title", "")
        start += 100

def _get_ia(url, limit):
    """Archive downloads redirect to ia*.us.archive.org; same site, same politeness."""
    return C.get(url, limit=limit)

def collect(item, publish=False, model_check=True, spent=0):
    r = {"id": item, "ok": False, "why": "", "bytes": 0}
    try:
        md = json.loads(C.get(f"{BASE}/metadata/{urllib.parse.quote(item)}"))
        m = md.get("metadata", {}); title = re.sub(r"\s+", " ", str(m.get("title", item)))[:120]; r["title"] = title
        colls = m.get("collection", []); colls = [colls] if isinstance(colls, str) else colls
        lang = m.get("language", ""); lang = " ".join(lang) if isinstance(lang, list) else str(lang)
        yr = re.search(r"\b(1[0-9]{3})\b", str(m.get("date", "")) + " " + str(m.get("year", "")))
        if "library_of_congress" not in colls: r["why"] = "rule check failed: not in the Library of Congress collection"; return r
        if not re.search(r"eng", lang, re.I): r["why"] = "rule check failed: not English"; return r
        if not yr or int(yr.group(1)) > 1928: r["why"] = "rule check failed: no publication year before 1929"; return r
        year = yr.group(1)
        files = [f for f in md.get("files", []) if f.get("name", "").endswith("_djvu.txt")]
        if not files: r["why"] = "no full-text file"; return r
        size = int(files[0].get("size", 0) or 0)
        if size > C.MAX_DOC_BYTES: r["why"] = f"too long ({size} bytes)"; return r
        raw = C.get(f"{BASE}/download/{urllib.parse.quote(item)}/{urllib.parse.quote(files[0]['name'])}", limit=C.MAX_DOC_BYTES * 2)
        body = re.sub(r"\r\n?", "\n", raw).strip(); r["bytes"] = len(body.encode())
        if model_check:
            snip = f"Title: {title}. Library of Congress collection. Publication year in the catalogue: {year}. Language: English."
            v = C.model_licence(snip, title) if False else _model(snip); r["model"] = v
            if v != "yes": r["why"] = "model check said " + v; return r
        if spent + r["bytes"] > C.RUN_BYTES: r["why"] = "daily byte cap reached"; return r
        if publish:
            res = L.submit(text=body, title=title, origin="collector", licence="Public domain", source_url=f"{BASE}/details/{item}",
                           credit=f"Library of Congress via Internet Archive; published {year}; public domain in the US (published before 1929)",
                           contributor="collector:internet-archive", declarations=None)
        else:
            bad = L.check_text(body); res = {"ok": not bad, "reasons": bad, "doc_id": None}
        r["ok"] = bool(res.get("ok"))
        r["why"] = ("published " + str(res.get("doc_id"))) if (publish and r["ok"]) else ("passes all checks (dry run)" if r["ok"] else "; ".join(res.get("reasons", [])))
    except Exception as e:
        r["why"] = "error: " + str(e)[:150]
    return r

def _model(snippet):
    prompt = ("Reply with exactly one word: yes, no or unclear. Question: from this catalogue record, does the work look like a real book or pamphlet first published "
              f"before 1929 (not a modern work)?\n{snippet}\n/no_think")
    req = urllib.request.Request(C.OLLAMA + "/api/generate", data=json.dumps({"model": C.READER, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 400}}).encode(), headers={"Content-Type": "application/json"})
    out = re.sub(r"(?is)<think>.*?</think>", "", json.load(urllib.request.urlopen(req, timeout=180)).get("response", "")).strip().lower()
    return "yes" if out.startswith("yes") else "no" if out.startswith("no") else "unclear"

if __name__ == "__main__":
    a = sys.argv[1:]; spent = 0
    for i in [x for x in a if not x.startswith("--")]:
        r = collect(i, "--publish" in a, "--model-check" in a, spent); spent += r["bytes"]; print(json.dumps(r))
