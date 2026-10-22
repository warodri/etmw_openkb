# Collection plan: collectors, user crawl agents, manual upload

Status: PLAN ONLY, for Walter's review. Nothing here is built. Written 2026-10-22.
Builds on docs/LIBRARIAN.md (spec draft) and the existing intake pipeline.

## Fixed rules (Walter's decisions)
- Decision 2026-10-22: single licence, CC BY-SA, for everything in the library. No donor choice of licence, no non-commercial (NC) variant.
- One library, one licence: CC BY-SA. No separate showcase or "producer" area. The producer idea stays as story material for posts and videos.
- Our own collectors take public domain or CC0 only. User crawl agents may also submit CC BY and CC BY-SA sources (section 2). Nothing else is collected by machine.
- Collectors are opencode agents on the local model. No paid model calls. Max 2 running at once.
- The public donate flow stays CLOSED ("Donations open soon") until Walter says otherwise.
- Every document keeps provenance (source URL, licence evidence, date, who added it). Takedown must work.
- Decision 2026-10-22, publishing model: NO human review before publishing, for anything. Our collectors and user submissions both auto-publish after automated checks. Safety comes from the checks, a provenance record on every document, the public report-and-remove path (section 4), an audit log, and invite-only access for user crawlers. A weekly sampled quality audit looks at results afterwards; it does not gate publishing.
- Decision 2026-10-22: any user must have a very clear public way to report content that should not be there (see section 4).

## 1. Collector agents (internet, public domain / CC0 only)
Goal: fill the library before users arrive, ranked by what people asked and the library could not answer (the not_found log), with a maintainer-written seed list until there are enough misses.

Flow per collection: seed list or topic -> find candidate pages -> fetch (respecting robots.txt) -> licence check -> convert to text -> dedupe -> spam / injection / quality filter -> write a provenance record -> auto-publish if all checks pass. Anything that fails or is "unclear" is NOT published; it is logged with the reason and dropped.

Allowed sources (allow-list, start small): Project Gutenberg, Wikisource, US government works, Library of Congress / Internet Archive items marked public domain, Wikimedia Commons text, CC0 datasets. A source not on the list is not fetched.

Licence check, two parts, both must pass:
1. Rule-based: the source's own licence field or page statement says public domain / CC0 (machine-readable where it exists).
2. The local model reads the licence text and gives a yes / no / unclear. "Unclear" is not published (no human queue, so unclear means no). The model never overrides a rule-based "no".

Limits: 2 collectors max, each with its own request rate and daily byte cap. User questions always win over collectors for the model. Heavy conversion runs off-hours.

## 2. Users adding their own crawl agents
Who: signed-in users on desktop or agent mode, pointing their own agent at their own sources. Not open to anonymous visitors.

Gate (the licensing gate):
- The user declares the source and the licence up front and agrees to the same three statements as a manual donation (it is theirs to share or the licence allows it, CC BY-SA OK, may be edited).
- Their agent submits through one API only, with the user's invitation key, and is subject to the same automated checks. A passing submission auto-publishes.
- Automated checks on every submission: licence declared and on the accepted list (PD / CC0 / CC BY / CC BY-SA), source URL present and reachable, page evidence agrees with the declaration where a licence statement can be read, dedupe against the library, spam / prompt-injection / quality filter, per-user rate and size limits. NC, ND, unclear and unlicensed sources are rejected. No human reviews it before it goes live.
- Each submission carries the user id, so a bad actor is traceable and can be cut off.

Decision 2026-10-22 (Walter): user crawl agents contribute to the ONE shared library, not to private collections. The point is to grow together instead of everyone duplicating the same work.
Accepted source licences for user crawlers: public domain, CC0, CC BY and CC BY-SA. The original author credit and licence are kept in the provenance record. NC and ND sources are excluded. Everything lands in the library under the single CC BY-SA rule (CC BY and CC BY-SA sources are compatible with it, with credit kept). Decision 2026-10-22: user submissions auto-publish after the automated checks (this replaces the earlier human-review rule).

Access is invite-only. How to request an invitation (to be written on the /agent page and a short /crawlers section before launch): a signed-in or emailing user sends a short request saying who they are, what sources their agent will crawl and under which licence; the maintainer replies with a personal invitation key, and the key can be revoked at any time. Keys carry the daily caps.

## 3. Manual upload
Reuses the existing donate pipeline: upload (PDF, Word, scans, photos) -> convert -> preview of the text -> three declarations -> automated checks -> join the library under CC BY-SA, credited, with a provenance record. No human review before publishing. It is built behind the closed switch, so the page can keep saying "opens soon" while Walter and a few testers use it. Walter's own book is the first test document, by his choice.

