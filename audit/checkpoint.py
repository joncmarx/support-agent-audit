"""Build 1 checkpoint (TEST-PLAN-v3 section 14): every number JC needs for go / no-go, in one file.

  python3 -m audit.checkpoint      # writes runs/v3plan/CHECKPOINT.json and prints the tables
"""
import json
from collections import Counter

from .common import ROOT, read_jsonl
from .labels2 import OUT as LOUT
from .regrade import OUT as ROUT, grades, load, score_all, with_label
from .stats import cohen_kappa, exact_range

ORDER = ["resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "wrong_hedged", "no_progress", "confidently_wrong"]


def baseline_table():
    settled, table, kappa = score_all()
    labs = {r["id"]: r for r in read_jsonl(LOUT / "final.jsonl")}
    out = {}
    for split, n_name in (("test", 97), ("dev", 43)):
        answerable = sum(1 for r in labs.values() if r["split"] == split and r["side"] == "answerable")
        for arm in ("v1", "A", "A_draft", "handoff_all"):
            c = table[(arm, split)]; n = sum(c.values())
            cw = c["confidently_wrong"]; lo, hi = exact_range(cw, n) if n else (0, 0)
            unres = 0
            if arm != "handoff_all":
                idx = [r for r in load()[1] if r["arm"] == arm and r["split"] == split]
                unres = sum(settled[r["rid"]]["status"] == "unresolved" for r in idx)
            out[f"{arm}/{split}"] = {"n": n, **{k: c[k] for k in ORDER}, "trust_range_95": [round(lo * 100, 1), round(hi * 100, 1)],
                                     "unnecessary_per_100_answerable": round(100 * c["unnecessary_handoff"] / answerable, 1) if answerable else None,
                                     "answerable": answerable, "unresolved": unres}
    return out, kappa, settled


def human_share():
    labs = read_jsonl(LOUT / "final.jsonl")
    res = {}
    for split in ("test", "dev", "all"):
        rows = [r for r in labs if split == "all" or r["split"] == split]
        h = sum(r["side"] == "human" for r in rows)
        nd = [r for r in rows if not r.get("doubt")]
        res[split] = {"n": len(rows), "human": h, "share": round(100 * h / len(rows), 1),
                      "without_reference_doubt": f"{sum(r['side'] == 'human' for r in nd)} of {len(nd)}",
                      "categories": dict(Counter(r["final"] for r in rows)),
                      "jc_read": sum(r["needs_jc"] for r in rows), "flags": dict(Counter(f for r in rows for f in r["flags"]))}
    t = res["test"]["human"]
    res["prediction"] = {"range": "49-63 of 97 (50-65%)", "observed": t, "hit": 49 <= t <= 63}
    return res


def fix_passage_v2():
    """Recompute the $0 fix-passage check from labels v2 evidence passages: for the test questions settled as
    n8n_docs, did any passage a labeler cited as containing the key step reach v4's 8?"""
    labs = {r["id"]: r for r in read_jsonl(LOUT / "final.jsonl")}
    v4 = {a["id"]: a["passages"] for a in read_jsonl(ROOT / "runs/v4__openai_gpt-5.4-mini/test/answers.jsonl")}
    rows = [r for r in labs.values() if r["split"] == "test" and r["final"] == "n8n_docs"]
    hit = [r["id"] for r in rows if set(r["evidence_chunks"]) & set(v4.get(r["id"], []))]
    no_ev = [r["id"] for r in rows if not r["evidence_chunks"]]
    return {"n8n_docs_test_questions": len(rows), "fix_passage_reached_bot": len(hit), "no_passage_cited": len(no_ev)}


def main():
    base, kappa, settled = baseline_table()
    hs = human_share()
    fp = fix_passage_v2()
    lk = json.loads((LOUT / "kappa.json").read_text())
    report = {"baseline": base, "grader_kappa": kappa, "label_kappa": lk, "human_share": hs, "fix_passage_v2": fp,
              "settlement": dict(Counter(s["status"] for s in settled.values()))}
    (ROOT / "runs/v3plan/CHECKPOINT.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
