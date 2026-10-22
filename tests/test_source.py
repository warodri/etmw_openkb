import os, sys, tempfile, time
d = tempfile.mkdtemp(); os.environ["OPENKB_LIBRARY_DB"] = d + "/l.db"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
import library as L, source as S
S.CACHE_DIR = d + "/cache"
def ok(c, m): print(("PASS " if c else "FAIL ") + m); assert c, m
import random
random.seed(5); W = ["river","fox","stone","lantern","harvest","orbit","copper","meadow","signal","winter","anchor","violet","engine","pocket","garden","thunder"]
body = " ".join(random.choice(W) + str(random.randint(0, 999)) for _ in range(1500)) + " quick unique ending sentence about otters."
fake = lambda v: [float(len(v) % 7), 1.0, 0.5]
r = L.submit(text=body, title="Fox", origin="collector", licence="Public domain", source_url="https://www.gutenberg.org/ebooks/1", text_url="https://www.gutenberg.org/cache/epub/1/pg1.txt", recipe="plain", contributor="t", declarations=None, embed=fake)
ok(r["ok"], "reference-only document published")
c = L.connect(); n = c.execute("SELECT count(*), sum(length(text)) FROM chunks WHERE doc_id=?", (r["doc_id"],)).fetchone()
ok(n[0] >= 2 and n[1] == 0, "no chunk text stored")
hits = [(1.0, {"id": r["doc_id"] + "#1", "source": "Fox", "doc_id": r["doc_id"], "text": ""})]
got, dropped = S.hydrate(hits, fetch=lambda u: body)
ok(len(got) == 1 and dropped == 0 and got[0][1]["text"] == body[L.CHUNK_CHARS - L.OVERLAP:][:L.CHUNK_CHARS], "chunk text cut from the source by offset, hash verified")
os.remove(S.CACHE_DIR + "/" + r["doc_id"] + ".txt")
got, dropped = S.hydrate(hits, fetch=lambda u: (_ for _ in ()).throw(OSError("gone")))
ok(got == [] and dropped == 1, "source gone: chunk dropped, no guessing")
got, dropped = S.hydrate(hits, fetch=lambda u: body.replace("fox", "fix"))
ok(got == [] and dropped == 1, "source changed: hash mismatch drops the chunk")
os.remove(S.CACHE_DIR + "/" + r["doc_id"] + ".txt") if os.path.exists(S.CACHE_DIR + "/" + r["doc_id"] + ".txt") else None
S.hydrate(hits, fetch=lambda u: body)
calls = []
S.hydrate(hits, fetch=lambda u: calls.append(u) or body)
ok(calls == [], "second read is served from the 24 h temporary cache")
p = S.CACHE_DIR + "/" + r["doc_id"] + ".txt"; old = time.time() - 25 * 3600; os.utime(p, (old, old))
S.hydrate(hits, fetch=lambda u: calls.append(u) or body)
ok(len(calls) == 1, "cache entry older than 24 h is fetched again")
S.MAX_FILES = 1
for i in range(3): open(S.CACHE_DIR + f"/x{i}.txt", "w").write("t"); time.sleep(0.01)
S._evict(); ok(len([f for f in os.listdir(S.CACHE_DIR) if f.endswith(".txt")]) == 1, "cache is capped")
print("source tests done")
