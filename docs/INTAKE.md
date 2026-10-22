# Open-web intake (step 1 of crawling by user agents) - built 22 Oct 2026

`app/intake.py` takes one web address from a user's crawl agent and either publishes a reference-only entry or refuses it with a logged reason (audit log, with the account). No person looks at it first.

Flow: address check (public http/https only; private and loopback addresses refused, every redirect hop re-checked) -> robots.txt (5 s timeout; 401/403 on robots.txt means stay out) -> one fetch, 5 s between requests to a host, 3 MB cap, text/html or text/plain only -> page asks not to be indexed (noindex, noai)? refuse -> licence the PAGE states (Creative Commons links and rel=license, meta license, SPDX line) -> readable text at least 800 chars -> duplicate, spam and injection checks -> publish offsets, hash, source link and vectors; no text stored.

Licence rule (Walter, 22 Oct 13:22): the page's own licence wins. A page that states one we do not accept (NonCommercial, NoDerivatives, conflicting licences, "all rights reserved") is refused even if the account has a default. If the page states none, the account's default licence applies, is logged with the account and the entry is tagged "user-declared" (reference only, no quotes).

Reading at question time: `source.py` recipe `html` turns the page into text the same way at index and question time (head, nav, header, footer, script, forms removed). Pages from hosts outside our collectors are fetched with the same safety rules, 1 s apart, kept in the 24 h temporary cache.

Known limits: a copyright line like "(c) 2026 Someone" is not treated as a licence statement (nearly every page has one); with an account default such a page is accepted as user-declared. Pages that need JavaScript are refused. Tests: `python3 tests/test_intake.py` (26 checks, local test server).
