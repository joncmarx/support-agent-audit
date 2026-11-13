"""Follow-up tests, added after the final test (JC, 2026-10-28). Labeled as such everywhere they are reported.

The holdout result (v5 = A, 4 of 100) stands. These answer the two questions the original design left open:

  H   Strong model + review step. Arm D's stored Sol drafts -> Sol reviews its own draft with v4's exact review
      prompt -> a blocked draft becomes a Sol handoff with v4's handoff template. Same structure as arm A (v4 as
      built); only the model changes. Declared self-review exception, like arm A's (audit/models.py).
  I   Strong model + an independent checker (added after H, JC 2026-10-28): as H, but the review is done by arm B's
      reviewer (MiMo-V2.6-Pro, Xiaomi). Blocked drafts are still rewritten by Sol. RI = R's routing, then I.
  R   Routing step first. Sol applies the support lead's routing rules (prompts/ROUTER_RULES.md, JC's words) to the
      question and the same doc passages. "person" -> a Sol handoff (prompts/ROUTER_HANDOFF.md = v4's handoff
      template with its first line adapted, since no draft exists). "bot" -> arm D's stored draft.
  RH  R's routing, then H's final reply for the questions routed to the bot.
  D   Arm D's drafts, the comparison point (graded on practice and test already; graded fresh on the holdout).

Everything else is frozen: questions, the passages v4 retrieved, prompts, graders, rubric, settlement rules.
Splits: dev (practice 43), test (97), holdout (100, already opened once: reported as "run after the final test").
Calls run over the API in resumable chunks; grader 1 (Sonnet) runs on Anthropic's batch host.

  python3 -m audit.followup draft holdout          # Sol drafts on the holdout (dev/test reuse arm D's)
  python3 -m audit.followup review|route|handoff <split>
  python3 -m audit.followup submit grader1 <split> | poll <split> | api grader2 <split> | tiebreak <split>
  python3 -m audit.followup status <split> | score <split>
"""
import argparse, json
from collections import Counter, defaultdict

from . import armd as AD, batch as BT, build2 as B2, llm, regrade as R
from .bot import CONFIGS, HANDOFF_PROMPT, REVIEW_PROMPT, customer_message, format_passages
from .common import ROOT, read_jsonl
from .grade3 import RUBRIC, packet_v2, parse_grade, render_item
from .pipeline import V4_USER, _parse_draft, _parse_review
from .severity import severity
from .stats import exact_range

SOL = "openai/gpt-6.1-sol"
OUT = ROOT / "runs/v3plan/followup"
PHASE = {"dev": "6-followup-practice", "test": "6-followup-test", "holdout": "6-followup-holdout"}
CEILING = {"dev": 2.50, "test": 6.50, "holdout": 9.00}  # estimates ~$1.7 / ~$3.6 / ~$7.0, x1.3 headroom, rounded up
# 2026-10-28 16:05: test raised $5.00 -> $6.50 before grading. The router sent 81 of 97 to a person (predicted 35-60),
# so there are ~91 new handoffs to grade, and Sol reviews/routing cost ~1.3c a call (estimate 0.5-1c). Logged in PREREGISTRATION.md.
GRADERS = [B2.G1, B2.G2, B2.TBM]
ROUTER_RULES = ROOT / "prompts/ROUTER_RULES.md"
ROUTER_PROMPT = (ROOT / "prompts/ROUTER.md").read_text()
ROUTER_HANDOFF = (ROOT / "prompts/ROUTER_HANDOFF.md").read_text()
CONFIGS_REPORTED = ["D", "H", "I", "R", "RH", "RI"]


# ------------------------------------------------------------------ per-split data (dev/test from Build 2, holdout from Build 3)
def _ho():
    from . import holdoutrun as HR
    return HR


_C = {}


