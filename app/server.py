#!/usr/bin/env python3
"""OpenKB local server - hardened, single-file, stdlib only.
Serves the Angular UI + JSON API backed by the library index in data/ and a local
ollama instance. Guards: per-IP + global rate limit, daily cap, input/output length
caps, request log, optional email alerts to the owner ONLY, no file/tool access for
the model. The RAG core lives in app/kb.py (shared with app/mcp_server.py).

Environment:
  OPENKB_DATA          library directory (default: <repo>/data)
  OPENKB_OLLAMA_HOST   ollama base URL (default: http://127.0.0.1:11434)
  OPENKB_PORT          listen port (default: 8641)
  OPENKB_OWNER_EMAIL   owner alert address (default: empty = mail alerts disabled)
  OPENKB_ENV_FILE      env file holding SMTP_HOST/PORT/USERNAME/PASSWORD,
                       EMAIL_FROM_ADDRESS/NAME (default: none)"""
import json, os, re, sqlite3, ssl, smtplib, socket, threading, time, urllib.request, uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("OPENKB_DATA") or os.path.join(ROOT, "data")
LOG = os.path.join(DATA, "demo_requests.log")
STATE = os.path.join(DATA, "demo_state.json")
ENV = os.environ.get("OPENKB_ENV_FILE", "")
PORT = int(os.environ.get("OPENKB_PORT", "8641"))
OWNER_EMAIL = os.environ.get("OPENKB_OWNER_EMAIL", "")  # only address this server may ever mail; empty disables alerts

PER_IP_PER_MIN = 10
GLOBAL_PER_MIN = 60
DAILY_CAP = 200
MAX_INPUT = 500

def load_env(path):
    d = {}
    try:
        for line in open(path):
            m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
            if m: d[m.group(1)] = m.group(2).strip()
    except OSError:
        pass
    return d

ENVV = load_env(ENV)

DB = os.path.join(DATA, "openkb.db")
DIST = os.path.join(ROOT, "ui", "dist", "ui", "browser")

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'active', created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, role TEXT, text TEXT, sources TEXT, ts TEXT)")
    return c

def task_rows(status):
    c = db()
    rows = c.execute("SELECT id, title, status, created_at FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    c.close()
    return [{"id": r[0], "title": r[1], "status": r[2], "created_at": r[3]} for r in rows]

def add_message(task_id, role, text, sources=None):
    c = db()
    c.execute("INSERT INTO messages (task_id, role, text, sources, ts) VALUES (?,?,?,?,?)",
              (task_id, role, text, json.dumps(sources or []), datetime.now(timezone.utc).isoformat()))
    c.commit(); c.close()

CTYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
          ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
          ".ico": "image/x-icon", ".woff2": "font/woff2", ".woff": "font/woff", ".txt": "text/plain"}

def send_mail(subject, body):
    """Email the owner only. Never sends to any other address."""
    if not OWNER_EMAIL:
        return False
    try:
        host, port = ENVV.get("SMTP_HOST"), int(ENVV.get("SMTP_PORT", "465"))
        user, pw = ENVV.get("SMTP_USERNAME"), ENVV.get("SMTP_PASSWORD")
        frm = ENVV.get("EMAIL_FROM_ADDRESS") or user
        name = ENVV.get("EMAIL_FROM_NAME", "OpenKB demo")
        if not (host and user and pw and frm): return False
        msg = MIMEText(body)
        msg["Subject"], msg["From"], msg["To"] = subject, f"{name} <{frm}>", OWNER_EMAIL
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as s:
            s.login(user, pw)
            s.sendmail(frm, [OWNER_EMAIL], msg.as_string())
        return True
    except Exception:
        return False

_mail_last = {}
def send_mail_throttled(category, subject, body, min_interval=600):
    """At most one alert email per category per min_interval seconds."""
    now = time.time()
    if now - _mail_last.get(category, 0) < min_interval:
        logline("mail-skipped", "-", category)
        return
    _mail_last[category] = now
    send_mail(subject, body)

lock = threading.Lock()
state = {"day": "", "count": 0, "first_alert_sent": False, "ips": {}}
if os.path.exists(STATE):
    try: state.update(json.load(open(STATE)))
    except Exception: pass

def today(): return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def save_state():
    try: json.dump(state, open(STATE, "w"))
    except OSError: pass

