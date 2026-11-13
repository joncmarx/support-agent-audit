"""The holdout (TEST-PLAN-v3 sections 4, 9; decisions 9, 10). Runs only after v5 is frozen in runs/PREREGISTRATION.md.
Prints counts and ids only, never question or answer text.

  python3 -m audit.holdoutrun scan          # decision 10: marker scan of the 11 hidden-history threads (code only)
  python3 -m audit.holdoutrun refcheck      # decision 9: round one's reference check (Sonnet 5.5), holdout then reserve
  python3 -m audit.holdoutrun select        # the final 100: replacements from the reserve, in order
  (labels: AUDIT_SET=holdout python3 -m audit.labelbatch ... / audit.labelrun ..., same code as labels v2)
  python3 -m audit.holdoutrun v4            # arm A as built: fresh retrieval (v4 settings), draft -> review -> handoff
  python3 -m audit.holdoutrun g             # v5 = G: v4's drafts and review decisions, blocked replies rewritten (G_HANDOFF)
  python3 -m audit.holdoutrun submit grader1|grader2 | poll | tiebreak | score
"""
import json, re, sys
from collections import Counter

from . import batch as BT, build2 as B2, llm, regrade as R
from .bot import CONFIGS, customer_message
from .common import ROOT, read_jsonl
from .grade import reference_check
from .grade3 import RUBRIC, packet_v2, parse_grade, render_item
from .jobs import run_jobs
from .severity import severity
from .stats import exact_range

SEALED = ROOT / "sealed"
OUT = ROOT / "runs/v3plan/holdout"
PH = "5-holdout"
MINI = "openai/gpt-5.4-mini"
SONNET = "anthropic/claude-sonnet-5.5"
GRADERS = [B2.G1, B2.G2, B2.TBM]
HIDDEN = "first-post history hidden: current text used"
MARKER = re.compile(r"(?i)(\[\s*solved\s*\]|\(\s*solved\s*\)|\b(?:update|updated|edit|edited|solved|resolved|solution)\s*[:\-–—]|^\s*\**\s*(?:update|edit|solved|resolved)\b)", re.M)
G_HANDOFF = (ROOT / "prompts/G_HANDOFF.md").read_text()
# Section 9 outcome (2026-10-16): G failed the practice screen (5 > 1), so v5 = A, v4 exactly as built. v5's holdout
# replies are v4's; the 'g' command is kept for the record but not used.
V5 = "A"


def _sealed(name):
    return {str(r["id"]): r for r in read_jsonl(SEALED / name)}


def candidates():
    """Holdout (rank 1-100) then reserve (101-120), merged with their solutions, in rank order."""
    rows = []
    for qf, sf in (("holdout_questions.jsonl", "holdout_solutions.jsonl"), ("reserve_questions.jsonl", "reserve_solutions.jsonl")):
        sol = _sealed(sf)
        for q in read_jsonl(SEALED / qf):
            rows.append({**q, "id": str(q["id"]), "split": "holdout", "accepted_answer": sol[str(q["id"])]["accepted_answer"]})
    return sorted(rows, key=lambda r: r["rank"])


def questions():
    """The final 100, after `select`."""
    ids = json.loads((OUT / "final_ids.json").read_text())["ids"]
    c = {q["id"]: q for q in candidates()}
    return [c[i] for i in ids]


# ------------------------------------------------------------------ decisions 9 and 10
def scan():
    hits = [q["id"] for q in candidates() if HIDDEN in q.get("flags", []) and MARKER.search(f"{q['title']}\n{q['question']}")]
    hidden = [q["id"] for q in candidates() if HIDDEN in q.get("flags", [])]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "marker_scan.json").write_text(json.dumps({"hidden": hidden, "marker_hits": hits, "regex": MARKER.pattern}))
    print(f"hidden-history threads: {len(hidden)} (holdout {sum(int(c['rank']) <= 100 for c in candidates() if c['id'] in hidden)}) | "
          f"marker hits: {len(hits)} -> {hits}")


