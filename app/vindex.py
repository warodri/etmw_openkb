"""Disk-based vector index (sqlite-vec). No vectors are held in Python memory.

Layout (data/vindex.db): `meta` (rowid, doc_id, cid, source, text) and a `vec` vec0 table with
float32[DIM] cosine vectors, aligned by rowid. The index is derived: library.db stays the source of
truth, `sync()` adds new live documents and drops removed ones, so a takedown also leaves the index.
"""
import os, sqlite3, struct, threading
import sqlite_vec

DIM = 2560
_lock = threading.Lock()

def _pack(v): return struct.pack(f"{len(v)}f", *v)

def connect(path):
    c = sqlite3.connect(path, timeout=30)
    c.enable_load_extension(True); sqlite_vec.load(c); c.enable_load_extension(False)
    c.execute("CREATE TABLE IF NOT EXISTS meta (rowid INTEGER PRIMARY KEY, doc_id TEXT, cid TEXT, source TEXT, text TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS meta_doc ON meta(doc_id)")
    c.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec USING vec0(embedding float[{DIM}] distance_metric=cosine)")
    return c

def sync(path, wanted):
    """wanted: {doc_id: callable -> [(chunk_dict, vector)]}. Adds missing docs, deletes docs not wanted. Returns (added, removed)."""
    with _lock:
        c = connect(path)
        have = {r[0] for r in c.execute("SELECT DISTINCT doc_id FROM meta")}
        gone = have - set(wanted); new = [d for d in wanted if d not in have]
        for d in gone:
            ids = [r[0] for r in c.execute("SELECT rowid FROM meta WHERE doc_id=?", (d,))]
            c.executemany("DELETE FROM vec WHERE rowid=?", [(i,) for i in ids]); c.execute("DELETE FROM meta WHERE doc_id=?", (d,))
        for d in new:
            for ch, v in wanted[d]():
                cur = c.execute("INSERT INTO meta(doc_id,cid,source,text) VALUES (?,?,?,?)", (d, ch["id"], ch["source"], ch["text"]))
                c.execute("INSERT INTO vec(rowid, embedding) VALUES (?,?)", (cur.lastrowid, _pack(v)))
        c.commit(); c.close()
        return len(new), len(gone)

def search(path, qvec, k=5):
    """[(score, chunk_dict)] best first; score = cosine similarity."""
    c = connect(path)
    rows = c.execute("SELECT m.doc_id, m.cid, m.source, m.text, v.distance FROM (SELECT rowid, distance FROM vec WHERE embedding MATCH ? AND k=?) v JOIN meta m ON m.rowid=v.rowid ORDER BY v.distance", (_pack(qvec), k)).fetchall()
    c.close()
    return [(1.0 - r[4], {"id": r[1], "source": r[2], "doc_id": r[0], "text": r[3]}) for r in rows]

def count(path):
    c = connect(path); n = c.execute("SELECT count(*) FROM meta").fetchone()[0]; c.close(); return n
