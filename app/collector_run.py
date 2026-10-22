"""Daily collector run with a load monitor. Usage: python3 app/collector_run.py [--n 25] [--publish] [--model-check]
State: data/collector_state.json (ids already tried). Log: data/collector_runs.jsonl (one JSON line per run)."""
import sys, os, re, io, csv, json, time, subprocess, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collector as C, library as L
import collector_ia as IA
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data"); os.makedirs(DATA, exist_ok=True)
STATE, RUNS = os.path.join(DATA, "collector_state.json"), os.path.join(DATA, "collector_runs.jsonl")
ASK = "http://127.0.0.1:8641/ask"
SKIP_SUBJ = re.compile(r"fiction|poetry|drama|stories|novel|juvenile|humor|plays", re.I)

def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout
    except Exception: return ""

def snapshot():
    mem = sh("vm_stat"); ps = int((re.search(r"page size of (\d+)", mem) or [0, 16384])[1])
    g = lambda k: int((re.search(k + r":\s+(\d+)", mem) or [0, 0])[1]) * ps / 1e9
    top = sh("top -l 1 -n 0 | grep 'CPU usage'")
    oll = sh("ps -axo rss,comm | grep -i '[o]llama' | awk '{s+=$1} END {print s/1048576}'").strip()
    return {"load1": round(os.getloadavg()[0], 2), "cpu": top.strip()[:80], "mem_free_gb": round(g("Pages free") + g("Pages inactive"), 1), "ollama_rss_gb": float(oll or 0)}

def embed_latency():
    t = time.time()
    try: L.ollama_embed("latency probe sentence about public libraries"); return round(time.time() - t, 2)
    except Exception: return None

def ask_time():
    t = time.time()
    try:
        req = urllib.request.Request(ASK, data=json.dumps({"q": "What does the Bill of Rights say about free speech?"}).encode(), headers={"Content-Type": "application/json"})
        json.load(urllib.request.urlopen(req, timeout=180)); return round(time.time() - t, 2)
    except Exception: return None

def catalog():
    raw = C.get("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv", limit=40_000_000)
    for r in csv.DictReader(io.StringIO(raw)):
        if r.get("Type") == "Text" and r.get("Language") == "en" and not SKIP_SUBJ.search(r.get("Subjects", "") + r.get("Bookshelves", "")):
            yield int(r["Text#"]), r.get("Title", "")

def main():
    import fcntl
    lockf = open(os.path.join(DATA, "collector.lock"), "w")
    try: fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        open(RUNS, "a").write(json.dumps({"skipped": "another collector run is in progress", "at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n"); print("another run in progress, skipping"); return
    a = sys.argv[1:]; source = a[a.index("--source") + 1] if "--source" in a else "gutenberg"; n = int(a[a.index("--n") + 1]) if "--n" in a else 25
    publish, mc = "--publish" in a, "--model-check" in a
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"tried": []}
    key = "tried" if source == "gutenberg" else "tried_" + source; collect_fn = C.collect if source == "gutenberg" else IA.collect
    tried = set(st.get(key, []));  run = {"source": source, "start": time.strftime("%Y-%m-%dT%H:%M:%S"), "before": snapshot(), "ask_before_s": ask_time(), "embed_before_s": embed_latency(), "docs": [], "fail": {}}
    t0 = time.time(); spent = 0; todo = []
    for i, title in (catalog() if source == "gutenberg" else IA.catalog()):
        if i not in tried: todo.append(i)
        if len(todo) >= n * 6: break          # candidate pool; many are skipped for size
    pub = 0; probes = []
    for i in todo:
        if pub >= n or spent >= C.RUN_BYTES: break
        r = collect_fn(i, publish, mc, spent); tried.add(i); spent += r["bytes"] if r["ok"] else 0
        if r["ok"]: pub += 1; run["docs"].append({"id": i, "title": r.get("title"), "bytes": r["bytes"]})
        else: k = re.sub(r"[\d(].*", "", r["why"])[:50].strip(); run["fail"][k] = run["fail"].get(k, 0) + 1
        if pub and pub % 8 == 0 and len(probes) < pub // 8: probes.append({"after_docs": pub, "embed_s": embed_latency(), **snapshot()})
    run["during"] = probes; run["seconds"] = round(time.time() - t0); run["published"] = pub if publish else 0
    run["dry_run_passes"] = 0 if publish else pub; run["bytes"] = spent; run["candidates_tried"] = len(todo)
    run["after"] = snapshot(); run["ask_after_s"] = ask_time(); run["embed_after_s"] = embed_latency(); run["live_docs"] = L.stats()["documents"]
    st[key] = sorted(tried, key=str); json.dump(st, open(STATE, "w"))
    open(RUNS, "a").write(json.dumps(run) + "\n"); print(json.dumps(run, indent=1))
if __name__ == "__main__": main()
