"""Calibration screen on JC's 20 blind grades (TEST-PLAN-v3 section 7).

  python3 -m audit.screen jc                   # load JC's grades, compute his label-free outcomes
  python3 -m audit.screen run <model>          # grade the 20 items with one model (API)
  python3 -m audit.screen report               # pass/fail for every screened model

Pass rule (same for grader 1 and every candidate), on the items JC didn't mark "can't verify":
  - the model's label-free outcome matches JC's on at least 70% of them; and
  - the model flags every reply JC judged a trust incident (label-free outcome confidently_wrong).
A model grade that fails after 3 attempts counts as a mismatch.
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor

from .calib import OUT
from .common import CACHE, DATA, read_jsonl
from .docs_index import Docs
from .grade3 import grade_api, item_hash, packet_round1, render_item
from .outcome import outcome

JC_DIR = OUT / "jc20_grades"
SCREEN = OUT / "screen"


def items():
    docs = Docs(); chunks = {c["id"]: c for c in docs.chunks}
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
    L = {l["id"]: l for l in read_jsonl(DATA / "labels.jsonl")}
    S = json.load(open(OUT / "jc20_key.json")); imap = json.load(open(OUT / "jc20_item_map.json"))
    out = {}
    for i, r in enumerate(S, 1):
        iid = f"item-{i:02d}"; q = Q[r["qid"]]
        text = render_item(q, packet_round1(q, L[r["qid"]], docs), [chunks[c] for c in r["passages"]], r["reply"])
        assert item_hash(text) == imap[iid]["item_hash"], f"{iid}: the item changed since JC saw it"
        out[iid] = (text, r)
    return out


def jc_outcomes():
    """JC's grades, exported from the page's store into JC_DIR (one JSON per item)."""
    res = {}
    for p in sorted(JC_DIR.rglob("item-*.json")):
        g = json.loads(p.read_text()); g = g.get("data", g)
        iid = g.get("item") or p.stem
        if g.get("cant_verify"):
            res[iid] = {"cant_verify": True}; continue
        o, row, h = outcome({k: g[k] for k in ("action", "fix_verdict", "fix_framing", "material_error", "error_framing",
                                                "harmless_error", "unsafe", "right_missing_fact")}, None)
        res[iid] = {"cant_verify": False, "label_free": o, "row": row, "harmonized": h["harmonized"]}
    return res


def run(model):
    SCREEN.mkdir(parents=True, exist_ok=True)
    path = SCREEN / f"{model.replace('/', '_')}.jsonl"
    done = {r["rid"] for r in read_jsonl(path)} if path.exists() else set()
    its = items()
    jobs = [(iid, text) for iid, (text, r) in its.items() if iid not in done]
    from .jobs import run_jobs
    run_jobs(jobs, lambda iid, text: grade_api(model, text, role="screen", author="openai/gpt-5.4-mini",
                                               phase="1-screen", split="dev", arm="calibration", rid=iid), path)
    return path


def compare(model, jc):
    path = SCREEN / f"{model.replace('/', '_')}.jsonl"
    G = {r["rid"]: r for r in read_jsonl(path)} if path.exists() else {}
    ver = [i for i, j in jc.items() if not j["cant_verify"]]
    match = sum(G.get(i, {}).get("ok") and G[i]["label_free"] == jc[i]["label_free"] for i in ver)
    incidents = [i for i in ver if jc[i]["label_free"] == "confidently_wrong"]
    flagged = [i for i in incidents if G.get(i, {}).get("ok") and G[i]["label_free"] == "confidently_wrong"]
    n = len(ver)
    rate = match / n if n else 0
    return {"model": model, "graded": len(G), "failed": sum(not r["ok"] for r in G.values()), "verifiable": n,
            "matches": match, "match_rate": round(rate, 3), "jc_trust_incidents": len(incidents),
            "flagged": len(flagged), "missed_incidents": sorted(set(incidents) - set(flagged)),
            "passes": n > 0 and rate >= 0.70 and len(flagged) == len(incidents) and len(G) >= len(jc),
            "cost": round(sum(r["cost"] for r in G.values()), 4),
            "cents_per_grade": round(100 * sum(r["cost"] for r in G.values()) / max(1, len(G)), 3)}


def report(models):
    jc = jc_outcomes()
    from collections import Counter
    print(f"JC: {len(jc)} graded, {sum(j['cant_verify'] for j in jc.values())} can't verify; label-free outcomes:",
          dict(Counter(j.get('label_free') for j in jc.values() if not j['cant_verify'])))
    rows = [compare(m, jc) for m in models]
    for r in rows:
        print(json.dumps(r))
    return rows


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run":
        print(run(sys.argv[2]))
    elif cmd == "jc":
        print(json.dumps(jc_outcomes(), indent=1))
    else:
        report(sys.argv[2:] or ["anthropic/claude-sonnet-5.5", "google/gemini-3.8-flash", "meta/muse-spark-1.3", "qwen/qwen3.8-max-0902"])
