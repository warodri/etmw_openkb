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
import hashlib, json, os, re, secrets, sqlite3, ssl, smtplib, socket, threading, time, urllib.request, uuid
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
    cols = [r[1] for r in c.execute("PRAGMA table_info(tasks)")]
    if "owner" not in cols:
        c.execute("ALTER TABLE tasks ADD COLUMN owner TEXT")
        c.execute("UPDATE tasks SET owner='legacy-shared' WHERE owner IS NULL")
        c.commit()
    c.execute("CREATE TABLE IF NOT EXISTS auth_codes (email_hash TEXT PRIMARY KEY, code_hash TEXT, expires REAL, attempts INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS auth_locks (email_hash TEXT PRIMARY KEY, until REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, owner TEXT, email TEXT, expires REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS send_log (k TEXT, ts REAL)")
    now = time.time()
    c.execute("DELETE FROM auth_codes WHERE expires<?", (now,))
    c.execute("DELETE FROM sessions WHERE expires<?", (now,))
    c.execute("DELETE FROM send_log WHERE ts<?", (now - 86400,))
    c.commit()
    return c

def task_rows(status, owner):
    c = db()
    rows = c.execute("SELECT id, title, status, created_at FROM tasks WHERE status=? AND owner=? ORDER BY created_at DESC", (status, owner)).fetchall()
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

# --- email-code sign-in (v0.1 beta) ---
# Login mail uses LOGIN_SMTP_* (widened outbound: login codes to visitors only, Walter 21 Oct).
# Owner alerts keep SMTP_* and remain owner-only.
LOGIN_MAIL = {k: ENVV.get("LOGIN_SMTP_" + k, "") for k in ("HOST", "PORT", "USER", "PASSWORD", "FROM")}
CODE_TTL = 600
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,240}\.[A-Za-z]{2,}$")
TURNSTILE_SECRET = ENVV.get("TURNSTILE_SECRET", "")  # hook: when set, clients send a turnstile token instead of the local challenge
_challenges = {}  # cid -> (answer, expires) - local bot-check, in-memory, one-time

def _h(x): return hashlib.sha256(x.encode()).hexdigest()

def send_login_code(email, code):
    if not LOGIN_MAIL["HOST"]: return False
    msg = MIMEText("Your OpenKB sign-in code is " + code + "\n\nIt is valid for 10 minutes. If you did not ask for it, you can ignore this email.")
    msg["Subject"] = "Your OpenKB sign-in code"
    msg["From"] = LOGIN_MAIL["FROM"]; msg["To"] = email
    with smtplib.SMTP_SSL(LOGIN_MAIL["HOST"], int(LOGIN_MAIL["PORT"] or "465"), context=ssl.create_default_context(), timeout=15) as s:
        if LOGIN_MAIL["USER"]: s.login(LOGIN_MAIL["USER"], LOGIN_MAIL["PASSWORD"])
        s.sendmail(LOGIN_MAIL["FROM"], [email], msg.as_string())
    return True

def rate_hit(c, key, limit, window):
    now = time.time()
    n = c.execute("SELECT COUNT(*) FROM send_log WHERE k=? AND ts>?", (key, now - window)).fetchone()[0]
    if n >= limit: return False
    c.execute("INSERT INTO send_log (k, ts) VALUES (?,?)", (key, now))
    return True

