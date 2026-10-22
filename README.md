# OpenKB

## The rules of AI say: knowledge answers come from a datacenter, rented by the query, from a model you'll never see, trained on text nobody was asked about. We're here to change those rules.

OpenKB answers questions from a library the community owns - donated documents,
open licences, named sources - read by a model that runs on your own machine.
No cloud. No API bill. No black box between you and the answer, and no answer
without a source you can check.

**Try the live demo:** 
https://openkb--warodri.entertomyworld.com/

**Install your own:** `./install.sh` 
See [docs/INSTALL.md](docs/INSTALL.md)

## What we're going after

We're set on running side by side with frontier models - a small local reader
giving answers you can't tell apart from the big labs', served from your own
machine, from a library the community owns. We work on it daily.

Our thesis: for most factual questions, you don't need a datacenter. You need a
reader that knows its limits, sitting on top of a library built by people who
said yes. If we're right, knowledge stops being a subscription and starts being
a commons.

The library grows together, not by everyone duplicating the same work: people and their own agents contribute to the one shared library, and every document keeps its source, licence and credit.

## How it works

- **The library** - documents donated under CC BY-SA, converted to Markdown,
  chunked, embedded locally. Every answer names its sources.
- **The reader** - a local Qwen MoE model via Ollama. Answers only from the
  library; when the library doesn't know, it says so. That refusal is
  server-side and can't be prompted away.
- **The app** - a task-organised chat UI (Angular), served by a small stdlib
  Python server with rate limits, daily caps, and a request log.
- **Agent mode** - opencode drives the same library through a read-only MCP
  bridge with its own quota, so agents can never eat the users' allowance.
- **Trust rules** - consent before donation, automatic checks before publish,
  reports checked automatically (copyright: we ask the named rights holder and only remove on their confirmation; a person only handles unclear cases), takedown on request. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contribute

We want this to be the easiest AI project you've ever contributed to:
stdlib Python, one Angular app, no framework soup.

- New here? Pick a [good first issue](docs/GOOD-FIRST-ISSUES.md).
- Got expertise? Donate a document (once donations open - the consent review
  comes first).
- Run it, break it, and tell us where it broke.

## Licence

Code: Apache 2.0. Library content: CC BY-SA 4.0, donated by its owners.

Welcome-page crawler counter: the hosted site shows how many crawler agents added documents in the last 48 hours. It is off by default in a clone. Set `OPENKB_SHOW_COUNTER=1` to show your own library's numbers (`/api/public-stats`).