def _chat(model, messages, max_tokens=800, json_mode=True, tag=""):
    # round one: same prompt and model, no thinking; the v3 call layer pins the host and turns thinking on, so the cap is 4,000
    r = llm.call(model, messages, role="refcheck", phase=PH, split="holdout", json_mode=json_mode, max_tokens=4000)
    if not r["ok"]:
        raise ValueError(str(r["failures"])[:200])
    return r["text"], {"cost": r["cost"]}


def refcheck(n_reserve=0):
    p = OUT / "refcheck.jsonl"
    done = {r["id"] for r in read_jsonl(p)} if p.exists() else set()
    cands = [q for q in candidates() if int(q["rank"]) <= 100 + n_reserve and q["id"] not in done]
    OUT.mkdir(parents=True, exist_ok=True)
    left = run_jobs([(q["id"], q) for q in cands], lambda k, q: reference_check(_chat, q), p, workers=40, max_seconds=120)
    rows = read_jsonl(p)
    print(f"reference check: {len(rows)} done, usable {sum(r['usable'] for r in rows)}, not usable "
          f"{[r['id'] for r in rows if not r['usable']]} | left {left}")


def select():
    ref = {r["id"]: r["usable"] for r in read_jsonl(OUT / "refcheck.jsonl")}
    marker = set(json.loads((OUT / "marker_scan.json").read_text())["marker_hits"])
    ids, log = [], []
    for q in candidates():
        if len(ids) == 100:
            break
        if q["id"] not in ref:
            raise SystemExit(f"rank {q['rank']} ({q['id']}) has no reference check yet: run refcheck with more reserve")
        why = "marker (decision 10)" if q["id"] in marker else None if ref[q["id"]] else "reference not usable (decision 9)"
        if why:
            log.append({"id": q["id"], "rank": q["rank"], "replaced_because": why}); continue
        ids.append(q["id"])
    c = {q["id"]: q for q in candidates()}
    flagged = [i for i in ids if HIDDEN in c[i].get("flags", [])]
    (OUT / "final_ids.json").write_text(json.dumps({"ids": ids, "dropped": log, "hidden_history": flagged}, indent=1))
    print(f"final {len(ids)} | dropped {len(log)}: {[(d['rank'], d['replaced_because']) for d in log]} | "
          f"reserve used {sum(int(c[i]['rank']) > 100 for i in ids)} | hidden-history flagged {len(flagged)}")


# ------------------------------------------------------------------ arm A (v4 as built) and v5 = G
def v4():
    from .docs_index import Docs
    from .labels2 import Searcher
    from .pipeline import run as run_pipeline
    from .bot import search_query
    docs = Docs(); s = Searcher(docs); chunks = {c["id"]: c for c in docs.chunks}
    p = OUT / "v4_answers.jsonl"
    done = {r["id"] for r in read_jsonl(p)} if p.exists() else set()
    todo = [q for q in questions() if q["id"] not in done]

    def one(k, q):
        passages = [chunks[i] for i in s.hybrid(search_query(q, "with_nodes"), k=CONFIGS["v4"]["k"])]
        return run_pipeline(q, passages, arm="A", drafter=MINI, reviewer=MINI, system=CONFIGS["v4"]["system"],
                            graders=GRADERS, phase=PH, split="holdout", reviewer_role="reviewer_A")
    left = run_jobs([(q["id"], q) for q in todo], one, p, workers=50, max_seconds=100)
    rows = read_jsonl(p)
    print(f"v4 on holdout: {len(rows)}/100 | passed {sum(r.get('review_safe') is True for r in rows)} | "
          f"system failures {sum(bool(r.get('system_failure')) for r in rows)} | left {left}")


def v4_answers():
    return {r["id"]: r for r in read_jsonl(OUT / "v4_answers.jsonl")}


