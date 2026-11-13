"""Calibration samples (TEST-PLAN-v3 section 7): JC's 20 blind grades and the 50-reply plan-check sample.
Both come from practice replies of v1-v4, before labels v2 exist, so the reference packet is the accepted
answer plus round one's key fix and evidence pages, and outcomes are compared label-free."""
import json, random, re

from .common import CACHE, DATA, ROOT, RUNS, read_jsonl

OUT = ROOT / "runs/v3plan/calibration"
SEED = 20260930
VERSIONS = ("v1", "v2", "v3", "v4")


def practice_replies():
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl") if q["id"] in usable and q["split"] == "dev"}
    out = []
    for v in VERSIONS:
        d = RUNS / f"{v}__openai_gpt-5.4-mini/dev"
        G = {g["id"]: g for g in read_jsonl(d / "grades.jsonl")}
        for a in read_jsonl(d / "answers.jsonl"):
            if a["id"] in Q and a["id"] in G:
                out.append({"rid": f"{v}:dev:{a['id']}:final", "qid": a["id"], "version": v, "reply": a["answer"],
                            "passages": a["passages"], "r1_outcome": G[a["id"]]["outcome"],
                            "r1_handoff": G[a["id"]]["handoff_detected"]})
    return out


def asks_question(text):
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    return any(line.strip().endswith("?") for line in prose.splitlines())


def stratum(r):
    o = r["r1_outcome"]
    if o == "right_question" or asks_question(r["reply"]) or (r["r1_handoff"] and o in ("resolved", "partial")):
        q = True
    else:
        q = False
    return {"Q": q, "A": o == "resolved", "W": o in ("confidently_wrong", "partial"),
            "H": o in ("correct_handoff", "unnecessary_handoff") and not asks_question(r["reply"])}


def sample(quota, exclude_rids=(), one_per_question=True, seed=SEED):
    """Fill quotas in the order given (rarest first), without reusing a question."""
    rng = random.Random(seed)
    pool = [r for r in practice_replies() if r["rid"] not in set(exclude_rids)]
    rng.shuffle(pool)
    used_q, picked = set(), []
    for s, n in quota:
        got = 0
        for r in pool:
            if got == n:
                break
            if r in picked or (one_per_question and r["qid"] in used_q) or not stratum(r)[s]:
                continue
            picked.append({**r, "stratum": s}); used_q.add(r["qid"]); got += 1
        if got < n:
            raise SystemExit(f"stratum {s}: only {got} of {n} available")
    rng.shuffle(picked)
    return picked


def jc20():
    return sample([("Q", 4), ("A", 5), ("W", 6), ("H", 5)])


def plancheck50(exclude):
    # 15 answers with fixes, 15 handoffs, 10 questions or mixed, 10 that round one graded wrong or bluffed.
    rng_quota = [("Q", 10), ("CW", 10), ("A2", 15), ("H", 15)]
    pool_strata = {"CW": lambda r: r["r1_outcome"] == "confidently_wrong",
                   "A2": lambda r: r["r1_outcome"] in ("resolved", "partial") and not r["r1_handoff"]}
    rng = random.Random(SEED + 1)
    pool = [r for r in practice_replies() if r["rid"] not in set(exclude)]
    rng.shuffle(pool)
    picked, seen = [], set()
    for s, n in rng_quota:
        test = pool_strata.get(s) or (lambda r, s=s: stratum(r)[s])
        got = [r for r in pool if r["rid"] not in seen and test(r)][:n]
        if len(got) < n:
            raise SystemExit(f"plan check stratum {s}: only {len(got)} of {n}")
        for r in got:
            picked.append({**r, "stratum": s}); seen.add(r["rid"])
    rng.shuffle(picked)
    return picked