def data(split):
    """dict(Q: qid->question, passages: qid->[chunk], side: qid->'answerable'|'human', category, evidence, rid)."""
    if split in _C:
        return _C[split]
    if split == "holdout":
        HR = _ho()
        from .docs_index import Docs
        chunks = {c["id"]: c for c in Docs().chunks}
        Q = {str(q["id"]): q for q in HR.questions()}
        A, L = HR.v4_answers(), HR.labels()
        d = {"Q": Q, "passages": {k: [chunks[c] for c in A[k]["passages"] if c in chunks] for k in Q},
             "side": {k: L[k]["side"] for k in Q}, "category": {k: L[k].get("final") for k in Q},
             "evidence": {k: [chunks[c] for c in L[k]["evidence_chunks"] if c in chunks] for k in Q},
             "rid": lambda k, text: B2.rid_of(f"h{k}", text)}
    else:
        c, ev = B2.ctx(), R.final_evidence()
        v4 = c["v4"][split]
        d = {"Q": {str(q): c["Q"][q] for q in v4},
             "passages": {str(q): [c["chunks"][i] for i in a["passages"]] for q, a in v4.items()},
             "side": {str(q): c["labs"][q]["side"] for q in v4}, "category": {str(q): c["labs"][q].get("final") for q in v4},
             "evidence": {str(q): [c["chunks"][x] for x in ev.get(q, []) if x in c["chunks"]] for q in v4},
             "rid": lambda k, text: B2.rid_of(int(k), text)}
    _C[split] = d
    return d


def path(split, name):
    return OUT / split / f"{name}.jsonl"


def done(split, name):
    """key -> record (ok) | 'failed' (3 attempts used). Pending keys are absent."""
    out = {}
    for k, recs in B2.records(path(split, name)).items():
        s = B2.state(recs)
        if s:
            out[k] = s
    return out


# ------------------------------------------------------------------ Sol drafts (arm D)
def drafts(split):
    """qid -> dict(kind, text, author) or None while pending."""
    if split != "holdout":
        return {str(q): f for q, f in AD.drafts(split).items()}
    got, out = done(split, "drafts"), {}
    for k in data(split)["Q"]:
        s = got.get(k)
        out[k] = (None if s is None else {"kind": "system_failure", "text": B2.SAFE, "author": "JC"} if s == "failed"
                  else {"kind": "draft", "text": s["parsed"], "author": SOL})
    return out


def run_drafts(split):
    assert split == "holdout", "dev/test reuse arm D's stored drafts"
    d = data(split); sysp = CONFIGS["v4"]["system"]
    msgs = {k: [{"role": "system", "content": sysp},
                {"role": "user", "content": V4_USER.format(passages=format_passages(d["passages"][k]), question=customer_message(q))}]
            for k, q in d["Q"].items()}
    guard(split)
    B2.run_chunk(list(msgs), lambda k, n: B2.one_call(SOL, msgs[k], role="drafter", author=None, split=split, arm="D", item=k,
                                                      attempt=n, parse=_parse_draft, phase=PHASE[split]),
                 path(split, "drafts"), workers=50, window=2)


# ------------------------------------------------------------------ review steps: H (Sol checks itself), I (independent checker)
# I (JC, 2026-10-28, after H): the same review prompt and handoff path, with arm B's independent reviewer (MiMo-V2.6-Pro,
# Xiaomi: not the drafter's company, not a grader's). Blocked drafts are rewritten by the drafter (Sol), as in every arm.
MIMO = "xiaomi/mimo-v2.6-pro"
REVIEWERS = {"H": (SOL, "reviewer_H", "reviews"), "I": (MIMO, "reviewer_I", "reviews_I")}


def run_review(split, arm="H"):
    model, role, name = REVIEWERS[arm]
    d, dr = data(split), drafts(split)
    if any(v is None for v in dr.values()):
        raise SystemExit("drafts still pending")
    keys = [k for k, f in dr.items() if f["kind"] == "draft"]
    msgs = {k: [{"role": "user", "content": REVIEW_PROMPT.format(question=customer_message(d["Q"][k]),
                                                                 passages=format_passages(d["passages"][k]), reply=dr[k]["text"])}]
            for k in keys}
    guard(split)
    B2.run_chunk(keys, lambda k, n: B2.one_call(model, msgs[k], role=role, author=SOL, split=split, arm=arm, item=k,
                                                attempt=n, json_mode=True, parse=_parse_review, phase=PHASE[split]),
                 path(split, name), workers=50, window=2)


