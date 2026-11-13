"""Labels v2 through OpenRouter batch mode (decisions 12-13): labeler 1 = Sonnet 5.5, labeler 2 = Gemini 3.8
Flash, each in two turns with the three recorded searches in between; the tie-breaker (Muse Spark 1.3, no batch
endpoint) runs over the regular API.

  python3 -m audit.labelbatch submit-a        # turn A for both labelers
  python3 -m audit.labelbatch poll a|b        # collect (and resubmit failures, up to 3 attempts)
  python3 -m audit.labelbatch submit-b        # searches + turn B for both labelers
  python3 -m audit.labelbatch api-b <role>    # turn B for one labeler over the regular API instead (decision 15)
  python3 -m audit.labelbatch finish          # write labels/labeler1.jsonl and labels/labeler2.jsonl
"""
import json, sys

import numpy as np

from . import batch as B
from . import llm
from .bot import search_query
from .docs_index import Docs
from .labels2 import GUIDE, HOLDOUT, OUT, PHASE, Searcher, codes, make_parse_b, parse_a, questions, turn_a_user, turn_b_user

PFX = "hlabels" if HOLDOUT else "labels"
LABELERS = {"labeler1": "anthropic/claude-sonnet-5.5", "labeler2": "google/gemini-3.8-flash"}
if HOLDOUT:  # holdout (2026-10-16): labeler 2 runs both turns over the API (Google's batch host stalled in Build 1; decisions 15-16)
    LABELERS = {"labeler1": "anthropic/claude-sonnet-5.5"}


def submit_a():
    for role, model in LABELERS.items():
        items = {f"q{q['id']}": [{"role": "system", "content": GUIDE}, {"role": "user", "content": turn_a_user(q)}] for q in questions()}
        B.create_job(f"{PFX}-{role}-a", model, f"{role}_a", items, phase=PHASE)
        print(B.submit(f"{PFX}-{role}-a")["batches"][-1])


def poll(turn):
    for role in LABELERS:
        job = f"{PFX}-{role}-{turn}"
        if not (B.BDIR / f"{job}.json").exists():
            print(job, "not submitted yet"); continue
        if turn == "a":
            print(B.poll(job, parse=parse_a))
        else:
            state = json.loads((OUT / f"{role}_codes.json").read_text())
            # each item has its own passage codes; an unparseable reply counts as a failed attempt (section 8)
            print(B.poll(job, parse_item=lambda cid, text: make_parse_b(codes(state[cid]["searches"]))(text)))
        if any(it["status"] == "pending" for it in B.load(job)["items"].values()):
            B.submit(job)


class FastSearcher(Searcher):
    """Embeds all fix queries in one request, then searches offline."""
    def __init__(self, docs, vectors_by_query):
        super().__init__(docs)
        self.qv = vectors_by_query

    def hybrid(self, query, k=8, pool=30):
        kw = self.docs.keyword(query, pool)
        v = np.array(self.qv[query], dtype=np.float32); v /= np.linalg.norm(v)
        sims = self.docs.vectors @ v
        sem = [(self.docs.chunks[i], float(sims[i])) for i in np.argsort(-sims)[:pool]]
        scores = {}
        for results in (kw, sem):
            for rank, (c, _) in enumerate(results):
                scores[c["id"]] = scores.get(c["id"], 0) + 1 / (60 + rank)
        return [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])[:k]]


def submit_b():
    """Turn B for every labeler whose turn A has finished (all items ok or failed) and whose turn B isn't submitted."""
    docs = Docs()
    Q = {f"q{q['id']}": q for q in questions()}
    ready = []
    for role in LABELERS:
        st = B.load(f"{PFX}-{role}-a")
        if all(it["status"] in ("ok", "failed") for it in st["items"].values()) and not (B.BDIR / f"{PFX}-{role}-b.json").exists():
            ready.append(role)
    if not ready:
        print("no labeler is ready for turn B"); return
    turn_a = {role: {cid: it["parsed"] for cid, it in B.load(f"{PFX}-{role}-a")["items"].items() if it["status"] == "ok"} for role in ready}
    queries = sorted({a["fix_query"][:6000] for ta in turn_a.values() for a in ta.values()})
    vecs = {}
    for i in range(0, len(queries), 64):
        for q, v in zip(queries[i:i + 64], llm.embed_v3(queries[i:i + 64], phase=PHASE)):
            vecs[q] = v
    s = FastSearcher(docs, vecs)
    for role in ready:
        model = LABELERS[role]
        items, state = {}, {}
        for cid, a in turn_a[role].items():
            a["fix_query"] = a["fix_query"][:6000]
            searches = s.run(Q[cid], a)
            state[cid] = {"turn_a": a, "searches": searches}
            items[cid] = [{"role": "system", "content": GUIDE}, {"role": "user", "content": turn_b_user(Q[cid], a, searches, s.by_id)}]
        (OUT / f"{role}_codes.json").write_text(json.dumps(state))
        B.create_job(f"{PFX}-{role}-b", model, f"{role}_b", items, phase=PHASE)
        print(role, "turn B items:", len(items), "| turn A failures:", len(Q) - len(turn_a[role]))
        print(B.submit(f"{PFX}-{role}-b")["batches"][-1])


