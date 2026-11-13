"""Arm D, drafts only (TEST-PLAN-v3 section 3; decision 18, 2026-10-13): GPT-6.1 Sol drafts with v4's exact drafting
prompt (v3 system prompt, private <triage> block) and the exact passages v4 retrieved for each question. Only the
drafting model changes. No reviewer pass (decision 18): the drafts themselves are graded blind, like v4's pre-review
drafts in phase 1. A draft with no usable reply after 3 attempts gives JC's fixed safe handoff (system_failure).

Route: OpenRouter batch on Sol's pinned host (openai). Practice first (section 13: measure real cost before test).

  python3 -m audit.armd submit draft <split>        # batch: Sol drafts (dev = practice, test)
  python3 -m audit.armd submit grader1|grader2 <split>
  python3 -m audit.armd poll <split>
  python3 -m audit.armd tiebreak <split>            # API chunk (Muse Spark has no batch route)
  python3 -m audit.armd status <split> | score <split>
"""
import argparse, json
from collections import Counter

from . import batch as BT, build2 as B2, regrade as R
from .bot import CONFIGS, customer_message, format_passages, split_triage
from .grade3 import RUBRIC, item_hash, packet_v2, parse_grade, render_item
from .stats import exact_range

SOL = "openai/gpt-6.1-sol"
OUT = B2.OUT.parent / "armD"
PHASE = {"dev": "3-armD-practice", "test": "3-armD"}
ARM = "D"
CEILING = {"dev": 2.00, "test": 4.50}  # estimates $1.35 and $3.10, x1.3 headroom (section 13), rounded up


def job(kind, split):
    return f"d-{split}-{kind}"


def parse_draft(text):
    triage, reply = split_triage(text)
    if not reply.strip():
        raise ValueError("empty reply after triage")
    return {"triage": triage, "reply": reply.strip()}


def draft_messages(split):
    c = B2.ctx()
    sysp = CONFIGS["v4"]["system"]
    return {str(q): [{"role": "system", "content": sysp},
                     {"role": "user", "content": f"Documentation excerpts:\n\n{format_passages([c['chunks'][i] for i in a['passages']])}"
                                                 f"\n\n---\nCustomer question:\n{customer_message(c['Q'][q])}"}]
            for q, a in c["v4"][split].items()}


def drafts(split):
    """qid -> dict(kind, text, author) or None while pending."""
    res = B2.results(job("draft", split), OUT / split / "drafts_api.jsonl")
    out = {}
    for q in B2.ctx()["v4"][split]:
        v = res.get(str(q))
        out[q] = (None if v is None else
                  {"kind": "draft", "text": v["parsed"]["reply"], "author": SOL} if v["ok"] else
                  {"kind": "system_failure", "text": B2.SAFE, "author": "JC"})
    return out


def items(split):
    old = set(R.load()[0])
    c, ev = B2.ctx(), R.final_evidence()
    out = {}
    for q, f in drafts(split).items():
        if f is None:
            continue
        rid = B2.rid_of(q, f["text"])
        if rid in old or rid in out:
            continue
        Q = c["Q"][q]
        out[rid] = ({"rid": rid, "qid": q, "author": f["author"]},
                    render_item(Q, packet_v2(Q, [c["chunks"][x] for x in ev.get(q, []) if x in c["chunks"]]),
                                [c["chunks"][x] for x in c["v4"][split][q]["passages"]], f["text"]))
    return out