def g():
    A, Q = v4_answers(), {q["id"]: q for q in questions()}
    keys = [k for k, a in A.items() if a.get("review_safe") is False]
    msgs = {k: [{"role": "user", "content": G_HANDOFF.format(problem=A[k]["review_problem"], question=customer_message(Q[k]))}]
            for k in keys}
    B2.run_chunk(keys, lambda k, n: B2.one_call(MINI, msgs[k], role="handoff", author=None, split="holdout", arm="G", item=k,
                                                attempt=n, phase=PH), OUT / "g_handoffs.jsonl", workers=60, window=2)


def finals(which):
    """qid -> dict(kind, text, author)."""
    out = {}
    if which == "v4":
        for k, a in v4_answers().items():
            out[k] = {"kind": a["answer_source"], "text": a["answer"],
                      "author": "JC" if a["answer_source"] == "safe_handoff" else MINI}
        return out
    if V5 == "A":
        return finals("v4")
    res = B2.records(OUT / "g_handoffs.jsonl")
    for k, a in v4_answers().items():
        if a.get("review_safe") is False:
            s = B2.state(res.get(k, []))
            out[k] = (None if s is None else {"kind": "handoff_failure", "text": B2.SAFE, "author": "JC"} if s == "failed"
                      else {"kind": "g_handoff", "text": s["text"].strip(), "author": MINI})
        else:
            out[k] = {"kind": a["answer_source"], "text": a["answer"], "author": "JC" if a["answer_source"] == "safe_handoff" else MINI}
    return out


# ------------------------------------------------------------------ grading
def labels():
    return {str(r["id"]): r for r in read_jsonl(OUT / "labels/final.jsonl")}


def items():
    from .docs_index import Docs
    chunks = {c["id"]: c for c in Docs().chunks}
    Q, L, A = {q["id"]: q for q in questions()}, labels(), v4_answers()
    out = {}
    for which in ("v4", "v5"):
        for k, f in finals(which).items():
            if f is None:
                continue
            rid = B2.rid_of(f"h{k}", f["text"])
            if rid in out:
                continue
            ev = [chunks[c] for c in L[k]["evidence_chunks"] if c in chunks]
            out[rid] = ({"rid": rid, "qid": k, "author": f["author"]},
                        render_item(Q[k], packet_v2(Q[k], ev), [chunks[c] for c in A[k]["passages"] if c in chunks], f["text"]))
    return out


