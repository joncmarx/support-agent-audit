"""The Claude-plan check (TEST-PLAN-v3 section 7): decides grader 1's route.

  python3 -m audit.plancheck export <model>    # write the 50 items for JC's terminal (plan runs p1, p2)
  python3 -m audit.plancheck api <model>       # the API arm: the same 50 items through OpenRouter
  python3 -m audit.plancheck report            # pass/fail

Pass rule (written before any plan grade exists; the stricter reading of section 7):
  - API vs plan run 1 and API vs plan run 2: each at least 45 of 50 identical label-free outcomes;
  - plan run 1 vs plan run 2: at least 45 of 50;
  - no disagreement on the trust-incident flag (label-free outcome confidently_wrong) among the three runs;
  - isolation: every plan reply was served by the chosen model, and its billed input tokens exceed the API
    route's prompt tokens for the same item by at most 300 (extra context would show up here).
A grade missing after 3 attempts counts as a disagreement.
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor

from .calib import OUT as CAL
from .common import CACHE, DATA, read_jsonl
from .docs_index import Docs
from .grade3 import RUBRIC, grade_api, packet_round1, parse_grade, render_item, score
from .planroute import export as plan_export, ingest

BATCH = "plancheck"
API_OUT = CAL / "plancheck_api.jsonl"
CLAUDE_CODE_IDS = {"anthropic/claude-sonnet-5.5": "claude-sonnet-5-5", "anthropic/claude-opus-5.5": "claude-opus-5-5"}


def items():
    docs = Docs(); chunks = {c["id"]: c for c in docs.chunks}
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
    L = {l["id"]: l for l in read_jsonl(DATA / "labels.jsonl")}
    S = json.load(open(CAL / "plancheck50_key.json"))
    return [(f"pc-{i:02d}", render_item(Q[r["qid"]], packet_round1(Q[r["qid"]], L[r["qid"]], docs),
                                        [chunks[c] for c in r["passages"]], r["reply"])) for i, r in enumerate(S, 1)]


def export(model):
    return plan_export(BATCH, RUBRIC, items(), CLAUDE_CODE_IDS[model], effort="high")


def api(model):
    done = {r["rid"] for r in read_jsonl(API_OUT)} if API_OUT.exists() else set()
    jobs = [(i, t) for i, t in items() if i not in done]
    from .jobs import run_jobs
    run_jobs(jobs, lambda iid, text: grade_api(model, text, role="plancheck", author="openai/gpt-5.4-mini",
                                               phase="1-plancheck", split="dev", arm="calibration", rid=iid), API_OUT)


def plan_outcomes(run):
    out = {}
    for iid, rec in ingest(BATCH, run).items():
        o = None
        if rec["ok"]:
            try:
                o = score(parse_grade(rec["text"]))[0]
            except ValueError:
                o = None
        out[iid] = {**rec, "label_free": o}
    return out


def report(model="anthropic/claude-sonnet-5.5"):
    ids = [i for i, _ in items()]
    A = {r["rid"]: r for r in read_jsonl(API_OUT)} if API_OUT.exists() else {}
    P1, P2 = plan_outcomes("p1"), plan_outcomes("p2")
    a = {i: (A[i]["label_free"] if A.get(i, {}).get("ok") else None) for i in ids}
    p1 = {i: P1.get(i, {}).get("label_free") for i in ids}
    p2 = {i: P2.get(i, {}).get("label_free") for i in ids}
    same = lambda x, y: sum(x[i] is not None and x[i] == y[i] for i in ids)
    trust = lambda d: {i for i in ids if d[i] == "confidently_wrong"}
    trust_disagree = sorted((trust(a) | trust(p1) | trust(p2)) - (trust(a) & trust(p1) & trust(p2)))
    want = CLAUDE_CODE_IDS[model]
    iso = []
    for run, P in (("p1", P1), ("p2", P2)):
        for i, rec in P.items():
            api_in = (A.get(i) or {}).get("prompt_tokens")
            iso.append({"run": run, "item": i, "models": rec["models"], "plan_in": rec["input_tokens_total"]})
    # API prompt tokens come from the cost ledger rows of the API arm
    from .llm import LEDGER
    api_in = {}
    for line in open(LEDGER):
        r = json.loads(line)
        if r.get("phase") == "1-plancheck" and r.get("ok"):
            api_in[r["item"]] = r.get("prompt_tokens")
    over = [x for x in iso if api_in.get(x["item"]) is None or x["plan_in"] - api_in[x["item"]] > 300]
    wrong_model = [x for x in iso if not any(m.startswith(want) for m in x["models"])]
    res = {"api_vs_p1": same(a, p1), "api_vs_p2": same(a, p2), "p1_vs_p2": same(p1, p2), "n": len(ids),
           "trust_flag_disagreements": trust_disagree, "plan_done": (len(P1), len(P2)),
           "isolation_over_300_tokens": len(over), "served_by_other_model": len(wrong_model),
           "median_extra_input_tokens": sorted(x["plan_in"] - (api_in.get(x["item"]) or 0) for x in iso)[len(iso) // 2] if iso else None,
           "api_equiv_cost_per_plan_grade": round(sum((r.get("api_equiv_cost") or 0) for r in list(P1.values()) + list(P2.values())) / max(1, len(P1) + len(P2)), 4)}
    res["passes"] = (res["api_vs_p1"] >= 45 and res["api_vs_p2"] >= 45 and res["p1_vs_p2"] >= 45 and not trust_disagree
                     and not over and not wrong_model and len(P1) == len(P2) == len(ids))
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    cmd, model = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "anthropic/claude-sonnet-5.5")
    {"export": lambda: print(export(model)), "api": lambda: api(model), "report": lambda: report(model)}[cmd]()