## 4. Reporting and removal (required before any auto-publish)
Decision 2026-10-22 (Walter): no human validates content, and no human validates reports either. Reports are triaged automatically; a person acts only when the case is not obvious.

Public reporting:
- A visible "Report this" on every answer with sources. One tap, no sign-in. A /report page in plain English explains what is checked, what is removed at once, and what goes to a person.
- Reports are not hidden on arrival. Immediate hide on any report is a griefing vector (anyone could knock out any document). The safe automatic rule is below.

Automatic triage (library.report):
- Abuse controls: 10 reports/hour per address, one report per reporter per document, spam and link-stuffing patterns dismissed, per-reporter reputation (three earlier reports that did not hold up and none upheld: ignored automatically).
- Copyright (Walter, 2026-10-22: "we ask the source; no answer, no removal"): the report must name the rights holder and give an email for them, a link to the original, and a good-faith statement. Incomplete: the reporter is told what to add. Complete: the evidence page is fetched and compared with the document (8-word overlap). Overlap under 10%: dismissed, nothing else happens. Otherwise the named contact must be tied to the evidence: its email or domain appears on the evidence page, or the page is on that domain. If not (or the page cannot be fetched), the report goes to the maintainer queue and NO email is drafted. If tied, a verification email to the NAMED rights holder is drafted (never to the reporter). It is held in an outbox and is only sent after Walter approves it (see "Verification email" below). The holder opens a one-time link and answers Yes (ours, used without permission: the document is removed at once) or No (kept, report closed). No answer in 7 days: the report is closed, the document stays, nothing is removed. A reporter cannot confirm their own claim: only the one-time link in the email to the named holder removes a document.
- Hold rule while waiting (proposal, implemented): the document stays LIVE, except when the evidence page is a clear match (overlap 50% or more, copyright notice, no permissive licence, different domain, not a collector document). Then it is HIDDEN, not removed, until the holder answers, and restored if they say No or do not answer in 7 days. Reason: hiding on a bare claim is a griefing vector; hiding on a clear match costs little and is reversible.
- Personal information: the reporter must quote the exact text. Not found in the document: dismissed. Found and it contains an email, phone, ID or similar identifier: removed automatically. Found but not an obvious identifier: queued.
- Harmful or quality: the document is rerun through the automatic checks; failing them removes it. Otherwise harmful reports are queued with details, hidden only when 3 separate reporters agree within 7 days; quality reports are noted and queued only at 3 separate reporters.
- Everything is written to the audit log with the reason for the outcome.

Maintainer queue: only reports marked queued. Commands: `python3 app/library.py reports | decide <id> remove|restore|dismiss | remove <doc-id> | log`. Target 24 hours. Each decision updates the reporter's reputation.

Residual risks, stated plainly:
- A griefer can fake a page that matches and name an email address they control as the 'rights holder'; their own confirmation would remove the document. The email goes to the contact the reporter gave, so we cannot tell. Mitigations: the document is only hidden pending (not removed) until they answer, a contact domain that differs from the evidence site is flagged in the log, the mail is sent only after Walter approves it, and the first real cases show if this needs a stronger check (for example, requiring the contact to appear on the evidence page). Silence never removes anything.
- Personal data is removed at the document level (no redaction yet).
- The evidence fetch makes our server open a stranger's link; it refuses private and local addresses, caps size and time.
- Overlap thresholds (10% / 50%) are first guesses. Tune after real reports.

Weekly audit: each week a random sample of auto-published documents (suggest 20) is checked by the maintainer for licence and quality. Results are logged. A failed sample pauses that source or user key until looked at.

## Staged order
1. Manual upload working end to end, behind the closed switch (smallest, uses what exists). Test with Walter's book and a few files.
2. Provenance records, automated checks, takedown, the Report this button, the /report page, the removal log and the audit log. This comes before any auto-publish.
3. One collector, one source (Project Gutenberg), 50 documents, off-hours, auto-publish on. Report the pass rate, the filter results and the model's licence-check accuracy.
4. Second collector in parallel (Wikisource or US government works). Add the rate and load throttles.
5. User crawl agents: API, declarations, per-user rate limits, abuse controls. Invite-only first.
6. Demand-ranked topics from the not_found log. Coverage map later (separate idea, not part of this plan).

Each stage ends with a check and a screenshot or sample for Walter before the next starts.

