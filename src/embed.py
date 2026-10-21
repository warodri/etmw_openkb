#!/usr/bin/env python3
"""Embed chunks with Qwen3-Embedding-4B via the OpenKB ollama instance.

Reads data/chunks.json, calls the ollama /api/embed endpoint in batches,
writes data/embeddings.json. Stdlib only.
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = os.environ.get("OPENKB_OLLAMA", "http://127.0.0.1:11434")
MODEL = "qwen3-embedding:4b"
BATCH = 16

def embed(texts):
    req = urllib.request.Request(
        HOST + "/api/embed",
        data=json.dumps({"model": MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["embeddings"]

def main():
    with open(os.path.join(ROOT, "data", "chunks.json"), encoding="utf-8") as f:
        chunks = json.load(f)
    vectors = []
    for i in range(0, len(chunks), BATCH):
        vectors.extend(embed([c["text"] for c in chunks[i:i + BATCH]]))
        print(f"embedded {min(i + BATCH, len(chunks))}/{len(chunks)}", flush=True)
    out = {"model": MODEL, "chunks": chunks, "vectors": vectors}
    with open(os.path.join(ROOT, "data", "embeddings.json"), "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"{len(vectors)} embeddings, dim {len(vectors[0]) if vectors else 0}")

if __name__ == "__main__":
    sys.exit(main())
