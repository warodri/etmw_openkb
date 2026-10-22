# Pointer-mode research tests 1 and 2 - results

Run 22 Oct 2026, 13:39-13:45 on the Mac Mini with the live reader (qwen3.6:35b-a3b) and embeddings (qwen3-embedding:4b). Research only: nothing public changed, nothing stored in the library. Script: tests/pointer_research.py. Raw results stayed in data/ (gitignored). Plan: docs/POINTER-MODE-PLAN.md.

## Test 1 - catalogue answers from short descriptions, no fetching
- 32 pointer entries (the open documents we already index), each described in one sentence by the reader from the first 2,500 characters: 51 s in total (about 1.6 s per entry).
- 10 catalogue questions with hand-made answers ("Which entries are speeches by US presidents?", "Which entry is a cookbook?", "Which entries are open letters?").
- Retrieval (embedding of title + description): the right entries were in the top 10 for 10 of 10 questions (recall 1.00).
- Reader answer from the top 10 entries: mean F1 0.96. Mean time 0.8 s per question.
- Caveat: 32 entries is small and the questions are easy topic questions. A catalogue of thousands, and questions like "unknown thriller authors", are not tested here.

## Test 2 - quick read: fetch one page, read the first 24,000 characters, answer
- 10 API/doc pages (docs.python.org, sqlite.org) and 10 public-domain book pages (Gutenberg). robots.txt honoured, 5 s between requests, one request per page, a research user agent.
- Correct: API pages 9 of 10, book pages 7 of 10 (16 of 20).
- Fetch: about 5.8 s per page (almost all of it the 5 s politeness delay). Read and answer: 7.0 s per API page, 8.9 s per book page, slowest 10.7 s. So a quick read costs about 13-15 s end to end, better than the 16 s per chunk estimate in the plan.
- Every one of the 4 misses was a refusal ("not on the page"), none was a wrong answer. 3 of the 4 had the answer inside the first 24,000 characters (python re.search, Pride and Prejudice, Treasure Island), so the reader refused when it should have answered. The 4th (Moby Dick, "Call me Ishmael") is after the long front matter, outside the first chunk: a correct partial-read refusal.
- So: quick read works and fails safe, but misses about 15 percent. Mitigations to test next: retrieve the matching part of the fetched page by keyword or embedding instead of always reading the first chunk; ask the reader to quote the line it used so quotes can be checked against the page.

## What this means for the open decisions
- Catalogue (pointer fields and descriptions) is cheap and accurate enough to build later.
- Live quick reads are slower (13-15 s) than stored retrieval (1-4 s) but usable as a labelled "read live" mode.
- Not tested: full reads, failure cases, prompt-injection pages, concurrency (tests 3 to 6 in the plan). Those need Walter's go.
