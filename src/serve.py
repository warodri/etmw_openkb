#!/usr/bin/env python3
"""Retrieval + reader: answer only from retrieved chunks, cite sources, refuse.

Usage: python3 serve.py "question here"
Stdlib only. Reader: qwen3.6:35b-a3b on the OpenKB ollama instance.
"""
import json, math, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = os.environ.get("OPENKB_OLLAMA", "http://127.0.0.1:11434")
EMBED_MODEL = "qwen3-embedding:4b"
READER_MODEL = "qwen3.6:35b-a3b"
TOP_K = 5
REFUSAL = "not in the KB"

def post(path, payload, timeout=600):
    req = urllib.request.Request(HOST + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

def load_store():
    with open(os.path.join(ROOT, "data", "embeddings.json"), encoding="utf-8") as f:
        return json.load(f)

def answer(question, store=None):
    if store is None:
        store = load_store()
    qvec = post("/api/embed", {"model": EMBED_MODEL, "input": [question]})["embeddings"][0]
    scored = sorted(((cosine(qvec, v), c) for c, v in zip(store["chunks"], store["vectors"])),
                    key=lambda t: t[0], reverse=True)[:TOP_K]
    context = "\n\n".join(f"[source: {c['source']}]\n{c['text']}" for _, c in scored)
    prompt = (
        "You are the OpenKB reader. Answer ONLY from the context below. "
        "Always cite the source filename(s) you used. If the context does not contain "
        f"the answer, reply exactly: {REFUSAL}\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:")
    res = post("/api/generate", {"model": READER_MODEL, "prompt": prompt, "stream": False,
                                 "options": {"temperature": 0.2}})
    tok_s = (res.get("eval_count", 0) / (res.get("eval_duration", 1) / 1e9)) if res.get("eval_duration") else 0
    return {"question": question, "answer": res.get("response", "").strip(),
            "sources": [c["source"] for _, c in scored], "tok_s": round(tok_s, 1)}

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is OpenKB?"
    r = answer(q)
    print(json.dumps(r, ensure_ascii=False, indent=1))
