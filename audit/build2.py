"""Build 2 (TEST-PLAN-v3 sections 3, 9, 11 and 14): the reviewer trial on practice, then arm B on test.

Every candidate reviews v4's stored drafts with v4's exact review prompt and answer format, so arm B differs from v4
only in its pass-or-block decisions. A blocked draft becomes a handoff: v4's stored handoff where v4 also blocked,
otherwise a new one written by the low-cost model with v4's template. A reviewer that never returns a readable
verdict gives the customer JC's fixed safe handoff, flagged system_failure; the draft is never passed.

Route (JC, 2026-10-13): OpenRouter batch mode wherever the pinned host accepts it (half price, up to 24 hours).
If a host refuses a batch, nothing is billed and that model runs over the regular API in resumable chunks: one
attempt per item per chunk (the linked Mac kills commands after about 3 minutes), up to 3 attempts per item.

  python3 -m audit.build2 submit review <model> <split>   # batch: one candidate's reviews (split: dev | test)
  python3 -m audit.build2 submit handoff <model> <split>  # batch: new handoffs for that reviewer's new blocks
  python3 -m audit.build2 submit grader1|grader2 <split>  # batch: grade every new reply (after all finals are in)
  python3 -m audit.build2 poll <split>                    # collect finished batches; resubmit failed items
  python3 -m audit.build2 api review|handoff <model> <split>   # API fallback chunk (refused hosts only)
  python3 -m audit.build2 api tiebreaker <split>          # tie-breaks (Muse Spark has no batch route): API chunk
  python3 -m audit.build2 status <split> | score <split>
"""
import argparse, hashlib, json, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import batch as BT, llm, models as M
from . import regrade as R
from .bot import HANDOFF_PROMPT, REVIEW_PROMPT, customer_message, format_passages
from .common import CACHE, ROOT, RUNS, read_jsonl
from .grade3 import RUBRIC, item_hash, packet_v2, parse_grade, render_item
from .normalize import normalize
from .stats import exact_range

OUT = ROOT / "runs/v3plan/build2"
V4 = RUNS / "v4__openai_gpt-5.4-mini"
MINI = "openai/gpt-5.4-mini"
CANDIDATES = ["xiaomi/mimo-v2.6-pro", "z-ai/glm-5.3", "moonshotai/kimi-k3"]  # section 9's fixed tie order
G1, G2, TBM = R.GRADERS["grader1"], R.GRADERS["grader2"], "meta/muse-spark-1.3"
GRADER_MODELS = {"grader1": G1, "grader2": G2, "tiebreaker": TBM}
SAFE = (ROOT / "prompts/SAFE_HANDOFF.txt").read_text().strip()
PHASE = {"dev": "2-trial", "test": "2-armB"}
ARM = {"dev": "B-trial", "test": "B"}
ATTEMPT_TIMEOUT = 165  # every call in a chunk starts at once (window 2 s), so it ends inside the Mac's 3-minute limit (section 8: 180 s)
CEILING = {"dev": 5.50, "test": 1.00}  # JC 2026-10-13: trial ceiling; arm B is priced and approved separately
ORDER = ["resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "wrong_hedged",
         "no_progress", "confidently_wrong"]
_C = {}


def slug(model):
    return model.split("/")[1]


def ctx():
    if not _C:
        _C["chunks"] = {c["id"]: c for c in read_jsonl(CACHE / "docs_chunks.jsonl")}
        _C["Q"] = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
        usable = {r["id"] for r in read_jsonl(ROOT / "data/reference_check.jsonl") if r["usable"]}
        _C["v4"] = {s: {a["id"]: a for a in read_jsonl(V4 / s / "answers.jsonl") if a["id"] in usable} for s in ("dev", "test")}
        _C["labs"] = R.final_labels()
    return _C


def cands(split):
    if split == "dev":
        return CANDIDATES
    chosen = json.loads((OUT / "score_dev.json").read_text())["chosen"]
    if chosen:
        return [chosen]
    # Decision 18 (JC, 2026-10-13): none passed; arm B on test runs once with the candidate closest to the trust
    # gate (fewest confidently wrong on practice), labeled "failed the practice screen".
    return ["xiaomi/mimo-v2.6-pro"]


def rid_of(qid, text):
    return "r-" + hashlib.sha256(f"{qid}|{normalize(text)}".encode()).hexdigest()[:16]


def arm_of(split, model=None):
    return f"{ARM[split]}:{slug(model)}" if model else ARM[split]