# ------------------------------------------------------------------ R: the routing step
def parse_route(text):
    out = llm.parse_json(text)
    r = str(out.get("route", "")).strip().lower()
    if r not in ("bot", "person"):
        raise ValueError(f"no readable route: {str(out)[:120]}")
    return {"route": r, "rule": str(out.get("rule") or ""), "reason": str(out.get("reason") or "")}


def run_route(split):
    rules = ROUTER_RULES.read_text().strip()
    d = data(split)
    msgs = {k: [{"role": "user", "content": ROUTER_PROMPT.format(rules=rules, question=customer_message(q),
                                                                 passages=format_passages(d["passages"][k]))}]
            for k, q in d["Q"].items()}
    guard(split)
    B2.run_chunk(list(msgs), lambda k, n: B2.one_call(SOL, msgs[k], role="router", author=None, split=split, arm="R", item=k,
                                                      attempt=n, json_mode=True, parse=parse_route, phase=PHASE[split]),
                 path(split, "routes"), workers=50, window=2)


# ------------------------------------------------------------------ handoffs for H's blocks and R's "person" routes
def handoff_jobs(split):
    d, rt = data(split), done(split, "routes")
    jobs = {}
    for arm, (_m, _r, name) in REVIEWERS.items():
        for k, s in done(split, name).items():
            if s != "failed" and not s["parsed"]["safe"]:
                jobs[f"{arm}|{k}"] = HANDOFF_PROMPT.format(problem=s["parsed"].get("problem", ""), question=customer_message(d["Q"][k]))
    for k, s in rt.items():
        if s != "failed" and s["parsed"]["route"] == "person":
            jobs[f"R|{k}"] = ROUTER_HANDOFF.format(problem=s["parsed"]["reason"], question=customer_message(d["Q"][k]))
    return jobs


def run_handoff(split):
    jobs = handoff_jobs(split)
    guard(split)
    B2.run_chunk(list(jobs), lambda k, n: B2.one_call(SOL, [{"role": "user", "content": jobs[k]}], role="handoff", author=None,
                                                      split=split, arm=k.split("|")[0], item=k, attempt=n, phase=PHASE[split]),
                 path(split, "handoffs"), workers=50, window=2)


# ------------------------------------------------------------------ final replies per configuration
def finals(cfg, split):
    """qid -> dict(kind, text, author) or None while pending."""
    dr = drafts(split)
    if cfg == "D":
        return dr
    rt, ho = done(split, "routes"), done(split, "handoffs")
    arm = "I" if cfg in ("I", "RI") else "H"
    rv = done(split, REVIEWERS[arm][2])

    def hand(key):
        s = ho.get(key)
        return (None if s is None else {"kind": "handoff_failure", "text": B2.SAFE, "author": "JC"} if s == "failed"
                else {"kind": "handoff", "text": s["text"].strip(), "author": SOL})

    def h_final(k):
        f = dr.get(k)
        if f is None:
            return None
        if f["kind"] != "draft":
            return f
        s = rv.get(k)
        if s is None:
            return None
        if s == "failed":  # never passed, never counted as a genuine block (section 8)
            return {"kind": "system_failure", "text": B2.SAFE, "author": "JC"}
        return {**f, "kind": "passed"} if s["parsed"]["safe"] else hand(f"{arm}|{k}")

    def r_route(k):
        s = rt.get(k)
        return None if s is None else ("failed" if s == "failed" else s["parsed"]["route"])

    out = {}
    for k in data(split)["Q"]:
        if cfg in ("H", "I"):
            out[k] = h_final(k)
            continue
        r = r_route(k)
        if r is None:
            out[k] = None
        elif r == "failed":  # a router that never answers sends the customer JC's safe handoff
            out[k] = {"kind": "system_failure", "text": B2.SAFE, "author": "JC"}
        elif r == "person":
            out[k] = hand(f"R|{k}")
        else:
            out[k] = dr.get(k) if cfg == "R" else h_final(k)
    return out


