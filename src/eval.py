#!/usr/bin/env python3
"""Run the eval set against the reader and write data/eval_report.md.

Scoring: hit = expected fact present in the answer AND correct source cited.
Trap pass = refusal given. Reports hits /20, refusals /5, tok/s, and ollama
memory from /api/ps. Stdlib only.
"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve

ROOT = serve.ROOT

def ollama_memory():
    try:
        with urllib.request.urlopen(serve.HOST + "/api/ps", timeout=30) as r:
            models = json.load(r).get("models", [])
        return {m["name"]: round(m.get("size_vram", m.get("size", 0)) / 1e9, 1) for m in models}
    except Exception as e:
        return {"error": str(e)}

def main():
    with open(os.path.join(ROOT, "data", "eval_run.json"), encoding="utf-8") as f:
        ev = json.load(f)
    store = serve.load_store()
    hits, results, tok_rates = 0, [], []
    for q in ev["answerable"]:
        r = serve.answer(q["question"], store)
        a = r["answer"].lower()
        norm = lambda s: s.replace(",", "").replace(".", "").replace(" ", "")
        ok_fact = (q["expected_fact"].lower() in a) or (norm(q["expected_fact"].lower()) in norm(a))
        ok_src = q["source"].lower() in a
        hit = ok_fact and ok_src
        hits += hit
        tok_rates.append(r["tok_s"])
        results.append({**q, "answer": r["answer"], "fact_ok": ok_fact, "src_ok": ok_src, "hit": hit, "tok_s": r["tok_s"]})
        print(f"Q{q['id']}: {'HIT' if hit else 'miss'} (fact={ok_fact} src={ok_src})", flush=True)
    refusals = 0
    for q in ev["traps"]:
        r = serve.answer(q["question"], store)
        refused = serve.REFUSAL.lower() in r["answer"].lower()
        refusals += refused
        results.append({**q, "answer": r["answer"], "refused": refused, "tok_s": r["tok_s"]})
        tok_rates.append(r["tok_s"])
        print(f"trap Q{q['id']}: {'REFUSED ok' if refused else 'HALLUCINATED'}", flush=True)
    mem = ollama_memory()
    avg_tok = round(sum(tok_rates) / len(tok_rates), 1) if tok_rates else 0
    lines = ["# OpenKB first retrieval test - report", "",
             f"- Hits (correct answer + citation): {hits} / {len(ev['answerable'])}",
             f"- Correct refusals: {refusals} / {len(ev['traps'])}",
             f"- Reader: {serve.READER_MODEL}, embeddings: {serve.EMBED_MODEL}",
             f"- Avg generation speed: {avg_tok} tok/s", f"- ollama memory (GB): {mem}", "",
             "## Detail", ""]
    for r in results:
        lines.append(f"### Q{r['id']} ({r.get('lang','?')}) {r['question']}")
        lines.append(f"- answer: {r['answer']}")
        for k in ("expected_fact", "source", "fact_ok", "src_ok", "hit", "refused", "tok_s"):
            if k in r:
                lines.append(f"- {k}: {r[k]}")
        lines.append("")
    with open(os.path.join(ROOT, "data", "eval_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"report -> data/eval_report.md | hits {hits}/20 refusals {refusals}/5 avg {avg_tok} tok/s")

if __name__ == "__main__":
    sys.exit(main())