def job_name(kind, split, model=None):
    return f"b2-{split}-{kind}" + (f"-{slug(model)}" if model else "")


# ------------------------------------------------------------------ result readers (batch first, API fallback)
def records(path):
    by = defaultdict(list)
    if path.exists():
        for r in read_jsonl(path):
            by[r["key"]].append(r)
    return by


def state(recs):
    for r in recs:
        if r["ok"]:
            return r
    return "failed" if len(recs) >= M.ATTEMPTS else None


def results(job, path):
    """key -> {'ok': True, text, parsed, usage, provider} | {'ok': False}. Pending items are absent."""
    out = {}
    if (BT.BDIR / f"{job}.json").exists():
        for k, it in BT.load(job)["items"].items():
            if it["status"] == "ok":
                out[k] = {"ok": True, "text": it["text"], "parsed": it.get("parsed"), "usage": it.get("usage") or {},
                          "provider": it.get("provider"), "route": "batch"}
            elif it["status"] == "failed":
                out[k] = {"ok": False, "route": "batch"}
    for k, recs in records(path).items():
        s = state(recs)
        if s == "failed":
            out[k] = {"ok": False, "route": "api"}
        elif s:
            out[k] = {"ok": True, "text": s["text"], "parsed": s["parsed"], "provider": s["provider"], "route": "api",
                      "usage": {"completion_tokens": s["completion_tokens"]}}
    return out


def review_path(model, split):
    return OUT / split / f"reviews_{slug(model)}.jsonl"


def handoff_path(model, split):
    return OUT / split / f"handoffs_{slug(model)}.jsonl"


def grade_path(role, split):
    return OUT / split / f"grades_{role}.jsonl"