## Risks and answers
- robots.txt and site terms: fetch only allow-listed sources, honour robots.txt and crawl-delay, identify the agent with a clear user-agent and contact, cache to avoid refetching. A source that blocks us is dropped, not worked around.
- Wrong licence call (the biggest risk, accepted by Walter): rules first, model second, "unclear" is not published, auto-publish only from allow-listed sources or declared accepted licences, provenance kept, public Report this, fast soft takedown, weekly sample audit, takedown removes text, chunks and vectors. Residual risk, stated honestly: with no human review, some wrongly licensed material will get published, and a rights holder may see it before we do. Public-domain status also differs by country, and a user can declare a licence falsely or a source page can be wrong. The defence is speed of removal and an audit trail showing good-faith process, not prevention. This does not remove legal exposure; a plain terms page and a named contact for rights holders (on /report) are needed, and Walter may want a lawyer to look at the terms before launch.
- Abuse of user crawlers: invite-only, signed-in, per-user daily caps, queue-only access, submissions traceable, strikes and cut-off, no direct publish, no fetching on our servers on a user's behalf (their agent fetches, we only receive text).
- Load on the Mac Mini: one model serves everyone. Max 2 collectors, throttled, yield to user questions, off-hours bulk work, daily caps on bytes and documents, a kill switch that stops all collectors at once. Disk growth is small (text and vectors) but is monitored.
- Review bottleneck: removed by design. The only human queue is reports, which are prioritised, and the weekly sample.
- Auto-publish means mistakes are live until caught: mitigated by the audit, reports, and a kill switch per source.
- Poisoned or low-quality text: automated only, per Walter: dedupe, minimum length and language and garbage checks, prompt-injection filter (collected text is data only, never instructions to the model), spam patterns, per-user rate limits. Test on the first 50 documents plus a set of deliberately bad samples. If the filters prove unmanageable or unreliable, the alternative to bring to Walter: a trust ladder, where a new key's first submissions publish after a short delay (e.g. 24 hours, visible to the report path) and trusted keys publish at once; still no per-document human review.
- Local model quality: Qwen has hung before on tool calls. Collectors run in small steps with timeouts and are restarted by a watchdog; failures leave the queue untouched.

## Not in this plan
Paid plan, donation opening, Product Hunt, coverage map, any showcase area, anything collecting non-PD / non-CC0 material by machine.

## Verification email (draft, nothing sends without Walter's approval)

To: the rights-holder address named in the report. Subject: "Please confirm: is this your work? (OpenKB copyright check)". Body: says someone reported that the document (title) belongs to them, that we do not remove on a stranger's say-so, a one-time link to a page with two buttons (Yes remove it / No keep it), that silence for 7 days means we keep it and close the report, that we never ask for money or documents, and that they can ignore it. The exact text is in app/library.py `verification_mail`. The page is GET-safe (opening the link, or a mail scanner, changes nothing; only the button press does).

Sending route (decision needed): the draft sits in an outbox (`python3 app/library.py outbox`, `approve <id>`). Options: (a) the existing OpenKB SMTP mailbox used for owner alerts, sending each approved message to the holder; (b) Instinct Agent Mail; (c) Walter sends it by hand. Recommended: (a) with per-message approval at first, then a rate limit (max 5 verification emails/day, one per address per 30 days) if Walter later allows automatic sending. Not wired up: no code sends to third parties yet.

## Verification email route (Walter, 2026-10-22)
Emails go out through Instinct's Agent Mail, not the OpenKB SMTP. The OpenKB side never sends to third parties. `python3 app/library.py outbox-json` prints drafts as JSON (id, report_id, to, subject, body). Walter approves each one; after the mail task sends it, `approve <id>` then `mark-sent <id>` start the 7-day clock (the one-time link only works once the status is sent). No automatic sending for now.

## First collector (built)
app/collector.py: Project Gutenberg only (allow-list), robots.txt checked, 5 s between requests, per-run byte cap, short works only at first. Rule check (page says public domain in the USA) AND local model reading the rights text (yes/no/unclear, unclear is not published), then the library checks. Dry run by default; `--publish` to publish.

### Collector schedule and load monitor
Daily at 03:30 on the Mac Mini (launchd job com.openkb.collector): `app/collector_run.py --n 25 --publish --model-check`. Each run appends one JSON line to data/collector_runs.jsonl (not in git): docs published, bytes, seconds, failures by reason, CPU, free memory, ollama memory, embedding latency, and the demo's answer time before and after. The candidate list comes from the Project Gutenberg catalogue feed (English text, non-fiction subjects first filter). First run (10:23, 25 docs, 1.57 MB, 24 min): see the report to Walter; answers stayed correct and the machine stayed mostly idle.
