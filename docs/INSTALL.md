# Install OpenKB

What you end up with: the web app (tasks + chat UI with sources), the local reader
answering from the bundled library, and agent mode (opencode driving the same
library through a read-only MCP bridge). Everything runs on your machine.

## Requirements

- Python 3.9+ (no packages to install - the server and tools are stdlib only)
- [Ollama](https://ollama.com), running locally
- Node.js 20+ (only to build the UI; the API works without it)
- [opencode](https://opencode.ai) (only for agent mode)
- Disk: ~25 GB for the models

## Install

```sh
./install.sh
```

The script: checks python3/ollama/node, pulls the two models
(`qwen3.6:35b-a3b` reader, `qwen3-embedding:4b` embeddings), gets the library
index, builds the UI, and writes `opencode.json` for your ollama address.

The library index (data/embeddings.json) comes from, in order:
1. an existing data/embeddings.json,
2. `OPENKB_LIB_SRC=/path/to/data ./install.sh` (copy from another install),
3. `OPENKB_LIB_URL=https://... ./install.sh` (download),
4. a rebuild from the bundled documents: `python3 src/ingest.py && python3 src/embed.py`.

## Run

```sh
python3 app/server.py
# UI and API on http://127.0.0.1:8641
```

Agent mode:

```sh
opencode
# pick the "openkb" agent - read-only, answers only from the library, cites sources
```

## Configuration (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENKB_OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama base URL (server + MCP bridge) |
| `OPENKB_PORT` | `8641` | Web app port |
| `OPENKB_DATA` | `<repo>/data` | Library index + local state |
| `OPENKB_READER_MODEL` | `qwen3.6:35b-a3b` | Reader model tag |
| `OPENKB_EMBED_MODEL` | `qwen3-embedding:4b` | Embedding model tag |
| `OPENKB_OWNER_EMAIL` | (empty) | Owner alert address; empty = no mail |
| `OPENKB_ENV_FILE` | (none) | File with SMTP_* for alert mail |
| `OPENKB_AGENT_DAILY_CAP` | `100` | Daily cap for agent (MCP) traffic |

## Guards

The web API keeps hard guards server-side: per-IP and global rate limits, a daily
cap, 500-character input, 400-token answers, a request log. Agent traffic through
the MCP bridge has its own separate daily quota (identity `agent-mcp`, its own
counter and log), so an agent loop can never eat the users' allowance. The
"not in the KB" refusal and the source list are computed server-side - no client,
agent or otherwise, can turn them off.

## Optional: dictation (local speech-to-text)

The mic button in the prompt box sends a short clip to `POST /api/transcribe`, which runs
[whisper.cpp](https://github.com/ggml-org/whisper.cpp) on your machine. Audio is held in a temp
folder only while it is transcribed, then deleted; neither audio nor text is logged.

    brew install whisper-cpp ffmpeg
    mkdir -p models && curl -L -o models/ggml-small.bin \
      https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin

Settings: `OPENKB_WHISPER_BIN`, `OPENKB_WHISPER_MODEL`, `OPENKB_STT_PER_MIN` (6), `OPENKB_STT_DAILY_CAP` (300).
Without the model file, the mic button reports that dictation is not set up.
