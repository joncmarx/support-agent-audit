"""Arms F0, F and DF, drafts only (TEST-PLAN-v3 sections 3-4; decisions 18 and 19).

  F0  gpt-5.4-mini   prompts/F0F_* , v4's stored doc passages, community section empty ("(none found)")
  F   gpt-5.4-mini   prompts/F0F_* , v4's stored doc passages, community section from audit/community.py
  DF  GPT-6.1 Sol    as F (decision 19: added after arm D's results; test only if it passes the practice screen)

No reviewer (decision 18). A draft with no usable reply after 3 attempts gives JC's fixed safe handoff (system_failure).
Grading is identical to every other arm (grade3 render_item: graders see the docs passages the agent had; the
community section is not shown to graders, so community-sourced claims count as true_unsupported in the 'support'
diagnostic only; correctness is judged against the reference packet).
Answerable (section 5): F0 docs-only; F and DF also count a question answerable when the community-availability
label says yes and it isn't account_access.
Routes: mini on the API at its pinned host (no batch route there); Sol and the graders in batch mode; Muse
tie-breaks on the API.

  python3 -m audit.armf draft <arm> <split>                 # F0/F: API chunk (resumable); DF: batch submit
  python3 -m audit.armf submit grader1|grader2 <arm> <split>
  python3 -m audit.armf poll <arm> <split>
  python3 -m audit.armf tiebreak <arm> <split>
  python3 -m audit.armf status <arm> <split> | score <arm> <split>
"""
import argparse, json
from collections import Counter

from . import batch as BT, build2 as B2, regrade as R
from .bot import customer_message, format_passages, split_triage
from .common import ROOT, read_jsonl
from .grade3 import RUBRIC, item_hash, packet_v2, parse_grade, render_item
from .severity import severity
from .stats import exact_range

MINI, SOL = "openai/gpt-5.4-mini", "openai/gpt-6.1-sol"
ARMS = {"F0": dict(model=MINI, role="drafter", community=False),
        "F": dict(model=MINI, role="drafter", community=True),
        "DF": dict(model=SOL, role="drafter_D", community=True),
        # G (section 9): the chosen configuration A (v4 as built) with its handoff writer switched to prompts/G_HANDOFF.md.
        # Reuses v4's drafts and review decisions; only blocked replies are rewritten (by v4's own model) and re-graded.
        "G": dict(model=MINI, role="handoff", community=False)}
G_HANDOFF = (ROOT / "prompts/G_HANDOFF.md").read_text()
SYSTEM = (ROOT / "prompts/F0F_SYSTEM.md").read_text()
USER = (ROOT / "prompts/F0F_USER.md").read_text()
OUT = ROOT / "runs/v3plan/armF"
COMM = ROOT / "runs/v3plan/community"
# estimates x1.3 headroom (section 13), rounded up; decision 19 re-pricing
CEILING = {("F0", "dev"): 1.80, ("F", "dev"): 1.90, ("DF", "dev"): 2.00,
           ("G", "dev"): 1.40, ("G", "test"): 0.0,
           ("F0", "test"): 4.25,  # JC 2026-10-16: approved finishing F0 past $4.00 (2 tie-breaks)
            ("F", "test"): 4.25, ("DF", "test"): 4.50}


def phase(arm, split):
    if arm == "G":
        return "5-G-practice"
    return f"4-arm{arm}" + ("-practice" if split == "dev" else "")


def job(arm, kind, split):
    return f"{arm.lower()}-{split}-{kind}"


def path(arm, split, name):
    return OUT / arm / split / name


def parse_draft(text):
    triage, reply = split_triage(text)
    if not reply.strip():
        raise ValueError("empty reply after triage")
    return {"triage": triage, "reply": reply.strip()}


def community(split):
    return {str(r["id"]): r for r in read_jsonl(COMM / f"{split}.jsonl")}


def messages(arm, split):
    if arm == "G":
        c = B2.ctx()
        return {str(q): [{"role": "user", "content": G_HANDOFF.format(problem=a["review_problem"],
                                                                       question=customer_message(c["Q"][q]))}]
                for q, a in c["v4"][split].items() if not a["review_safe"]}
    c, cm = B2.ctx(), community(split)
    out = {}
    for q, a in c["v4"][split].items():
        sec = cm[str(q)]["community"] if ARMS[arm]["community"] else ""
        user = USER.format(passages=format_passages([c["chunks"][i] for i in a["passages"]]),
                           community=sec or "(none found)", question=customer_message(c["Q"][q]))
        out[str(q)] = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    return out


