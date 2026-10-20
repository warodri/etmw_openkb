# Amelia OpenKB

A small reader and a shared library. Amelia OpenKB is a community-held knowledge base built for AI retrieval: people donate expert, structured content under an open licence, and a small, cheap reader model answers questions by reading only what is relevant - so the knowledge lives outside the model and belongs to everyone.

OpenKB is the open knowledge layer of [Amelia](https://entertomyworld.com/apps/amelia/#/), built by Enter To My World (ETMW). Spanish first, then many languages.

- Concept: [docs/CONCEPT.md](docs/CONCEPT.md)
- Code licence: [Apache 2.0](LICENSE)
- Content licence: [CC BY-SA 4.0](CONTENT-LICENSE.md) with explicit AI-retrieval consent
- Donate content: [consent/](consent/) - consent forms and the public donor log

## Status

Early scaffold. The repo is private while the licence and consent flow are reviewed. First milestone: ingestion for 50 donated documents (Spanish and English) and a small open model answering questions from only those documents, demoed locally.

## Stack (initial)

- Reader model: Qwen3.6-35B-A3B (Apache 2.0), runs locally on a Mac Mini M4 Pro 48GB
- Embeddings: Qwen3-Embedding-4B + Qwen3-Reranker (Apache 2.0, 100+ languages)
- Vector store: LanceDB or Qdrant, local
- Language: Python

## Layout

- `docs/` - concept and design notes
- `consent/` - donor consent templates (EN/ES) and the public donor log
- `src/` - ingestion, embedding, retrieval and serving (skeleton)
- `tests/` - evaluation questions for the first retrieval test
- `data/` - local data, never committed
