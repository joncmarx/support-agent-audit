"""Pre-publish check (TEST-PLAN-v3 section 16): scan files for text copied from forum posts.

Forum posts belong to their authors. The public repo and site may carry thread ids, titles, links and our own
generated text (bot replies, reviewer notes, grader reasoning, labeler summaries), not post text. This finds every
run of N consecutive words (default 12) that appears in a forum post we collected (evaluation threads, the sealed
holdout and reserve, and the 2,739-thread harvest) and not in n8n's docs, and reports it per file.

  python3 -m audit.forumscan FILE_OR_DIR ...      # prints files with hits, worst first
"""
import hashlib, json, pickle, re, sys
from html import unescape
from pathlib import Path

from .common import CACHE, ROOT

N = 12
WORD = re.compile(r"[a-z0-9]+")
TAG = re.compile(r"<[^>]+>")
PKL = CACHE / f"forum_shingles_{N}_blake2b.pkl"


def words(text):
    return WORD.findall(unescape(TAG.sub(" ", text)).lower())


def h(s):
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")


def shingles(text):
    w = words(text)
    return {h(" ".join(w[i:i + N])) for i in range(len(w) - N + 1)}


def forum_texts():
    for d in (CACHE / "forum", ROOT / "sealed/forum"):
        for p in d.glob("*.json"):
            t = json.loads(p.read_text())
            for post in t.get("post_stream", {}).get("posts", []):
                yield post.get("cooked") or ""
    for p in (CACHE / "questions_full.jsonl", ROOT / "sealed/holdout_questions.jsonl", ROOT / "sealed/holdout_solutions.jsonl",
              ROOT / "sealed/reserve_questions.jsonl", ROOT / "sealed/reserve_solutions.jsonl", CACHE / "harvest/threads.jsonl"):
        if p.exists():
            for line in open(p):
                r = json.loads(line)
                yield " ".join(str(r.get(k) or "") for k in ("question", "accepted_answer", "answer"))


def corpus():
    if PKL.exists():
        return pickle.loads(PKL.read_bytes())
    forum = set()
    for t in forum_texts():
        forum |= shingles(t)
    docs = set()
    for line in open(CACHE / "docs_chunks.jsonl"):
        docs |= shingles(json.loads(line).get("text", ""))
    out = forum - docs
    PKL.write_bytes(pickle.dumps(out))
    return out


def scan(path, F):
    w = words(Path(path).read_text(errors="ignore"))
    hits, spans, last = 0, [], -10
    for i in range(len(w) - N + 1):
        if h(" ".join(w[i:i + N])) in F:
            hits += 1
            if i > last + N:
                spans.append(" ".join(w[i:i + N]))
            last = i
    return hits, spans


if __name__ == "__main__":
    F = corpus()
    files = []
    for a in sys.argv[1:]:
        p = Path(a)
        files += [x for x in p.rglob("*") if x.is_file()] if p.is_dir() else [p]
    res = [(f, *scan(f, F)) for f in files if f.suffix in (".json", ".jsonl", ".md", ".html", ".txt", ".py", ".csv")]
    res = [r for r in res if r[1]]
    for f, h, sp in sorted(res, key=lambda r: -r[1]):
        print(f"{h:7d} hits {len(sp):5d} spans  {f}")
        for s in sp[:2]:
            print("          e.g.", s[:110])
    print(f"scanned {len(files)} files; {len(res)} with forum text")
