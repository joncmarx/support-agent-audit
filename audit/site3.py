"""Build 4: export what the results page shows (TEST-PLAN-v3 section 17) into site/data/.

Only our own material goes in: thread titles and links, the labeler's one-line summary of the fix that worked, the
bot's replies, the reviewers' notes, and the graders' verdicts and reasoning. Forum post bodies never go in.
Every count is re-derived here from the stored grades and checked against the score files written during the runs.

  python3 -m audit.site3 export     # writes site/data/*.json, then runs the count check
  python3 -m audit.site3 check      # the count check only
"""
import json, sys
from collections import Counter

from . import armd as AD, armf as AF, build2 as B2, holdoutrun as H, regrade as R
from .common import ROOT, RUNS, read_jsonl
from .severity import severity
from .stats import exact_range, paired_bootstrap

OUT = ROOT / "site/data"
V3 = ROOT / "runs/v3plan"
MIMO = "xiaomi/mimo-v2.6-pro"
ORDER = B2.ORDER
ROLES = ("grader1", "grader2", "tiebreaker")
WHO = {"grader1": "Claude Sonnet 5.5", "grader2": "Gemini 3.8 Flash", "tiebreaker": "Muse Spark 1.3 (tie-break)"}
ARMS = {"dev": ["v1", "A_draft", "A", "B", "D", "DF", "F0", "F", "G"],
        "test": ["v1", "A_draft", "A", "B", "D", "F0", "F"],
        "holdout": ["A"]}
_OLD = {}


def old(role):
    if role not in _OLD:
        _OLD[role] = R.grades(role)
    return _OLD[role]


def own(arm, role, split):
    if split == "holdout":
        return H.gstate(role)
    if arm in ("v1", "A", "A_draft"):
        return {}
    if arm == "B":
        return B2.grade_state(role, split)
    if arm == "D":
        return AD.gstate(role, split)
    return AF.gstate(arm, role, split)


def finals(arm, split):
    """qid -> dict(kind, text, extra) for one arm on one set."""
    if split == "holdout":
        A = H.v4_answers()
        return {k: {"kind": f["kind"], "text": f["text"], "draft": A[k].get("draft"), "review": A[k].get("review_problem")}
                for k, f in H.finals("v5").items()}
    v4 = B2.ctx()["v4"][split]
    if arm == "v1":
        uniq, index = R.load()
        return {r["qid"]: {"kind": "final", "text": uniq[r["rid"]]["text"]} for r in index if r["arm"] == "v1" and r["split"] == split}
    if arm == "A_draft":
        return {q: {"kind": "draft", "text": a["draft"]} for q, a in v4.items()}
    if arm == "A":
        return {q: {"kind": f["kind"], "text": f["text"], "review": v4[q].get("review_problem")} for q, f in B2.finals("v4", split).items()}
    if arm == "B":
        vd = B2.verdicts(MIMO, split)
        return {q: {"kind": f["kind"], "text": f["text"], "review": (vd.get(q) or {}).get("problem")}
                for q, f in B2.finals(MIMO, split).items()}
    if arm == "D":
        return {q: {"kind": f["kind"], "text": f["text"]} for q, f in AD.drafts(split).items()}
    return {q: {"kind": f["kind"], "text": f["text"]} for q, f in AF.drafts(arm, split).items()}


def answerable(arm, split):
    if split == "holdout":
        return {k: v["side"] == "answerable" for k, v in H.labels().items()}
    if arm in ("F", "DF"):
        return AF.answerable(arm, split)
    labs = B2.ctx()["labs"]
    return {q: labs[q]["side"] == "answerable" for q in B2.ctx()["v4"][split]}


