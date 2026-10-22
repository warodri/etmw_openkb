# Architecture - where OpenKB lives

Three pieces, each replaceable on its own.

## 1. The library (GitHub) - source of truth

Every donated document lives in this public repo as plain Markdown with a header:

```
---
source: where the knowledge comes from (book, manual, lived experience)
licence: CC BY-SA 4.0
donor: name or handle from the public donor log
date: YYYY-MM-DD
---
```

If you can read this repo, you can rebuild everything else. No other system is required.

## 2. The index (Hugging Face dataset) - the fast path

Searching needs embeddings. Computing them for the whole library takes time, so we publish a **prebuilt, versioned index** as a Hugging Face dataset: the chunks, their vectors, and the model version they were made with (currently Qwen3-Embedding-4B). The index is always rebuildable from the repo - it is a cache, not a source. Large files (audio, scans, datasets) live on the Hugging Face side, not in git.

Versioning rule: embedding model changes mean a new index version, never a silent overwrite.

## 3. The demo / API (ETMW) - just one consumer

ETMW hosts the live demo, and later an optional hosted API, both reading the public index. Anyone else can do the same: clone the repo or pull the index, run the reader on your own machine. ETMW hosting is a convenience, not a gate.

## Donation flow

Donors are readers, writers and neighbours, not developers. Nobody is asked to write Markdown or headers.

1. **Submit anything** - a PDF book, DOCX, EPUB, TXT, HTML, whatever you have. You answer three short questions in a form: what it is, who you are (name or handle), and the licence + AI-retrieval consent (EN/ES).
2. **Intake converts it for you** - an automated step turns the upload into clean Markdown using open-source converters (the plan is [Docling](https://github.com/docling-project/docling), MIT-licensed, strongest on PDFs including scanned pages, with MarkItDown and Pandoc as fallbacks for other formats) and fills the document header from your form answers. Scanned books go through OCR, and OCR makes mistakes - which is what step 3 is for.
3. **You confirm the preview** - you see the converted document before anyone else does. Nothing goes to review without your OK.
4. **Automatic checks** - licence, consent declarations, sourcing, duplicates, spam and prompt-injection filters run before publish. No person reads a document first (decision 2026-10-22); safety comes from provenance, the public report path with automatic triage, and an append-only audit log. See docs/COLLECTION-PLAN.md.
5. **Merged** - the document lands in the repo, the donor log is updated, and the index picks it up on the next build.

Licensing note: book donations raise a real question - whether CC BY-SA 4.0 fits, or books need a retrieval-only option (the model reads and cites, no copying). Undecided; the default stays CC BY-SA 4.0 until the owner decides.

Takedown is real: ask and your content is removed from the library and the next index build.

## Takedown policy

Git remembers: a public repo keeps history, and copies may survive in old commits and other people's clones. So takedown works in three tiers, and the consent text says this plainly before anyone donates.

1. **Normal takedown.** On request, the document leaves the repo HEAD, the donor log is annotated, and the next index build drops it. We say honestly that history and existing clones cannot be recalled.
2. **Sensitive donations.** If a donor flags content as sensitive at intake (for example a book), the file itself never enters git: the repo holds only metadata, a hash and a pointer to the Hugging Face copy. Takedown deletes the dataset file, which is fully in our control.
3. **Legal necessity.** Court order or personal data: full history rewrite (git filter-repo) with a public note that it happened. Reserved, never routine.

The promise is removal, engineered to be real where it matters; the honesty is that no one can recall a public clone.

## Self-hosting with Janus (optional)

Some donors will want to keep material on their own computer while letting OpenKB read it. [Janus](https://entertomyworld.com/apps/janus/) is one way: it gives a local service a public URL, so a donor's own machine can serve documents to the library while the files stay home.

Two honest notes: Janus is entirely optional - OpenKB works fully without it, through the repo and index above. And Janus is itself an ETMW product, built by the same studio as this project's first reader; use it if it helps, ignore it if not.
