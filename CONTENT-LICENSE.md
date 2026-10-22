# Content licence - donated knowledge

Decision 2026-10-22: the library takes several OPEN licences, tagged per document: public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0 and BSD. Each document keeps its own licence, credit and (where required) notice, and answers show the licence of every source. Non-commercial (NC), no-derivatives (ND), all-rights-reserved and unlicensed material is never included. Donations without a stated licence from this list are not published.

For material donated without a more specific choice, the legal text is **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** where the donor picks it.

Status: policy. The code still stores one licence field per document and the live upload form still offers CC BY-SA only; per-document licence tagging, the picker and licences in answers are not built yet.

Open legal question: mixing share-alike (CC BY-SA) with permissive licences in one retrievable library and in generated answers. A lawyer should read this before charging for access.

Legal code: https://creativecommons.org/licenses/by-sa/4.0/legalcode
Human-readable summary: https://creativecommons.org/licenses/by-sa/4.0/

## AI-retrieval consent

Donating to OpenKB is a deliberate act. At donation time every donor gives explicit consent, in plain language, for their content to be:

1. stored and indexed for AI retrieval (chunked and embedded into vector stores),
2. read by AI reader models to answer questions, with attribution,
3. redistributed under the same licence as part of the knowledge base.

Consent templates live in `consent/` (English and Spanish). Donations without completed consent are not accepted.

## Donor log

A public log records who donated what, when, and under which licence: `consent/donor-log.md`.

## Takedown

A donor can request removal of their content at any time. Everything is versioned, so removal is real: the content leaves the current index and future releases, and the log records the takedown.
