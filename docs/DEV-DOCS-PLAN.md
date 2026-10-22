# Plan: index MCP servers and API docs ("how exactly do I use X?")

Status: PLAN ONLY, for Walter's approval. Nothing here is built. Written 2026-10-22.

Goal: a small local model answers "how exactly do I call tool Y of MCP server X" correctly, from the real docs, with the version and fetch date shown. Promo hook: "try it with these MCPs we indexed".

## 1. Licence rule for developer docs and MCP READMEs
Developer text is licensed differently from books: most is MIT or Apache-2.0 (code licences), some docs are CC BY or CC BY-SA, some are vendor-copyrighted ("all rights reserved", terms of service).

Rule, all machine-checkable:
- Accepted: MIT, Apache-2.0, BSD-2/3, ISC, CC0, CC BY 4.0, CC BY-SA 4.0 (SPDX id read from the repo's LICENSE file at the same commit we fetch). The repo must carry the licence file, and the README or docs must live in that repo.
- Rejected: no licence file, all rights reserved, GPL/AGPL docs mixed with code (unclear for text, skip), source-available or "non-commercial" licences, vendor docs sites, and any page behind terms of service. No human queue: unclear means not indexed.
- Attribution kept: every document stores repo URL, licence SPDX id, copyright line, commit SHA, fetch date, and the NOTICE text when the licence needs it (Apache-2.0). Answers show the source with licence.
- The upstream project can mix licences. Example, checked today: the MCP project's own LICENSE says it is moving from MIT to Apache-2.0, some contributions stay MIT, and documentation contributions (not specs) are CC BY 4.0. So the check is per file or per directory, not per repo: take the licence statement that covers that file, else skip.

Where it lives: a separate collection ("developer docs"), not mixed into the CC BY-SA general library. Reasons: (1) MIT/Apache text cannot be relicensed as CC BY-SA by us, it must keep its own licence and notice; (2) the "everything in this library is CC BY-SA, reuse it freely" promise stays true for the general library; (3) answers can say "from developer docs, Apache-2.0". The general library keeps one licence, as Walter decided. CC BY and CC0 developer docs could also sit in the main library, but one rule per collection is simpler. Retrieval searches both; the answer says which collection each source came from.

## 2. Version, fetch date, staleness
- Every doc chunk carries: project, version or tag (or commit SHA if untagged), fetch date, source URL. Answers show it under the sources: "From server-fetch, v1.2.0 (commit a1b2c3d), fetched 2026-10-22".
- Weekly refresh by the collector: re-fetch each indexed repo, compare commit SHA. Changed: re-index the changed files and keep the old version for 30 days labelled "older version". Gone or licence changed to a rejected one: remove at once (same takedown path as everything else).
- Staleness shown to the user: older than 30 days since fetch: "docs checked N days ago". If the upstream licence changed or the repo was archived, say so.
- If the question names a version we do not have, the answer says which versions it has and refuses to guess.

## 3. Starter set (3 to 5, open licences; not Vonage)
Checked today in the official reference repo (https://github.com/modelcontextprotocol/servers, README lists them as reference servers):
- Fetch (web content fetching and conversion)
- Filesystem (file operations with access controls)
- Git (read, search, manipulate repositories)
- Memory (knowledge-graph memory)
- Time (time and timezone conversion)
(also Sequential Thinking and Everything).
Proposed first four: Fetch, Filesystem, Git, Time. Small, widely used, easy to verify. Licence per file must still be confirmed by the rule above (the repo says MIT or Apache-2.0 depending on contribution, docs CC BY 4.0). Third-party servers (for example Brave Search's official server) need their own LICENSE check before adding; I have not verified any beyond the reference servers.

## 4. Published test set
- About 30 "how do I" questions, 6 to 8 per server, e.g. "which parameters does the Git server's log tool take", "how do I give the Filesystem server access to a folder", "what does fetch return for robots.txt-blocked pages".
- Each question has an answer key written from the official README and source at the indexed commit (tool names, parameter names, required fields, example config). Scoring: correct only if the tool and parameter names and the config are exactly right; partial answers count as wrong.
- Two columns published on the site and in the repo: OpenKB with the docs indexed, and the same small model without them (to show the lift). Method, commit SHAs, questions, answers and the score all public. Same style as the existing 20-question test (19/20). We do not tune the test set to the results.
- Rerun after each refresh; the score and date appear on the page. If the score drops, say so.

## 5. How it enters via manual upload
- A tester or donor pastes a repo URL (or a README) on the donate page and picks "developer docs". The server fetches the repo's LICENSE at a pinned commit, reads the SPDX id, and applies section 1. The declared licence is never trusted without the licence file.
- Passing: indexed in the developer-docs collection with provenance (repo, commit, licence, fetch date). Failing: the reason is shown, nothing stored.
- Same report-and-remove path as the general library (copyright reports go to the named holder; nothing removed on a claim alone).
- The collector can later add repos from an allow-list by the same code. Third-party users' own agents stay invite-only, as for the general library.

## 6. The licensing question on manual upload (conflict with earlier decisions)
Walter said the manual upload could let users pick other licensing models and would cover his books. Earlier decisions: one licence for the shared library (CC BY-SA), NC and ND excluded, and (12:07) not to upload his novels. Options:

(a) Keep the single licence. Manual upload stays CC BY-SA only. Simple, true to "an open library". His books are not uploaded (already his decision).

(b) A private personal shelf per user. Never shared, never searched for anyone else, never in the public library, any licence including all rights reserved. Signed-in only. The user can ask the model about their own books and notes. Consequences: needs per-user storage and retrieval scoped by user id, a delete-everything button, a size cap, and strict isolation tests. A scoping bug would leak a copyrighted book to strangers, which is the main risk. We also store copies and embeddings of material the user may not own, so the declaration "this is mine or I may store it" is needed and the takedown path must work here too. Privacy law applies to personal documents (notes, letters). It does not change the licence of the public library.

(c) Several licences in the shared library (for example CC BY, CC BY-NC, all rights reserved). Consequences: every answer would have to carry a licence per source; NC and ND break "reuse freely"; all-rights-reserved text in shared answers is a copyright problem for us (we would be quoting it to other people); the library can no longer be redistributed as one CC BY-SA corpus; the report path becomes much heavier. This reverses a decision Walter made today.

Recommendation: (a) now, and (b) later as a separate "My shelf" feature once accounts are solid, built behind a flag and tested for isolation before anyone uploads books. Do not do (c). (b) gives Walter the book use-case he described without touching the shared library's licence. Risks of (b): a leak, storage cost, takedown and privacy handling for personal documents, and the temptation to share a shelf later (that would be (c) by the back door). A shelf must never feed the shared library.

## 7. Risks of the whole plan
- Docs change faster than we refresh: mitigated by commit-SHA checks and showing the fetch date; a weekly lag is still visible.
- A wrong "correct" answer about an API is worse than a refusal: the test set and the "not in the KB" refusal rule apply, and answers quote tool and parameter names from the source.
- Prompt injection in READMEs (text aimed at agents): the same injection filter runs on every document, and developer docs get an extra check for instructions aimed at an AI, since they are likely targets.
- Mixed licences inside one repo: per-file rule, skip when unclear.
- Hooks like "we indexed X MCP" imply endorsement or affiliation: wording must say "unofficial index of public docs".

## What Walter needs to decide
1. Separate developer-docs collection with each project's own licence (recommended) or only CC BY and CC0 docs in the main library.
2. Starter set: Fetch, Filesystem, Git, Time (recommended).
3. Manual upload licensing: (a), (b) later, or (c) (recommended: a now, b later, not c).
4. Approval to start building the licence check and the first test set.
