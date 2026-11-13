"""Run labels v2 for the 140 practice and test questions (TEST-PLAN-v3 section 5).

  python3 -m audit.labelrun api labeler2 <model>     # labeler 2 over the API (resumable, time-boxed)
  python3 -m audit.labelrun plan-a <model>           # labeler 1: export turn A for JC's terminal
  python3 -m audit.labelrun plan-b                   # ingest turn A, run the searches, export turn B
  python3 -m audit.labelrun plan-in                  # ingest turn B -> labels/labeler1.jsonl
  python3 -m audit.labelrun tiebreak <model>         # blind tie-breaker where needed
  python3 -m audit.labelrun settle                   # settlement, JC's sheet, final labels, kappa
"""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor

from .docs_index import Docs
from .labels2 import (CATS, GUIDE, OUT, Searcher, codes, label_api, make_parse_b, parse_a, questions, settle, side,
                      turn_a_user, turn_b_user)
from .common import read_jsonl
from .planroute import export as plan_export, ingest
from .stats import cohen_kappa

CC = {"anthropic/claude-opus-5.5": "claude-opus-5-5", "anthropic/claude-sonnet-5.5": "claude-sonnet-5-5"}


def path(role):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / f"{role}.jsonl"


def load(role):
    p = path(role)
    return {r["id"]: r for r in read_jsonl(p)} if p.exists() else {}


def run_api(role, model, ids=None, max_seconds=110, workers=6):
    from .jobs import run_jobs
    s = Searcher(Docs())
    done = set(load(role))  # a failed label counts as a disagreement (section 8); never re-run
    todo = [(q["id"], q) for q in questions() if q["id"] not in done and (ids is None or q["id"] in ids)]
    return run_jobs(todo, lambda k, q: label_api(model, q, s, role="labeler" if role != "label_tb" else "label_tb"),
                    path(role), workers=workers, max_seconds=max_seconds)


def plan_a(model):
    items = [(f"q{q['id']}", turn_a_user(q)) for q in questions()]
    return plan_export("labels1-a", GUIDE, items, CC[model], effort="high")


def plan_b():
    s = Searcher(Docs())
    A = ingest("labels1-a", "r1")
    Q = {f"q{q['id']}": q for q in questions()}
    items, state = [], {}
    for iid, rec in A.items():
        try:
            a = parse_a(rec["text"]) if rec["ok"] else None
        except ValueError:
            a = None
        if a is None:
            state[iid] = {"ok": False, "failure": "turn A unusable"}; continue
        q = Q[iid]; searches = s.run(q, a)
        state[iid] = {"ok": True, "turn_a": a, "searches": searches, "models": rec["models"]}
        items.append((iid, turn_b_user(q, a, searches, s.by_id)))
    (OUT / "labeler1_state.json").write_text(json.dumps(state))
    d = plan_export("labels1-b", GUIDE, items, json.loads((OUT.parent / "plan/labels1-a/batch.json").read_text())["model"], effort="high")
    print("turn A usable:", sum(v["ok"] for v in state.values()), "of", len(Q), "->", d)


def plan_in():
    state = json.loads((OUT / "labeler1_state.json").read_text())
    B = ingest("labels1-b", "r1")
    rows = []
    for iid, st in state.items():
        qid = int(iid[1:])
        rec = {"id": qid, "model": "anthropic/claude-opus-5.5", "role": "labeler1", "route": "plan", "ok": False}
        if st["ok"] and iid in B and B[iid]["ok"]:
            try:
                b = make_parse_b(codes(st["searches"]))(B[iid]["text"])
                rec.update(ok=True, turn_a=st["turn_a"], searches=st["searches"], turn_b=b, category=b["category"],
                           evidence_chunks=b["evidence_chunks"], reference_doubt=b["reference_doubt"], models=B[iid]["models"],
                           api_equiv_cost=B[iid]["api_equiv_cost"])
            except ValueError as e:
                rec["failure"] = f"turn B unparseable: {e}"
        else:
            rec["failure"] = "turn A or B missing"
        rows.append(rec)
    path("labeler1").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print("labeler 1 ok:", sum(r["ok"] for r in rows), "of", len(rows))


def needing_tb():
    L1, L2 = load("labeler1"), load("labeler2")
    return {q["id"] for q in questions() if settle(L1.get(q["id"]), L2.get(q["id"]))["needs_tb"]}


