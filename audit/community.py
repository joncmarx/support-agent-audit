"""Community knowledge for arms F and DF (TEST-PLAN-v3 section 4; decision 19). Prints counts only.

  python3 -m audit.community embed [max_seconds]   # embed every harvested thread (title + accepted answer); resumable
  python3 -m audit.community retrieve dev|test     # per-question eligibility, hybrid search, top 3, 1,500-token cap
  python3 -m audit.community status

Pool: the harvest crawl (solved Questions threads created 2025-07-01..2026-09-15, audit/harvest.py).
Excluded for every question:
  E  the thread is a practice, test, holdout or reserve thread;
  X  cross-post of a practice or test thread (same asker, created within 14 days, similar title: difflib ratio
     >= 0.6 or content-word Jaccard >= 0.5, the holdout rule);
  C  its accepted answer copies a practice, test, holdout or reserve solution (holdout.copied: a shared run of
     >= 25 words, or >= 50% of the shorter answer's 8-word shingles). Sealed text is compared in code only.
Excluded per question:
  A  same asker as the question;
  T  time rule: the accepted answer was posted at or after the question's creation time, or edited after it
     (full timestamps).
Retrieval: v4's query (bot.search_query, 'with_nodes'), the docs' hybrid search (BM25 + bge-m3, reciprocal-rank
fusion, pool 30) restricted to the eligible threads; top 3; the section is capped at 1,500 tokens in total,
estimated at 4 characters per token. An answer that doesn't fit is cut at the cap (kept only if >= 150 tokens remain).
Holdout retrieval, if v5 uses the harvest, runs after the freeze with the same code.
"""
import difflib, json, re, sys, time
from datetime import datetime

import numpy as np

from . import llm
from .bot import search_query
from .common import CACHE, ROOT, read_jsonl, write_jsonl
from .docs_index import BM25
from .holdout import _shingles, copied, cwords

HDIR = CACHE / "harvest"
THREADS = HDIR / "threads.jsonl"
VEC, PART = HDIR / "vectors.npy", HDIR / "vectors_partial.npy"
OUT = ROOT / "runs/v3plan/community"
SEALED = ROOT / "sealed"
TOP, CAP_TOKENS, MIN_TAIL, POOL = 3, 1500, 150, 30
PHASE = "4-knowledge"


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def doc_text(t):
    return f"{t['title']}\n{t['answer']}"[:6000]


def threads():
    """Harvested threads with a usable accepted answer (6 of 2,745 have no answer text and are dropped; a missing
    answer edit time means it was never edited, so its creation time is used)."""
    out = []
    for h in read_jsonl(THREADS):
        if not (h.get("answer") or "").strip() or not h.get("answer_created_at"):
            continue
        h["answer_updated_at"] = h.get("answer_updated_at") or h["answer_created_at"]
        out.append(h)
    return out


# ------------------------------------------------------------------ evaluation threads
def eval_questions():
    """The 140 usable practice and test questions, with full creation time and asker from round one's cache."""
    usable = {r["id"] for r in read_jsonl(ROOT / "data/reference_check.jsonl") if r["usable"]}
    out = []
    for q in read_jsonl(CACHE / "questions_full.jsonl"):
        if q["id"] not in usable:
            continue
        t = json.loads((CACHE / "forum" / f"{q['id']}.json").read_text())
        q = dict(q, created_full=t["created_at"], asker=t["post_stream"]["posts"][0]["username"])
        out.append(q)
    return out


def all_eval_ids_and_solutions():
    ids, sols = set(), []
    for q in read_jsonl(CACHE / "questions_full.jsonl"):
        ids.add(str(q["id"])); sols.append(q["accepted_answer"])
    for f in ("holdout_solutions.jsonl", "reserve_solutions.jsonl"):
        for r in read_jsonl(SEALED / f):
            ids.add(str(r["id"])); sols.append(r["accepted_answer"])
    return ids, sols


def cross_post(h, q):
    if h["asker"] != q["asker"]:
        return False
    if abs((ts(h["created_at"]) - ts(q["created_full"])).days) > 14:
        return False
    r = difflib.SequenceMatcher(None, h["title"].lower(), q["title"].lower()).ratio()
    a, b = cwords(h["title"]), cwords(q["title"])
    return r >= 0.6 or len(a & b) / max(1, len(a | b)) >= 0.5


def global_exclusions(hs, qs):
    ids, sols = all_eval_ids_and_solutions()
    sol_sh = set()
    for s in sols:
        sol_sh |= _shingles(s)[1]
    why = {}
    for h in hs:
        hid = str(h["id"])
        if hid in ids:
            why[hid] = "E"; continue
        if any(cross_post(h, q) for q in qs):
            why[hid] = "X"; continue
        if _shingles(h["answer"])[1] & sol_sh and any(copied(h["answer"], s) for s in sols):
            why[hid] = "C"
    return why


def eligible(h, q):
    if h["asker"] == q["asker"]:
        return "A"
    qt = ts(q["created_full"])
    if ts(h["answer_created_at"]) >= qt or ts(h["answer_updated_at"]) > qt:
        return "T"
    return None