def _prepare_b(role):
    """The three recorded searches and the turn-B messages for one labeler, from its finished turn A.
    The searches are run once and cached in labels/<role>_codes.json, so a resumed run sends identical prompts."""
    docs = Docs()
    Q = {f"q{q['id']}": q for q in questions()}
    p = OUT / f"{role}_codes.json"
    if p.exists():
        state = json.loads(p.read_text())
        s = FastSearcher(docs, {})
    else:
        st = B.load(f"{PFX}-{role}-a")
        if not all(it["status"] in ("ok", "failed") for it in st["items"].values()):
            raise SystemExit(f"{role}: turn A is not finished")
        turn_a = {cid: it["parsed"] for cid, it in st["items"].items() if it["status"] == "ok"}
        queries = sorted({a["fix_query"][:6000] for a in turn_a.values()})
        vecs = {}
        for i in range(0, len(queries), 64):
            for q, v in zip(queries[i:i + 64], llm.embed_v3(queries[i:i + 64], phase=PHASE)):
                vecs[q] = v
        s = FastSearcher(docs, vecs)
        state = {}
        for cid, a in turn_a.items():
            a["fix_query"] = a["fix_query"][:6000]
            state[cid] = {"turn_a": a, "searches": s.run(Q[cid], a)}
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state))
    items = {cid: [{"role": "system", "content": GUIDE}, {"role": "user", "content": turn_b_user(Q[cid], v["turn_a"], v["searches"], s.by_id)}]
             for cid, v in state.items()}
    return items, state


def api_b(role, max_seconds=110, workers=8):
    """Turn B over the regular API (decision 15): same model, prompts, settings and caps as the batch route; the host is
    the model's API host from audit/models.py. Resumable and time-boxed; each item gets 3 attempts (section 8)."""
    from .jobs import run_jobs
    if (B.BDIR / f"{PFX}-{role}-b.json").exists():
        raise SystemExit(f"{role}: turn B was already submitted as a batch")
    items, state = _prepare_b(role)
    out = OUT / f"{role}_b_api.jsonl"
    done = {json.loads(l)["cid"] for l in out.open()} if out.exists() else set()
    model = LABELERS[role]

    def fn(cid, msgs):
        r = llm.call(model, msgs, role=f"{role}_b", phase=PHASE, item=cid, json_mode=True,
                     parse=make_parse_b(codes(state[cid]["searches"])))
        return {"cid": cid, **{k: r.get(k) for k in ("ok", "text", "attempts", "failures", "cost", "usage", "provider", "seconds")}}
    return run_jobs([(cid, m) for cid, m in items.items() if cid not in done], fn, out, workers=workers, max_seconds=max_seconds)


def _turn_b(role):
    """cid -> (status, text) for a labeler's turn B, from whichever route ran it."""
    if (B.BDIR / f"{PFX}-{role}-b.json").exists():
        return {cid: (it["status"], it.get("text")) for cid, it in B.load(f"{PFX}-{role}-b")["items"].items()}, "batch"
    out = OUT / f"{role}_b_api.jsonl"
    rows = {}
    if out.exists():
        for line in out.open():
            r = json.loads(line)
            rows[r["cid"]] = ("ok" if r["ok"] else "failed", r["text"])
    return rows, "batch A + api B"


def finish():
    for role, model in LABELERS.items():
        state = json.loads((OUT / f"{role}_codes.json").read_text())
        tb_items, route = _turn_b(role)
        rows = []
        for q in questions():
            cid = f"q{q['id']}"
            rec = {"id": q["id"], "model": model, "role": role, "route": route, "ok": False}
            status, text = tb_items.get(cid, (None, None))
            if status == "ok":
                try:
                    b = make_parse_b(codes(state[cid]["searches"]))(text)
                    rec.update(ok=True, turn_a=state[cid]["turn_a"], searches=state[cid]["searches"], turn_b=b,
                               category=b["category"], evidence_chunks=b["evidence_chunks"], reference_doubt=b["reference_doubt"])
                except ValueError as e:
                    rec["failure"] = f"turn B unparseable: {e}"
            else:
                rec["failure"] = "turn A or B failed after 3 attempts" if status == "failed" or (status is None and cid not in state) else "not finished"
            rows.append(rec)
        (OUT / f"{role}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(role, "ok:", sum(r["ok"] for r in rows), "of", len(rows))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"submit-a": submit_a, "poll": lambda: poll(sys.argv[2]), "submit-b": submit_b, "finish": finish,
     "api-b": lambda: api_b(sys.argv[2])}[cmd]()