def verify_turnstile(token, ip):
    try:
        req = urllib.request.Request("https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=json.dumps({"secret": TURNSTILE_SECRET, "response": token, "remoteip": ip}).encode(),
            headers={"Content-Type": "application/json"})
        return bool(json.load(urllib.request.urlopen(req, timeout=10)).get("success"))
    except Exception:
        return False

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
<h1>OpenKB v0.1 (Beta)</h1>
<p><small>Community-held knowledge base read by a small local model. Answers come only from the test library and cite their source. Entries are sourced, not "true".</small></p>
<textarea id=q maxlength=500 placeholder="Ask a question..."></textarea>
<button onclick="ask()">Ask</button> <span id=msg></span>
<div id=out></div>
<div id=addkb style="display:none;margin-top:1.5em;border:1px solid #ccc;border-radius:8px;padding:1em">
<b>Add this knowledge</b>
<p><small>OpenKB grows by donation. Know this well - a manual, local knowledge, your own book (say, your copy of "Away")? Here is how it will work:</small></p>
<ol style="font-size:.9em;color:#444;margin:0 0 0 1.2em;padding:0">
<li>You keep your copyright. Donations are published under the open licence you pick (public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0 or BSD) - anyone may reuse and share what you donate, as that licence allows, with credit to you. Good to know before you give.</li>
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
    def _visitor(self):
        m = re.search(r"(?:^|;\s*)okv=([0-9a-f]{32})", self.headers.get("Cookie", ""))
        if m: return m.group(1), False
        return uuid.uuid4().hex, True
    def _session(self):
        m = re.search(r"(?:^|;\s*)oks=([0-9a-f]{48})", self.headers.get("Cookie", ""))
        if not m: return None
        c = db()
        r = c.execute("SELECT owner, email, expires FROM sessions WHERE token_hash=?", (_h(m.group(1)),)).fetchone()
        c.close()
        if r and r[2] > time.time(): return {"owner": r[0], "email": r[1]}
        return None
    def _owner(self):
        ses = self._session()
        return (ses["owner"] if ses else self._vid)
    def _ck(self):
        if getattr(self, "_newv", False):
            self.send_header("Set-Cookie", "okv=%s; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax" % self._vid)
    def _json(self, code, obj, extra=None):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self._ck()
        for k, v in (extra or []): self.send_header(k, v)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _file(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return False
        self.send_response(200); self.send_header("Content-Type", CTYPES.get(ext, "application/octet-stream"))
        self._ck()
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        return True

    def do_GET(self):
        self._vid, self._newv = self._visitor()
        path = self.path.split("?")[0]
        if path.startswith("/api/auth/"):
            return self._auth_post(path)
        if path == "/api/tasks":
            return self._json(200, {"active": task_rows("active", self._owner()), "archived": task_rows("done", self._owner())})
        m = re.match(r"^/api/tasks/([A-Za-z0-9-]+)$", path)
        if m:
            c = db()
            t = c.execute("SELECT id, title, status, created_at FROM tasks WHERE id=? AND owner=?", (m.group(1), self._owner())).fetchone()
            msgs = c.execute("SELECT role, text, sources, ts FROM messages WHERE task_id=? ORDER BY id", (m.group(1),)).fetchall()
            c.close()
            if not t: return self._json(404, {"error": "no such task"})
            return self._json(200, {"task": {"id": t[0], "title": t[1], "status": t[2], "created_at": t[3]},
                                    "messages": [{"role": r[0], "text": r[1], "sources": json.loads(r[2] or "[]"), "ts": r[3]} for r in msgs]})
        if path == "/api/auth/me":
            ses = self._session()
            return self._json(200, {"email": ses["email"] if ses else None})
        if path == "/api/auth/challenge":
            a, b = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
            cid = secrets.token_hex(8)
            _challenges[cid] = (a + b, time.time() + 300)
            return self._json(200, {"id": cid, "q": f"What is {a} + {b}? (bot check)"})
        if path == "/api/public-stats":
            # welcome-page crawler counter. Off by default for clones: set OPENKB_SHOW_COUNTER=1 to show your own library's numbers.
            if os.environ.get("OPENKB_SHOW_COUNTER", ENVV.get("OPENKB_SHOW_COUNTER", "0")) != "1": return self._json(200, {"enabled": False})
            try:
                import library as _lib
                return self._json(200, dict(_lib.public_stats(), enabled=True))
            except Exception:
                return self._json(200, {"enabled": False})
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
        self._vid, self._newv = self._visitor()
        path = self.path.split("?")[0]
        if path == "/api/tasks":
            n = int(self.headers.get("Content-Length", 0))
            try:
                title = (json.loads(self.rfile.read(n) or b"{}").get("title") or "New task").strip()[:120]
            except Exception:
                title = "New task"
            tid = uuid.uuid4().hex[:12]
            c = db()
            c.execute("INSERT INTO tasks (id, title, status, created_at, owner) VALUES (?,?,?,?,?)",
                      (tid, title or "New task", "active", datetime.now(timezone.utc).isoformat(), self._owner()))
            c.commit(); c.close()
            return self._json(200, {"id": tid, "title": title or "New task"})
        m = re.match(r"^/api/tasks/([A-Za-z0-9-]+)/done$", path)
        if m:
            c = db()
            t = c.execute("SELECT status FROM tasks WHERE id=? AND owner=?", (m.group(1), self._owner())).fetchone()
            if not t: c.close(); return self._json(404, {"error": "no such task"})
            new = "done" if t[0] == "active" else "active"
            c.execute("UPDATE tasks SET status=? WHERE id=? AND owner=?", (new, m.group(1), self._owner()))
            c.commit(); c.close()
            return self._json(200, {"id": m.group(1), "status": new})
        if path == "/api/transcribe":
            import transcribe
            return transcribe.handle(self, logline)
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
        if task_id:
            c = db()
            own = c.execute("SELECT 1 FROM tasks WHERE id=? AND owner=?", (task_id, self._owner())).fetchone()
            c.close()
            if not own: return self._json(404, {"error": "no such task"})
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

    def _auth_post(self, path):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 4096: return self._json(413, {"error": "request too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad request"})
        ip = self._ip()
        now = time.time()
        if path == "/api/auth/request-code":
            email = (body.get("email") or "").strip().lower()
            if not EMAIL_RE.match(email): return self._json(400, {"error": "Enter a valid email address."})
            if TURNSTILE_SECRET:
                if not verify_turnstile(body.get("turnstile") or "", ip):
                    return self._json(403, {"error": "Bot check failed. Try again."})
            else:
                cid, ans = body.get("cid") or "", body.get("ans")
                ch = _challenges.pop(cid, None)
                try: ok = ch and ch[1] > now and int(ans) == ch[0]
                except (TypeError, ValueError): ok = False
                if not ok: return self._json(403, {"error": "Bot check failed. Try again."})
            eh = _h(email)
            c = db()
            lock = c.execute("SELECT until FROM auth_locks WHERE email_hash=?", (eh,)).fetchone()
            if lock and lock[0] > now:
                c.close(); return self._json(429, {"error": "Too many attempts. Try again tomorrow."})
            if not rate_hit(c, "e1:" + eh, 3, 3600) or not rate_hit(c, "e2:" + eh, 5, 86400):
                c.commit(); c.close(); return self._json(429, {"error": "Too many codes requested for this address. Try again later."})
            if not rate_hit(c, "ip:" + ip, 20, 3600):
                c.commit(); c.close(); return self._json(429, {"error": "Too many requests. Try again later."})
            code = f"{secrets.randbelow(1000000):06d}"
            c.execute("INSERT OR REPLACE INTO auth_codes (email_hash, code_hash, expires, attempts) VALUES (?,?,?,0)",
                      (eh, _h(code), now + CODE_TTL))
            c.commit(); c.close()
            logline("auth", ip, f"code requested for {_h(email)[:12]}")
            try:
                if not send_login_code(email, code):
                    return self._json(503, {"error": "Email sign-in is not configured on this server. Anonymous mode still works."})
            except Exception as e:
                logline("error", ip, "login mail failed: " + str(e)[:200])
                return self._json(502, {"error": "Could not send the sign-in email. Try again later."})
            return self._json(200, {"sent": True})
        if path == "/api/auth/verify":
            email = (body.get("email") or "").strip().lower()
            code = (body.get("code") or "").strip()
            eh = _h(email)
            c = db()
            lock = c.execute("SELECT until FROM auth_locks WHERE email_hash=?", (eh,)).fetchone()
            if lock and lock[0] > now:
                c.close(); return self._json(429, {"error": "Too many attempts. Try again tomorrow."})
            row = c.execute("SELECT code_hash, expires, attempts FROM auth_codes WHERE email_hash=?", (eh,)).fetchone()
            if not row or row[1] < now:
                c.close(); return self._json(400, {"error": "Code expired - request a new one."})
            if row[2] >= 5:
                c.close(); return self._json(400, {"error": "Too many wrong tries - request a new code."})
            if _h(code) != row[0]:
                att = row[2] + 1
                if att >= 5:
                    c.execute("DELETE FROM auth_codes WHERE email_hash=?", (eh,))
                    c.execute("INSERT INTO send_log (k, ts) VALUES (?,?)", ("burn:" + eh, now))
                    burns = c.execute("SELECT COUNT(*) FROM send_log WHERE k=? AND ts>?", ("burn:" + eh, now - 86400)).fetchone()[0]
                    if burns >= 10:
                        c.execute("INSERT OR REPLACE INTO auth_locks (email_hash, until) VALUES (?,?)", (eh, now + 86400))
                else:
                    c.execute("UPDATE auth_codes SET attempts=? WHERE email_hash=?", (att, eh))
                c.commit(); c.close()
                return self._json(400, {"error": "Wrong code. Check and try again."})
            token = secrets.token_hex(24)
            owner = "u:" + eh
            c.execute("DELETE FROM auth_codes WHERE email_hash=?", (eh,))
            c.execute("INSERT INTO sessions (token_hash, owner, email, expires) VALUES (?,?,?,?)",
                      (_h(token), owner, email, now + 30 * 86400))
            c.execute("UPDATE tasks SET owner=? WHERE owner=?", (owner, self._vid))
            c.commit(); c.close()
            logline("auth", ip, f"sign-in {_h(email)[:12]}")
            return self._json(200, {"ok": True, "email": email},
                              [("Set-Cookie", f"oks={token}; Path=/; Max-Age={30*86400}; HttpOnly; SameSite=Lax")])
        if path == "/api/auth/logout":
            m = re.search(r"(?:^|;\s*)oks=([0-9a-f]{48})", self.headers.get("Cookie", ""))
            if m:
                c = db(); c.execute("DELETE FROM sessions WHERE token_hash=?", (_h(m.group(1)),)); c.commit(); c.close()
            return self._json(200, {"ok": True},
                              [("Set-Cookie", "oks=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")])
        return self._json(404, {"error": "not found"})

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
