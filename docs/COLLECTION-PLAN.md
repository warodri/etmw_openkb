# Collection plan: collectors, user crawl agents, manual upload

Status: PLAN ONLY, for Walter's review. Nothing here is built. Written 2026-10-22.
Builds on docs/LIBRARIAN.md (spec draft) and the existing intake pipeline.

## Fixed rules (Walter's decisions)
- Decision 2026-10-22: single licence, CC BY-SA, for everything in the library. No donor choice of licence, no non-commercial (NC) variant.
- One library, one licence: CC BY-SA. No separate showcase or "producer" area. The producer idea stays as story material for posts and videos.
- Collectors take public domain or CC0 only. Nothing else is collected by machine.
- Collectors are opencode agents on the local model. No paid model calls. Max 2 running at once.
- The public donate flow stays CLOSED ("Donations open soon") until Walter says otherwise.
- Every document keeps provenance (source URL, licence evidence, date, who added it). Takedown must work.
- Decision 2026-10-22, risk-split publishing: documents from allow-listed PD/CC0 sources auto-publish (the licence comes from the source) with a provenance record, one-click takedown and a weekly sampled quality audit. Human review stays for user submissions, non-listed sites and any "unclear" licence check.
- Decision 2026-10-22: any user must have a very clear public way to report content that should not be there (see section 4).

## 1. Collector agents (internet, public domain / CC0 only)
Goal: fill the library before users arrive, ranked by what people asked and the library could not answer (the not_found log), with a maintainer-written seed list until there are enough misses.

Flow per collection: seed list or topic -> find candidate pages -> fetch (respecting robots.txt) -> licence check -> convert to text -> dedupe -> write a provenance record -> auto-publish if the source is allow-listed and the licence passes, else review queue.

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

## 4. Reporting and removal (required before any auto-publish)
Public reporting:
- A visible "Report this" on every answer and on every source shown under an answer. One tap, no sign-in needed. Fields: which document or answer (filled automatically), reason (copyright, personal data, harmful, wrong or low quality, other), free text, optional email for a reply.
- A /report page, plain English: what you can report, what happens next, who reviews (the maintainer), how fast (target: content that is reported for copyright or personal data is hidden within 24 hours pending review, then removed or restored), and how to contact us directly. Linked from the footer and the sidebar.
Removal workflow:
1. Report arrives, gets an id, goes to the maintainer queue, reporter gets the id.
2. Copyright and personal-data reports hide the document from answers immediately (soft takedown), pending review. Other reasons are reviewed first.
3. Maintainer decides: remove for good (text, chunks, vectors, source record), restore, or fix. The reporter is told the outcome if they left an email.
4. One-click takedown for the maintainer is the same action, usable any time.
Removal log: every report and every removal is written to an append-only log (what, when, reason, who decided, outcome), so the library can show it handled each case. A source that causes repeated valid reports is dropped from the allow-list.

Weekly audit: each week a random sample of auto-published documents (suggest 20) is checked by the maintainer for licence and quality. Results are logged. A failed sample pauses that source until reviewed.

## Staged order
1. Manual upload working end to end, behind the closed switch (smallest, uses what exists). Test with Walter's book and a few files.
2. Provenance records, review queue, takedown, the Report this button, the /report page and the removal log. This comes before any auto-publish.
3. One collector, one source (Project Gutenberg), 50 documents, off-hours. Auto-publish on, with the first batch fully reviewed by the maintainer after the fact as a check. Report the pass rate and the model's licence-check accuracy.
4. Second collector in parallel (Wikisource or US government works). Add the rate and load throttles.
5. User crawl agents: API, declarations, per-user rate limits, abuse controls. Invite-only first.
6. Demand-ranked topics from the not_found log. Coverage map later (separate idea, not part of this plan).

Each stage ends with a check and a screenshot or sample for Walter before the next starts.

## Risks and answers
- robots.txt and site terms: fetch only allow-listed sources, honour robots.txt and crawl-delay, identify the agent with a clear user-agent and contact, cache to avoid refetching. A source that blocks us is dropped, not worked around.
- Wrong licence call (the biggest risk): rules first, model second, "unclear" goes to a human, auto-publish only from allow-listed sources whose licence comes from the source, provenance kept, public Report this, fast soft takedown, weekly sample audit, takedown removes text, chunks and vectors. Public-domain status also varies by country and some "PD" pages carry reuse limits on scans or editions; the check records the stated basis, and the maintainer decides edge cases.
- Abuse of user crawlers: invite-only, signed-in, per-user daily caps, queue-only access, submissions traceable, strikes and cut-off, no direct publish, no fetching on our servers on a user's behalf (their agent fetches, we only receive text).
- Load on the Mac Mini: one model serves everyone. Max 2 collectors, throttled, yield to user questions, off-hours bulk work, daily caps on bytes and documents, a kill switch that stops all collectors at once. Disk growth is small (text and vectors) but is monitored.
- Review bottleneck: auto-publish from allow-listed sources removes most of it; user submissions and unclear cases still queue. Cap the queue so collectors pause when it is full. Reports are a second queue and are prioritised.
- Auto-publish means mistakes are live until caught: mitigated by the audit, reports, and a kill switch per source.
- Poisoned or low-quality text: dedupe, minimum quality checks, prompt-injection filter on collected text (the model must treat page text as data only), review before publish.
- Local model quality: Qwen has hung before on tool calls. Collectors run in small steps with timeouts and are restarted by a watchdog; failures leave the queue untouched.

## Not in this plan
Paid plan, donation opening, Product Hunt, coverage map, any showcase area, anything collecting non-PD / non-CC0 material by machine.
