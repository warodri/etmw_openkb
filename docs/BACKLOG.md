# OpenKB backlog

Priorities change; order is not ranking. Add dated entries, keep them short.

## Queued (in order)

4. **Coverage-map page** (Walter, 2026-10-21): a public page mapping the topics the
   library covers (graph / visual map), so visitors see the gaps and know what to
   donate. Sequence: AFTER the 50-doc retrieval test. No build yet - idea recorded.

## Holds and intent (Walter, 2026-10-21)

- **Product Hunt launch: HELD** until the DB has more depth. Do not prepare or
  schedule launch work until Walter reopens it.
- Walter intends to use OpenKB himself for both Chat and Work via the desktop
  client - the desktop client is his own daily driver, not only a later user stage.

- **Licence decision (Walter, 2026-10-22, revised 12:35 - several open licences tagged per document, see COLLECTION-PLAN "Licences per document"; the next text is the older rule): CC BY-SA only, for all content. No donor choice, no NC variant. Open: whether user crawl agents accept only PD/CC0 sources (proposal) - awaiting Walter.

- **Publishing model (Walter, 2026-10-22):** risk-split. Auto-publish from allow-listed PD/CC0 sources (provenance record, one-click takedown, weekly sampled audit). SUPERSEDED same day: no human review before publishing at all; user submissions and collectors auto-publish after automated checks. Required: public "Report this" on answers/sources, /report page, removal workflow and log. See docs/COLLECTION-PLAN.md. No build yet.

- **User crawl agents (Walter, 2026-10-22):** they feed the one shared library (grow together, not duplicate work). Accepted licences: PD, CC0, CC BY, CC BY-SA, credit kept in provenance; NC and ND excluded. Invite-only; auto-publish after automated checks (no human review, Walter 2026-10-22, 08:58); residual licence risk accepted, mitigated by report-and-remove and audit log. No build yet.

- **Report triage (Walter, 2026-10-22, 10:04):** reports are triaged automatically (rate limits, dedupe, reputation, evidence check for copyright, quoted-text check for personal data); obvious = auto-remove, bogus = dismiss + log, ambiguous = maintainer queue. No hide-on-any-report. See docs/COLLECTION-PLAN.md section 4.

## Done

- **Pages 1-3 shipped** (2026-10-21): /agent (agent mode guide), /how (How this works), /donate (donations CLOSED, "opens soon", LLM/agent path documented only). Sidebar links updated. Awaiting Walter's review; the machine-gathered licensing decision stays his.
- **"Host it yourself" as a full page** (2026-10-21, commit af8bfd9): /host route
  with step-by-step guide, disk-size chart, install flow + architecture diagrams,
  troubleshooting; replaced the popup. Approved by Walter 21 Oct ("this is a yes").

- **Welcome-page crawler counter (Walter, 2026-10-22, after the first collector works):** a small honest live counter under the hero (active collectors/keys, last active, docs added; honest zero state). Config flag so clones show their own count or hide it. Hero text unchanged.
- **MCP / API docs index (Walter, 2026-10-22, PLAN ONLY):** see docs/DEV-DOCS-PLAN.md. Nothing built until approved.
- **Pointer-index mode (Walter, 2026-10-22, PLAN ONLY):** see docs/POINTER-MODE-PLAN.md.