# ------------------------------------------------------------------ grading (only replies no earlier phase graded)
def prior_settled(split):
    if split == "holdout":
        HR = _ho()
        L, a, b, t = HR.labels(), HR.gstate("grader1"), HR.gstate("grader2"), HR.gstate("tiebreaker")
        out = {}
        for rid, (r, _t) in HR.items().items():
            if rid in a and rid in b:
                ans = L[r["qid"]]["side"] == "answerable"
                s = R.settle_reply(rid, ans, a[rid], b[rid], None)
                if s["status"] == "needs_tiebreak" and rid in t:
                    s = R.settle_reply(rid, ans, a[rid], b[rid], t[rid])
                out[rid] = {**s, "g": (a[rid], b[rid], t.get(rid))}
        return out
    old, _t, _k = R.score_all()
    out = {rid: {**s} for rid, s in old.items()}
    a, b, t = AD.gstate("grader1", split), AD.gstate("grader2", split), AD.gstate("tiebreaker", split)
    for rid, s in AD.settle(split).items():
        out[rid] = {**s, "g": (a.get(rid), b.get(rid), t.get(rid))}
    return out


def items(split):
    d, prior, out = data(split), prior_settled(split), {}
    for cfg in CONFIGS_REPORTED:
        for k, f in finals(cfg, split).items():
            if f is None:
                continue
            rid = d["rid"](k, f["text"])
            if rid in prior or rid in out:
                continue
            Q = d["Q"][k]
            out[rid] = ({"rid": rid, "qid": k, "author": f["author"]},
                        render_item(Q, packet_v2(Q, d["evidence"][k]), d["passages"][k], f["text"]))
    return out


