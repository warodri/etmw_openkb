# First retrieval test - evaluation set

Go/no-go gate for the reader-plus-library loop. Run against the first 50 donated documents (Spanish and English), ingested locally.

## Method

1. Ingest the 50 documents: chunk (~800 tokens, 15% overlap), embed (Qwen3-Embedding-4B), store (LanceDB or Qdrant) with source metadata.
2. The reader (Qwen3.6-35B-A3B) must answer ONLY from retrieved chunks, cite the source document, and say "not in the KB" when the answer is missing.
3. Score by hand: correct answer, correct citation, correct refusal.

## Questions (to fill per donated corpus)

### Answerable - Spanish (10)

| # | Question | Expected source | Result |
|---|----------|-----------------|--------|
| 1 |  |  |  |
...

### Answerable - English (10)

| # | Question | Expected source | Result |
|---|----------|-----------------|--------|
| 1 |  |  |  |
...

### Traps - answer NOT in the KB (5)

The correct answer is a refusal ("not in the KB"). Anything else is a hallucination.

| # | Question | Result |
|---|----------|--------|
| 1 |  |  |
...

## Scorecard

- Hits (correct answer + citation): __ / 20
- Correct refusals: __ / 5
- Notes (quant level, tok/s, memory, reranker on/off):
