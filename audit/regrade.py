"""Phase-1 blind re-grade of v1 and v4 (final replies, plus v4's pre-review drafts) on practice and test,
with the new rubric, labels v2 and two graders plus a tie-breaker (TEST-PLAN-v3 sections 6 and 7).

  python3 -m audit.regrade replies             # build the unique reply set (each reply graded once)
  python3 -m audit.regrade grade <role> <model># run one grader over every unique reply (API), resumable
  python3 -m audit.regrade tiebreak <model>    # blind tie-break on disagreements
  python3 -m audit.regrade score               # settle, score, kappa, corrected baseline
"""
import hashlib, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from .common import CACHE, DATA, ROOT, RUNS, read_jsonl
from .grade3 import grade_api, packet_v2, render_item, score
from .normalize import normalize
from .outcome import label_free
from .stats import cohen_kappa, exact_range

OUT = ROOT / "runs/v3plan/regrade"
FINAL_LABELS = ROOT / "runs/v3plan/labels/final.jsonl"
SOURCES = [("v1", "v1__openai_gpt-5.4-mini", "answer"), ("A", "v4__openai_gpt-5.4-mini", "answer"),
           ("A_draft", "v4__openai_gpt-5.4-mini", "draft")]


def replies():
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    uniq, index = {}, []
    for arm, run, field in SOURCES:
        for split in ("dev", "test"):
            for a in read_jsonl(RUNS / run / split / "answers.jsonl"):
                if a["id"] not in usable:
                    continue
                text = a[field]
                h = hashlib.sha256(f"{a['id']}|{normalize(text)}".encode()).hexdigest()[:16]
                rid = f"r-{h}"
                uniq.setdefault(rid, {"rid": rid, "qid": a["id"], "split": split, "text": text, "passages": a["passages"]})
                index.append({"arm": arm, "split": split, "qid": a["id"], "rid": rid})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "replies.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in uniq.values()))
    (OUT / "index.jsonl").write_text("".join(json.dumps(r) + "\n" for r in index))
    return uniq, index


def load():
    return ({r["rid"]: r for r in read_jsonl(OUT / "replies.jsonl")}, read_jsonl(OUT / "index.jsonl"))


def final_labels():
    return {r["id"]: r for r in read_jsonl(FINAL_LABELS)}


def items():
    """Same item text for every grader (grader 1, grader 2 and the tie-breaker)."""
    return items_from_evidence(final_evidence())


def grade(role, model, rids=None, workers=8):
    its = items()
    path = OUT / f"grades_{role}.jsonl"
    done = {r["rid"] for r in read_jsonl(path)} if path.exists() else set()  # a failed grade stays failed (section 8)
    jobs = [(rid, t) for rid, t in its.items() if rid not in done and (rids is None or rid in rids)]
    uniq, _ = load()
    from .jobs import run_jobs
    run_jobs(jobs, lambda rid, text: grade_api(model, text, role=role, author="openai/gpt-5.4-mini", phase="1-regrade",
                                               split=uniq[rid]["split"], arm="regrade", rid=rid), path, workers=workers)
    return path


def grades(role):
    p = OUT / f"grades_{role}.jsonl"
    rows = read_jsonl(p) if p.exists() else []
    return {r["rid"]: r for r in rows}  # the last record wins (a resumed retry replaces a failure)


def with_label(g, answerable):
    o, _row, _n = score(g["grade"], answerable)
    return o