def gstate(role, split):
    return {k: ({"ok": True, "grade": v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in B2.results(job(role, split), OUT / split / f"grades_{role}.jsonl").items()}


def spend(split):
    return sum(json.loads(l).get("cost") or 0 for l in open(B2.llm.LEDGER) if f'"{PHASE[split]}"' in l)


def guard(split, add=0.0):
    if spend(split) + add > CEILING[split]:
        raise SystemExit(f"STOP: {PHASE[split]} spend ${spend(split):.2f} + ${add:.2f} would pass the ${CEILING[split]:.2f} ceiling")


def submit(kind, split):
    j = job(kind, split)
    if kind == "draft":
        guard(split)
        BT.create_job(j, SOL, "drafter_D", draft_messages(split), phase=PHASE[split], split=split, arm=ARM, json_mode=False)
    else:
        if any(f is None for f in drafts(split).values()):
            raise SystemExit("drafts still pending")
        guard(split)
        its = items(split)
        (OUT / split).mkdir(parents=True, exist_ok=True)
        (OUT / split / "items_hash.json").write_text(json.dumps({rid: item_hash(t) for rid, (_r, t) in its.items()}))
        BT.create_job(j, B2.GRADER_MODELS[kind], kind,
                      {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}] for rid, (_r, t) in its.items()},
                      phase=PHASE[split], split=split, arm=ARM, authors={rid: r["author"] for rid, (r, _t) in its.items()})
    st = BT.submit(j)
    print(j, "submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])


def poll(split):
    for p in sorted(BT.BDIR.glob(f"d-{split}-*.json")):
        kind = p.stem.split("-")[2]
        parse = parse_draft if kind == "draft" else parse_grade
        info = BT.poll(p.stem, parse=parse)
        if any(it["status"] == "pending" for it in BT.load(p.stem)["items"].values()):
            BT.submit(p.stem); info = BT.poll(p.stem, parse=parse)
        print(info)


def needs_tb(split, its):
    labs, a, b = B2.ctx()["labs"], gstate("grader1", split), gstate("grader2", split)
    return [rid for rid, (r, _t) in its.items() if rid in a and rid in b and
            R.settle_reply(rid, labs[r["qid"]]["side"] == "answerable", a[rid], b[rid], None)["status"] == "needs_tiebreak"]


def tiebreak(split):
    guard(split)
    its = items(split)
    B2.run_chunk(needs_tb(split, its), lambda k, n: B2.one_call(
        B2.TBM, [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role="tiebreaker",
        author=its[k][0]["author"], split=split, arm=ARM, item=k, attempt=n, json_mode=True, parse=parse_grade,
        phase=PHASE[split]),
        OUT / split / "grades_tiebreaker.jsonl", workers=48, window=2)


def settle(split):
    labs, its = B2.ctx()["labs"], items(split)
    a, b, t = gstate("grader1", split), gstate("grader2", split), gstate("tiebreaker", split)
    out = {}
    for rid, (r, _t) in its.items():
        if rid in a and rid in b:
            ans = labs[r["qid"]]["side"] == "answerable"
            s = R.settle_reply(rid, ans, a[rid], b[rid], None)
            if s["status"] == "needs_tiebreak" and rid in t:
                s = R.settle_reply(rid, ans, a[rid], b[rid], t[rid])
            out[rid] = s
    return out


def score(split):
    c = B2.ctx(); labs = c["labs"]
    old, _t, _k = R.score_all(); new = settle(split); settled = {**old, **new}
    answerable = sum(labs[q]["side"] == "answerable" for q in c["v4"][split])
    rows = {}
    for name, fin in (("v4_drafts", {q: {"kind": "draft", "text": a["draft"]} for q, a in c["v4"][split].items()}),
                      ("D_drafts", drafts(split))):
        cnt, kinds, pend, unres = Counter(), Counter(), 0, 0
        for q, f in fin.items():
            s = settled.get(B2.rid_of(q, f["text"])) if f else None
            if not s or not s.get("outcome"):
                pend += 1; continue
            cnt[s["outcome"]] += 1; kinds[f["kind"]] += 1; unres += s["status"] == "unresolved"
        n = len(fin); lo, hi = exact_range(cnt["confidently_wrong"], n)
        rows[name] = {"n": n, "pending": pend, **{k: cnt[k] for k in B2.ORDER}, "unresolved": unres, "kinds": dict(kinds),
                      "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)],
                      "unnecessary_per_100_answerable": round(100 * cnt["unnecessary_handoff"] / answerable, 1)}
    rows["D_drafts"]["spend_usd"] = round(spend(split), 4)
    rep = {"split": split, "answerable": answerable, "arms": rows, "settlement": dict(Counter(s["status"] for s in new.values()))}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"score_{split}.json").write_text(json.dumps(rep, indent=1))
    return rep


def status(split):
    d = drafts(split)
    print(f"drafts {sum(f is not None for f in d.values())}/{len(d)} (system failures {sum(1 for f in d.values() if f and f['kind'] == 'system_failure')})")
    if all(d.values()):
        its = items(split)
        for role in ("grader1", "grader2"):
            print(role, f"{len(gstate(role, split))}/{len(its)}")
        print("tie-breaks", f"{len(gstate('tiebreaker', split))}/{len(needs_tb(split, its))}")
    print(f"{PHASE[split]} spend ${spend(split):.3f} (ceiling ${CEILING[split]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); a = ap.parse_args()
    if a.cmd == "submit":
        submit(a.args[0], a.args[1])
    elif a.cmd == "poll":
        poll(a.args[0])
    elif a.cmd == "tiebreak":
        tiebreak(a.args[0])
    elif a.cmd == "status":
        status(a.args[0])
    elif a.cmd == "score":
        print(json.dumps(score(a.args[0]), indent=1))