def settle_arm(arm, split):
    """qid -> reply record with its settled outcome, severity and the grades that decided it."""
    fin, ans = finals(arm, split), answerable(arm, split)
    st = {role: own(arm, role, split) for role in ROLES}
    out = {}
    for q, f in fin.items():
        rid = B2.rid_of(f"h{q}" if split == "holdout" else q, f["text"])
        g = {role: st[role].get(rid) or (old(role).get(rid) if split != "holdout" else None) for role in ROLES}
        rec = {"kind": f["kind"], "text": f["text"], **{k: f[k] for k in ("draft", "review") if f.get(k)}}
        if not (g["grader1"] and g["grader2"]):
            rec["outcome"] = None; out[q] = rec; continue
        s = R.settle_reply(rid, ans[q], g["grader1"], g["grader2"], None)
        used = ["grader1", "grader2"]
        if s["status"] == "needs_tiebreak":
            s = R.settle_reply(rid, ans[q], g["grader1"], g["grader2"], g["tiebreaker"]) if g["tiebreaker"] else s
            used.append("tiebreaker")
        rec["outcome"], rec["status"] = s["outcome"], s["status"]
        if s["outcome"] == "confidently_wrong":
            rec["severity"] = severity(*(g[r] for r in used))
        rec["grades"] = []
        for role in used:
            x = g[role]
            if not (x and x.get("ok")):
                rec["grades"].append({"by": WHO[role], "outcome": None}); continue
            gr = x["grade"]
            rec["grades"].append({"by": WHO[role], "outcome": R.with_label(x, ans[q]), "why": gr.get("rationale", ""),
                                  "error": gr.get("material_error_what") or "", "unsafe": gr.get("unsafe_what") or ""})
        out[q] = rec
    return out


def count(recs, n_answerable):
    c = Counter(r["outcome"] for r in recs.values())
    sev = Counter(r["severity"] for r in recs.values() if r.get("severity"))
    n = len(recs); lo, hi = exact_range(c["confidently_wrong"], n); rlo, rhi = exact_range(c["resolved"], n)
    return {"resolved_range_95_per_100": [round(rlo * 100, 1), round(rhi * 100, 1)], "n": n, "pending": c[None], **{k: c[k] for k in ORDER}, "answerable": n_answerable,
            "unnecessary_per_100_answerable": round(100 * c["unnecessary_handoff"] / n_answerable, 1),
            "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)], "severity": dict(sev),
            "settlement": dict(Counter(r.get("status") for r in recs.values()))}


def stored(arm, split):
    """The score files written during the runs (None where a set wasn't scored by its own module)."""
    if split == "holdout":
        return json.loads((V3 / "holdout/score.json").read_text())["v5"]["all"]
    if arm in ("v1", "A", "A_draft"):
        return dict(_TABLE[(arm, split)])
    if arm == "B":
        return json.loads((V3 / f"build2/score_{split}.json").read_text())["arms"][MIMO]
    if arm == "D":
        return json.loads((V3 / f"armD/score_{split}.json").read_text())["arms"]["D_drafts"]
    return json.loads((V3 / f"armF/score_{arm}_{split}.json").read_text())["arm"]


_TABLE = {}


def build():
    if not _TABLE:
        _s, t, k = R.score_all(); _TABLE.update(t); _TABLE["kappa"] = k
    data, problems = {}, []
    for split, arms in ARMS.items():
        data[split] = {}
        for arm in arms:
            recs = settle_arm(arm, split)
            na = sum(answerable(arm, split).values())
            sc = count(recs, na)
            ref = stored(arm, split)
            for key in ORDER:
                if (ref.get(key) or 0) != sc[key]:
                    problems.append(f"{arm} {split} {key}: export {sc[key]} vs stored {ref.get(key)}")
            data[split][arm] = (recs, sc)
    return data, problems


