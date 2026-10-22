# Librarian and plug-in path - spec draft (not approved for build)

> Update 2026-10-22: superseded in part by docs/COLLECTION-PLAN.md. Wherever this draft says "maintainer review" or "review queue", read "automatic checks, then publish": Walter decided there is no human review before publishing, and reports are triaged automatically.

Two additions, both keeping the same trust spine as human donations: provenance on
everything, maintainer review before publish, takedown that works.

## A. The AI librarian

Agents that build the library while the first users arrive.

**Collectors are opencode agents on the local model.** Every collector runs through
opencode on the machine's own ollama (the same local Qwen the reader uses). Zero
paid API cost, by design - no collector may call a paid model.

**Parallel collectors, capped at 2 (Walter's decision, 21 Oct).** Collections run
independently at the same time - e.g. a 40s-comics collector and an AI-news
collector side by side. Each collection has its own queue of candidates and its
own rate budget, so a noisy collection cannot starve a quiet one.

Honest concurrency note: one Mac Mini means one model. Two collectors plus the
demo reader all hit the same ollama instance, and total tokens/second is fixed -
"parallel" means interleaved loops, not doubled throughput. Rules so the reader
is never starved:
- user-facing traffic (the demo reader and the UI) always wins; collectors yield
- collectors run at most 2 concurrent loops, each throttled (pause between model
  calls; back off further when the demo has served traffic in the last minutes)
- heavy collector cycles (bulk conversion, re-embedding) run off-hours
- collector model calls count against the agent quota identity, never the users' cap

Non-model costs: bandwidth for fetching candidate texts (modest - text-scale,
capped per collection), storage for the growing index and provenance records
(small - chunks and vectors are kilobytes per document), and maintainer review
time, which stays the real bottleneck by design.

**What gets collected is demand-ranked.** The servers already log every question
the library could not answer (the not_found flag). That miss log ranks what the
library lacks: collections and topics are prioritised by miss frequency. Until
enough misses exist, seed collections (a maintainer-written list) provide the
starting coverage.

Pipeline (per collection):
1. **Seed / demand topics** - from the miss log, then from the maintainer seed list.
2. **Candidate discovery** - find candidate texts from openly licensed sources only:
   public-domain archives (Project Gutenberg, Internet Archive texts), CC0 / CC BY /
   CC BY-SA sources, open government publications. No crawling of arbitrary web pages.
   **News is a special case**: fast-expiring and mostly copyrighted, so article text
   is never ingested. A news collection stores only the link, a short factual summary
   (bare facts, which copyright does not protect, with the source named), the fetch
   date, and an expiry; entries refresh on the collection's cycle and drop out of the
   index when they expire. Summaries must stay strictly factual - headlines and ledes
   can carry protectable expression, so this boundary is a legal judgment, not just a
   technical one, and it is flagged in Open problems.
3. **License screen** - every candidate must carry a machine-checkable license.
   No license, no candidate. This is the hard gate.
4. **Intake** - the same conversion pipeline as human donations (intake/intake.py):
   convert, show what the text became.
5. **Dedupe check** - embed candidate chunks, similarity search against the existing
   index. Above threshold: mark as "already covered by <doc>", skip. Borderline:
   stage both and let the reviewer decide.
6. **Provenance record** - source URL, license, fetched-at timestamp, converter
   version, model that proposed it. Stored with the entry, shown in the UI.
7. **Maintainer review** - staged entries enter the same review queue as human
   donations. Nothing the librarian finds is published without a human accept.
8. **Publish** - under CC BY-SA like the rest, with its provenance attached.

The librarian runs at a capped rate (its own quota, separate from user traffic) so
review stays the bottleneck by design, not model speed.

## B. Plug-in path: connect your own model

Anyone can point their own model or agent at an OpenKB instance.

- **Read side**: a small, documented HTTP API (and an MCP server wrapper for agent
  frameworks like opencode): `search(query)` returns chunks with source names;
  `answer(query)` returns a grounded answer with citations or the explicit
  not-in-the-KB refusal. Read-only. Same guards as the UI: rate limits, caps, logs.
- **Write side (propose)**: `propose(document, metadata)` submits a candidate
  through the same pipeline as the librarian: license declaration, intake
  conversion, dedupe check (with the "already covered" response when it matches),
  provenance record, maintainer review. A plug-in can never publish directly.

## Decisions (Walter, 21 Oct)

- **Machine-gathered content: option (a) - public domain / CC0 only.** The
  librarian may gather only public-domain and CC0 texts. News and anything
  else non-PD stays out for now. This settles open problem 1b. The rule is
  approved; the librarian BUILD is not - spec only until Walter says build.
- **Books are retrieval-only.** Book content gets a retrieval-only permission:
  index it, answer with citations, never redistribute the text itself. This
  matches option (c) in open problem 1b, decided specifically for books. The
  general licensing pick for other machine-gathered content (a/b/c below) is
  still pending Walter's choice.

## Open problems

1. **News summaries vs copyright.** The news design (link + short factual summary +
   expiry) rests on facts being free of copyright. The line between a bare-facts
   summary and a rewrite of protectable expression is a judgment call per item, and
   getting it wrong at scale is the librarian's biggest legal risk. Walter should
   confirm this boundary before any news collector runs.
1b. **Licensing and provenance for machine-gathered content.** The library's promise
   today is consent-based: every document donated by someone who confirmed it is
   theirs. Machine gathering breaks that frame even when licenses are honored.
   Options: (a) librarian restricted to public domain / CC0 only - cleanest, smallest
   pool; (b) allow CC BY / CC BY-SA with attribution plumbing and license-compatibility
   checks - bigger pool, real legal surface; (c) retrieval-only for gathered content -
   index it, answer with citations, never redistribute the text itself, link out -
   weakest library, safest legally. DECIDED (Walter, 21 Oct): option (a) - public
   domain / CC0 only; see Decisions above. Books follow the retrieval-only pattern
   separately, also decided above.
2. **Takedown.** Consent-based takedown assumes a donor. Gathered content needs:
   delete-by-source using the provenance record (tractable, designed in above), a
   public takedown contact, and honoring removal requests even when the license
   (e.g. CC BY) does not legally require it. Takedown beats license minimalism here.
3. **Review bottleneck.** The librarian can produce candidates far faster than a
   maintainer can review. Rate caps are in the design, but review UI and possibly
   reviewer tooling become the real work.
4. **Dedupe judgment.** Near-duplicates with different provenance (two translations,
   an abridged and full edition) are not exact merges. Threshold behavior and a
   "related, kept both" state need policy, not just math.
5. **Guard amplification.** Agents loop. All librarian and plug-in traffic needs its
   own identity and quota so a runaway agent trips its own cap, never the users'.
6. **Citation honesty under agents.** When an agent framework calls the read API,
   the answer's sources are returned by the server (enforceable), but the agent's
   final phrasing is prompt-level only. The refusal string and not_found flag stay
   server-side so they survive; the visible citation habit depends on the agent
   behaving. Document this limit plainly.
