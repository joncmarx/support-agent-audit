"""Build 1 step 3: dry run of the repaired harness on 5 practice questions (pennies).
Arm A (v4 as built) runs draft -> review -> handoff on the new call layer, reusing round one's retrieved
passages; the 5 final replies are graded by grader 1 and the three grader-2 candidates, only to prove
that every host pin, thinking setting, parser and ledger row works. Results are not used for any choice.

  python3 -m audit.dryrun price | run | report
"""
import json, random, sys, time
from concurrent.futures import ThreadPoolExecutor

from . import llm, models
from .bot import CONFIGS
from .calib import SEED
from .common import CACHE, DATA, ROOT, RUNS, read_jsonl
from .docs_index import Docs
from .grade3 import grade_api, packet_round1, render_item
from .pipeline import run as run_pipeline

OUT = ROOT / "runs/v3plan/dryrun"
GRADERS = ["anthropic/claude-sonnet-5.5", "google/gemini-3.8-flash", "meta/muse-spark-1.3", "qwen/qwen3.8-max-0902"]


def pick5():
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    ids = sorted(q["id"] for q in read_jsonl(CACHE / "questions_full.jsonl") if q["split"] == "dev" and q["id"] in usable)
    return random.Random(SEED + 5).sample(ids, 5)


def estimate():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ledger", ROOT / "runs/ledger.py"); L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
    lines = [(1, "dry run drafts", "openai/gpt-5.4-mini", "drafter", "draft", 5, "api"),
             (1, "dry run reviews", "openai/gpt-5.4-mini", "reviewer_A", "review", 5, "api"),
             (1, "dry run handoffs", "openai/gpt-5.4-mini", "handoff", "handoff", 5, "api")]
    lines += [(1, "dry run grades", g, "screen", "grade", 5, "api") for g in GRADERS]
    tot, rows = L.price(lines)
    return sum(tot.values()), rows, L


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    docs = Docs(); chunks = {c["id"]: c for c in docs.chunks}
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
    L = {l["id"]: l for l in read_jsonl(DATA / "labels.jsonl")}
    V4 = {a["id"]: a for a in read_jsonl(RUNS / "v4__openai_gpt-5.4-mini/dev/answers.jsonl")}
    ids = pick5()
    ans_path = OUT / "answers.jsonl"
    done = {r["id"] for r in read_jsonl(ans_path)} if ans_path.exists() else set()

    def one(qid):
        q = Q[qid]; passages = [chunks[c] for c in V4[qid]["passages"]]
        return run_pipeline(q, passages, arm="A", drafter="openai/gpt-5.4-mini", reviewer="openai/gpt-5.4-mini",
                            system=CONFIGS["v4"]["system"], graders=GRADERS, phase="1-dryrun", split="dev", reviewer_role="reviewer_A")
    with ThreadPoolExecutor(5) as pool, open(ans_path, "a") as f:
        for rec in pool.map(one, [i for i in ids if i not in done]):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    answers = {r["id"]: r for r in read_jsonl(ans_path)}
    g_path = OUT / "grades.jsonl"
    gdone = {(r["rid"], r["grader"]) for r in read_jsonl(g_path)} if g_path.exists() else set()
    jobs = []
    for qid, a in answers.items():
        q = Q[qid]
        item = render_item(q, packet_round1(q, L[qid], docs), [chunks[c] for c in a["passages"]], a["answer"])
        for g in GRADERS:
            rid = f"dryrunA:dev:{qid}:final"
            if (rid, g) not in gdone:
                author = "JC" if a["answer_source"] == "safe_handoff" else "openai/gpt-5.4-mini"
                jobs.append((g, item, author, rid))
    with ThreadPoolExecutor(10) as pool, open(g_path, "a") as f:
        for rec in pool.map(lambda j: grade_api(j[0], j[1], role="screen", author=j[2], phase="1-dryrun", split="dev", arm="A", rid=j[3]), jobs):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
    report()


def report():
    A = read_jsonl(OUT / "answers.jsonl"); G = read_jsonl(OUT / "grades.jsonl")
    print("pipeline:", [(a["id"], a["answer_source"], a["review_safe"], a["system_failure"], {k: len(v) for k, v in a["attempt_failures"].items()}) for a in A])
    for g in GRADERS:
        rows = [r for r in G if r["grader"] == g]
        print(f"{g}: ok {sum(r['ok'] for r in rows)}/{len(rows)} | outcomes {[r.get('label_free') for r in rows]} | "
              f"attempts {[r['attempts'] for r in rows]} | provider {sorted({str(r['provider']) for r in rows})} | "
              f"reasoning tokens {[r.get('reasoning_tokens') for r in rows]} | cost ${sum(r['cost'] for r in rows):.4f} | secs {[round(r['seconds']) for r in rows]}")
        for r in rows:
            if not r["ok"]:
                print("   failures:", r["failures"][:2])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "price":
        tot, rows, _ = estimate()
        for r in rows:
            print(f"  {r[1]:16s} {r[2].split('/')[-1]:18s} {r[4]} x {r[5]:.3f}c ({r[6]})")
        print(f"estimate ${tot:.2f}")
    elif cmd == "run":
        run()
    else:
        report()
