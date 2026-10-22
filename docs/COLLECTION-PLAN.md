# Collection plan: collectors, user crawl agents, manual upload

Status: PLAN ONLY, for Walter's review. Nothing here is built. Written 2026-10-22.
Builds on docs/LIBRARIAN.md (spec draft) and the existing intake pipeline.

## Fixed rules (Walter's decisions)
- One library, one licence: CC BY-SA. No separate showcase or "producer" area. The producer idea stays as story material for posts and videos.
- Collectors take public domain or CC0 only. Nothing else is collected by machine.
- Collectors are opencode agents on the local model. No paid model calls. Max 2 running at once.
- The public donate flow stays CLOSED ("Donations open soon") until Walter says otherwise.
- Every document keeps provenance (source URL, licence evidence, date, who added it). A maintainer reviews before anything is published. Takedown must work.

## 1. Collector agents (internet, public domain / CC0 only)
Goal: fill the library before users arrive, ranked by what people asked and the library could not answer (the not_found log), with a maintainer-written seed list until there are enough misses.

Flow per collection: seed list or topic -> find candidate pages -> fetch (respecting robots.txt) -> licence check -> convert to text -> dedupe -> write a provenance record -> put in the review queue. Nothing goes live from here without a maintainer approval.

Allowed sources (allow-list, start small): Project Gutenberg, Wikisource, US government works, Library of Congress / Internet Archive items marked public domain, Wikimedia Commons text, CC0 datasets. A source not on the list is not fetched.

Licence check, two parts, both must pass:
1. Rule-based: the source's own licence field or page statement says public domain / CC0 (machine-readable where it exists).
2. The local model reads the licence text and gives a yes / no / unclear. "Unclear" goes to the maintainer, never auto-passes. The model never overrides a rule-based "no".

Limits: 2 collectors max, each with its own request rate and daily byte cap. User questions always win over collectors for the model. Heavy conversion runs off-hours.

## 2. Users adding their own crawl agents
Who: signed-in users on desktop or agent mode, pointing their own agent at their own sources. Not open to anonymous visitors.

Gate (the licensing gate):
- The user declares the source and the licence up front and agrees to the same three statements as a manual donation (it is theirs to share or the licence allows it, CC BY-SA OK, may be edited).
- Their agent submits through one API only: it can add candidates to the review queue. It cannot publish.
- Same machine-side licence check as section 1. Public domain / CC0 / CC BY / CC BY-SA sources can pass the check for a user's crawler only if the user's declaration and the page evidence agree; anything else is rejected or held.
- Each submission carries the user id, so a bad actor is traceable and can be cut off.

Open decision for Walter: should user crawlers be limited to PD / CC0 like ours, or also accept CC BY / CC BY-SA sources? Proposal: start with PD / CC0 only, same as ours. Widen later.

## 3. Manual upload
Reuses the existing donate pipeline: upload (PDF, Word, scans, photos) -> convert -> preview of the text -> three declarations -> maintainer review -> join the library under CC BY-SA, credited. It is built behind the closed switch, so the page can keep saying "opens soon" while Walter and a few testers use it. Walter's own book is the first test document, by his choice.

## Staged order
1. Manual upload working end to end, behind the closed switch (smallest, uses what exists). Test with Walter's book and a few files.
2. Review queue and provenance records: the shared spine for stages 3 and 4. Plus takedown.
3. One collector, one source (Project Gutenberg), 50 documents, off-hours. Maintainer reviews every one. Report the pass rate and the model's licence-check accuracy.
4. Second collector in parallel (Wikisource or US government works). Add the rate and load throttles.
5. User crawl agents: API, declarations, per-user rate limits, abuse controls. Invite-only first.
6. Demand-ranked topics from the not_found log. Coverage map later (separate idea, not part of this plan).

Each stage ends with a check and a screenshot or sample for Walter before the next starts.

## Risks and answers
- robots.txt and site terms: fetch only allow-listed sources, honour robots.txt and crawl-delay, identify the agent with a clear user-agent and contact, cache to avoid refetching. A source that blocks us is dropped, not worked around.
- Wrong licence call (the biggest risk): rules first, model second, "unclear" goes to a human, a maintainer approves every document, provenance kept, takedown removes text, chunks and vectors. Public-domain status also varies by country and some "PD" pages carry reuse limits on scans or editions; the check records the stated basis, and the maintainer decides edge cases.
- Abuse of user crawlers: invite-only, signed-in, per-user daily caps, queue-only access, submissions traceable, strikes and cut-off, no direct publish, no fetching on our servers on a user's behalf (their agent fetches, we only receive text).
- Load on the Mac Mini: one model serves everyone. Max 2 collectors, throttled, yield to user questions, off-hours bulk work, daily caps on bytes and documents, a kill switch that stops all collectors at once. Disk growth is small (text and vectors) but is monitored.
- Review bottleneck: a maintainer reviewing is the real limit. Cap the queue size so collectors pause when it is full.
- Poisoned or low-quality text: dedupe, minimum quality checks, prompt-injection filter on collected text (the model must treat page text as data only), review before publish.
- Local model quality: Qwen has hung before on tool calls. Collectors run in small steps with timeouts and are restarted by a watchdog; failures leave the queue untouched.

## Not in this plan
Paid plan, donation opening, Product Hunt, coverage map, any showcase area, anything collecting non-PD / non-CC0 material by machine.
