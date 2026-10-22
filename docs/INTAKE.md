# Open-web intake (step 1 of crawling by user agents) - built 22 Oct 2026

`app/intake.py` takes one web address from a user's crawl agent and either publishes a reference-only entry or refuses it with a logged reason (audit log, with the account). No person looks at it first.

Flow: address check (public http/https only; private and loopback addresses refused, every redirect hop re-checked) -> robots.txt (5 s timeout; 401/403 on robots.txt means stay out) -> one fetch, 5 s between requests to a host, 3 MB cap, text/html or text/plain only -> page asks not to be indexed (noindex, noai)? refuse -> licence the PAGE states (Creative Commons links and rel=license, meta license, SPDX line) -> readable text at least 800 chars -> duplicate, spam and injection checks -> publish offsets, hash, source link and vectors; no text stored.

Licence rule (Walter, 22 Oct 13:22): the page's own licence wins. A page that states one we do not accept (NonCommercial, NoDerivatives, conflicting licences, "all rights reserved") is refused even if the account has a default. If the page states none, the account's default licence applies, is logged with the account and the entry is tagged "user-declared" (reference only, no quotes).

Reading at question time: `source.py` recipe `html` turns the page into text the same way at index and question time (head, nav, header, footer, script, forms removed). Pages from hosts outside our collectors are fetched with the same safety rules, 1 s apart, kept in the 24 h temporary cache.

Known limits: a copyright line like "(c) 2026 Someone" is not treated as a licence statement (nearly every page has one); with an account default such a page is accepted as user-declared. Pages that need JavaScript are refused. Tests: `python3 tests/test_intake.py` (26 checks, local test server).

## Step 2: accounts, keys and the submission API - built 22 Oct 2026
`app/crawlkeys.py` + endpoints in the live server. Nothing is public: only the owner and testers (the same list as donations) can make an account or key; the submit endpoint answers only a valid key.
- Account: mandatory default licence (must be accepted by the library; NC/ND/all rights reserved refused) plus acceptance of the terms (`TERMS_VERSION`, text in docs/CRAWLER-TERMS-DRAFT.md). Logged as `crawler-default-set`.
- Keys: up to 3 active per account, `okc_` + 48 hex characters, shown once, only a hash is stored. Created and revoked events are logged.
- Submit: `POST /api/crawl/submit` with header `Authorization: Bearer okc_...` and body `{"url": "https://..."}`. Answer `{ok, doc_id, licence, basis, title, reasons}`; status 200 published, 422 refused (with reasons), 401 bad key, 429 more than 6 a minute per key, 503 busy. One submission is processed at a time; on success the index is reloaded.
- Account endpoints (signed-in testers): `GET /api/crawl/account`, `POST /api/crawl/account {default_licence, accept_terms}`, `POST /api/crawl/keys {label}`, `POST /api/crawl/keys/revoke {id}`.
- A user crawler that publishes counts in the public "collectors" number (actor `crawler:<hash>`).
- Tests: `python3 tests/test_crawlkeys.py` (20 checks).
Not built yet: the account page in the UI, and an MCP/CLI helper for agents.
