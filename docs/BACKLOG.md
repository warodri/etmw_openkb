# OpenKB backlog

Priorities change; order is not ranking. Add dated entries, keep them short.

## Queued (in order)

1. **Agent mode without the desktop client** (Walter, 2026-10-21): surface opencode
   agent mode for users who never install the desktop app. In-repo setup plus a
   docs/guide page for running opencode with the local model against the KB. The
   installer already writes opencode.json; the guide page should explain what agent
   mode is, the read-only MCP bridge and its separate daily quota, and how to start
   it (`opencode`, pick the "openkb" agent). Desktop client stays a later stage.
   Note: not urgent - pick a good time, use the opencode API (DeepSeek) for drafting.

2. **Full page for "How this works"** (Walter, 2026-10-21): same pattern as /host -
   dedicated route, guided layout, graphics in the pixel-robot style, mobile +
   light/dark.

3. **Full page for "Donate knowledge" at /donate** (Walter, 2026-10-21, detailed spec):
   Everything a donor needs on one page:
   - upload any format (PDF, Word, scans, even photos of pages)
   - the three-question consent (it is yours to share; you are OK with CC BY-SA;
     it can be edited)
   - converted-text preview before anything is stored
   - review status (maintainer reviews, then it joins the library)
   - CC BY-SA explained lightly
   Plus a section for users' own LLMs/agents adding content:
   - propose-content endpoint via API/MCP
   - license declaration
   - dedupe / "already covered" check
   - human review
   This agent path is also what OpenKB's own local collectors will use.
   HARD GATES until Walter decides otherwise:
   - donations stay CLOSED in the live demo: submit gated, visible "opens soon" state
   - machine-gathered licensing is Walter's open decision: the LLM section documents
     the path under that gate - no real ingestion until he decides
   Same visual language as /host: pixel-robot style, diagrams, mobile + light/dark.
   Report with screenshots when live.

4. **Coverage-map page** (Walter, 2026-10-21): a public page mapping the topics the
   library covers (graph / visual map), so visitors see the gaps and know what to
   donate. Sequence: AFTER the 50-doc retrieval test. No build yet - idea recorded.

## Holds and intent (Walter, 2026-10-21)

- **Product Hunt launch: HELD** until the DB has more depth. Do not prepare or
  schedule launch work until Walter reopens it.
- Walter intends to use OpenKB himself for both Chat and Work via the desktop
  client - the desktop client is his own daily driver, not only a later user stage.

## Done

- **"Host it yourself" as a full page** (2026-10-21, commit af8bfd9): /host route
  with step-by-step guide, disk-size chart, install flow + architecture diagrams,
  troubleshooting; replaced the popup. Approved by Walter 21 Oct ("this is a yes").