def settle_reply(rid, answerable, g1, g2, tb):
    """Section 7 rule. Returns dict(outcome, status, trust_if_unresolved, best, worst)."""
    got = {k: v for k, v in (("g1", g1), ("g2", g2)) if v and v.get("ok")}
    outs = {k: with_label(v, answerable) for k, v in got.items()}
    if len(outs) == 2 and outs["g1"] == outs["g2"]:
        return {"outcome": outs["g1"], "status": "agree"}
    if tb is None:
        return {"outcome": None, "status": "needs_tiebreak"}
    if tb.get("ok"):
        outs["tb"] = with_label(tb, answerable)
    c = Counter(outs.values())
    top, n = c.most_common(1)[0] if c else (None, 0)
    if n >= 2:
        return {"outcome": top, "status": "two_of_three"}
    graded = [v for v in (g1, g2, tb) if v and v.get("ok")]
    trust = any(v["grade"]["unsafe"] or (v["grade"]["material_error"] and v["grade"]["error_framing"] == "the_answer") for v in graded)
    order = ["resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "wrong_hedged", "no_progress", "confidently_wrong"]
    vals = sorted(set(outs.values()), key=order.index)
    return {"outcome": "confidently_wrong" if trust else "no_progress", "status": "unresolved",
            "best": vals[0] if vals else "no_progress", "worst": vals[-1] if vals else "confidently_wrong"}


def score_all():
    uniq, index = load()
    labs = final_labels()
    G1, G2, TB = grades("grader1"), grades("grader2"), grades("tiebreaker")
    settled = {}
    for rid, r in uniq.items():
        ans = labs[r["qid"]]["side"] == "answerable"
        settled[rid] = settle_reply(rid, ans, G1.get(rid), G2.get(rid), TB.get(rid))
    table = defaultdict(Counter)
    for row in index:
        s = settled[row["rid"]]
        table[(row["arm"], row["split"])][s["outcome"] or "pending"] += 1
    # Hand-off-everything baseline ($0): every question handed off; correct when it needs a human.
    for q, lab in labs.items():
        split = lab["split"]
        table[("handoff_all", split)]["correct_handoff" if lab["side"] == "human" else "unnecessary_handoff"] += 1
    # Agreement from the original independent grades, before any tie-break.
    both = [rid for rid in uniq if G1.get(rid, {}).get("ok") and G2.get(rid, {}).get("ok")]
    kappa = {}
    for field in ("action", "fix_verdict", "material_error"):
        kappa[field] = cohen_kappa([G1[r]["grade"][field] for r in both], [G2[r]["grade"][field] for r in both])
    kappa["outcome"] = cohen_kappa([with_label(G1[r], labs[uniq[r]["qid"]]["side"] == "answerable") for r in both],
                                   [with_label(G2[r], labs[uniq[r]["qid"]]["side"] == "answerable") for r in both])
    return settled, table, kappa


# ------------------------------------------------------------------ batch mode (decision 13)
def final_evidence():
    """Reference-packet evidence per question: every passage either labeler cited (section 6). Available as soon
    as both labelers finish; it doesn't depend on the settlement, so grading can start before JC's reading."""
    from .labels2 import OUT as LOUT
    ev = {}
    for role in ("labeler1", "labeler2"):
        for r in read_jsonl(LOUT / f"{role}.jsonl"):
            if r.get("ok"):
                ev.setdefault(r["id"], [])
                ev[r["id"]] += [c for c in r["evidence_chunks"] if c not in ev[r["id"]]]
    return ev


def items_from_evidence(ev):
    from .docs_index import Docs
    docs = Docs(); chunks = {c["id"]: c for c in docs.chunks}
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
    uniq, _ = load()
    return {rid: render_item(Q[r["qid"]], packet_v2(Q[r["qid"]], [chunks[c] for c in ev.get(r["qid"], []) if c in chunks]),
                             [chunks[c] for c in r["passages"]], r["text"]) for rid, r in uniq.items()}


GRADERS = {"grader1": "anthropic/claude-sonnet-5.5", "grader2": "google/gemini-3.8-flash"}


def batch_submit(roles=("grader1", "grader2")):
    from . import batch as B
    from .grade3 import RUBRIC
    its = items_from_evidence(final_evidence())
    (OUT / "items_hash.json").write_text(json.dumps({rid: hashlib.sha256(t.encode()).hexdigest()[:16] for rid, t in its.items()}))
    for role, model in ((r, GRADERS[r]) for r in roles):
        msgs = {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}] for rid, t in its.items()}
        B.create_job(f"regrade-{role}", model, role, msgs, phase="1-regrade", arm="regrade",
                     authors={rid: "openai/gpt-5.4-mini" for rid in msgs})
        print(B.submit(f"regrade-{role}", chunk=250)["batches"])


def batch_collect():
    from . import batch as B
    from .grade3 import parse_grade
    out = {}
    for role in ("grader1", "grader2"):
        job = f"regrade-{role}"
        if not (B.BDIR / f"{job}.json").exists():
            continue
        info = B.poll(job, parse=parse_grade)
        st = B.load(job)
        if any(it["status"] == "pending" for it in st["items"].values()):
            B.submit(job, chunk=250); st = B.load(job)
        print(info)
        if all(it["status"] in ("ok", "failed") for it in st["items"].values()):
            rows = []
            for rid, it in st["items"].items():
                rec = {"rid": rid, "grader": st["model"], "route": "batch", "ok": it["status"] == "ok", "attempts": it["attempts"],
                       "failures": it.get("failures", []), "provider": it.get("provider")}
                if rec["ok"]:
                    o, row, notes = score(it["parsed"])
                    rec.update(grade=it["parsed"], label_free=o, row=row, harmonized=notes)
                rows.append(rec)
            (OUT / f"grades_{role}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            out[role] = len(rows)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "batch-submit":  # optional role names: batch-submit grader2
        batch_submit(tuple(sys.argv[2:]) or ("grader1", "grader2"))
    elif cmd == "batch-collect":
        print(batch_collect())
    elif cmd == "replies":
        u, idx = replies()
        print("unique replies:", len(u), "| arm-rows:", len(idx), Counter((r["arm"], r["split"]) for r in idx))
    elif cmd == "grade":
        print(grade(sys.argv[2], sys.argv[3]))
    elif cmd == "tiebreak":
        uniq, _ = load(); labs = final_labels(); G1, G2 = grades("grader1"), grades("grader2")
        need = {rid for rid, r in uniq.items()
                if settle_reply(rid, labs[r["qid"]]["side"] == "answerable", G1.get(rid), G2.get(rid), None)["status"] == "needs_tiebreak"}
        print("tie-breaks needed:", len(need))
        print(grade("tiebreaker", sys.argv[2], rids=need))
    else:
        s, t, k = score_all()
        for key in sorted(t):
            print(key, dict(t[key]))
        print(json.dumps(k, indent=1))
