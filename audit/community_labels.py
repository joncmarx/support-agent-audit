"""Community-availability labels (TEST-PLAN-v3 section 5; decision 19). Prints counts only.

Scope (decision 19): the 37 practice and test questions on the human side whose category is bug_or_release or
undocumented_n8n; only there can the label change F's or DF's answerable denominator.
Each labeler (labeler 1 Sonnet 5.5, labeler 2 Gemini 3.8 Flash; the labels-v2 labelers) runs two searches over
that question's eligible harvest (audit/community.py rules), the same hybrid search, top 10 each: S1 the question
itself (v4's query), S2 the key fix alone (the labeler's own labels-v2 fix query). It answers yes (with the
answer's code, mapped to a thread id) or no. Disagreements: the tie-breaker (Muse Spark 1.3) answers blind, shown
both labelers' searches merged; two of three decide.

  python3 -m audit.community_labels prep               # store both labelers' searches
  python3 -m audit.community_labels run                # both labelers, all calls at once, resumable
  python3 -m audit.community_labels tiebreak
  python3 -m audit.community_labels settle
"""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import llm
from .bot import customer_message, search_query
from . import build2 as B2
from .common import CACHE, ROOT, read_jsonl
from .community import OUT, POOL, PHASE, doc_text, eligible, eval_questions, global_exclusions, threads, VEC
from .docs_index import BM25
from .models import ROLES

GUIDE = (ROOT / "rubric/COMMUNITY-LABEL.md").read_text()
LDIR = ROOT / "runs/v3plan/labels"
CL = OUT / "labels"
K, ANSWER_CHARS = 10, 1500
LABELERS = {"labeler1": ROLES["labeler1"], "labeler2": ROLES["labeler2"]}
PH = "4-community-labels"


def scope():
    fin = {r["id"]: r for r in read_jsonl(LDIR / "final.jsonl")}
    qs = [q for q in eval_questions() if fin[q["id"]]["side"] == "human"
          and fin[q["id"]]["final"] in ("bug_or_release", "undocumented_n8n")]
    return qs


class Index:
    def __init__(self):
        self.hs = threads()
        self.vec = np.load(VEC)
        self.bm = BM25([doc_text(h) for h in self.hs])
        self.gx = global_exclusions(self.hs, eval_questions())
        p = CL / "query_vectors.json"
        self.qcache_p = p
        self.qcache = json.loads(p.read_text()) if p.exists() else {}

    def mask(self, q):
        return np.array([str(h["id"]) not in self.gx and eligible(h, q) is None for h in self.hs])

    def qvec(self, key, text, q):
        if key not in self.qcache:
            self.qcache[key] = llm.embed_v3([text[:6000]], phase=PH, split=q["split"], item=key)[0]
        v = np.array(self.qcache[key], dtype=np.float32)
        return v / np.linalg.norm(v)

    def hybrid(self, q, key, text, ok, k=K):
        kw = [i for i, _ in self.bm.search(text, len(self.hs)) if ok[i]][:POOL]
        sims = np.where(ok, self.vec @ self.qvec(key, text, q), -9)
        sem = [int(i) for i in np.argsort(-sims)[:POOL] if ok[i]]
        s = {}
        for res in (kw, sem):
            for rank, i in enumerate(res):
                s[i] = s.get(i, 0) + 1 / (60 + rank)
        return [str(self.hs[i]["id"]) for i, _ in sorted(s.items(), key=lambda x: -x[1])[:k]]

    def save(self):
        CL.mkdir(parents=True, exist_ok=True)
        self.qcache_p.write_text(json.dumps(self.qcache))


def labels_v2(role):
    return {r["id"]: r for r in read_jsonl(LDIR / f"{role}.jsonl")}


def user_msg(q, key_step, searches, by_id):
    parts = [f"## The customer's question\n<<<\n{customer_message(q)}\n>>>\n",
             f"## The accepted answer\n<<<\n{q['accepted_answer'][:6000]}\n>>>\n"]
    if key_step:
        parts.append(f"## Key step\n{key_step}\n")
    parts.append("## Earlier community answers from the two recorded searches")
    for s in searches:
        parts.append(f"\n### {s['name']}: {s['what']}")
        for i, tid in enumerate(s["ids"], 1):
            h = by_id[tid]
            a = h["answer"] if len(h["answer"]) <= ANSWER_CHARS else h["answer"][:ANSWER_CHARS] + " […]"
            parts.append(f"[{s['name']}-{i}] {h['title']} (answered {h['answer_created_at'][:10]})\n{a}")
    parts.append("\nReturn only the JSON object.")
    return "\n".join(parts)


