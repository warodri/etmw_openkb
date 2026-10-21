#!/usr/bin/env bash
# OpenKB installer - sets up the library, the UI, and agent mode (opencode).
# Stdlib Python only; the only heavy downloads are the models and npm packages.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

echo "== OpenKB install =="

# --- 1. Requirements -------------------------------------------------------
fail() { echo "MISSING: $1"; echo "  $2"; exit 1; }

command -v python3 >/dev/null || fail "python3" "Install Python 3.9 or newer."
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' \
  || fail "python3 $PYV" "OpenKB needs Python 3.9 or newer."
echo "python3 $PYV ok"

OLLAMA_HOST="${OPENKB_OLLAMA_HOST:-http://127.0.0.1:11434}"
if ! command -v ollama >/dev/null; then
  fail "ollama" "Install from https://ollama.com and start it, then re-run."
fi
curl -sf -m 5 "$OLLAMA_HOST/api/tags" >/dev/null \
  || fail "ollama not answering at $OLLAMA_HOST" "Start ollama, or set OPENKB_OLLAMA_HOST."
echo "ollama ok at $OLLAMA_HOST"

# --- 2. Models --------------------------------------------------------------
READER="${OPENKB_READER_MODEL:-qwen3.6:35b-a3b}"
EMBED="${OPENKB_EMBED_MODEL:-qwen3-embedding:4b}"
# ollama list reports "name:tag"; match the exact tag as a word
have_model() { ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$1"; }
# When pointing at a non-default ollama host, OLLAMA_HOST (no http://) must be set for the CLI
export OLLAMA_HOST="${OLLAMA_HOST#http://}"
export OLLAMA_HOST="${OLLAMA_HOST#https://}"
for M in "$READER" "$EMBED"; do
  if have_model "$M"; then
    echo "model $M already present"
  else
    echo "pulling model $M (this is the big download)..."
    ollama pull "$M"
  fi
done

# --- 3. Library index -------------------------------------------------------
if [ -f data/embeddings.json ]; then
  echo "library index already present"
elif [ -n "${OPENKB_LIB_SRC:-}" ]; then
  echo "copying library index from $OPENKB_LIB_SRC"
  mkdir -p data
  cp "$OPENKB_LIB_SRC/embeddings.json" data/embeddings.json
elif [ -n "${OPENKB_LIB_URL:-}" ]; then
  echo "downloading library index from $OPENKB_LIB_URL"
  mkdir -p data
  curl -fL "$OPENKB_LIB_URL" -o data/embeddings.json
elif [ -d data/fixtures ]; then
  echo "building library index from data/fixtures"
  python3 src/ingest.py
  OPENKB_OLLAMA="http://$OLLAMA_HOST" python3 src/embed.py
else
  fail "library index" "No data/embeddings.json, no OPENKB_LIB_SRC/OPENKB_LIB_URL, no data/fixtures."
fi
echo "library index ok"

# --- 4. UI ------------------------------------------------------------------
if command -v npm >/dev/null; then
  (cd ui && npm install && npx ng build)
  echo "UI built"
else
  echo "WARNING: npm not found - skipping the UI build."
  echo "  The API still works; install Node 20+ and run: (cd ui && npm install && npx ng build)"
fi

# --- 5. Agent mode (opencode) -----------------------------------------------
if [ ! -f opencode.json ] && [ -f opencode.json.example ]; then
  sed -e "s|http://localhost:11434/v1|http://$OLLAMA_HOST/v1|" -e "s|http://127.0.0.1:11434|http://$OLLAMA_HOST|" opencode.json.example > opencode.json
  echo "opencode.json written for $OLLAMA_HOST"
fi

echo
echo "== Done =="
echo "Run the app:     python3 app/server.py        # UI + API on http://127.0.0.1:${OPENKB_PORT:-8641}"
echo "Agent mode:      opencode                     # then pick the 'openkb' agent"
echo "Uninstall note:  everything stays inside this folder except the ollama models."
