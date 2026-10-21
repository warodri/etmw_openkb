#!/usr/bin/env python3
"""OpenKB intake prototype: upload -> Docling -> Markdown + header -> preview.

Donors submit any format; this converts to clean Markdown, fills the document
header from the donor's form answers, and renders a local preview page to
confirm before anything goes to review. Local only - never exposed publicly.

Usage:
  python3 intake.py convert <file> --source "..." --donor "name-or-handle" [--licence "CC BY-SA 4.0"] [--date YYYY-MM-DD]
  python3 intake.py serve     # local upload+preview page on 127.0.0.1:8642 (NOT public)
"""
import html, json, os, re, sys, time, urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in dir() else "."
OUT = os.path.join(ROOT, "data", "intake", "out")
PORT = 8642
HEADER_ORDER = ("source", "licence", "donor", "date")

def convert_file(path, source, donor, licence="CC BY-SA 4.0", day=None):
    """Convert any upload to Markdown with the OpenKB header. Returns (md_path, preview_path)."""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        sys.exit("Docling not installed here. Use the intake venv: data/intake/venv/bin/python intake.py ...")
    day = day or date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(path))[0].lower()).strip("-")
    os.makedirs(OUT, exist_ok=True)
    doc = DocumentConverter().convert(path).document
    body = doc.export_to_markdown().strip()
    ocr_note = ""
    if path.lower().endswith(".pdf") and len(body) < 400:
        ocr_note = ("\n> WARNING: very little text came out. If this is a scanned book, the OCR step "
                    "may have missed pages - check the preview carefully before confirming.\n")
    header = (f"---\nsource: {source}\nlicence: {licence}\ndonor: {donor}\ndate: {day}\n---\n\n")
    md = header + ocr_note + body + "\n"
    md_path = os.path.join(OUT, slug + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    preview_path = os.path.join(OUT, slug + "_preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview_html(os.path.basename(path), md))
    return md_path, preview_path

def preview_html(title, md):
    return ("<!doctype html><html><head><meta charset=utf-8><title>OpenKB intake preview</title>"
            "<style>body{font-family:system-ui;max-width:760px;margin:2em auto;padding:0 1em}"
            "pre{white-space:pre-wrap;background:#f6f6f6;padding:1em;border-radius:8px;font-size:.9em}</style></head><body>"
            f"<h1>Preview: {html.escape(title)}</h1>"
            "<p>This is exactly how your document would enter OpenKB. Check the text (OCR can make mistakes), "
            "the header fields, and the licence. Nothing is published yet - a maintainer reviews after you confirm.</p>"
            f"<pre>{html.escape(md)}</pre>"
            "</body></html>")

FORM = """<!doctype html><html><head><meta charset=utf-8><title>OpenKB intake (local)</title>
<style>body{font-family:system-ui;max-width:560px;margin:3em auto;padding:0 1em}input,label{display:block;margin:.4em 0;width:100%}button{margin-top:1em;padding:.6em 1.4em}</style></head><body>
<h1>OpenKB intake (local prototype)</h1>
<form method=post enctype=multipart/form-data action=/convert>
<label>File (PDF, DOCX, EPUB, TXT, HTML...) <input type=file name=file required></label>
<label>What is it? (source) <input name=source required placeholder="e.g. my novel Away"></label>
<label>Your name or handle (donor) <input name=donor required></label>
<label>Licence <input name=licence value="CC BY-SA 4.0"></label>
<button>Convert and preview</button></form>
<p><small>Local only. Nothing leaves this machine. Consent signing is a separate step in the real flow.</small></p>
</body></html>"""

def serve():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, body, ctype="text/html; charset=utf-8"):
            b = body.encode() if isinstance(body, str) else body
            self.send_response(200); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            self._send(FORM) if self.path == "/" else self._send("<h1>404</h1>")
        def do_POST(self):
            if self.path != "/convert": return self._send("<h1>404</h1>")
            ctype = self.headers.get("Content-Type", "")
            boundary = ctype.split("boundary=")[-1].encode()
            data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            fields, file_bytes, fname = {}, None, None
            for part in data.split(b"--" + boundary):
                if b'name="file"' in part and b"filename=" in part:
                    fname = re.search(rb'filename="([^"]+)"', part).group(1).decode(errors="replace")
                    file_bytes = part.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
                elif b'name="' in part:
                    m = re.search(rb'name="([^"]+)"', part)
                    if m: fields[m.group(1).decode()] = part.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0].decode(errors="replace").strip()
            if not file_bytes or not fname:
                return self._send("<h1>No file received</h1>")
            tmp = os.path.join(OUT, "..", "upload_" + str(int(time.time())) + "_" + re.sub(r"[^A-Za-z0-9._-]", "_", fname))
            os.makedirs(os.path.dirname(tmp), exist_ok=True)
            with open(tmp, "wb") as f: f.write(file_bytes)
            try:
                md_path, preview_path = convert_file(tmp, fields.get("source", "unspecified"),
                                                     fields.get("donor", "anonymous"),
                                                     fields.get("licence") or "CC BY-SA 4.0")
            except Exception as e:
                return self._send(f"<h1>Conversion failed</h1><pre>{html.escape(str(e))}</pre>")
            with open(preview_path, encoding="utf-8") as f:
                self._send(f.read())
    print(f"Intake preview server on http://127.0.0.1:{PORT} (local only)")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "serve":
        serve()
    elif args and args[0] == "convert" and len(args) >= 2:
        def flag(name, default=None):
            return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default
        md, pv = convert_file(args[1], flag("--source", "unspecified"), flag("--donor", "anonymous"),
                              flag("--licence", "CC BY-SA 4.0"), flag("--date"))
        print("markdown:", md); print("preview:", pv)
    else:
        print(__doc__)