def make_parse(codes):
    def parse(text):
        d = llm.parse_json(text)
        if not isinstance(d.get("available"), bool):
            raise ValueError("available must be true/false")
        if d["available"] and d.get("evidence") not in codes:
            raise ValueError(f"evidence {d.get('evidence')!r} is not a shown code")
        d["thread"] = codes[d["evidence"]] if d["available"] else None
        return d
    return parse


def codes_of(searches):
    return {f"{s['name']}-{i}": tid for s in searches for i, tid in enumerate(s["ids"], 1)}


def one(role, model, q, searches, key_step, by_id):
    codes = codes_of(searches)
    r = llm.call(model, [{"role": "system", "content": GUIDE},
                         {"role": "user", "content": user_msg(q, key_step, searches, by_id)}],
                 role=role, phase=PH, split=q["split"], item=q["id"], json_mode=True, parse=make_parse(codes))
    return {"id": q["id"], "role": role, "model": model, "ok": r["ok"], "searches": searches,
            "verdict": r["parsed"], "attempts": r["attempts"], "cost": r["cost"], "failures": r["failures"]}


def prep():
    """Run and store every labeler's two searches (query embeddings batched, cached)."""
    qs, ix = scope(), Index()
    keys, texts = [], []
    for role in LABELERS:
        v2 = labels_v2(role)
        for q in qs:
            for k, txt in ((f"{q['id']}:S1", search_query(q, "with_nodes")), (f"{q['id']}:{role}:S2", v2[q["id"]]["turn_a"]["fix_query"])):
                if k not in ix.qcache and k not in keys:
                    keys.append(k); texts.append(txt[:6000])
    for i in range(0, len(keys), 16):
        for k, v in zip(keys[i:i + 16], llm.embed_v3(texts[i:i + 16], phase=PH, item=f"cl-queries:{i}")):
            ix.qcache[k] = v
        ix.save()
    S = {}
    for role in LABELERS:
        v2 = labels_v2(role)
        for q in qs:
            ok = ix.mask(q)
            a = v2[q["id"]]
            S[f"{role}:{q['id']}"] = {
                "searches": [{"name": "S1", "what": "the original question",
                              "ids": ix.hybrid(q, f"{q['id']}:S1", search_query(q, "with_nodes"), ok)},
                             {"name": "S2", "what": f"the key fix alone: {a['turn_a']['fix_query'][:200]}",
                              "ids": ix.hybrid(q, f"{q['id']}:{role}:S2", a["turn_a"]["fix_query"], ok)}],
                "key_step": (a.get("turn_b") or {}).get("key_step") or a["turn_a"]["key_step"]}
    (CL / "searches.json").write_text(json.dumps(S))
    print(f"searches stored for {len(S)} labeler-question pairs")


def _chunk(keys, spec_of, path):
    by_id = {str(h["id"]): h for h in threads()}
    qs = {str(q["id"]): q for q in scope()}

    def fn(k, n):
        role, model, qid, searches, key_step = spec_of(k)
        q = qs[qid]
        codes = codes_of(searches)
        r = B2.one_call(model, [{"role": "system", "content": GUIDE},
                                {"role": "user", "content": user_msg(q, key_step, searches, by_id)}],
                        role=role, author=None, split=q["split"], arm="community-labels", item=k, attempt=n,
                        json_mode=True, parse=make_parse(codes), phase=PH)
        r["searches"] = searches
        return r
    B2.run_chunk(keys, fn, path, workers=48, window=2)


def run():
    S = json.loads((CL / "searches.json").read_text())
    def spec(k):
        role, qid = k.split(":")
        return role, LABELERS[role], qid, S[k]["searches"], S[k]["key_step"]
    _chunk(list(S), spec, CL / "calls.jsonl")
    status()


