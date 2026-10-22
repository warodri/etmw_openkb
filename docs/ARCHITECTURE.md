# Architecture - where OpenKB lives

Updated 22 Oct 2026 to match docs/VISION.md. Status marks: DECIDED (Walter) or OPEN.

Three pieces, each replaceable on its own.

## 1. The library = an index of references (DECIDED 22 Oct, 13:14 and 13:18; build pending)
The library does not host documents. For every document it keeps:
- the source URL and title,
- the licence (Public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0 or BSD) and credit,
- per chunk: byte or character offsets into the source, a hash of the chunk, and the embedding vector.

At question time the reader fetches only the top few chunks from the source URL, checks the hash, and answers from them with the licence shown. If the source is gone or has changed, that chunk is dropped and the answer says so. No whole books are loaded.

OPEN: a short-lived cache (proposal: 24 hours, capped) for fetched source pages, so hosts are not hit on every question. Without it we would break our own one-request-per-5-seconds crawl rule at volume. Awaiting Walter's yes.

Today (before the change) the Mac Mini still stores chunk text for 32 library documents plus 50 synthetic test documents. Purge is on hold until the design is tested (19/20 retest).

## 2. The index - on disk, not in memory (DECIDED, live since 22 Oct)
sqlite-vec, float32 cosine vectors in data/vindex.db (app/vindex.py). No vectors are held in Python memory. 821 chunks use 13.8 MB; a 20,000-chunk test (about 800 documents) takes 64 ms per search and 211 MB. The index is derived: a takedown or hide drops the document from it on the next sync.

Versioning rule: an embedding model change means a new index, never a silent overwrite.

## 3. The demo / API (ETMW) - just one consumer
ETMW hosts the live demo. Anyone else can run the reader on their own machine against the same references. ETMW hosting is a convenience, not a gate.

## Contributing (DECIDED)
Contributors submit a reference (a URL or location), not the text. Crawl agents submit the same way. Uploading a file is not part of the plan.
1. **Submit a reference** - URL, title, the licence you declare, and who you are.
2. **Fetch and convert** - the server fetches the URL, respecting robots.txt and rate rules, and converts it to text with open-source converters.
3. **Automatic checks** - licence (declared and detected), duplicates, spam, prompt-injection filters, quality. No person reads a document first (decision 2026-10-22). The licence found on the page wins over the declaration if they disagree.
4. **Index** - chunk offsets, hashes and vectors are stored. Text is not stored.
5. **Audit** - every step lands in an append-only audit log.

OPEN: pages with no licence (proposal: a pointer-only entry, no text indexed) and the pointer-mode tests; see docs/POINTER-MODE-PLAN.md.

## Takedown (DECIDED)
A copyright report needs the rights holder's name and contact. We ask that named holder (Walter approves each email). The document is hidden within 24 hours while the report is open; 7 days with no answer means it stays; a confirmed holder means removal. A weekly sample of 20 documents is checked; a person only handles unclear cases. Because the library holds references and vectors, not copies, takedown means dropping the entry and its vectors from the index.

## Self-hosting with Janus (optional)
A donor who keeps material on their own computer can serve it to the library through [Janus](https://entertomyworld.com/apps/janus/), which gives a local service a public URL. The library then indexes that URL like any other reference. Janus is optional and is an ETMW product, built by the same studio as this project's first reader.
