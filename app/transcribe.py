"""OpenKB dictation: local speech-to-text with whisper.cpp. Stdlib only.

POST /api/transcribe with the raw audio (any format ffmpeg reads: webm/opus from
Chrome, mp4 from Safari). Audio is held in a temp dir only while it is converted
and transcribed, then deleted. Neither the audio nor the transcript is logged or
stored. Own limits, separate from the question quota.

Environment:
  OPENKB_WHISPER_BIN    whisper.cpp CLI (default: whisper-cli on PATH)
  OPENKB_WHISPER_MODEL  ggml model file (default: <repo>/models/ggml-small.bin)
  OPENKB_FFMPEG         ffmpeg binary (default: ffmpeg on PATH)
  OPENKB_STT_PER_MIN    per-address limit per minute (default 6)
  OPENKB_STT_DAILY_CAP  total clips per UTC day (default 300)
"""
import os, shutil, subprocess, tempfile, threading, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.environ.get("OPENKB_WHISPER_BIN") or shutil.which("whisper-cli") or "/opt/homebrew/bin/whisper-cli"
MODEL = os.environ.get("OPENKB_WHISPER_MODEL") or os.path.join(ROOT, "models", "ggml-small.bin")
FFMPEG = os.environ.get("OPENKB_FFMPEG") or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
PER_MIN = int(os.environ.get("OPENKB_STT_PER_MIN", "6"))
DAILY = int(os.environ.get("OPENKB_STT_DAILY_CAP", "300"))
MAX_BYTES = 2_000_000
MAX_SECONDS = 30
THREADS = os.environ.get("OPENKB_STT_THREADS", "4")

_lock = threading.Lock()      # one transcription at a time, so the reader stays responsive
_state = {"day": "", "n": 0, "ips": {}}
_state_lock = threading.Lock()


def _allow(ip):
    with _state_lock:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if _state["day"] != today:
            _state.update(day=today, n=0, ips={})
        now = time.time()
        hits = [t for t in _state["ips"].get(ip, []) if now - t < 60]
        if len(hits) >= PER_MIN:
            return 429, "Too many dictation clips. Try again in a minute."
        if _state["n"] >= DAILY:
            return 503, "Daily dictation limit reached. Back tomorrow."
        hits.append(now)
        _state["ips"][ip] = hits
        _state["n"] += 1
    return None


def transcribe_bytes(data):
    with tempfile.TemporaryDirectory(prefix="okb-stt-") as d:
        src, wav = os.path.join(d, "in"), os.path.join(d, "a.wav")
        with open(src, "wb") as f:
            f.write(data)
        r = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-t", str(MAX_SECONDS), "-i", src,
                            "-ar", "16000", "-ac", "1", "-f", "wav", wav],
                           capture_output=True, timeout=30)
        if r.returncode != 0 or not os.path.isfile(wav):
            raise ValueError("unreadable audio")
        r = subprocess.run(["nice", "-n", "10", BIN, "-m", MODEL, "-f", wav, "-nt", "-np", "-l", "auto",
                            "-t", THREADS, "-ng"], capture_output=True, timeout=90)
        if r.returncode != 0:
            raise RuntimeError("whisper failed")
        return " ".join(r.stdout.decode("utf-8", "replace").split()).strip()


def handle(h, logline):
    """h is the request handler (needs rfile, headers, _ip(), _json())."""
    ip = h._ip()
    g = _allow(ip)
    if g:
        logline("stt-guard", ip, g[1])
        return h._json(g[0], {"error": g[1]})
    if not os.path.isfile(MODEL):
        return h._json(503, {"error": "Dictation is not set up on this server."})
    try:
        n = int(h.headers.get("Content-Length", 0))
    except ValueError:
        n = 0
    if n <= 0 or n > MAX_BYTES:
        return h._json(413 if n > 0 else 400, {"error": "Audio clip is empty or too long (30 seconds max)."})
    data = h.rfile.read(n)
    if not _lock.acquire(timeout=20):
        return h._json(503, {"error": "Dictation is busy. Try again in a moment."})
    try:
        t0 = time.time()
        text = transcribe_bytes(data)
        logline("stt", ip, "%.1fs %dB" % (time.time() - t0, n))   # no audio, no text in the log
        return h._json(200, {"text": text[:500]})
    except ValueError:
        return h._json(400, {"error": "Could not read that recording."})
    except Exception:
        logline("stt-error", ip, "transcription failed")
        return h._json(502, {"error": "Could not transcribe. Try again."})
    finally:
        _lock.release()
        del data
