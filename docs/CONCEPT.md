# Amelia OpenKB - concept in one page

**Date:** 20 October 2026
**Owner:** Walter Rodriguez / Enter To My World (ETMW)
**Status:** draft for review, nothing built yet

## The idea

A small reader and a shared library. Today's AI loads an entire giant model into memory to answer anything, so only a few companies can afford to run one. The bet here is the opposite: a small, cheap core model that knows language and reasoning, and reads only the material relevant to the conversation at hand. The knowledge lives outside the model, in a shared, community-held knowledge base: Amelia OpenKB. The reader is cheap enough to run anywhere; the library belongs to everyone.

## The problem

Knowledge inside AI is locked in giant models controlled by a handful of companies. Running them needs datacentres. Communities cannot own, inspect, or govern the knowledge their AI uses. Open weights help, but the model still memorised the library instead of reading it.

## Why not just Wikipedia

Wikipedia is the free baseline and the reader should read it too. OpenKB only matters if it adds what Wikipedia lacks: expert, structured, licensed-for-AI content that people choose to donate. Manuals, local knowledge, domain notes, field guides, how-tos. Written for retrieval, not for encyclopedia style. Many languages, Spanish first - that is our edge and our first community.

## Who donates

People who know something well and want it usable by anyone's AI, not only by the big labs: hobbyists, professionals, teachers, local communities. Donating is a deliberate act with clear consent, closer to contributing code than to posting content.

## Licence and consent

- Every donation is published under an open licence, default CC BY-SA 4.0.
- Donors give explicit consent for AI retrieval use at donation time, in plain language.
- A public log records who donated what and under which licence.
- Takedown on request, with version history so removal is real.

## Quality control

The hard part is not code, it is trust. Per-topic maintainers review before merge, like open source. Every entry carries its source. Automated checks catch junk, duplicates, and poisoned content. Everything is versioned, so mistakes roll back.

## Trust and verification

Entries are sourced, not "true". Every claim in the library carries its source, and the reader always cites the donor document it read from. Verification borrows what works: Wikipedia-style sourcing with full edit history and rollback, and Community-Notes-style bridging consensus for corrections, so a fix has to convince people who disagree, not only the loudest side. Donors sit in trust tiers: new donors start unreviewed, trusted donors are fast-tracked, and verified domain experts carry the most weight. Disagreement is not deleted; it gets a "contested" label with both positions and their sources. Poisoning defences come before scale: rate limits on donations, reputation that builds slowly, and automated duplicate and contradiction checks.

## How it ties to Amelia

OpenKB is not a new product. It is Amelia's open knowledge layer: the library the reader reads. One project, one story, not a fourth front next to FabulAI and Minerva.

## First milestone

A public repo with the licence and consent documents, ingestion working for the first 50 donated documents in Spanish and English, and a small open model answering questions from only those documents, demoed locally. That proves the reader-plus-library loop end to end.

## Honest risks

- Licensing mistakes are easy and expensive to fix later. Consent flow comes before content.
- Junk and poisoned donations are a matter of when, not if. Review and rollback must exist before scale.
- The first 100 contributors are harder than the code.
- Small readers still often fail to use what they retrieve. How small the core can get is an open research question; we measure, we do not assume.
- Time. This stays Amelia's layer, built in evenings, or it does not survive.
