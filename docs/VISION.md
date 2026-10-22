# OpenKB vision

Single page Walter and the build team check first. Last updated 22 Oct 2026, 13:36. Each line is marked DECIDED (with date) or OPEN.

## 1. Vision (DECIDED)
- A small model that runs locally, plus one giant shared index. The model fetches only the parts it needs. No whole books are loaded.
- The goal is to provide information, not to cure cancer. A modest, reliable reader over a shared library.
- Answers come only from the library and cite their sources. If it is not in the library, the model says so.

## 2. Shared library and licences
- DECIDED (22 Oct): one shared library with several OPEN licences, tagged per document and shown in answers: Public Domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0, BSD.
- DECIDED: NC, ND and all-rights-reserved content stays out.
- DECIDED: no private shelf. Walter's novels stay out. No separate dev-docs collection.
- DECIDED: $3/month tier buys access to the model and the library.
- BUILT (22 Oct): all seven licences are accepted and stored per document; the licence is shown next to each source in answers; the contribution form has a licence picker. NC/ND are refused automatically.

## 3. Contributors
- DECIDED (22 Oct, 13:18): contributors submit a reference (URL or location) to content, not the text itself. Uploading text is not part of the plan. User crawl agents submit the same way. The server fetches the URL, checks it, and indexes it as offsets + hash + URL. Auto-published after automated checks. No human validation of content.
- DECIDED: Walter's novels enter only later, as a submitted public URL (for example a public Google Drive PDF/Doc), through the same pipeline.
- DECIDED: crawl agents detect the licence per document.
- DECIDED (22 Oct, 13:22): crawlers use the licence detected on the page. If none is found, the crawler user's mandatory default licence applies (logged with the account) and the entry is tagged "user-declared". Anyone can request removal.
- DECIDED and BUILT (22 Oct, 13:40): user-declared entries show reference only, no quotes, unless the page states its own licence. The page licence wins; with none, the crawler user's default is used, recorded in the audit log with the account, shown as "(user-declared)" next to the source and the reader is told to paraphrase, not quote. A page showing NC or ND is refused even with a default. Crawl-agent invitation and the default-licence setting on the account are not built yet.

## 4. Answers and quotes
- DECIDED (22 Oct, 13:04): default answer is reference only. Quote on request, with the licence shown. No quote length limit, because indexed content is open-licensed by definition.

## 5. Copyright reports
- DECIDED: a report needs the rights holder and a contact. We email that named holder (Walter approves each outgoing email).
- The document stays visible while a copyright report is open. 7 days with no answer: the document stays. A confirmed holder removes it.
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
- DECIDED (22 Oct, 13:14): no hosted full text. The library keeps references, offsets, hashes and vectors; the text is fetched from the source at question time. Direction decided; design and build pending (see docs/ARCHITECTURE.md). Source gone or changed = that chunk is dropped and the answer says so.
- DECIDED (22 Oct, 13:19): 24 h capped cache of fetched source pages, labelled a temporary copy (so hosts are not hit on every question).
- DECIDED (22 Oct, 13:20): the 50 synthetic test documents are deleted too. A new retest uses real Gutenberg/IA documents. Purge only after that retest passes.
- DECIDED and DONE (22 Oct, 13:19): converted copy of Walter's novel in data/intake deleted.
- DONE (22 Oct, 13:33): all stored text purged on the Mac Mini. library.db holds 771 chunks with offsets, hashes and vectors and no text; the 50 test documents are deleted; the index carries no text. Source pages are read at question time into a temporary copy cache (24 h, max 300 pages, data/cache). A private backup of the old data (mode 700, outside the served path) stays until Walter says to delete it.
- Retest after the purge (cold cache): 13/13 answers, 5/5 refusals, avg 4.6 s, slowest 20 s. Warm cache is about 1 s.
- DECIDED (22 Oct, 13:02): disk-based vector index (sqlite-vec, float32, cosine). No all-vectors-in-RAM.
- Built and tested on 22 Oct: see docs/BACKLOG.md and the commit log. 821 chunks use 13.8 MB on disk; the server's memory dropped from about 90 MB to about 39 MB; a 20,000-chunk test (about 800 docs) takes 64 ms per search and 211 MB on disk.
- Retrieval test: 19/20 answers and 5/5 refusals, same as before. Q10 stays as is.

## 9. OPEN / UNDECIDED
1. Pointer-mode research tests 1 and 2: DONE 22 Oct 13:45, see docs/POINTER-MODE-RESULTS.md (catalogue F1 0.96; quick read 16/20 correct, all misses were refusals, 13-15 s). Tests 3 to 6 DONE 22 Oct (approved 13:50), hardening built and pushed 14:22, see the same file.
2. Pointer-mode build: not approved. Second-source cross-check (reader compares sources and flags a page that contradicts the others): DECIDED 22 Oct 14:25, being built.
3. A lawyer reads docs/CONTENT-LICENSE.md (share-alike interplay) before the paid tier or public launch.
4. Reference-only build and the purge of stored text (section 8).

## 10. Prior art
- II-Commons, HIVE, Context7 and Common Corpus are inputs and neighbours. The architecture (small reader plus retrieval over a shared index) is not new.
- The opening: simplicity and trust for ordinary local-AI users. One install, an open library, clear licences, answers that cite.

## 11. Vision, NOT BUILT: a fact-checker and an open library in one (stated by Walter, 22 Oct 14:25)
- VISION, not built, not designed yet. Walter says more is coming; wait for his next message before designing anything.
- The system agreed at the start is a mix of two things made for this cause: a Twitter-style fact-checker (community notes: who stands behind a claim, and how contested it is) and a Wikipedia-like open library.
- What this means for today's build, only as a reading of the idea and not a plan: the library already answers with its sources and licences; the second-source cross-check (section 9) is a first small step towards "how contested is a claim".
- Open questions for Walter, to ask only when he sends the rest: who may stand behind a claim (named people, accounts, organisations), how "contested" is shown, whether the library keeps claims as entries or only links to sources.