def settle_all(jc=None):
    L1, L2, TB = load("labeler1"), load("labeler2"), load("label_tb")
    jc = jc or {}
    final, sheet = [], []
    for q in questions():
        k = q["id"]
        s = settle(L1.get(k), L2.get(k), TB.get(k), jc.get(str(k)))
        ev = []
        for L in (L1.get(k), L2.get(k)):
            if L and L.get("ok"):
                ev += [c for c in L.get("evidence_chunks", []) if c not in ev]
        row = {"id": k, "split": q["split"], **s, "labels": {n: (L.get(k) or {}).get("category") for n, L in (("l1", L1), ("l2", L2), ("tb", TB))},
               "evidence_chunks": ev}
        final.append(row)
        if s["needs_jc"]:
            sheet.append(k)
    c1 = [(L1.get(q["id"]) or {}).get("category") for q in questions()]
    c2 = [(L2.get(q["id"]) or {}).get("category") for q in questions()]
    kappa = {"category": cohen_kappa(c1, c2),
             "side": cohen_kappa([side(c) if c else None for c in c1], [side(c) if c else None for c in c2])}
    return final, sheet, kappa


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "api":
        run_api(sys.argv[2], sys.argv[3])
    elif cmd == "plan-a":
        print(plan_a(sys.argv[2]))
    elif cmd == "plan-b":
        plan_b()
    elif cmd == "plan-in":
        plan_in()
    elif cmd == "tiebreak":
        need = needing_tb(); print("tie-breaks needed:", len(need))
        run_api("label_tb", sys.argv[2], ids=need)
    elif cmd == "final":
        jc = {}
        for f in (OUT / "jc_readings").glob("*.json"):
            r = json.loads(f.read_text()); r = r.get("data", r)
            jc[str(r["item"]).lstrip("q")] = r
        final, sheet, kappa = settle_all(jc)
        missing = [r["id"] for r in final if r["final"] is None]
        (OUT / "final.jsonl").write_text("".join(json.dumps(r) + "\n" for r in final))
        (OUT / "kappa.json").write_text(json.dumps(kappa, indent=1))
        print("final labels:", len(final) - len(missing), "of", len(final), "| unsettled:", missing)
    else:
        final, sheet, kappa = settle_all()
        from collections import Counter
        print("settled:", sum(r["final"] is not None for r in final), "| waiting for tie-breaker:", sum(r["needs_tb"] and r["final"] is None and not r["needs_jc"] for r in final),
              "| for JC:", len(sheet), "| kappa:", json.dumps(kappa))


def jc_sheet_items():
    """Items for JC's reading page: no labels or categories shown, only the fix and the closest passages."""
    from .bot import customer_message
    from .docs_index import Docs
    docs = Docs(); by_id = {c["id"]: c for c in docs.chunks}
    Q = {q["id"]: q for q in questions()}
    L = {n: load(n) for n in ("labeler1", "labeler2", "label_tb")}
    final, sheet, _ = settle_all()
    items = []
    for qid in sheet:
        recs = [L[n].get(qid) for n in L if L[n].get(qid, {}).get("ok")]
        keys = []
        for r in recs:
            k = (r.get("turn_b") or {}).get("key_step") or (r.get("turn_a") or {}).get("key_step")
            if k and k not in keys:
                keys.append(k)
        ev = []
        for r in recs:
            ev += [c for c in r.get("evidence_chunks", []) if c not in ev]
        source = "The docs passages the labelers cited"
        if not ev:
            for r in recs:
                s2 = next((s for s in r.get("searches", []) if s["name"] == "S2"), None)
                ev += [c for c in (s2["chunks"][:3] if s2 else []) if c not in ev]
            source = "No labeler cited a passage. Top docs search results for the fix"
        q = Q[qid]
        items.append({"id": f"q{qid}", "title": q["title"], "question": customer_message(q)[:8000],
                      "accepted": q["accepted_answer"][:6000], "key_steps": keys[:3], "passages_source": source,
                      "passages": [{"title": by_id[c]["page_title"], "heading": by_id[c]["heading"], "url": by_id[c]["url"],
                                    "text": by_id[c]["text"]} for c in ev[:5] if c in by_id]})
    return items