def verdicts(model, split):
    return {int(k): ({"ok": True, **v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in results(job_name("review", split, model), review_path(model, split)).items()}


def handoff_results(model, split):
    return results(job_name("handoff", split, model), handoff_path(model, split))


def grade_state(role, split):
    return {k: ({"ok": True, "grade": v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in results(job_name(role, split), grade_path(role, split)).items()}


# ------------------------------------------------------------------ prompts
def parse_review(text):
    out = llm.parse_json(text)
    s = out.get("safe")
    if isinstance(s, str) and s.strip().lower() in ("true", "false"):
        s = s.strip().lower() == "true"
    if not isinstance(s, bool):
        raise ValueError("no readable safe/unsafe verdict")
    return {"safe": s, "problem": str(out.get("problem") or "")}


def review_messages(split):
    c = ctx()
    return {str(q): [{"role": "user", "content": REVIEW_PROMPT.format(
        question=customer_message(c["Q"][q]), passages=format_passages([c["chunks"][i] for i in a["passages"]]),
        reply=a["draft"])}] for q, a in c["v4"][split].items()}


def handoff_keys(model, split):
    v4, vd = ctx()["v4"][split], verdicts(model, split)
    return [str(q) for q, v in vd.items() if v["ok"] and not v["safe"] and v4[q]["review_safe"]]


def handoff_messages(model, split):
    c, vd = ctx(), verdicts(model, split)
    return {k: [{"role": "user", "content": HANDOFF_PROMPT.format(problem=vd[int(k)]["problem"],
                                                                  question=customer_message(c["Q"][int(k)]))}]
            for k in handoff_keys(model, split)}


# ------------------------------------------------------------------ final replies per reviewer
def finals(model, split):
    """qid -> dict(kind, text, author, passed), or None while pending. model='v4' gives arm A as stored."""
    v4 = ctx()["v4"][split]
    if model == "v4":
        return {q: {"kind": "passed" if a["review_safe"] else "reused_v4_handoff", "text": a["answer"], "author": MINI,
                    "passed": a["review_safe"]} for q, a in v4.items()}
    vd, ho = verdicts(model, split), handoff_results(model, split)
    out = {}
    for q, a in v4.items():
        v = vd.get(q)
        if v is None:
            out[q] = None
        elif not v["ok"]:
            out[q] = {"kind": "system_failure", "text": SAFE, "author": "JC", "passed": False}
        elif v["safe"]:
            out[q] = {"kind": "passed", "text": a["draft"], "author": MINI, "passed": True}
        elif not a["review_safe"]:
            out[q] = {"kind": "reused_v4_handoff", "text": a["answer"], "author": MINI, "passed": False}
        else:
            h = ho.get(str(q))
            out[q] = (None if h is None else
                      {"kind": "new_handoff", "text": h["text"].strip(), "author": MINI, "passed": False} if h["ok"] else
                      {"kind": "handoff_failure", "text": SAFE, "author": "JC", "passed": False})
    return out


def finals_complete(split):
    return all(f is not None for m in cands(split) for f in finals(m, split).values())


# ------------------------------------------------------------------ grading replies the phase-1 re-grade never saw
def items(split):
    """rid -> (reply, item text). Same item format as phase 1 (reference packet + the bot's passages + reply)."""
    old = set(R.load()[0])
    c, ev = ctx(), R.final_evidence()
    new = {}
    for m in cands(split):
        for q, f in finals(m, split).items():
            if f is None:
                continue
            rid = rid_of(q, f["text"])
            if rid not in old and rid not in new:
                new[rid] = {"rid": rid, "qid": q, "text": f["text"], "author": f["author"],
                            "passages": c["v4"][split][q]["passages"]}
    return {rid: (r, render_item(c["Q"][r["qid"]],
                                 packet_v2(c["Q"][r["qid"]], [c["chunks"][x] for x in ev.get(r["qid"], []) if x in c["chunks"]]),
                                 [c["chunks"][x] for x in r["passages"]], r["text"])) for rid, r in new.items()}


def needs_tiebreak(split, its):
    labs, a, b = ctx()["labs"], grade_state("grader1", split), grade_state("grader2", split)
    return [rid for rid, (r, _t) in its.items() if rid in a and rid in b and
            R.settle_reply(rid, labs[r["qid"]]["side"] == "answerable", a[rid], b[rid], None)["status"] == "needs_tiebreak"]


def settled_new(split):
    labs, its = ctx()["labs"], items(split)
    a, b, t = grade_state("grader1", split), grade_state("grader2", split), grade_state("tiebreaker", split)
    out = {}
    for rid, (r, _t) in its.items():
        if rid not in a or rid not in b:
            continue
        ans = labs[r["qid"]]["side"] == "answerable"
        s = R.settle_reply(rid, ans, a[rid], b[rid], None)
        if s["status"] == "needs_tiebreak" and rid in t:
            s = R.settle_reply(rid, ans, a[rid], b[rid], t[rid])
        out[rid] = s
    return out


# ------------------------------------------------------------------ batch submission and polling
def submit(kind, split, model=None):
    job = job_name(kind, split, model)
    if (BT.BDIR / f"{job}.refused.json").exists():
        raise SystemExit(f"{job}: host refused batch earlier; use the api command")
    if kind == "review":
        msgs = review_messages(split)
        BT.create_job(job, model, "reviewer_B", msgs, phase=PHASE[split], split=split, arm=arm_of(split, model),
                      authors={k: MINI for k in msgs}, graders=[G1, G2, TBM])
    elif kind == "handoff":
        msgs = handoff_messages(model, split)
        if not msgs:
            print(f"{job}: no new handoffs needed"); return
        BT.create_job(job, MINI, "handoff", msgs, phase=PHASE[split], split=split, arm=arm_of(split, model), json_mode=False)
    elif kind in ("grader1", "grader2"):
        if not finals_complete(split):
            raise SystemExit("finals still pending: grade only once every reviewer's finals are in")
        its = items(split)
        if not its:
            print(f"{job}: nothing new to grade"); return
        (OUT / split).mkdir(parents=True, exist_ok=True)
        (OUT / split / "items_hash.json").write_text(json.dumps({rid: item_hash(t) for rid, (_r, t) in its.items()}))
        BT.create_job(job, GRADER_MODELS[kind], kind, {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}]
                                                       for rid, (_r, t) in its.items()},
                      phase=PHASE[split], split=split, arm=arm_of(split), authors={rid: r["author"] for rid, (r, _t) in its.items()})
    try:
        st = BT.submit(job)
        print(job, "submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])
    except RuntimeError as e:
        p = BT.BDIR / f"{job}.json"
        p.rename(BT.BDIR / f"{job}.refused.json")
        print(f"{job}: BATCH REFUSED, nothing billed -> API fallback. {str(e)[:300]}")


PARSERS = {"review": parse_review, "grader1": parse_grade, "grader2": parse_grade, "handoff": None}


def poll(split):
    for p in sorted(BT.BDIR.glob(f"b2-{split}-*.json")):
        if p.name.endswith(".refused.json"):
            continue
        job = p.stem
        kind = job.split("-")[2]
        info = BT.poll(job, parse=PARSERS[kind])
        st = BT.load(job)
        if any(it["status"] == "pending" for it in st["items"].values()):
            BT.submit(job); info = BT.poll(job, parse=PARSERS[kind])
        print(info)


# ------------------------------------------------------------------ API fallback chunks
def one_call(model, messages, *, role, author, split, arm, item, attempt, json_mode=False, parse=None, phase=None):
    r = llm.call(model, messages, role=role, author=author, graders=[G1, G2, TBM], arm=arm, phase=phase or PHASE[split],
                 split=split, item=item, json_mode=json_mode, parse=parse, attempts=1, timeout=ATTEMPT_TIMEOUT)
    u = r.get("usage") or {}
    return {"key": str(item), "model": model, "attempt": attempt, "ok": r["ok"], "failures": r["failures"],
            "cost": r["cost"], "provider": r.get("provider"), "seconds": r["seconds"], "finish": r.get("finish"),
            "completion_tokens": u.get("completion_tokens"), "reasoning_tokens": r.get("reasoning_tokens"),
            "text": r["text"], "parsed": r["parsed"]}


def run_chunk(keys, fn, path, workers=16, window=45):
    have = records(path)
    todo = [k for k in keys if state(have.get(k, [])) is None]
    t0, n = time.time(), 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(workers) as pool, open(path, "a") as f:
        futs, it = {}, iter(todo)

        def go():
            if time.time() - t0 <= window:
                k = next(it, None)
                if k is not None:
                    futs[pool.submit(fn, k, len(have.get(k, [])) + 1)] = k
        for _ in range(workers):
            go()
        while futs:
            done = next(as_completed(list(futs)))
            k = futs.pop(done)
            try:
                f.write(json.dumps(done.result(), ensure_ascii=False) + "\n"); f.flush(); n += 1
            except Exception as e:  # our own bug, not a model failure: not counted as an attempt
                print("CODE ERROR", k, str(e)[:300])
            go()
    have = records(path)
    left = sum(state(have.get(k, [])) is None for k in keys)
    failed = sum(state(have.get(k, [])) == "failed" for k in keys)
    print(f"{path.relative_to(ROOT)}: +{n} attempts in {time.time() - t0:.0f}s | {len(keys) - left - failed} done, "
          f"{failed} failed after 3, {left} left")


def api(kind, split, model=None, window=2):
    total = spend(split) + (spend_smoke() if split == "dev" else 0)
    if split in CEILING and total >= CEILING[split]:
        raise SystemExit(f"STOP: phase spend ${total:.2f} has reached the ${CEILING[split]:.2f} ceiling")
    if kind == "review":
        msgs = review_messages(split)
        run_chunk(list(msgs), lambda k, n: one_call(model, msgs[k], role="reviewer_B", author=MINI, split=split,
                                                     arm=arm_of(split, model), item=k, attempt=n, json_mode=True,
                                                     parse=parse_review), review_path(model, split), workers=48, window=window)
    elif kind == "handoff":
        msgs = handoff_messages(model, split)
        run_chunk(list(msgs), lambda k, n: one_call(MINI, msgs[k], role="handoff", author=None, split=split,
                                                     arm=arm_of(split, model), item=k, attempt=n), handoff_path(model, split),
                  window=window)
    elif kind == "tiebreaker":
        its = items(split)
        run_chunk(needs_tiebreak(split, its), lambda k, n: one_call(
            TBM, [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role="tiebreaker",
            author=its[k][0]["author"], split=split, arm=arm_of(split), item=k, attempt=n, json_mode=True, parse=parse_grade),
            grade_path("tiebreaker", split), workers=20, window=window)


# ------------------------------------------------------------------ section 9 scoring
def spend(split, arm=None, role=None):
    tot = 0.0
    for line in open(llm.LEDGER):
        r = json.loads(line)
        if r.get("phase") == PHASE[split] and (arm is None or r.get("arm") == arm) and (role is None or r.get("role") == role):
            tot += r.get("cost") or 0
    return tot


def spend_smoke():
    return sum(json.loads(l).get("cost") or 0 for l in open(llm.LEDGER) if '"2-smoke"' in l)


def score_split(split):
    c = ctx(); labs = c["labs"]
    old, _t, _k = R.score_all()
    new = settled_new(split)
    settled = {**old, **new}
    answerable = sum(labs[q]["side"] == "answerable" for q in c["v4"][split])
    rows = {}
    for m in ["v4"] + cands(split):
        fin = finals(m, split)
        cnt, kinds, let, blocked, pending, unresolved = Counter(), Counter(), Counter(), Counter(), 0, 0
        for q, f in fin.items():
            s = settled.get(rid_of(q, f["text"])) if f else None
            if not s or not s.get("outcome"):
                pending += 1; continue
            cnt[s["outcome"]] += 1; kinds[f["kind"]] += 1
            unresolved += s["status"] == "unresolved"
            d = settled[rid_of(q, c["v4"][split][q]["draft"])]["outcome"]
            (let if f["passed"] else blocked)[d] += 1
        n = len(fin)
        lo, hi = exact_range(cnt["confidently_wrong"], n)
        row = {"n": n, "pending": pending, **{k: cnt[k] for k in ORDER}, "unresolved": unresolved, "kinds": dict(kinds),
               "final_failure_rate": round((kinds["system_failure"] + kinds["handoff_failure"]) / n, 3),
               "unnecessary_per_100_answerable": round(100 * cnt["unnecessary_handoff"] / answerable, 1),
               "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)],
               "drafts_let_through": dict(let), "drafts_blocked": dict(blocked)}
        if m != "v4":
            res = results(job_name("review", split, m), review_path(m, split))
            toks = [v["usage"].get("completion_tokens") or 0 for v in res.values() if v["ok"]]
            cost = spend(split, arm=arm_of(split, m))
            row.update(cost_usd=round(cost, 4), cents_per_question=round(100 * cost / n, 3),
                       longest_reply_tokens=max(toks or [0]), routes=dict(Counter(v["route"] for v in res.values())),
                       hosts=dict(Counter(v.get("provider") for v in res.values() if v["ok"])),
                       attempt_failures=sum(1 for line in open(llm.LEDGER) if (lambda r: r.get("phase") == PHASE[split]
                                             and r.get("arm") == arm_of(split, m) and r.get("role") == "reviewer_B"
                                             and not r.get("ok"))(json.loads(line))))
        rows[m] = row
    report = {"split": split, "answerable": answerable, "arms": rows, "new_replies": len(items(split)),
              "new_settlement": dict(Counter(s["status"] for s in new.values())),
              "grading_cost_usd": round(spend(split, arm=arm_of(split)), 4)}
    if split == "dev":  # section 9: screen (<=1 confidently wrong, final failure rate <=5%), then rank
        ranked = []
        for m in CANDIDATES:
            r = rows[m]
            r["passes_screen"] = r["pending"] == 0 and r["confidently_wrong"] <= 1 and r["final_failure_rate"] <= 0.05
            if r["passes_screen"]:
                ranked.append(m)
        ranked.sort(key=lambda m: (-rows[m]["resolved"], rows[m]["unnecessary_handoff"], rows[m]["cents_per_question"],
                                   CANDIDATES.index(m)))
        report.update(ranked_passing=ranked, chosen=ranked[0] if ranked else None,
                      complete=all(rows[m]["pending"] == 0 for m in CANDIDATES))
    (OUT / f"score_{split}.json").write_text(json.dumps(report, indent=1))
    return report


def status(split):
    n = len(ctx()["v4"][split])
    for m in cands(split):
        vd = verdicts(m, split); ho = handoff_results(m, split)
        print(f"{slug(m):14} reviews {len(vd)}/{n} (failed {sum(not v['ok'] for v in vd.values())}, blocked "
              f"{sum(v['ok'] and not v['safe'] for v in vd.values())}) | new handoffs {len(ho)}/{len(handoff_keys(m, split))}"
              f" | ${spend(split, arm=arm_of(split, m)):.3f}")
    if finals_complete(split):
        its = items(split)
        for role in ("grader1", "grader2", "tiebreaker"):
            print(f"{role:10} graded {len(grade_state(role, split))}/{len(its) if role != 'tiebreaker' else len(needs_tiebreak(split, its))}")
    print(f"phase {PHASE[split]} spend so far: ${spend(split):.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); ap.add_argument("--window", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "submit":
        kind = a.args[0]
        if kind in ("review", "handoff"):
            submit(kind, a.args[2], a.args[1])
        else:
            submit(kind, a.args[1])
    elif a.cmd == "poll":
        poll(a.args[0])
    elif a.cmd == "api":
        kind = a.args[0]
        api(kind, a.args[-1], a.args[1] if kind in ("review", "handoff") else None, a.window)
    elif a.cmd == "status":
        status(a.args[0])
    elif a.cmd == "score":
        print(json.dumps(score_split(a.args[0]), indent=1))