def questions(split):
    if split == "holdout":
        Q, L = {q["id"]: q for q in H.questions()}, H.labels()
        L1 = {str(r["id"]): r for r in read_jsonl(V3 / "holdout/labels/labeler1.jsonl")}
        hidden = set(json.loads((V3 / "holdout/final_ids.json").read_text())["hidden_history"])
        ids = json.loads((V3 / "holdout/final_ids.json").read_text())["ids"]
    else:
        Q, L = B2.ctx()["Q"], B2.ctx()["labs"]
        L1 = {r["id"]: r for r in read_jsonl(V3 / "labels/labeler1.jsonl")}
        hidden, ids = set(), list(B2.ctx()["v4"][split])
    comm = {str(r["id"]): r.get("available") for r in read_jsonl(V3 / "community/labels/final.jsonl")}
    out = []
    for i in ids:
        q, lab = Q[i if i in Q else str(i)], L[i]
        l1 = L1.get(i) or L1.get(str(i)) or {}
        out.append({"id": str(i), "title": q["title"], "url": q["url"], "date": str(q["created_at"])[:10],
                    "category": lab["final"], "side": lab["side"], "basis": lab["basis"], "doubt": lab.get("doubt", False),
                    "fix": ((l1.get("turn_a") or {}).get("key_step") or ""), "hidden_history": str(i) in hidden,
                    "community_has_fix": comm.get(str(i)), "docs": lab.get("evidence_chunks", [])[:3]})
    return out


def paired(data, a, b, outcome, split="test"):
    ra, rb = data[split][a][0], data[split][b][0]
    diffs = [(ra[q]["outcome"] == outcome) - (rb[q]["outcome"] == outcome) for q in ra]
    lo, hi = paired_bootstrap(diffs)
    d = sum(diffs) / len(diffs)
    return {"a": a, "b": b, "outcome": outcome, "diff_per_100": round(100 * d, 1),
            "range_95": [round(100 * lo, 1), round(100 * hi, 1)], "clear": lo > 0 or hi < 0}


def spend():
    by = Counter()
    for l in open(RUNS / "cost_ledger.jsonl"):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        by["round one" if not d.get("plan") else d.get("phase")] += float(d.get("cost") or 0)
    return {k: round(v, 2) for k, v in sorted(by.items())}, round(sum(by.values()), 2)


def export():
    data, problems = build()
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"scores": {s: {a: sc for a, (_r, sc) in arms.items()} for s, arms in data.items()},
               "handoff_all": {s: dict(_TABLE[("handoff_all", s)]) for s in ("dev", "test")},
               "kappa_regrade": _TABLE["kappa"],
               "reviewers": {split: {k: json.loads((V3 / f"build2/score_{split}.json").read_text())["arms"][k]
                                     for k in ("v4", MIMO)} for split in ("dev", "test")},
               "paired_test": [paired(data, "D", "A_draft", "confidently_wrong"), paired(data, "D", "A_draft", "resolved"),
                               paired(data, "D", "A", "resolved"), paired(data, "D", "A", "confidently_wrong"),
                               paired(data, "B", "A", "resolved"), paired(data, "B", "A", "confidently_wrong"),
                               paired(data, "F", "F0", "resolved"), paired(data, "F", "F0", "confidently_wrong"),
                               paired(data, "F0", "A_draft", "resolved"), paired(data, "F0", "A_draft", "confidently_wrong")],
               "jc_read_D_test": json.loads((V3 / "armD/test/jc_read/jc_ratings.json").read_text())["ratings"],
               "spend": spend(), "check_problems": problems}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    for split, arms in data.items():
        qs = questions(split)
        rep = {"questions": qs, "replies": {a: {str(q): r for q, r in recs.items()} for a, (recs, _sc) in arms.items()}}
        # U+FFFD (a model quoting undecodable bytes) is shown as a visible placeholder box instead
        (OUT / f"replies-{ {'dev': 'practice'}.get(split, split)}.json").write_text(
            json.dumps(rep, ensure_ascii=False).replace("\ufffd", "\u25a1"))
    return problems


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    p = export() if cmd == "export" else build()[1]
    print("count check:", "all exported counts match the stored score files" if not p else "\n".join(p))
