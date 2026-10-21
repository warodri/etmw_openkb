#!/usr/bin/env python3
"""Ingest donated/test documents into chunks with source metadata.

Reads data/fixtures/*.md (or data/donations/*.md), chunks at ~800 tokens
(approximated as 3200 chars) with 15% overlap, writes data/chunks.json.
Stdlib only.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIRS = [os.path.join(ROOT, "data", "donations"), os.path.join(ROOT, "data", "fixtures")]
OUT = os.path.join(ROOT, "data", "chunks.json")
CHUNK_CHARS = 3200
OVERLAP = int(CHUNK_CHARS * 0.15)

def chunks_for(text, source):
    text = text.strip()
    if not text:
        return []
    out, start, i = [], 0, 0
    while start < len(text):
        out.append({"id": f"{source}#{i}", "source": source, "text": text[start:start + CHUNK_CHARS]})
        i += 1
        start += CHUNK_CHARS - OVERLAP
    return out

def main():
    all_chunks = []
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".md"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    all_chunks.extend(chunks_for(f.read(), fn))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=1)
    print(f"{len(all_chunks)} chunks from {len({c['source'] for c in all_chunks})} documents -> {OUT}")

if __name__ == "__main__":
    sys.exit(main())