def latest(role):
    out = {}
    for k, recs in B2.records(CL / ("tb_calls.jsonl" if role == "label_tb" else "calls.jsonl")).items():
        r, qid = k.split(":")
        if r != role:
            continue
        s = B2.state(recs)
        if s and s != "failed":
            out[qid] = {"ok": True, "verdict": s["parsed"], "searches": s["searches"]}
        elif s == "failed":
            out[qid] = {"ok": False}
    return out


def tiebreak():
    qs = {str(q["id"]): q for q in scope()}
    l1, l2 = latest("labeler1"), latest("labeler2")
    todo = [i for i in qs if l1.get(i, {}).get("ok") and l2.get(i, {}).get("ok")
            and l1[i]["verdict"]["available"] != l2[i]["verdict"]["available"]]
    print(f"disagreements needing a tie-break: {len(todo)}")

    def merged(i):
        s1 = l1[i]["searches"][0]["ids"]
        s2 = [t for t in dict.fromkeys(l1[i]["searches"][1]["ids"] + l2[i]["searches"][1]["ids"]) if t not in s1]
        return [{"name": "S1", "what": "the original question", "ids": s1},
                {"name": "S2", "what": "the key fix alone (both labelers' queries, merged)", "ids": s2}]
    _chunk([f"label_tb:{i}" for i in todo], lambda k: ("label_tb", ROLES["tiebreaker"], k.split(":")[1], merged(k.split(":")[1]), None),
           CL / "tb_calls.jsonl")
    status()


def settle():
    qs = scope()
    l1, l2, tb = latest("labeler1"), latest("labeler2"), latest("label_tb")
    F = {}
    for s in ("dev", "test"):
        for r in read_jsonl(OUT / f"{s}.jsonl"):
            F[str(r["id"])] = {p["id"] for p in r["picked"]}
    rows = []
    for q in qs:
        qid = str(q["id"])
        v = [x[qid]["verdict"] for x in (l1, l2) if x.get(qid, {}).get("ok")]
        if len(v) < 2:
            rows.append({"id": q["id"], "split": q["split"], "available": None, "basis": "incomplete"}); continue
        if v[0]["available"] == v[1]["available"]:
            avail, basis, votes = v[0]["available"], "agree", v
        else:
            t = tb.get(qid)
            if not (t and t["ok"]):
                rows.append({"id": q["id"], "split": q["split"], "available": None, "basis": "needs tie-break"}); continue
            avail, basis = t["verdict"]["available"], "two of three"
            votes = [x for x in v + [t["verdict"]] if x["available"] == avail]
        threads_yes = [x["thread"] for x in votes if x.get("thread")]
        rows.append({"id": q["id"], "split": q["split"], "available": avail, "basis": basis,
                     "threads": threads_yes, "f_found": bool(set(threads_yes) & F.get(qid, set())) if avail else None})
    from .common import write_jsonl
    write_jsonl(CL / "final.jsonl", rows)
    for s in ("dev", "test"):
        rs = [r for r in rows if r["split"] == s]
        print(f"{s}: {len(rs)} questions | available {sum(r['available'] is True for r in rs)}, "
              f"not {sum(r['available'] is False for r in rs)}, open {sum(r['available'] is None for r in rs)} | "
              f"agree {sum(r['basis'] == 'agree' for r in rs)}, two of three {sum(r['basis'] == 'two of three' for r in rs)} | "
              f"F's search found it {sum(bool(r.get('f_found')) for r in rs)}")


def status():
    import collections
    cost = collections.Counter()
    for f in ("calls.jsonl", "tb_calls.jsonl"):
        for r in (read_jsonl(CL / f) if (CL / f).exists() else []):
            cost[r["key"].split(":")[0]] += float(r.get("cost") or 0)
    for role in ("labeler1", "labeler2", "label_tb"):
        d = latest(role)
        print(f"{role}: {sum(r['ok'] for r in d.values())} ok, {sum(not r['ok'] for r in d.values())} failed | "
              f"yes {sum(bool(r['ok'] and r['verdict']['available']) for r in d.values())} | cost ${cost[role]:.3f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"prep": prep, "run": run, "tiebreak": tiebreak, "settle": settle, "status": status}[cmd]()