def drafts(arm, split):
    res = B2.results(job(arm, "draft", split), path(arm, split, "drafts_api.jsonl"))
    out = {}
    if arm == "G":
        for q, a in B2.ctx()["v4"][split].items():
            if a["review_safe"]:
                out[q] = {"kind": "passed", "text": a["answer"], "author": MINI}
                continue
            v = res.get(str(q))
            out[q] = (None if v is None else
                      {"kind": "g_handoff", "text": v["text"].strip(), "author": MINI} if v["ok"] else
                      {"kind": "handoff_failure", "text": B2.SAFE, "author": "JC"})
        return out
    for q in B2.ctx()["v4"][split]:
        v = res.get(str(q))
        out[q] = (None if v is None else
                  {"kind": "draft", "text": v["parsed"]["reply"], "author": ARMS[arm]["model"]} if v["ok"] else
                  {"kind": "system_failure", "text": B2.SAFE, "author": "JC"})
    return out


def spend(arm, split):
    ph = f'"{phase(arm, split)}"'
    return sum(json.loads(l).get("cost") or 0 for l in open(B2.llm.LEDGER) if ph in l)


def guard(arm, split, add=0.0):
    lim = CEILING[(arm, split)]
    if spend(arm, split) + add > lim:
        raise SystemExit(f"STOP: {phase(arm, split)} spend ${spend(arm, split):.2f} + ${add:.2f} passes the ${lim:.2f} ceiling")


