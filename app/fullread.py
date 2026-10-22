"""Full read of a long source (map-reduce) as a LOW-PRIORITY job: it runs in parts of about 20,000 characters (about 2 s each) and
waits between parts while any question is being answered, so questions keep their normal speed. Research-tested; not wired to the app yet."""
import re, time

def _n(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def full_read(text, gen, waiting=lambda: 0, size=20000, max_wait=120):
    """gen(prompt, max_tokens) -> str. waiting() -> number of questions running or queued. Returns (summary, quotes_checked, quotes_verbatim, waited_s)."""
    sums, ok, bad, waited = [], 0, 0, 0.0
    for i in range(0, len(text), size):
        c = text[i:i + size]; t = time.time()
        while waiting() > 0 and time.time() - t < max_wait: time.sleep(0.4)
        waited += time.time() - t
        o = gen("Read this passage from a book. Line 1: summarise it in one sentence. Line 2: QUOTE: copy one exact sentence from the passage, word for word.\n\nPASSAGE:\n" + c + "\n", 140)
        mm = re.split(r"(?i)\n\s*(?:line 2:?\s*)?(?:quote:)\s*|\n\s*line 2:\s*(?:quote:)?\s*", o, maxsplit=1)
        sums.append(re.sub(r"(?i)^line 1:\s*", "", mm[0]).strip())
        q = mm[1].strip().strip('"\u201c\u201d') if len(mm) > 1 else ""
        if q: (ok := ok + 1) if _n(q) in _n(c) else (bad := bad + 1)
    final = gen("Here are one-sentence summaries of consecutive parts of a book. Write a summary of the whole book in about 100 words.\n\n" + "\n".join("- " + s for s in sums) + "\n\nSummary:", 220)
    return final, ok + bad, ok, round(waited)
