# UI - the OpenKB app

Chat-shaped, task-organised. Familiar to anyone who has used ChatGPT; honest about what is different.

## Layout

```
+------------------+--------------------------------------+
|  TASKS           |  Active task                         |
|  + New task      |                                      |
|  - Kitchen aid   |  user: How long to proof brioche?    |
|  - Trip to Leon  |  openkb: 2 to 3 hours at room temp.  |
|  - Done          |  (source: doc-31-en.md)              |
|    v archived    |                                      |
+------------------+--------------------------------------+
```

- **Tasks, not conversations.** Users do not "start a new chat"; they start a task. A task is a thread with a purpose. It can be marked **Done** (moves to archived, stays searchable) and archived tasks can be reopened.
- The answer style stays as in the demo: grounded answers cite the source document; when the library lacks it, the plain "the library does not have that yet" reply with the **Add this knowledge** panel.
- Small talk works, but the home screen nudges toward tasks: "What are you trying to get done?"

## Guided panels

The UI teaches, in this order:

1. **How this works** - three sentences: small local reader, community library, answers are sourced not "true". Plus the trust rules (consent, review, takedown).
2. **Upload / donate** - the intake flow from ARCHITECTURE.md: upload anything, three form questions, preview, automatic checks. Donations open once consent review closes.
3. **Host it yourself (Janus, optional)** - a guide that walks to Janus for serving OpenKB from your own computer. Clearly marked: optional, and an ETMW product; OpenKB works fully without it.

## Stack

- **Angular app** (same framework as the other ETMW clients) served as static files; talks to the existing Python API over JSON. Trade-off accepted: Angular thins the casual-contributor pool versus React, but the owner builds in Angular and consistency across ETMW apps wins.
- API grows from today's demo: `POST /ask` (exists, guards unchanged), plus `GET/POST /tasks`, `POST /tasks/:id/done`, `GET /tasks/:id`, `POST /donate` (when the flow opens). The hard guards (rate limits, caps, request log, mail alerts, kill switch) stay exactly where they are: server-side, in front of the model.

## Storage for a local install

Two things need storing: tasks/threads, and the library index (chunks + vectors).

- **Recommendation: local-first, embedded.** SQLite for tasks and metadata; the prebuilt index pulled once from the Hugging Face dataset (or rebuilt from the repo) and read from disk. Nothing to install, works offline, one-command setup: clone, pull index, run.
- **Online database: optional, never required.** The hosted version (entertomyworld.com/apps/openkb) uses ETMW's database behind the same API. Self-hosters who want multi-device sync can point the app at an online DB instead - same API, different backing.
- Builder's checklist for a local install: Python 3.10+, the reader model (Ollama), the index download, `run.sh`. No database server, no Docker, no accounts.
