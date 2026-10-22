# OpenKB vision

Single page Walter and the build team check first. Last updated 22 Oct 2026. Each line is marked DECIDED (with date) or OPEN.

## 1. Vision (DECIDED)
- A small model that runs locally, plus one giant shared index. The model fetches only the parts it needs. No whole books are loaded.
- The goal is to provide information, not to cure cancer. A modest, reliable reader over a shared library.
- Answers come only from the library and cite their sources. If it is not in the library, the model says so.

## 2. Shared library and licences
- DECIDED (22 Oct): one shared library with several OPEN licences, tagged per document and shown in answers: Public Domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0, BSD.
- DECIDED: NC, ND and all-rights-reserved content stays out.
- DECIDED: no private shelf. Walter's novels stay out. No separate dev-docs collection.
- DECIDED: $3/month tier buys access to the model and the library.
- OPEN: per-document licence tagging, the upload licence picker and licences shown in answers are not built yet.

## 3. Contributors
- DECIDED: two routes, uploads and user crawl agents. Content is auto-published after automated checks. No human validation of content.
- DECIDED: crawl agents detect the licence per document.
- OPEN: what happens when no licence is found. Current default is "not published". Proposal: a pointer-only entry (title, URL, short note, no text stored). Needs Walter's decision.

## 4. Answers and quotes
- DECIDED (22 Oct, 13:04): default answer is reference only. Quote on request, with the licence shown. No quote length limit, because indexed content is open-licensed by definition.

## 5. Copyright reports
- DECIDED: a report needs the rights holder and a contact. We email that named holder (Walter approves each outgoing email).
- 24 hours: the document is hidden while the report is open. 7 days with no answer: the document stays. A confirmed holder removes it.
- A weekly sample of 20 documents is reviewed. A human acts only on unclear cases (target 24 h).

## 6. Collectors
- DECIDED and running: Project Gutenberg (03:30 daily, 25 docs), Internet Archive Library of Congress collection, pre-1929 only (05:00 daily).
- DECIDED: Wikisource later.
- Rules: one worker per host, 5 s between requests, robots.txt respected, only PD/CC0 for our own collectors.
- DECIDED: raise the daily limit to 60-100 per collector after 2-3 nightly logs look clean (check scheduled for 25 Oct).

## 7. Counter and limits
- DECIDED: public counter shows active crawl agents (no robot icon). Queue message live. DAILY_CAP is 1000.
- DECIDED: donations stay closed ("Donations open soon") until Walter decides.

## 8. Index and storage
- DECIDED (22 Oct, 13:02): disk-based vector index (sqlite-vec, float32, cosine). No all-vectors-in-RAM.
- Built and tested on 22 Oct: see docs/BACKLOG.md and the commit log. 821 chunks use 13.8 MB on disk; the server's memory dropped from about 90 MB to about 39 MB; a 20,000-chunk test (about 800 docs) takes 64 ms per search and 211 MB on disk.
- Retrieval test: 19/20 answers and 5/5 refusals, same as before. Q10 stays as is.

## 9. OPEN / UNDECIDED
1. No-licence pages as pointer-only entries (see docs/POINTER-MODE-PLAN.md). Research tests 1 and 2 approved 22 Oct 13:05, research only, nothing public.
2. Pointer-mode build: not approved.
3. A lawyer reads docs/CONTENT-LICENSE.md (share-alike interplay) before the paid tier or public launch.
4. Tagging, upload picker, licences in answers (section 2).

## 10. Prior art
- II-Commons, HIVE, Context7 and Common Corpus are inputs and neighbours. The architecture (small reader plus retrieval over a shared index) is not new.
- The opening: simplicity and trust for ordinary local-AI users. One install, an open library, clear licences, answers that cite.
