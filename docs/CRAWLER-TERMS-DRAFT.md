# Crawler terms - DRAFT PROPOSAL for Walter's decision (not approved, not shown to anyone)
Plain-language draft for people who connect a crawl agent to OpenKB. Not legal advice; a lawyer should read it before it goes public (same step as docs/CONTENT-LICENSE.md). Version tag in code: `draft-1` (app/crawlkeys.py `TERMS_VERSION`); change it when the text changes so every account accepts the new version.

## What you agree to when you make a crawler account
1. **You pick a default licence, and it is required.** It must be one of: public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0, BSD. It applies only to pages that state no licence of their own. You are telling OpenKB: "pages my agent sends that show no licence are free for OpenKB to reference under this licence, and I have the right to say so."
2. **The page's own licence always wins.** If a page states a licence, OpenKB uses that one. If the page states one OpenKB does not accept (NonCommercial, NoDerivatives, all rights reserved, or conflicting statements), the page is refused, whatever your default says.
3. **Only send pages you may send.** Public pages that anyone can read without logging in. No private, paywalled, personal or illegal content, and nothing from a site whose robots.txt or terms forbid automated reading. OpenKB checks robots.txt and refuses what it can detect, but you stay responsible for what your agent sends.
4. **OpenKB keeps references, not copies.** It stores the page address, a fingerprint and search vectors, and reads the page again when someone asks a question (a temporary copy is kept for up to 24 hours). Answers show the source and its licence as a link. Entries based on your default are marked "(user-declared)" and answers paraphrase them instead of quoting.
5. **Your account is on record.** The entry, the licence basis and your account are logged. Your email is never shown to other people; the public sees the source and licence only.
6. **Removal.** Anyone can ask for an entry to be removed through the Report button. If you or the rights holder asks, it is removed. If a page was submitted under your default and the real rights holder objects, the entry goes and your key can be revoked.
7. **Limits.** Up to 3 keys, 6 submissions per minute per key, 20 new entries per account per day while OpenKB is in beta. OpenKB may change limits, refuse a page or revoke a key at any time, for example for repeated bad submissions.
8. **No guarantee.** OpenKB is a beta. Entries are sourced, not "true". Keys can be revoked by you at any time on your account.

## Choices for Walter (each changes the text)
- Keep or add a tick-box "I own this site or may license it" for pages that show only a (c) line (see the decision in the step 1 report).
- Daily cap per account (now 20) and who may open an account first (today only the owner and testers; nothing public).
- Whether account holders must be signed-in humans with a verified email (today yes).
- Wording of item 6 for a rights holder who objects to a user-declared entry (the 7 day silence rule applies to named rights holders only).