def gstate(role):
    return {k: ({"ok": True, "grade": v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in B2.results(f"ho-{role}", OUT / f"grades_{role}.jsonl").items()}


def submit(role):
    its = items()
    BT.create_job(f"ho-{role}", B2.GRADER_MODELS[role], role,
                  {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}] for rid, (_r, t) in its.items()},
                  phase=PH, split="holdout", arm="holdout", authors={rid: r["author"] for rid, (r, _t) in its.items()})
    st = BT.submit(f"ho-{role}")
    print(f"ho-{role} submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])


def poll():
    for role in ("grader1", "grader2"):
        j = f"ho-{role}"
        if not (BT.BDIR / f"{j}.json").exists():
            continue
        info = BT.poll(j, parse=parse_grade)
        if any(it["status"] == "pending" for it in BT.load(j)["items"].values()):
            BT.submit(j); info = BT.poll(j, parse=parse_grade)
        print(info)


def needs_tb(its):
    L, a, b = labels(), gstate("grader1"), gstate("grader2")
    return [rid for rid, (r, _t) in its.items() if rid in a and rid in b and
            R.settle_reply(rid, L[r["qid"]]["side"] == "answerable", a[rid], b[rid], None)["status"] == "needs_tiebreak"]


def tiebreak():
    its = items()
    B2.run_chunk(needs_tb(its), lambda k, n: B2.one_call(
        B2.TBM, [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role="tiebreaker",
        author=its[k][0]["author"], split="holdout", arm="holdout", item=k, attempt=n, json_mode=True, parse=parse_grade,
        phase=PH), OUT / "grades_tiebreaker.jsonl", workers=60, window=2)


def score():
    L, a, b, t = labels(), gstate("grader1"), gstate("grader2"), gstate("tiebreaker")
    hidden = set(json.loads((OUT / "final_ids.json").read_text())["hidden_history"])
    rep = {}
    for which in ("v4", "v5"):
        rows = {}
        for subset, keep in (("all", lambda k: True), ("without_hidden_history", lambda k: k not in hidden)):
            cnt, sev, pend, st = Counter(), Counter(), 0, Counter()
            fin = {k: f for k, f in finals(which).items() if keep(k)}
            for k, f in fin.items():
                rid = B2.rid_of(f"h{k}", f["text"]) if f else None
                if not rid or rid not in a or rid not in b:
                    pend += 1; continue
                ans = L[k]["side"] == "answerable"
                s = R.settle_reply(rid, ans, a[rid], b[rid], None)
                if s["status"] == "needs_tiebreak":
                    if rid not in t:
                        pend += 1; continue
                    s = R.settle_reply(rid, ans, a[rid], b[rid], t[rid])
                cnt[s["outcome"]] += 1; st[s["status"]] += 1
                if s["outcome"] == "confidently_wrong":
                    sev[severity(a[rid], b[rid], t.get(rid) if s["status"] != "agree" else None)] += 1
            n = len(fin); lo, hi = exact_range(cnt["confidently_wrong"], n)
            na = sum(L[k]["side"] == "answerable" for k in fin)
            rows[subset] = {"n": n, "pending": pend, **{k: cnt[k] for k in B2.ORDER}, "answerable": na,
                            "unnecessary_per_100_answerable": round(100 * cnt["unnecessary_handoff"] / max(1, na), 1),
                            "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)],
                            "severity": dict(sev), "settlement": dict(st),
                            "gate_met": (cnt["confidently_wrong"] <= 2) if subset == "all" and not pend else None}
        rep[which] = rows
    (OUT / "score.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "refcheck":
        refcheck(int(args[0]) if args else 0)
    elif cmd == "submit":
        submit(args[0])
    elif cmd == "score":
        print(json.dumps(score(), indent=1))
    else:
        {"scan": scan, "select": select, "v4": v4, "g": g, "poll": poll, "tiebreak": tiebreak}[cmd]()


# ------------------------------------------------------------------ the freeze (section 9 step 4)
def freeze_hashes(v5):
    """sha256 of every input v5's behaviour and scoring depend on."""
    import hashlib, inspect
    from . import bot, models, outcome, pipeline, regrade, severity as sev
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    parts = {
        "drafter_system_prompt (bot.CONFIGS['v4']['system'])": CONFIGS["v4"]["system"],
        "drafter_user_template (pipeline.V4_USER)": pipeline.V4_USER,
        "review_prompt (bot.REVIEW_PROMPT)": bot.REVIEW_PROMPT,
        "handoff_prompt": G_HANDOFF if v5 == "G" else bot.HANDOFF_PROMPT,
        "retrieval (hybrid, k, query)": json.dumps({k: CONFIGS["v4"][k] for k in ("retrieval", "k", "query")}),
        "models_and_hosts (gpt-5.4-mini spec, caps, attempts)": json.dumps({"spec": models.MODELS[MINI], "caps": {str(k): v for k, v in models.CAPS.items() if MINI in k},
                                                                           "attempts": models.ATTEMPTS, "timeout": models.DEFAULT_TIMEOUT}, sort_keys=True),
        "docs_commit": (ROOT / "data/docs_commit.txt").read_text(),
        "safe_handoff": (ROOT / "prompts/SAFE_HANDOFF.txt").read_text(),
        "pipeline.run": inspect.getsource(pipeline),
        "scoring: outcome.py": inspect.getsource(outcome),
        "scoring: regrade.settle_reply": inspect.getsource(regrade.settle_reply),
        "scoring: severity.py": inspect.getsource(sev),
        "rubric (grade3.RUBRIC)": RUBRIC,
        "holdout runner (audit/holdoutrun.py)": (ROOT / "audit/holdoutrun.py").read_text(),
    }
    return {k: h(v) for k, v in parts.items()}
