# Plan: index MCP servers and API docs ("how exactly do I use X?")

Status: PLAN ONLY, for Walter's approval. Nothing here is built. Written 2026-10-22. Updated 12:35 with Walter's decisions: developer docs go in the SAME shared library (no separate collection), the library takes several open licences tagged per document, and there is no private shelf. Where the text below disagrees with this note, this note wins.

Goal: a small local model answers "how exactly do I call tool Y of MCP server X" correctly, from the real docs, with the version and fetch date shown. Promo hook: "try it with these MCPs we indexed".

## 1. Licence rule for developer docs and MCP READMEs
Developer text is licensed differently from books: most is MIT or Apache-2.0 (code licences), some docs are CC BY or CC BY-SA, some are vendor-copyrighted ("all rights reserved", terms of service).

Rule, all machine-checkable:
- Accepted: MIT, Apache-2.0, BSD-2/3, ISC, CC0, CC BY 4.0, CC BY-SA 4.0 (SPDX id read from the repo's LICENSE file at the same commit we fetch). The repo must carry the licence file, and the README or docs must live in that repo.
- Rejected: no licence file, all rights reserved, GPL/AGPL docs mixed with code (unclear for text, skip), source-available or "non-commercial" licences, vendor docs sites, and any page behind terms of service. No human queue: unclear means not indexed.
- Attribution kept: every document stores repo URL, licence SPDX id, copyright line, commit SHA, fetch date, and the NOTICE text when the licence needs it (Apache-2.0). Answers show the source with licence.
- The upstream project can mix licences. Example, checked today: the MCP project's own LICENSE says it is moving from MIT to Apache-2.0, some contributions stay MIT, and documentation contributions (not specs) are CC BY 4.0. So the check is per file or per directory, not per repo: take the licence statement that covers that file, else skip.

Where it lives (Walter, 12:35): in the same shared library, not a separate collection. Each document keeps its own licence (MIT, Apache-2.0, BSD, CC0, CC BY, CC BY-SA, PD), tagged per document. Answers show the licence of every source. This replaces the earlier recommendation of a separate collection. The consequence is the share-alike question in docs/COLLECTION-PLAN.md ("Share-alike interplay"): a generated answer that merges a CC BY-SA source with MIT or Apache docs. A lawyer should read it before charging.

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

## 6. Manual upload licensing (decided by Walter, 12:35)
- The shared library takes several open licences, tagged per document: PD, CC0, CC BY, CC BY-SA, MIT, Apache-2.0, BSD. The user picks the licence from that list when uploading; for repos the LICENSE file must agree.
- User crawl agents: licence detected automatically per document. No licence found: not published (awaiting Walter's confirmation of that default).
- No private shelf. Everything uploaded is shared, so his novels stay out. The earlier option (b) is dropped.
- NC, ND, all-rights-reserved and unlicensed stay out, so the $3/month access charge is clean.
- Open risk: share-alike interplay (see docs/COLLECTION-PLAN.md). Recommendation: a lawyer reads it first.

## 7. Risks of the whole plan
- Docs change faster than we refresh: mitigated by commit-SHA checks and showing the fetch date; a weekly lag is still visible.
- A wrong "correct" answer about an API is worse than a refusal: the test set and the "not in the KB" refusal rule apply, and answers quote tool and parameter names from the source.
- Prompt injection in READMEs (text aimed at agents): the same injection filter runs on every document, and developer docs get an extra check for instructions aimed at an AI, since they are likely targets.
- Mixed licences inside one repo: per-file rule, skip when unclear.
- Hooks like "we indexed X MCP" imply endorsement or affiliation: wording must say "unofficial index of public docs".

## What is still open
1. Confirm "no licence found means not published" for user crawl agents.
2. Starter set: Fetch, Filesystem, Git, Time (recommended).
3. A lawyer's read of the share-alike interplay before the paid tier.
4. Approval to start building (per-document licence field and display, licence check from the repo LICENSE file, the first test set).
