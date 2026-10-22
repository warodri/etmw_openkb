"""Open-web intake for user crawl agents (step 1). One URL in, a reference-only library entry out, or a logged reason it was refused.
Steps: URL safety -> robots.txt -> one polite fetch -> licence found on the page vs the account default -> readable text ->
duplicate / spam / injection checks -> publish (offsets + hash + URL + vectors, no stored text). No person reviews it first."""
import re, time, json, html, threading, socket, urllib.request, urllib.parse, urllib.error, urllib.robotparser
import library as L, source as S

UA = "OpenKB-crawler/0.1 (+https://github.com/warodri/etmw_openkb; respects robots.txt)"
HOST_DELAY = 5.0          # seconds between requests to one host while crawling (query-time reads use source.QUERY_DELAY)
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 4
ALLOW_LOCAL = False       # tests only: allow 127.0.0.1
_last, _robots, _lock = {}, {}, threading.Lock()

class Refused(Exception): pass

def _safe(url):
    if ALLOW_LOCAL and urllib.parse.urlparse(url).hostname in ("127.0.0.1", "localhost"): return True
    return L._safe_url(url)

def _robots_ok(url):
    pr = urllib.parse.urlparse(url); base = "%s://%s" % (pr.scheme, pr.netloc)
    if base not in _robots or time.time() - _robots[base][1] > 3600:
        rp = urllib.robotparser.RobotFileParser(); rp.set_url(base + "/robots.txt")
        try: rp.parse(urllib.request.urlopen(urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA}), timeout=5).read(500_000).decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): rp.disallow_all = True
            else: rp.allow_all = True
        except Exception: rp.allow_all = True
        _robots[base] = (rp, time.time())
    return _robots[base][0].can_fetch(UA, url)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def fetch_url(url, delay=HOST_DELAY, limit=MAX_BYTES):
    """Returns (raw_text, final_url, content_type). Raises Refused(reason). Every redirect hop is checked again."""
    for hop in range(MAX_REDIRECTS + 1):
        if not _safe(url): raise Refused("the address is not a public web page")
        if not _robots_ok(url): raise Refused("robots.txt does not allow reading this page")
        host = urllib.parse.urlparse(url).netloc
        with _lock:
            w = delay - (time.time() - _last.get(host, 0))
            if w > 0: time.sleep(w)
            _last[host] = time.time()
        try:
            r = urllib.request.build_opener(_NoRedirect).open(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain"}), timeout=20)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"]); continue
            raise Refused({401: "the page needs a login", 402: "the page is behind a paywall", 403: "the site refuses automated readers", 404: "the page does not exist", 410: "the page is gone", 429: "the site is limiting requests, try later"}.get(e.code, "the site answered with error %d" % e.code))
        except Exception as e: raise Refused("the page could not be reached (%s)" % str(e)[:60])
        ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ct not in ("text/html", "text/plain", "application/xhtml+xml"): raise Refused("not a text page (%s)" % (ct or "unknown type"))
        cl = r.headers.get("Content-Length")
        if cl and cl.isdigit() and int(cl) > limit: raise Refused("the page is too large (%d MB)" % (int(cl) // 1_000_000))
        data = r.read(limit + 1)
        if len(data) > limit: raise Refused("the page is too large")
        return data.decode(r.headers.get_content_charset() or "utf-8", "replace"), url, ct
    raise Refused("too many redirects")

_CC = re.compile(r"creativecommons\.org/(?:licenses/([a-z\-]+)/[\d.]+|publicdomain/(zero|mark)/[\d.]+)", re.I)
_REL = re.compile(r"<(?:a|link)\b[^>]*\brel=[\"'][^\"']*\blicense\b[^\"']*[\"'][^>]*>", re.I)

def detect_licence(raw):
    """Look for a licence the PAGE states about itself. Returns (licence, refusal). One of them is empty; both are empty if the page says nothing.
    A licence the page states that we do not accept (NC, ND, all rights reserved) is a refusal even if the account has a default."""
    scope = " ".join(_REL.findall(raw)) or raw
    found = set(); bad = ""
    for m in _CC.finditer(scope):
        code = (m.group(1) or "").lower()
        if m.group(2): found.add("CC0" if m.group(2).lower() == "zero" else "Public domain")
        elif re.search(r"(^|-)n[cd]($|-)", code): bad = "the page states a Creative Commons NonCommercial or NoDerivatives licence"
        elif code == "by": found.add("CC BY")
        elif code == "by-sa": found.add("CC BY-SA")
    text = S.html_to_text(raw).lower() if "<" in raw else raw.lower()
    m = re.search(r"spdx-license-identifier:\s*(mit|apache-2\.0|bsd-[23]-clause)", text)
    if m: found.add({"mit": "MIT", "apache-2.0": "Apache-2.0"}.get(m.group(1), "BSD"))
    for m in re.finditer(r"<meta[^>]+name=[\"'](?:license|dc\.rights|dcterms\.rights)[\"'][^>]*content=[\"']([^\"']+)", raw, re.I):
        k = L.norm_licence(m.group(1))
        if k: found.add(L.ACCEPTED[k])
    if bad: return "", bad
    if len(found) > 1: return "", "the page states conflicting licences (%s)" % ", ".join(sorted(found))
    if found: return next(iter(found)), ""
    if re.search(r"all rights reserved", text): return "", "the page says all rights reserved"
    return "", ""

def _meta(raw, name):
    m = re.search(r"<meta[^>]+name=[\"']%s[\"'][^>]*content=[\"']([^\"']*)" % name, raw, re.I)
    return html.unescape(m.group(1)).strip() if m else ""

def ingest(url, contributor, default_licence="", declarations=None, embed=None, db_path=None, dry_run=False, delay=HOST_DELAY):
    """Returns {ok, doc_id, reasons, licence, basis, title}. Every refusal is written to the audit log with the account."""
    c = L.connect(db_path); out = {"ok": False, "doc_id": None, "reasons": [], "licence": "", "basis": "", "title": "", "url": url}
    def refuse(why):
        out["reasons"].append(why); L.log(c, "rejected", None, contributor, json.dumps({"url": url, "origin": "user-crawler", "reasons": out["reasons"]})); c.commit(); c.close(); return out
    url = (url or "").strip()
    if not re.match(r"^https?://", url): return refuse("not a web address")
    if c.execute("SELECT 1 FROM documents WHERE source_url=? AND status IN ('live','hidden')", (url,)).fetchone(): return refuse("this page is already in the library")
    try: raw, final, ct = fetch_url(url, delay=delay)
    except Refused as e: return refuse(str(e))
    if re.search(r"<meta[^>]+name=[\"']robots[\"'][^>]*content=[\"'][^\"']*(noindex|noai|none)", raw, re.I): return refuse("the page asks not to be indexed")
    lic, why = detect_licence(raw) if ct != "text/plain" else ("", "")
    if why: return refuse(why)
    recipe = "plain" if ct == "text/plain" else "html"
    text = S.transform(raw, recipe) or ""
    if not S.readable(text): return refuse("the page has no readable text (it may need JavaScript or a login)")
    title = html.unescape(re.sub(r"\s+", " ", (re.search(r"(?is)<title[^>]*>(.*?)</title>", raw) or re.search(r"(?is)<h1[^>]*>(.*?)</h1>", raw) or [0, ""])[1])).strip()
    title = re.sub(r"<[^>]+>", "", title)[:160] or urllib.parse.urlparse(final).netloc
    out["title"] = title
    kw = dict(text=text, title=title, origin="user-crawler", licence="", source_url=final, credit=_meta(raw, "author")[:120], contributor=contributor, declarations=declarations,
              text_url=final, recipe=recipe, detected_licence=lic, default_licence=default_licence, db_path=db_path)
    if embed: kw["embed"] = embed
    c.close()
    if dry_run:
        r = {"ok": not L.check_text(text), "doc_id": None, "reasons": L.check_text(text)}
    else: r = L.submit(**kw)
    out.update(ok=r["ok"], doc_id=r.get("doc_id"), reasons=r.get("reasons", []), licence=lic or default_licence, basis="page" if lic else "user-declared")
    return out
