"""Pointer-mode research tests 1 and 2 (research only, nothing public). Usage: python3 tests/pointer_research.py 1|2
Test 1: catalogue answers from short descriptions only (no fetching). Test 2: quick read - fetch a page, read the first ~24k characters, answer."""
import sys, os, re, json, time, urllib.request, urllib.parse, urllib.robotparser
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
import library as L, source as S
OLLAMA, READER, EMB = "http://127.0.0.1:11436", "qwen3.6:35b-a3b", "qwen3-embedding:4b"
OUT = os.path.join(os.path.dirname(L.DB_PATH), "pointer_results.json")
UA = "OpenKB-research/0.1 (+https://github.com/warodri/etmw_openkb; research test, one request per page)"

def gen(prompt, n=300):
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps({"model": READER, "prompt": prompt, "stream": False, "think": False, "options": {"num_predict": n, "temperature": 0.1}}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))["response"].strip()

def emb(t):
    return json.loads(urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/embed", data=json.dumps({"model": EMB, "input": t}).encode(), headers={"Content-Type": "application/json"}), timeout=120).read())["embeddings"][0]

def cos(a, b):
    d = sum(x * y for x, y in zip(a, b)); return d / ((sum(x * x for x in a) ** .5) * (sum(y * y for y in b) ** .5))

Q1 = [
 ("Which entries are speeches or addresses by US presidents?", ["First Inaugural", "Second Inaugural", "Gettysburg", "Roosevelt", "Kennedy"]),
 ("Which entries are founding documents of the United States?", ["Declaration of Independence of the United", "United States Declaration", "Constitution", "Bill of Rights", "Mayflower"]),
 ("Which entries are about the first atomic bomb test?", ["Trinity Site", "Trinity Site: 1945", "Photos and Maps of Trinity"]),
 ("Which entries are by or about Frederick Douglass?", ["Collected Articles of Frederick Douglass", "Narrative of the Life"]),
 ("Which entries relate to Martin Luther?", ["Disputation", "Smalcald"]),
 ("Which entry is a cookbook?", ["Bread and pastry"]),
 ("Which entries are about Native Americans?", ["Indian Heroes", "Soul of the Indian"]),
 ("Which entry is about shaving?", ["Shaving made easy"]),
 ("Which entry is the ritual book of a fraternal order?", ["Eastern star"]),
 ("Which entries are open letters?", ["Open Letter on Translating", "Father Damien"]),
]

def test1():
    docs = L.connect().execute("SELECT id, title, text_url, recipe FROM documents WHERE status='live' ORDER BY title").fetchall()
    ents = []; t0 = time.time()
    for d in docs:
        t = S.source_text(d["id"], d["text_url"], d["recipe"]) or ""
        head = re.sub(r"\s+", " ", t[:2500])
        desc = gen("Write a one-sentence description (max 30 words) of this work for a library catalogue, in your own words. Say what it is and what it is about.\nTitle: %s\nOpening text: %s\nDescription:" % (d["title"], head), 120)
        ents.append({"id": d["id"], "title": d["title"], "desc": desc})
    t_desc = time.time() - t0
    for e in ents: e["vec"] = emb(e["title"] + ". " + e["desc"])
    res = []
    for q, exp in Q1:
        t = time.time(); qv = emb(q)
        ranked = sorted(ents, key=lambda e: -cos(qv, e["vec"]))[:10]
        lst = "\n".join("%d. %s - %s" % (i + 1, e["title"], e["desc"]) for i, e in enumerate(ranked))
        out = gen("Catalogue entries:\n%s\n\nQuestion: %s\nAnswer with ONLY the numbers of the entries that match, comma separated. Use only the catalogue." % (lst, q), 60)
        picked = {int(n) - 1 for n in re.findall(r"\d+", out) if 0 < int(n) <= len(ranked)}
        got = {ranked[i]["title"] for i in picked}
        is_exp = lambda title: any(x.lower() in title.lower() for x in exp)
        tp = sum(is_exp(g) for g in got); allexp = {e["title"] for e in ents if is_exp(e["title"])}
        rec = tp / max(1, len(allexp)); prec = tp / max(1, len(got)); f1 = 0 if not tp else 2 * prec * rec / (prec + rec)
        r10 = len({e["title"] for e in ranked} & allexp) / max(1, len(allexp))
        res.append({"q": q, "expected": sorted(allexp), "answered": sorted(got), "recall_top10": round(r10, 2), "precision": round(prec, 2), "recall": round(rec, 2), "f1": round(f1, 2), "s": round(time.time() - t, 1)})
        print(json.dumps(res[-1]), flush=True)
    summ = {"entries": len(ents), "describe_s_total": round(t_desc), "mean_f1": round(sum(r["f1"] for r in res) / len(res), 2), "mean_recall_top10": round(sum(r["recall_top10"] for r in res) / len(res), 2), "mean_answer_s": round(sum(r["s"] for r in res) / len(res), 1)}
    json.dump({"test1": {"summary": summ, "results": res, "sample_descriptions": [{"title": e["title"], "desc": e["desc"]} for e in ents[:6]]}}, open(OUT.replace(".json", "1.json"), "w"), indent=1); print(json.dumps(summ))

_robots = {}
def fetch(url, limit=200_000):
    h = urllib.parse.urlparse(url).hostname
    if h not in _robots:
        rp = urllib.robotparser.RobotFileParser(); rp.set_url("https://%s/robots.txt" % h)
        try: rp.read()
        except Exception: pass
        _robots[h] = rp
    if not _robots[h].can_fetch(UA, url): return None, "robots.txt disallows"
    time.sleep(5)
    try: raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read(limit).decode("utf-8", "replace")
    except Exception as e: return None, "fetch error: " + str(e)[:80]
    return raw, "ok"

def plain(raw):
    raw = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", re.sub(r"(?s)<[^>]+>", " ", raw))).strip()

API = [
 ("https://docs.python.org/3/library/json.html", "Which function serializes an object to a JSON formatted string?", "dumps"),
 ("https://docs.python.org/3/library/heapq.html", "Which function removes and returns the smallest item from the heap?", "heappop"),
 ("https://docs.python.org/3/library/collections.html", "Which class is a dict subclass for counting hashable objects?", "Counter"),
 ("https://docs.python.org/3/library/re.html", "Which function scans through a string looking for the first location where the pattern produces a match?", "search"),
 ("https://docs.python.org/3/library/os.path.html", "Which function joins path segments intelligently?", "join"),
 ("https://www.sqlite.org/limits.html", "What is the default maximum number of columns in a table?", "2000"),
 ("https://www.sqlite.org/lang_select.html", "Which keyword removes duplicate rows from a SELECT result?", "DISTINCT"),
 ("https://www.sqlite.org/wal.html", "What is the name of the shared-memory file used in WAL mode?", "shm"),
 ("https://www.sqlite.org/datatype3.html", "Which storage class stores floating point values?", "REAL"),
 ("https://docs.python.org/3/library/argparse.html", "Which method adds an argument to an ArgumentParser?", "add_argument"),
]
BOOKS = [
 (1342, "Pride and Prejudice", "According to the opening sentence, what does a single man in possession of a good fortune must be in want of?", "wife"),
 (11, "Alice's Adventures in Wonderland", "What animal does Alice see run close by her at the start?", "rabbit"),
 (84, "Frankenstein", "To whom is the first letter addressed?", "Saville"),
 (2701, "Moby Dick", "What name does the narrator give in the opening line?", "Ishmael"),
 (98, "A Tale of Two Cities", "Complete: 'It was the best of times, it was the ...'", "worst"),
 (345, "Dracula", "What is the name of the diarist in the first chapter?", "Harker"),
 (1661, "The Adventures of Sherlock Holmes", "Who is 'the woman' to Sherlock Holmes?", "Adler"),
 (120, "Treasure Island", "Who asks Dr Livesey to write the narrative of the treasure hunt (the squire)?", "Trelawney"),
 (1400, "Great Expectations", "What is the narrator's nickname?", "Pip"),
 (1260, "Jane Eyre", "What was impossible that day, because of the weather?", "walk"),
]

def test2():
    res = []
    items = [("api", u, q, a) for u, q, a in API] + [("book", "https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (i, i), q, a) for i, t, q, a in BOOKS]
    for kind, url, q, ans in items:
        t0 = time.time(); raw, st = fetch(url, 120_000 if kind == "book" else 400_000)
        rec = {"kind": kind, "url": url, "q": q, "expected": ans, "fetch": st}
        if raw is None: rec["ok"] = False; res.append(rec); print(json.dumps(rec), flush=True); continue
        if kind == "book":
            m = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw); raw = raw[m.end():] if m else raw
            text = re.sub(r"\r\n?", "\n", raw)
        else: text = plain(raw)
        first = text[:24000]; rec["answer_in_page"] = ans.lower() in text.lower(); rec["answer_in_first_chunk"] = ans.lower() in first.lower()
        t1 = time.time(); out = gen("Answer ONLY from the page text below. If it is not there, say: not on the page. Be brief.\n\nPAGE:\n%s\n\nQuestion: %s\nAnswer:" % (first, q), 120)
        rec.update({"answer": out[:160], "correct": ans.lower() in out.lower(), "fetch_s": round(t1 - t0, 1), "read_s": round(time.time() - t1, 1), "chars_read": len(first)})
        res.append(rec); print(json.dumps(rec), flush=True)
    for k in ("api", "book"):
        r = [x for x in res if x["kind"] == k]
        print(k, "correct", sum(bool(x.get("correct")) for x in r), "/", len(r), "answer in first chunk", sum(bool(x.get("answer_in_first_chunk")) for x in r), "mean read s", round(sum(x.get("read_s", 0) for x in r) / len(r), 1), "mean fetch s", round(sum(x.get("fetch_s", 0) for x in r) / len(r), 1))
    json.dump({"test2": res}, open(OUT.replace(".json", "2.json"), "w"), indent=1)

if __name__ == "__main__":
    test1() if sys.argv[1] == "1" else test2()
