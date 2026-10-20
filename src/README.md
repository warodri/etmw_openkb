# src - OpenKB pipeline (skeleton)

Python. Implementation to be built with DeepSeek via the ETMW opencode API (fallback: local qwen3-coder:30b on the Mac Mini). Planned modules:

- `ingest.py` - load donated documents from `data/donations/`, record donor-log metadata, chunk (~800 tokens, 15% overlap)
- `embed.py` - Qwen3-Embedding-4B embeddings into LanceDB or Qdrant, with source metadata per chunk
- `serve.py` - retrieval + reader: top-k chunks (+ Qwen3-Reranker) into Qwen3.6-35B-A3B via Ollama/LM Studio; answer only from retrieved chunks, cite sources, refuse when missing
- `eval.py` - run `tests/eval_questions.md` and report hits, refusals, tok/s and memory

Nothing here is final. The first milestone only proves the loop end to end on 50 documents.
