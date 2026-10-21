# OpenKB backlog

Priorities change; order is not ranking. Add dated entries, keep them short.

## Queued

- **Agent mode without the desktop client** (Walter, 2026-10-21): surface opencode
  agent mode for users who never install the desktop app. In-repo setup plus a
  docs/guide page for running opencode with the local model against the KB. The
  installer already writes opencode.json; the guide page should explain what agent
  mode is, the read-only MCP bridge and its separate daily quota, and how to start
  it (`opencode`, pick the "openkb" agent). Desktop client stays a later stage.
  Note: not urgent - pick a good time, use the opencode API (DeepSeek) for drafting.

- **Full-page treatment for "How this works" and "Donate knowledge"** (Walter,
  2026-10-21): same pattern as /host - dedicated routes, guided layout, graphics in
  the pixel-robot style, mobile + light/dark. Do after the agent-mode page.

## Done

- **"Host it yourself" as a full page** (2026-10-21, commit af8bfd9): /host route
  with step-by-step guide, disk-size chart, install flow + architecture diagrams,
  troubleshooting; replaced the popup.
