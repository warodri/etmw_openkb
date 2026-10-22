# Plan: pointer-index mode (live reading) in the same library

Status: PLAN ONLY, for Walter's approval. Nothing here is built. Written 2026-10-22 after his 12:38-12:41 direction.

Idea: besides full documents, the library holds pointer entries: title, author, short description, licence if known, URL. At question time an agent fetches the page or book, reads it with the small local model, and answers with a summary plus short quotes. Good for catalogue questions ("unknown thriller authors"), "what is this book about?" on open books, and live API docs (always current).

## 1. Two modes, one library
- Stored mode (what exists today): the text is in the library, chunked and embedded, retrieved by vector search. Licence-gated: open licences only.
- Pointer mode: the entry has no stored text. Fields: id, title, author, short description, genre or topic tags, URL, licence_known (an open licence id, "unknown", or "indexed by author consent"), robots_ok (checked at add time and again at fetch time), added_by, consent record when the author asked for it, date checked, status (live, gone, blocked).
- Retrieval: one search over both. Stored chunks answer as now. Pointer entries are searched by title, author, description and tags (embedded like documents, so "unknown thriller authors" works). A router step decides per question: answer from stored text, answer from the catalogue (no fetch), or read an entry live.
- Every answer lists its sources with the mode ("stored text" or "read live on <date>") and the licence.

## 2. How long-text reading works with a small local model
Measured today on this Mac Mini with the reader model: summarising one 24,000-character chunk (about 5,800 tokens) with a 300-token output took 16 s. A combine ("reduce") step over 10 summaries took 7.5 s. So:
- Map-reduce: split the text into chunks of about 24k characters, summarise each (map), then combine the notes into one summary (reduce, in more than one pass if there are many chunks).
- A short work (the 263 KB book we hold, about 11 chunks) takes about 3 minutes plus fetching. A 1 MB book takes 12 minutes or more. A web page or API doc page (under 24k characters) takes 16 s.
- That is too long for a chat reply, so three reading depths:
  1. Catalogue answer: from the stored description, no fetch, seconds.
  2. Quick read: fetch, read the first chunk or two, the table of contents, or the part matching the question (retrieve by keyword inside the fetched text), 20 to 40 s. Say so in the answer ("based on the first part"). API docs are mostly this case.
  3. Full read: a background job with progress ("reading chapter 4 of 11"), a notification when done, then the summary is cached (see below). Only for open books, one at a time.
- Quotes: the answer may contain short quotes (a few sentences, with the location). Quotes are checked against the fetched text so the model cannot invent them. For non-open entries the quote limit is small and fixed (proposal: under 25 words each, at most 3 per answer). Open and public-domain entries can quote more.
- Cache of derived summaries: for open and public-domain entries only, the chunk summaries and the final summary are cached with the source hash and the date. A changed page invalidates the cache. For non-open entries nothing derived from the text is kept; only the pointer fields and the fetch log (URL, time, status) are stored.

## 3. Fetch rules
- robots.txt honoured from day one, checked at add time and at every fetch. Disallowed means the entry is marked blocked and never read live.
- One request at a time per host, 5 s between requests (the same rules as the collectors). A user-agent that names OpenKB and a contact URL. A cap on size (about 2 MB) and time per fetch.
- No logins, no paywall tricks, no CAPTCHA solving, no cookies, no following links to other domains. An HTML, plain text or PDF page only.
- Site terms: at add time a person or the automatic check records whether the site's terms forbid automated access. Unknown is treated as a risk and shown (see section 7).
- Server-side fetch safety: the same checks as the report evidence fetch (no private or local addresses, redirect limits).
- Live pages are untrusted input. The reading agent only has the fetch of that one entry's URL (no other tools, no web search, no email), treats the page as data, and a prompt-injection filter runs on the fetched text before the model sees it. The answer is checked for instructions or links that came from the page.

## 4. Failure modes and what the user sees
- JavaScript-only pages: the plain fetch returns an empty shell. Try an offline text extraction. If still empty: "I could not read this page." (A headless browser is a later option and raises load and legal questions.)
- Paywall or login: "This needs a login. I can only point you to it."
- Page gone (404, domain dead): mark the entry gone, answer from the stored description with "link no longer works". A weekly check removes dead pointers.
- Changed page: cached summary invalidated, re-read on demand.
- Page too large or not text: "too large to read here", pointer only.
- Slow or down site: timeout, say so, fall back to the description.
- The model fails or the queue is full: the existing busy and queue messages apply. Live reads must not block normal questions (see section 6).