def draft(arm, split):
    guard(arm, split)
    if arm == "DF" and split == "test":
        sc = OUT / "score_DF_dev.json"
        if not sc.exists() or json.loads(sc.read_text())["arm"]["confidently_wrong"] > 1:
            raise SystemExit("STOP: DF runs on test only if it passed the practice screen (decision 19)")
    msgs, spec = messages(arm, split), ARMS[arm]
    if spec["model"] == SOL:
        j = job(arm, "draft", split)
        BT.create_job(j, SOL, spec["role"], msgs, phase=phase(arm, split), split=split, arm=arm, json_mode=False)
        st = BT.submit(j)
        print(j, "submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])
        return
    B2.run_chunk(list(msgs), lambda k, n: B2.one_call(
        spec["model"], msgs[k], role=spec["role"], author=None, split=split, arm=arm, item=k, attempt=n,
        parse=None if arm == "G" else parse_draft, phase=phase(arm, split)), path(arm, split, "drafts_api.jsonl"),
        workers=48, window=2)


def answerable(arm, split):
    labs = B2.ctx()["labs"]
    ans = {q: labs[q]["side"] == "answerable" for q in B2.ctx()["v4"][split]}
    if ARMS[arm]["community"]:
        fin = {str(r["id"]): r for r in read_jsonl(COMM / "labels/final.jsonl")}
        for q in ans:
            r = fin.get(str(q))
            if r and r["available"] is None:
                raise SystemExit(f"community label for {q} is not settled")
            if r and r["available"]:
                ans[q] = True  # scope excludes account_access by construction
    return ans


def items(arm, split):
    old = set(R.load()[0])
    c, ev = B2.ctx(), R.final_evidence()
    out = {}
    for q, f in drafts(arm, split).items():
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


def gstate(arm, role, split):
    return {k: ({"ok": True, "grade": v["parsed"]} if v["ok"] else {"ok": False})
            for k, v in B2.results(job(arm, role, split), path(arm, split, f"grades_{role}.jsonl")).items()}


def submit(kind, arm, split):
    if any(f is None for f in drafts(arm, split).values()):
        raise SystemExit("drafts still pending")
    guard(arm, split)
    its = items(arm, split)
    path(arm, split, "x").parent.mkdir(parents=True, exist_ok=True)
    path(arm, split, "items_hash.json").write_text(json.dumps({rid: item_hash(t) for rid, (_r, t) in its.items()}))
    j = job(arm, kind, split)
    BT.create_job(j, B2.GRADER_MODELS[kind], kind,
                  {rid: [{"role": "system", "content": RUBRIC}, {"role": "user", "content": t}] for rid, (_r, t) in its.items()},
                  phase=phase(arm, split), split=split, arm=arm, authors={rid: r["author"] for rid, (r, _t) in its.items()})
    st = BT.submit(j)
    print(j, "submitted:", [(b["id"][-10:], b["n"], b["status"]) for b in st["batches"]])


def poll(arm, split):
    for p in sorted(BT.BDIR.glob(f"{arm.lower()}-{split}-*.json")):
        kind = p.stem.split("-")[2]
        parse = parse_draft if kind == "draft" else parse_grade
        info = BT.poll(p.stem, parse=parse)
        if any(it["status"] == "pending" for it in BT.load(p.stem)["items"].values()):
            BT.submit(p.stem); info = BT.poll(p.stem, parse=parse)
        print(info)


def needs_tb(arm, split, its):
    ans, a, b = answerable(arm, split), gstate(arm, "grader1", split), gstate(arm, "grader2", split)
    return [rid for rid, (r, _t) in its.items() if rid in a and rid in b and
            R.settle_reply(rid, ans[r["qid"]], a[rid], b[rid], None)["status"] == "needs_tiebreak"]


def tiebreak(arm, split):
    guard(arm, split)
    its = items(arm, split)
    B2.run_chunk(needs_tb(arm, split, its), lambda k, n: B2.one_call(
        B2.TBM, [{"role": "system", "content": RUBRIC}, {"role": "user", "content": its[k][1]}], role="tiebreaker",
        author=its[k][0]["author"], split=split, arm=arm, item=k, attempt=n, json_mode=True, parse=parse_grade,
        phase=phase(arm, split)), path(arm, split, "grades_tiebreaker.jsonl"), workers=48, window=2)


def score(arm, split):
    """Every reply is settled with this arm's answerable flag (an F reply that also appears in another arm is
    re-settled here, since the flag can differ). Grades are reused across arms when the reply text is identical."""
    c = B2.ctx(); ans = answerable(arm, split)
    a, b, t = gstate(arm, "grader1", split), gstate(arm, "grader2", split), gstate(arm, "tiebreaker", split)
    old_a, old_b, old_t = (R.grades(x) for x in ("grader1", "grader2", "tiebreaker"))  # phase-1 grades of identical texts
    cnt, kinds, pend, unres, settle_ct, sev = Counter(), Counter(), 0, 0, Counter(), Counter()
    for q, f in drafts(arm, split).items():
        if f is None:
            pend += 1; continue
        rid = B2.rid_of(q, f["text"])
        ga, gb, gt = a.get(rid) or old_a.get(rid), b.get(rid) or old_b.get(rid), t.get(rid) or old_t.get(rid)
        if not (ga and gb):
            pend += 1; continue
        s = R.settle_reply(rid, ans[q], ga, gb, None)
        if s["status"] == "needs_tiebreak":
            if not gt:
                pend += 1; continue
            s = R.settle_reply(rid, ans[q], ga, gb, gt)
        cnt[s["outcome"]] += 1; kinds[f["kind"]] += 1; unres += s["status"] == "unresolved"; settle_ct[s["status"]] += 1
        if s["outcome"] == "confidently_wrong":
            sev[severity(ga, gb, gt if s["status"] != "agree" else None)] += 1
    n = len(c["v4"][split]); lo, hi = exact_range(cnt["confidently_wrong"], n)
    na = sum(ans.values())
    rep = {"arm": {"n": n, "pending": pend, **{k: cnt[k] for k in B2.ORDER}, "unresolved": unres, "kinds": dict(kinds),
                   "trust_range_95_per_100": [round(lo * 100, 1), round(hi * 100, 1)], "answerable": na,
                   "unnecessary_per_100_answerable": round(100 * cnt["unnecessary_handoff"] / na, 1),
                   "spend_usd": round(spend(arm, split), 4)},
           "name": arm, "split": split, "settlement": dict(settle_ct), "severity_split": dict(sev),
           "screen_passed": (cnt["confidently_wrong"] <= 1 and not pend) if split == "dev" else None}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"score_{arm}_{split}.json").write_text(json.dumps(rep, indent=1))
    return rep


def status(arm, split):
    d = drafts(arm, split)
    print(f"{arm} {split}: drafts {sum(f is not None for f in d.values())}/{len(d)} "
          f"(system failures {sum(1 for f in d.values() if f and f['kind'] == 'system_failure')})")
    if all(d.values()):
        its = items(arm, split)
        for role in ("grader1", "grader2"):
            print(" ", role, f"{len(gstate(arm, role, split))}/{len(its)}")
        try:
            print("  tie-breaks", f"{len(gstate(arm, 'tiebreaker', split))}/{len(needs_tb(arm, split, its))}")
        except SystemExit as e:
            print("  tie-breaks: wait:", e)
    print(f"  {phase(arm, split)} spend ${spend(arm, split):.3f} (ceiling ${CEILING[(arm, split)]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); a = ap.parse_args()
    if a.cmd == "submit":
        submit(*a.args)
    elif a.cmd == "score":
        print(json.dumps(score(*a.args), indent=1))
    else:
        {"draft": draft, "poll": poll, "tiebreak": tiebreak, "status": status}[a.cmd](*a.args)
