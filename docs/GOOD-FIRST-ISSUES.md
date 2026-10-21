# Good first issues

Small, self-contained, real. Each touches one area. Claim one by opening an
issue before you start.

1. **Add a fixture document + eval question.** Pick a topic the test library
   lacks, write a short factual document in the style of data/fixtures, add one
   English question with its expected answer to the gate in src/eval.py.
   Area: content/eval. No dependencies.

2. **Chunking: split on sentence boundaries.** src/ingest.py chunks by fixed
   character windows. Split on sentence ends with a small overlap instead, and
   show the gate score does not regress. Area: Python.

3. **More languages in the fixtures.** Add 5+ documents in a language we don't
   cover (French, German, Portuguese, ...) with matching eval questions.
   Area: content/eval.

4. **Eval report: latency and token stats.** src/eval.py reports pass/fail.
   Extend the report with per-question latency and answer length so regressions
   in speed are visible too. Area: Python.

5. **UI: remember the theme.** The light/dark switch resets on reload. Persist
   it in localStorage and respect the OS preference on first visit.
   Area: Angular, small.

6. **UI: rename a task.** Inline edit of a task title in the sidebar (pencil
   icon, Enter to save). Needs a small PATCH-style endpoint in app/server.py.
   Area: Angular + Python.

7. **UI: message timestamps + copy button.** Show each message's time and add a
   copy-to-clipboard button on answers. Area: Angular, small.

8. **Smoke-test script.** A scripts/smoke.sh that boots the server on a scratch
   port, hits /health, /api/tasks, one /ask, and prints PASS/FAIL. Our CI-start
   point. Area: bash + Python.

9. **MCP: kb_list_sources tool.** Add a third tool to app/mcp_server.py listing
   the documents in the library (id, source name, chunk count). Area: Python.

10. **Translate the install docs.** docs/INSTALL.md in your language under
    docs/i18n/. Area: docs.