## 5. Licence and terms handling per entry
- licence_known is a stored field: an open licence id, "unknown", or "indexed by author consent". It is shown in every answer.
- Open or PD entries: may be read in full, summaries cached, longer quotes allowed. These are also candidates for conversion into stored mode (collectors do this today for PD).
- Copyrighted entries the author asked us to index (consent via a verified email, like the copyright verification flow): pointer fields and live reading with short quotes only; nothing cached. The consent says what we do, in plain words, and can be withdrawn.
- Unknown licence: pointer fields only (title, author, a short description) and no live reading of the full text unless the site's terms and robots allow it. Default to the safer behaviour.
- Takedown works as everywhere: a report removes the pointer; a copyright claimant is asked by email like in the stored library.
- Description text: our own short summary written by the local model or provided by the author is safest. Do not copy a publisher's blurb wholesale, it is their copyright.
- Conflict to settle (flag): Walter's 12:35 decision keeps all-rights-reserved material out so charging $3/month stays clean. Pointer mode brings such works back in as metadata and live reading. Metadata (title, author, facts) is not copyrightable text, but live summarising of a copyrighted work for a paying user is a different thing from linking. Recommendation: say plainly that pointer mode is a separate, clearly labelled feature, and have a lawyer decide whether it is inside the paid tier.

## 6. Load and cost
- All reading runs on the local reader model, no paid calls. The reader answers one thing at a time, so a live read slows other users. Rules: at most one live read in flight, a maximum of 2 chunks for a chat-time quick read, full reads only as background jobs at night or with a low priority, and a normal question always goes first. Each job logs time and bytes, like the collector load monitor.
- Fetch cost: one request per page (about 5 s with politeness). Catalogue answers cost nothing extra. Cached summaries make a repeat of an open book free.
- Storage: pointer entries are kilobytes each. Cached summaries for open books are a few KB. No stored text for non-open entries.

## 7. Risks
- Terms and robots: honouring robots.txt does not mean the terms allow automated reading. Many sites forbid it. A live read of a page is not a licence to use its text.
- Quotes and summaries of copyrighted text for a paid service are legal grey. "Face it when the moment comes" is Walter's view; Walter's own position is robots and terms honoured from day one, short quotes only, and legal review before public launch. This plan follows that.
- Prompt injection from live pages (see section 3). Higher risk than stored documents, because the content changes after any check.
- Wrong answers: the small model may mis-summarise a long book. Mitigations: quotes checked against the text, "based on the first part" when it is partial, no answer when the page could not be read.
- Staleness is solved for live reads but the pointer descriptions can go stale; weekly dead-link checks.
- Reliability of the sources: a pointer to someone else's site means answers depend on it being up.
- The share-alike and licence-mixing question in docs/COLLECTION-PLAN.md also applies to cached summaries of open entries.

## 8. How it fits the developer-docs idea
- Open, permissively licensed docs and READMEs (MIT, Apache, BSD, CC) can be stored (current plan, with commit and fetch date), and also read live for the newest version.
- Vendor docs that cannot be stored (all rights reserved, terms against copying) could be pointer entries, read live and never cached, if their robots and terms allow automated reading. That would let a small model answer "how exactly do I call X" from the current docs with no stale copy. It is also where the terms risk is largest, so each vendor is a deliberate choice.
- The test set in docs/DEV-DOCS-PLAN.md applies to both modes: same questions, scored on stored versus live.

## 9. What to test first (before anything is built)
1. Catalogue question quality: 30 pointer entries (open, public domain), ask 10 catalogue questions ("which of these are about sailing?"), score against hand answers. No fetching needed.
2. Quick read: 10 API-doc pages and 10 public-domain book pages through fetch plus first-chunk reading. Score answer correctness and time.
3. Full read of 3 public-domain books (short, medium, long): time, summary quality against the Gutenberg synopsis, quote accuracy. Expect about 3 minutes, 12 minutes or more.
4. Failure cases: 10 URLs that are JS-only, paywalled, dead, or huge. Check the messages.
5. Prompt-injection pages: a page that tells the model to ignore its rules or reveal something, check that nothing leaks or changes.
6. Concurrency: a live read running while questions arrive, check answer times stay near the 5-6 s we measured.

## 10. What Walter needs to decide
1. Confirm quote limits for non-open entries (proposal: under 25 words, at most 3 per answer).
2. Whether pointer entries for copyrighted works are in or out of the paid $3/month tier (needs the lawyer).
3. Approval to run test 1 and 2 (no public change, research only).
4. Whether authors can ask to be indexed by email consent, using the same verification flow as copyright reports.
