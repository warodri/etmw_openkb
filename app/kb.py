"""OpenKB RAG core - shared by the HTTP server (app/server.py) and the MCP server
(app/mcp_server.py). Stdlib only. Loads the library index from data/embeddings.json
and answers through a local ollama instance.

Configuration via environment:
  OPENKB_DATA          library directory (default: <repo>/data)
  OPENKB_OLLAMA_HOST   ollama base URL (default: http://127.0.0.1:11434)
  OPENKB_READER_MODEL  reader model tag (default: qwen3.6:35b-a3b)
  OPENKB_EMBED_MODEL   embedding model tag (default: qwen3-embedding:4b)
"""
import json, os, urllib.request

DATA = os.environ.get("OPENKB_DATA") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OLLAMA = os.environ.get("OPENKB_OLLAMA_HOST", "http://127.0.0.1:11434")
READER = os.environ.get("OPENKB_READER_MODEL", "qwen3.6:35b-a3b")
EMBED = os.environ.get("OPENKB_EMBED_MODEL", "qwen3-embedding:4b")
TOP_K = 5
MAX_OUT_TOKENS = 400

_INDEX = None

def _load():
    global _INDEX
    if _INDEX is None:
        path = os.path.join(DATA, "embeddings.json")
        if not os.path.isfile(path):
            raise SystemExit(
                "OpenKB library index not found at %s - run install.sh first (see docs/INSTALL.md)" % path)
        doc = json.load(open(path))
        _INDEX = (doc["chunks"], doc["vectors"])
    return _INDEX

def ollama_embed(text):
    req = urllib.request.Request(OLLAMA + "/api/embed", data=json.dumps({"model": EMBED, "input": text}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["embeddings"][0]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b)); na = sum(x*x for x in a)**0.5; nb = sum(x*x for x in b)**0.5
    return dot / (na * nb) if na and nb else 0.0

def retrieve(q):
    chunks, embs = _load()
    qe = ollama_embed(q)
    scored = sorted(((cosine(qe, e), c) for c, e in zip(chunks, embs)), key=lambda t: -t[0])
    return scored[:TOP_K]

def generate(prompt, max_tokens, timeout=300):
    req = urllib.request.Request(OLLAMA + "/api/generate",
        data=json.dumps({"model": READER, "prompt": prompt, "stream": False,
                         "think": False, "options": {"num_predict": max_tokens, "temperature": 0.2}}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))["response"].strip()

def classify(q):
    prompt = ("Classify the user message into exactly one word. "
              "CHAT = greeting, small talk, thanks, opinion chat, a question about you, this demo, or OpenKB itself, or a clarification about the conversation. "
              "FACT = a request for factual knowledge about the world.\n"
              f"Message: {q}\nOne word:")
    out = generate(prompt, 8, timeout=120).upper()
    return "CHAT" if "CHAT" in out else "FACT"

def chat(q):
    prompt = ("You are the friendly assistant of the OpenKB demo. OpenKB is a community-held knowledge base "
              "read by a small local AI model: people donate expert content under an open licence, and the model "
              "answers factual questions ONLY from that donated library, citing sources. This demo runs a 50-document "
              "test library (English and Spanish). Be warm, brief, natural. Never answer factual world-knowledge "
              "questions here; if the user wants facts, invite them to just ask and you will check the library.\n\n"
              f"User: {q}\nAssistant:")
    return generate(prompt, 200, timeout=180), [], False

def answer(q):
    """Returns (answer_text, sources_list, not_found). The refusal string and the
    not_found flag are computed here, server-side, so they survive any client."""
    if classify(q) == "CHAT":
        return chat(q)
    hits = retrieve(q)
    ctx = "\n\n".join(f"[source: {c.get('source','doc')}]\n{c['text']}" for _, c in hits)
    prompt = ("You are the OpenKB reader. Answer ONLY from the context below. "
              "Always cite the source filename(s) you used. If the context does not contain "
              "the answer, reply exactly: not in the KB\n\n"
              f"Context:\n{ctx}\n\nQuestion: {q}\nAnswer:")
    out = generate(prompt, MAX_OUT_TOKENS)
    not_found = "not in the kb" in out.lower()
    if not_found:
        out = ("Honestly? The OpenKB library does not have that one yet - and I would rather say so "
               "than guess. I only answer from the documents people have donated.")
    return out, [c.get("source", "doc") for _, c in hits], not_found