# ------------------------------------------------------------------ index
def embed(max_seconds=150, batch=64):
    hs = threads()
    done = np.load(PART) if PART.exists() else np.zeros((0, 0), dtype=np.float32)
    rows = [done] if done.size else []
    n = len(done) if done.size else 0
    t0 = time.time()
    while n < len(hs) and time.time() - t0 < max_seconds:
        # the pinned host's context limit applies to the whole request: at most 16 texts and ~20,000 characters
        m, size = n, 0
        while m < len(hs) and m - n < 16 and (m == n or size + len(doc_text(hs[m])) <= 20000):
            size += len(doc_text(hs[m])); m += 1
        v = np.array(llm.embed_v3([doc_text(h) for h in hs[n:m]], phase=PHASE, item=f"harvest:{n}"),
                     dtype=np.float32)
        rows.append(v); n += len(v)
        np.save(PART, np.vstack(rows))
    if n >= len(hs):
        m = np.vstack(rows); m /= np.linalg.norm(m, axis=1, keepdims=True)
        np.save(VEC, m)
        print(f"embedded all {n} harvested threads")
    else:
        print(f"embedded {n}/{len(hs)}; run again to continue")


def section(picked):
    """Format the community section, capped at CAP_TOKENS (4 chars per token)."""
    budget, parts, used = CAP_TOKENS * 4, [], []
    for i, h in enumerate(picked, 1):
        head = f"[C{i}] {h['title']} (community.n8n.io/t/{h['id']}, answered {h['answer_created_at'][:10]})\n"
        room = budget - len(head)
        if room < MIN_TAIL * 4:
            break
        body = h["answer"] if len(h["answer"]) <= room else h["answer"][:room].rsplit(" ", 1)[0] + " […]"
        parts.append(head + body); budget -= len(head) + len(body)
        used.append({"id": str(h["id"]), "truncated": len(body) < len(h["answer"])})
    return "\n\n".join(parts), used


def retrieve(split):
    hs = threads()
    if not VEC.exists():
        raise SystemExit("run `python3 -m audit.community embed` first")
    vec = np.load(VEC)
    qs_all = eval_questions()
    qs = [q for q in qs_all if q["split"] == split]
    gx = global_exclusions(hs, qs_all)
    bm = BM25([doc_text(h) for h in hs])
    OUT.mkdir(parents=True, exist_ok=True)
    qcache_p = OUT / "query_vectors.json"
    qcache = json.loads(qcache_p.read_text()) if qcache_p.exists() else {}
    rows, reasons = [], {"E": 0, "X": 0, "C": 0}
    for r in gx.values():
        reasons[r] += 1
    for q in qs:
        per = {"A": 0, "T": 0}
        ok = np.zeros(len(hs), dtype=bool)
        for i, h in enumerate(hs):
            if str(h["id"]) in gx:
                continue
            e = eligible(h, q)
            if e:
                per[e] += 1
            else:
                ok[i] = True
        query = search_query(q, "with_nodes")
        if q["id"] not in qcache:
            qcache[q["id"]] = llm.embed_v3([query[:6000]], phase=PHASE, split=split, item=q["id"])[0]
            qcache_p.write_text(json.dumps(qcache))
        v = np.array(qcache[q["id"]], dtype=np.float32); v /= np.linalg.norm(v)
        kw = [i for i, _ in bm.search(query, len(hs)) if ok[i]][:POOL]
        sims = np.where(ok, vec @ v, -9)
        sem = [int(i) for i in np.argsort(-sims)[:POOL] if ok[i]]
        score = {}
        for res in (kw, sem):
            for rank, i in enumerate(res):
                score[i] = score.get(i, 0) + 1 / (60 + rank)
        top = [hs[i] for i, _ in sorted(score.items(), key=lambda x: -x[1])[:TOP]]
        text, used = section(top)
        rows.append({"id": q["id"], "split": split, "eligible": int(ok.sum()), "excluded_same_asker": per["A"],
                     "excluded_time": per["T"], "picked": used, "community": text,
                     "tokens_est": round(len(text) / 4)})
    write_jsonl(OUT / f"{split}.jsonl", rows)
    el = sorted(r["eligible"] for r in rows)
    print(f"{split}: {len(rows)} questions | pool {len(hs)}, excluded for all: {reasons} | eligible per question: "
          f"min {el[0]}, median {el[len(el)//2]}, max {el[-1]} | questions with 0 picks: "
          f"{sum(not r['picked'] for r in rows)} | section tokens median "
          f"{sorted(r['tokens_est'] for r in rows)[len(rows)//2]}, truncated answers "
          f"{sum(p['truncated'] for r in rows for p in r['picked'])}")


def status():
    n = len(threads())
    part = len(np.load(PART)) if PART.exists() else 0
    print({"harvested": n, "embedded": part, "index_ready": VEC.exists(),
           **{s: (OUT / f"{s}.jsonl").exists() for s in ("dev", "test")}})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "embed":
        embed(float(sys.argv[2]) if len(sys.argv) > 2 else 150)
    elif cmd == "retrieve":
        retrieve(sys.argv[2])
    else:
        status()
