"""Move stored-text documents to reference-only. Usage: python3 app/migrate_refs.py [--purge]
Step 1 (default, additive): for every live document with stored chunk text, work out the source text URL and recipe, fetch it
politely, check every stored chunk equals the source slice at its offset, then record text_url, recipe, start and chash.
Step 2 (--purge): only for documents that passed step 1 AND whose live check passes again, blank the stored chunk text.
Documents that fail are reported and left alone."""
import sys, os, re, json, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library as L, collector as C, source as S
C.ALLOW.add("archive.org")

def locate(doc):
    u = doc["source_url"] or ""
    m = re.match(r"https://www\.gutenberg\.org/ebooks/(\d+)$", u)
    if m: return f"https://www.gutenberg.org/cache/epub/{m.group(1)}/pg{m.group(1)}.txt", "gutenberg"
    m = re.match(r"https://archive\.org/details/([^/?#]+)$", u)
    if m:
        item = m.group(1)
        md = json.loads(C.get(f"https://archive.org/metadata/{urllib.parse.quote(item)}"))
        f = [x for x in md.get("files", []) if x.get("name", "").endswith("_djvu.txt")]
        if f: return f"https://archive.org/download/{urllib.parse.quote(item)}/{urllib.parse.quote(f[0]['name'])}", "ia"
    return None, None

def main(purge=False):
    c = L.connect(); res = {"ok": [], "fail": []}
    docs = c.execute("SELECT * FROM documents WHERE status IN ('live','hidden')").fetchall()
    for d in docs:
        rows = c.execute("SELECT idx, text FROM chunks WHERE doc_id=? ORDER BY idx", (d["id"],)).fetchall()
        if not rows: continue
        try:
            url, recipe = (d["text_url"], d["recipe"]) if d["text_url"] else locate(d)
            if not url: raise ValueError("no known text source for " + str(d["source_url"]))
            raw = C.get(url, limit=C.MAX_DOC_BYTES * 3, delay=5.0)
            t = S.transform(raw, recipe)
            if not t: raise ValueError("transform failed")
            for r in rows:
                st = r["idx"] * (L.CHUNK_CHARS - L.OVERLAP)
                if r["text"] and t[st:st + L.CHUNK_CHARS] != r["text"]: raise ValueError(f"chunk {r['idx']} differs from the source")
            n = len(L.chunk_text(t))
            if n != len(rows): raise ValueError(f"chunk count differs: stored {len(rows)}, source {n}")
            for r in rows:
                st = r["idx"] * (L.CHUNK_CHARS - L.OVERLAP); piece = t[st:st + L.CHUNK_CHARS]
                c.execute("UPDATE chunks SET start=?, chash=? WHERE doc_id=? AND idx=?", (st, S.chash(piece), d["id"], r["idx"]))
            c.execute("UPDATE documents SET text_url=?, recipe=? WHERE id=?", (url, recipe, d["id"]))
            if purge: c.execute("UPDATE chunks SET text='' WHERE doc_id=?", (d["id"],))
            L.log(c, "reference_only" if purge else "reference_verified", d["id"], "migrate_refs", url); c.commit()
            res["ok"].append(d["id"])
        except Exception as e:
            res["fail"].append([d["id"], d["title"][:50], str(e)[:120]])
    print(json.dumps({"ok": len(res["ok"]), "fail": res["fail"], "purged": purge}))

if __name__ == "__main__": main("--purge" in sys.argv)