def logline(kind, ip, detail):
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "ip": ip, "detail": detail[:600]}) + "\n")
    except OSError: pass

def check_guards(ip):
    """Returns None if allowed, else (http_code, message)."""
    with lock:
        if state["day"] != today():
            state["day"], state["count"], state["ips"] = today(), 0, {}
        now = time.time()
        reqs = [t for t in state["ips"].get(ip, []) if now - t < 60]
        state["ips"][ip] = reqs
        if len(reqs) >= PER_IP_PER_MIN:
            return 429, "Rate limit: too many requests from your address. Try again in a minute."
        if sum(len([t for t in v if now - t < 60]) for v in state["ips"].values()) >= GLOBAL_PER_MIN:
            return 429, "The demo is busy. Try again in a minute."
        if state["count"] >= DAILY_CAP:
            return 503, "Daily demo limit reached. Back tomorrow."
        reqs.append(now)
        state["count"] += 1
        save_state()
    return None

import kb  # app/kb.py: embeddings, retrieval, classify, answer (shared with mcp_server.py)
answer = kb.answer
retrieve = kb.retrieve


PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>OpenKB demo</title><style>
body{font-family:system-ui;max-width:640px;margin:3em auto;padding:0 1em;color:#222}
textarea{width:100%;height:5em;font-size:1em;padding:.5em}button{margin-top:.5em;padding:.6em 1.4em;font-size:1em}
#out{white-space:pre-wrap;margin-top:1.5em;border-top:1px solid #ccc;padding-top:1em}
small{color:#666}</style></head><body>
<h1>OpenKB demo</h1>
<p><small>Community-held knowledge base read by a small local model. Answers come only from the demo corpus and cite their source. Entries are sourced, not "true".</small></p>
<textarea id=q maxlength=500 placeholder="Ask a question..."></textarea>
<button onclick="ask()">Ask</button> <span id=msg></span>
<div id=out></div>
<div id=addkb style="display:none;margin-top:1.5em;border:1px solid #ccc;border-radius:8px;padding:1em">
<b>Add this knowledge</b>
<p><small>OpenKB grows by donation. Know this well - a manual, local knowledge, your own book (say, your copy of "Away")? Here is how it will work:</small></p>
<ol style="font-size:.9em;color:#444;margin:0 0 0 1.2em;padding:0">
<li>You keep your copyright. Donations are published under the open CC BY-SA 4.0 licence - anyone may reuse and share what you donate, with credit to you. Good to know before you give.</li>
<li>You sign a short, plain-language consent for AI retrieval (English or Spanish). No consent, no content.</li>
<li>Your donation is listed in the public donor log.</li>
<li>A topic maintainer reviews it before it goes in, like open-source code.</li>
<li>Changed your mind? Ask and it comes out - takedown is real, with version history.</li>
</ol>
<p><small><b>Donations open soon.</b> The consent flow is still in review, so there is nothing to upload to yet on purpose.</small></p>
</div>
<script>
async function ask(){
 const q=document.getElementById('q').value.trim(); if(!q)return;
 document.getElementById('msg').textContent='Thinking (local model, can take a minute)...';
 document.getElementById('out').textContent='';
 try{
  const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})});
  const j=await r.json();
  document.getElementById('out').textContent=j.answer||j.error||('Error '+r.status);
  document.getElementById('msg').textContent=j.sources?('Sources: '+j.sources.join(', ')):'';
  document.getElementById('addkb').style.display=j.not_found?'block':'none';
 }catch(e){document.getElementById('msg').textContent='Request failed.';}
}
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _ip(self): return self.client_address[0]
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _file(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return False
        self.send_response(200); self.send_header("Content-Type", CTYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        return True

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/tasks":
            return self._json(200, {"active": task_rows("active"), "archived": task_rows("done")})
        m = re.match(r"^/api/tasks/([A-Za-z0-9-]+)$", path)
        if m:
            c = db()
            t = c.execute("SELECT id, title, status, created_at FROM tasks WHERE id=?", (m.group(1),)).fetchone()
            msgs = c.execute("SELECT role, text, sources, ts FROM messages WHERE task_id=? ORDER BY id", (m.group(1),)).fetchall()
            c.close()
            if not t: return self._json(404, {"error": "no such task"})
            return self._json(200, {"task": {"id": t[0], "title": t[1], "status": t[2], "created_at": t[3]},
                                    "messages": [{"role": r[0], "text": r[1], "sources": json.loads(r[2] or "[]"), "ts": r[3]} for r in msgs]})
        if path == "/health":
            return self._json(200, {"ok": True, "count": state["count"], "cap": DAILY_CAP})
        # static Angular build; fall back to the old single page until the build exists
        if os.path.isdir(DIST):
            rel = path.lstrip("/") or "index.html"
            cand = os.path.normpath(os.path.join(DIST, rel))
            if cand.startswith(DIST) and os.path.isfile(cand):
                return self._file(cand)
            return self._file(os.path.join(DIST, "index.html"))  # SPA fallback
        if path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            self._json(404, {"error": "not found"})
    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/tasks":
            n = int(self.headers.get("Content-Length", 0))
            try:
                title = (json.loads(self.rfile.read(n) or b"{}").get("title") or "New task").strip()[:120]
            except Exception:
                title = "New task"
            tid = uuid.uuid4().hex[:12]
            c = db()
            c.execute("INSERT INTO tasks (id, title, status, created_at) VALUES (?,?,?,?)",
                      (tid, title or "New task", "active", datetime.now(timezone.utc).isoformat()))
            c.commit(); c.close()
            return self._json(200, {"id": tid, "title": title or "New task"})
        m = re.match(r"^/api/tasks/([A-Za-z0-9-]+)/done$", path)
        if m:
            c = db()
            t = c.execute("SELECT status FROM tasks WHERE id=?", (m.group(1),)).fetchone()
            if not t: c.close(); return self._json(404, {"error": "no such task"})
            new = "done" if t[0] == "active" else "active"
            c.execute("UPDATE tasks SET status=? WHERE id=?", (new, m.group(1)))
            c.commit(); c.close()
            return self._json(200, {"id": m.group(1), "status": new})
        if path != "/ask": return self._json(404, {"error": "not found"})
        ip = self._ip()
        guard = check_guards(ip)
        if guard:
            code, msg = guard
            logline("guard", ip, msg)
            send_mail_throttled("guard", f"[OpenKB demo] Guard tripped: {msg[:60]}", f"IP: {ip}\nGuard: {msg}\nTime: {datetime.now(timezone.utc).isoformat()}\n(Further guard alerts muted for 10 min; all events are in the log.)")
            return self._json(code, {"error": msg})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 4096: return self._json(413, {"error": "request too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
            q, task_id = body.get("q", ""), (body.get("task_id") or "").strip()
        except Exception:
            return self._json(400, {"error": "bad request"})
        q = q.strip()[:MAX_INPUT]
        if not q: return self._json(400, {"error": "empty question"})
        logline("ask", ip, q)
        if not state.get("first_alert_sent"):
            state["first_alert_sent"] = True; save_state()
            send_mail("[OpenKB demo] First question received", f"IP: {ip}\nQuestion: {q}\nTime: {datetime.now(timezone.utc).isoformat()}")
        try:
            t0 = time.time()
            ans, srcs, not_found = answer(q)
            logline("answer", ip, f"{time.time()-t0:.1f}s sources={srcs} not_found={not_found}")
            if task_id:
                add_message(task_id, "user", q)
                add_message(task_id, "assistant", ans, srcs)
            self._json(200, {"answer": ans, "sources": srcs, "not_found": not_found})
        except Exception as e:
            logline("error", ip, str(e)[:300])
            send_mail_throttled("error", "[OpenKB demo] Error answering", f"IP: {ip}\nError: {str(e)[:300]}\n(Further error alerts muted for 10 min; all events are in the log.)")
            self._json(502, {"error": "The local model could not answer. Try again."})

def daily_digest():
    while True:
        now = time.time(); time.sleep(86400 - (now % 86400))
        with lock: c, d = state["count"], state["day"]
        send_mail("[OpenKB demo] Daily digest", f"Date: {d}\nRequests served: {c} of {DAILY_CAP}\nLog: {LOG}")

if __name__ == "__main__":
    socket.setdefaulttimeout(30)
    threading.Thread(target=daily_digest, daemon=True).start()
    logline("start", "-", f"port={PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
