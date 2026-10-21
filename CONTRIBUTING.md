# Contributing to OpenKB

We're glad you're here. OpenKB is deliberately easy to hack on: stdlib Python,
one Angular app, no framework soup.

## Start small

Pick a [good first issue](docs/GOOD-FIRST-ISSUES.md) and say you're taking it -
one comment on the issue is enough.

## Set up

`./install.sh` gets you the library, the models, the UI build, and agent mode.
See [docs/INSTALL.md](docs/INSTALL.md).

## The rules that matter

- **The library is consent-based.** Never add code that ingests content without
  a provenance record and a license check. The trust rules in
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) are not optional.
- **The refusal is a feature.** If the library doesn't have the answer, OpenKB
  says so. Don't "helpfully" fill gaps from model knowledge.
- **Guards stay server-side.** Rate limits, caps, quotas. No client-side
  overrides, ever.
- **Keep it small and local.** Stdlib Python unless there's a real reason.
  If a change needs a datacenter, it doesn't belong here.

## Style

- Python: stdlib only, 3.9-compatible, plain functions over clever classes.
- Angular: standalone components, signals, Tailwind utility classes.
- Docs: say what is measured and what is a target. Never blur the two.

## Testing

Run the gate before you send a PR: `python3 src/eval.py` - 20 English + 5
Spanish questions must stay green (see tests/eval_questions.md).
