"""OpenKB MCP server - read-only, stdio transport, stdlib only.

Exposes the library to agent frameworks (opencode and others) as two tools:
  kb_search(query)  -> top matching chunks with source names
  kb_answer(query)  -> grounded answer with sources, or the explicit refusal

This server has its OWN quota identity, separate from the web UI guards: its own
daily cap, its own counter in data/openkb.db, its own log data/agent_requests.log.
A runaway agent trips its own cap, never the users'.

Environment: same OPENKB_* vars as app/kb.py, plus
  OPENKB_AGENT_DAILY_CAP   max tool calls per UTC day (default: 100)

Protocol: newline-delimited JSON-RPC 2.0 over stdin/stdout (MCP stdio transport).
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kb

DATA = kb.DATA
DB = os.path.join(DATA, "openkb.db")
LOG = os.path.join(DATA, "agent_requests.log")
IDENTITY = "agent-mcp"
DAILY_CAP = int(os.environ.get("OPENKB_AGENT_DAILY_CAP", "100"))

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "openkb", "version": "0.1.0"}
TOOLS = [
    {"name": "kb_answer",
     "description": ("Ask the OpenKB library a question. Returns a grounded answer with its source "
                     "documents, or an explicit refusal when the library does not contain the answer. "
                     "Always repeat the returned sources when you use the answer. Never replace a "
                     "refusal with your own knowledge."),
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string", "description": "The question to answer from the library."}},
                     "required": ["query"]}},
    {"name": "kb_search",
     "description": ("Search the OpenKB library. Returns the top matching chunks with their source "
                     "document names and similarity scores."),
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string", "description": "The search query."}},
                     "required": ["query"]}},
]

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS quotas (identity TEXT, day TEXT, n INTEGER, PRIMARY KEY (identity, day))")
    return c

def logline(kind, detail):
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": kind,
                                "identity": IDENTITY, "detail": detail[:600]}) + "\n")
    except OSError:
        pass

def check_quota():
    """True if this call is allowed; increments the counter. Own identity, own cap."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    c = db()
    row = c.execute("SELECT n FROM quotas WHERE identity=? AND day=?", (IDENTITY, day)).fetchone()
    n = row[0] if row else 0
    if n >= DAILY_CAP:
        c.close()
        logline("quota-blocked", f"cap {DAILY_CAP} reached")
        return False
    c.execute("INSERT INTO quotas (identity, day, n) VALUES (?,?,1) "
              "ON CONFLICT(identity, day) DO UPDATE SET n=n+1", (IDENTITY, day))
    c.commit(); c.close()
    return True

def tool_result(payload):
    return {"content": [{"type": "text", "text": payload if isinstance(payload, str) else json.dumps(payload, indent=1)}]}

def call_tool(name, args):
    if not check_quota():
        return tool_result("OpenKB agent quota reached for today. Back tomorrow."), True
    q = (args or {}).get("query", "").strip()
    if not q:
        return tool_result("Empty query."), True
    try:
        if name == "kb_search":
            hits = kb.retrieve(q)
            out = [{"source": c.get("source", "doc"), "score": round(s, 4), "text": c["text"]} for s, c in hits]
            logline("search", q)
            return tool_result(json.dumps({"results": out}, indent=1)), False
        if name == "kb_answer":
            text, sources, not_found = kb.answer(q)
            logline("answer", f"{q} | not_found={not_found}")
            return tool_result(json.dumps({"answer": text, "sources": sources, "not_found": not_found}, indent=1)), False
        return tool_result(f"Unknown tool: {name}"), True
    except Exception as e:
        logline("error", str(e)[:300])
        return tool_result("The local model could not answer. Try again."), True

def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, rid = req.get("method"), req.get("id")
        if method in ("notifications/initialized", "notifications/cancelled"):
            continue  # notifications get no reply
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = req.get("params") or {}
            result, is_error = call_tool(params.get("name"), params.get("arguments"))
            out = {"jsonrpc": "2.0", "id": rid, "result": result}
            if is_error:
                out["result"]["isError"] = True
            send(out)
        else:
            if rid is not None:
                send({"jsonrpc": "2.0", "id": rid,
                      "error": {"code": -32601, "message": f"Method not found: {method}"}})

if __name__ == "__main__":
    main()