def gstate(role, split):
    return {k: ({"ok": True, "grade": v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in B2.results(f"fu-{split}-{role}", path(split, f"grades_{role}")).items()}


def complete(split):
    return all(f is not None for cfg in CONFIGS_REPORTED for f in finals(cfg, split).values())


def submit(role, split):
    if not complete(split):
        raise SystemExit("finals still pending: grade only once every configuration's finals are in")
    guard(split)
    its = items(split)
    BT.create_job(f"fu-{split}-{role}", B2.GRADER_MODELS[role], role,
                  {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}] for rid, (_r, t) in its.items()},
                  phase=PHASE[split], split=split, arm="followup", authors={rid: r["author"] for rid, (r, _t) in its.items()})
    st = BT.submit(f"fu-{split}-{role}")
    print(f"fu-{split}-{role} submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])


def poll(split):
    for role in ("grader1", "grader2"):
        j = f"fu-{split}-{role}"
        if (BT.BDIR / f"{j}.json").exists():
            info = BT.poll(j, parse=parse_grade)
            if any(it["status"] == "pending" for it in BT.load(j)["items"].values()):
                BT.submit(j); info = BT.poll(j, parse=parse_grade)
            print(info)


def api_grade(role, split):
    if not complete(split):
        raise SystemExit("finals still pending")
    guard(split)
    its = items(split)
    B2.run_chunk(list(its), lambda k, n: B2.one_call(
        B2.GRADER_MODELS[role], [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role=role,
        author=its[k][0]["author"], split=split, arm="followup", item=k, attempt=n, json_mode=True, parse=parse_grade,
        phase=PHASE[split]), path(split, f"grades_{role}"), workers=50, window=2)


def needs_tb(split, its):
    d, a, b = data(split), gstate("grader1", split), gstate("grader2", split)
    return [rid for rid, (r, _t) in its.items() if rid in a and rid in b and
            R.settle_reply(rid, d["side"][r["qid"]] == "answerable", a[rid], b[rid], None)["status"] == "needs_tiebreak"]


def tiebreak(split):
    guard(split)
    its = items(split)
    B2.run_chunk(needs_tb(split, its), lambda k, n: B2.one_call(
        B2.TBM, [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role="tiebreaker",
        author=its[k][0]["author"], split=split, arm="followup", item=k, attempt=n, json_mode=True, parse=parse_grade,
        phase=PHASE[split]), path(split, "grades_tiebreaker"), workers=40, window=2)


def settled(split):
    d, its = data(split), items(split)
    a, b, t = gstate("grader1", split), gstate("grader2", split), gstate("tiebreaker", split)
    out = prior_settled(split)
    for rid, (r, _t) in its.items():
        if rid in a and rid in b:
            ans = d["side"][r["qid"]] == "answerable"
            s = R.settle_reply(rid, ans, a[rid], b[rid], None)
            if s["status"] == "needs_tiebreak" and rid in t:
                s = R.settle_reply(rid, ans, a[rid], b[rid], t[rid])
            out[rid] = {**s, "g": (a[rid], b[rid], t.get(rid))}
    return out


# ------------------------------------------------------------------ scoring
def score(split):
    d, st = data(split), settled(split)
    answerable = sum(v == "answerable" for v in d["side"].values())
    rows = {}
    for cfg in CONFIGS_REPORTED:
        cnt, kinds, sev, bycat, pend = Counter(), Counter(), Counter(), defaultdict(Counter), 0
        for k, f in finals(cfg, split).items():
            s = st.get(d["rid"](k, f["text"])) if f else None
            if not s or not s.get("outcome"):
                pend += 1; continue
            cnt[s["outcome"]] += 1; kinds[f["kind"]] += 1; bycat[d["category"][k]][s["outcome"]] += 1
            if s["outcome"] == "confidently_wrong" and s.get("g"):
                g1, g2, tb = s["g"]
                sev[severity(g1, g2, tb if s["status"] != "agree" else None)] += 1
        n = len(d["Q"]); lo, hi = exact_range(cnt["confidently_wrong"], n)
        rows[cfg] = {"n": n, "pending": pend, **{o: cnt[o] for o in B2.ORDER}, "kinds": dict(kinds),
                     "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)],
                     "unnecessary_per_100_answerable": round(100 * cnt["unnecessary_handoff"] / max(1, answerable), 1),
                     "severity": dict(sev),
                     "by_category": {c: {"n": sum(v.values()), "resolved": v["resolved"], "confidently_wrong": v["confidently_wrong"]}
                                     for c, v in bycat.items()}}
    rt = done(split, "routes")
    conf = Counter((d["side"][k], s["parsed"]["route"] if s != "failed" else "failed") for k, s in rt.items())
    rep = {"split": split, "answerable": answerable, "configs": rows,
           "router_vs_answer_key": {f"{side}->{route}": n for (side, route), n in sorted(conf.items())},
           "spend_usd": round(spend(split), 4)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"score_{split}.json").write_text(json.dumps(rep, indent=1))
    return rep


# ------------------------------------------------------------------ money
def spend(split):
    return sum(json.loads(l).get("cost") or 0 for l in open(llm.LEDGER) if f'"{PHASE[split]}"' in l)


def guard(split):
    if spend(split) >= CEILING[split]:
        raise SystemExit(f"STOP: {PHASE[split]} spend ${spend(split):.2f} has reached the ${CEILING[split]:.2f} ceiling")


def status(split):
    d = data(split)
    dr = drafts(split)
    print(f"drafts {sum(v is not None for v in dr.values())}/{len(dr)}")
    for name in ("reviews", "reviews_I", "routes", "handoffs"):
        print(f"{name:9} {len(done(split, name))}" + (f"/{len(handoff_jobs(split))}" if name == "handoffs" else ""))
    if complete(split):
        its = items(split)
        print(f"new replies to grade: {len(its)}")
        for role in ("grader1", "grader2"):
            print(f"{role} {len(gstate(role, split))}/{len(its)}")
        print(f"tie-breaks {len(gstate('tiebreaker', split))}/{len(needs_tb(split, its))}")
    print(f"{PHASE[split]} spend ${spend(split):.3f} (ceiling ${CEILING[split]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); a = ap.parse_args()
    c, x = a.cmd, a.args
    if c == "draft":
        run_drafts(x[0])
    elif c == "review":
        run_review(x[0], x[1] if len(x) > 1 else "H")
    elif c == "route":
        run_route(x[0])
    elif c == "handoff":
        run_handoff(x[0])
    elif c == "submit":
        submit(x[0], x[1])
    elif c == "api":
        api_grade(x[0], x[1])
    elif c == "poll":
        poll(x[0])
    elif c == "tiebreak":
        tiebreak(x[0])
    elif c == "status":
        status(x[0])
    elif c == "score":
        print(json.dumps(score(x[0]), indent=1))
