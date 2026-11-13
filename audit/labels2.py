"""Answer key v2 (TEST-PLAN-v3 section 5). Two labelers from different companies, a blind tie-breaker,
and JC's reading of the cases that cross the "bot could answer / needs a human" line.

Each labeler works in two turns: A (read the thread, state the key step, a fix query and exact terms),
then three recorded searches run here, then B (read the passages and label). Labelers never see a bot reply.
"""
import json, os, re

import numpy as np

from . import llm
from .bot import customer_message, search_query
from .common import CACHE, DATA, ROOT, RUNS, read_jsonl

GUIDE = (ROOT / "rubric/LABELING-v2.md").read_text()
CATS = ("account_access", "n8n_docs", "general_tech", "bug_or_release", "undocumented_n8n")
ANSWERABLE = {"n8n_docs", "general_tech"}
# AUDIT_SET=holdout runs the same labeling on the frozen holdout (TEST-PLAN-v3 section 5; after the v5 freeze)
HOLDOUT = os.environ.get("AUDIT_SET") == "holdout"
OUT = ROOT / ("runs/v3plan/holdout/labels" if HOLDOUT else "runs/v3plan/labels")
PHASE = "5-holdout-labels" if HOLDOUT else "1-labels"
K = 8


def side(cat):
    return "answerable" if cat in ANSWERABLE else "human"


def questions():
    if HOLDOUT:
        from .holdoutrun import questions as hq
        return hq()
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    return [q for q in read_jsonl(CACHE / "questions_full.jsonl") if q["id"] in usable]


# ------------------------------------------------------------------ turn A
def turn_a_user(q):
    return (f"## The customer's question\n<<<\n{customer_message(q)}\n>>>\n\n"
            f"## The accepted answer\n<<<\n{q['accepted_answer'][:6000]}\n>>>\n\n"
            "This is turn A. Return only the turn-A JSON object.")


def parse_a(text):
    a = llm.parse_json(text)
    if not isinstance(a.get("key_step"), str) or not a["key_step"].strip():
        raise ValueError("no key_step")
    if not isinstance(a.get("fix_query"), str) or not a["fix_query"].strip():
        raise ValueError("no fix_query")
    terms = a.get("exact_terms") or []
    if not isinstance(terms, list):
        raise ValueError("exact_terms must be a list")
    a["exact_terms"] = [str(t)[:120] for t in terms if str(t).strip()][:6]
    return a


# ------------------------------------------------------------------ the three recorded searches
class Searcher:
    """Hybrid search exactly like Docs.hybrid, with host-pinned query embeddings; plus an exact-term search."""
    def __init__(self, docs):
        self.docs = docs
        self.by_id = {c["id"]: c for c in docs.chunks}
        self.v4 = {}
        for split in ("dev", "test"):
            for a in read_jsonl(RUNS / f"v4__openai_gpt-5.4-mini/{split}/answers.jsonl"):
                self.v4[a["id"]] = a["passages"]
        hp = ROOT / "runs/v3plan/holdout/v4_answers.jsonl"
        if HOLDOUT and hp.exists():  # S1 on the holdout = the passages v4 retrieved there (same query and settings)
            for a in read_jsonl(hp):
                self.v4[a["id"]] = a["passages"]

    def hybrid(self, query, k=K, pool=30):
        kw = self.docs.keyword(query, pool)
        v = np.array(llm.embed_v3([query[:6000]], phase=PHASE)[0], dtype=np.float32)
        v /= np.linalg.norm(v)
        sims = self.docs.vectors @ v
        sem = [(self.docs.chunks[i], float(sims[i])) for i in np.argsort(-sims)[:pool]]
        scores = {}
        for results in (kw, sem):
            for rank, (c, _) in enumerate(results):
                scores[c["id"]] = scores.get(c["id"], 0) + 1 / (60 + rank)
        return [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])[:k]]

    def exact(self, terms, k=K):
        terms = [t for t in terms if len(t) >= 3]
        if not terms:
            return []
        hits = {}
        for c in self.docs.chunks:
            body = f"{c['page_title']} {c['heading']} {c['text']}".lower()
            n = sum(t.lower() in body for t in terms)
            if n:
                hits[c["id"]] = n
        ranked = {c["id"]: s for c, s in self.docs.keyword(" ".join(terms), 200)}
        return sorted(hits, key=lambda i: (-hits[i], -ranked.get(i, 0)))[:k]

    def run(self, q, a):
        s1 = self.v4.get(q["id"]) or self.hybrid(search_query(q, "with_nodes"))  # v4's own query and settings
        return [{"name": "S1", "what": "the original question (the bot's own search)", "chunks": s1},
                {"name": "S2", "what": f"the key fix alone: {a['fix_query'][:200]}", "chunks": self.hybrid(a["fix_query"])},
                {"name": "S3", "what": "exact terms: " + ", ".join(a["exact_terms"]), "chunks": self.exact(a["exact_terms"])}]


def codes(searches):
    m = {}
    for s in searches:
        for i, cid in enumerate(s["chunks"], 1):
            m[f"{s['name']}-{i}"] = cid
    return m


def turn_b_user(q, a, searches, by_id):
    parts = [f"## The customer's question\n<<<\n{customer_message(q)}\n>>>\n",
             f"## The accepted answer\n<<<\n{q['accepted_answer'][:6000]}\n>>>\n",
             f"## Your turn A\nKey step: {a['key_step']}\nVersion: {a.get('version')}\n",
             "## Docs passages from the three recorded searches"]
    for s in searches:
        parts.append(f"\n### {s['name']}: {s['what']}")
        if not s["chunks"]:
            parts.append("(no results)")
        for i, cid in enumerate(s["chunks"], 1):
            c = by_id[cid]
            parts.append(f"[{s['name']}-{i}] {c['page_title']} — {c['heading']} ({c['url']})\n{c['text']}")
    parts.append("\nThis is turn B. Return only the turn-B JSON object.")
    return "\n".join(parts)


def make_parse_b(code_map):
    def parse_b(text):
        b = llm.parse_json(text)
        if b.get("category") not in CATS:
            raise ValueError(f"category={b.get('category')!r}")
        if not isinstance(b.get("reference_doubt"), bool):
            raise ValueError("reference_doubt must be true/false")
        ev = b.get("evidence") or []
        if not isinstance(ev, list):
            raise ValueError("evidence must be a list")
        b["evidence"] = [e for e in ev if e in code_map]
        b["evidence_chunks"] = [code_map[e] for e in b["evidence"]]
        return b
    return parse_b


# ------------------------------------------------------------------ API route (labeler 2, tie-breaker)
def label_api(model, q, searcher, *, role, phase=PHASE):
    rec = {"id": q["id"], "model": model, "role": role, "route": "api", "ok": False, "cost": 0.0}
    ra = llm.call(model, [{"role": "system", "content": GUIDE}, {"role": "user", "content": turn_a_user(q)}],
                  role=f"{role}_a", phase=phase, split=q["split"], item=q["id"], json_mode=True, parse=parse_a)
    rec["cost"] += ra["cost"]; rec["attempts_a"] = ra["attempts"]
    if not ra["ok"]:
        rec["failure"] = "turn A: " + "; ".join(ra["failures"])[:300]
        return rec
    a = ra["parsed"]; rec["turn_a"] = a
    searches = searcher.run(q, a); rec["searches"] = searches
    cm = codes(searches)
    rb = llm.call(model, [{"role": "system", "content": GUIDE}, {"role": "user", "content": turn_b_user(q, a, searches, searcher.by_id)}],
                  role=f"{role}_b", phase=phase, split=q["split"], item=q["id"], json_mode=True, parse=make_parse_b(cm))
    rec["cost"] += rb["cost"]; rec["attempts_b"] = rb["attempts"]
    if not rb["ok"]:
        rec["failure"] = "turn B: " + "; ".join(rb["failures"])[:300]
        return rec
    rec.update(ok=True, turn_b=rb["parsed"], category=rb["parsed"]["category"],
               evidence_chunks=rb["parsed"]["evidence_chunks"], reference_doubt=rb["parsed"]["reference_doubt"])
    return rec


# ------------------------------------------------------------------ settlement (section 5)
def settle(l1, l2, tb=None, jc=None):
    """Return the final label record for one question.
    l1, l2, tb: label records (ok=False counts as a disagreement, section 8). jc: JC's answers or None.
    Returns dict(final, side, needs_tb, needs_jc, flags, basis)."""
    c1 = l1.get("category") if l1 and l1.get("ok") else None
    c2 = l2.get("category") if l2 and l2.get("ok") else None
    d1 = bool(l1 and l1.get("reference_doubt")); d2 = bool(l2 and l2.get("reference_doubt"))
    out = {"flags": [], "needs_tb": False, "needs_jc": False}
    if c1 and c1 == c2 and d1 == d2:
        out.update(final=c1, basis="both labelers agree", doubt=d1)
        out["side"] = side(c1); return out
    out["needs_tb"] = True
    if tb is None or not tb.get("ok"):
        out.update(final=None, basis="waiting for tie-breaker" if tb is None else "tie-breaker failed")
        return out
    ct, dt = tb["category"], bool(tb.get("reference_doubt"))
    labels = [c for c in (c1, c2, ct) if c]
    doubt = sum([d1, d2, dt]) >= 2 if (d1 != d2) else d1
    out["doubt"] = doubt
    if c1 == c2:  # labelers agreed on the category; only doubt was split
        out.update(final=c1, side=side(c1), basis="labelers agree on category; tie-breaker settled reference doubt")
        return out
    sides = {side(c) for c in labels}
    three_way = len(set(labels)) == 3
    if len(sides) == 1 and not three_way:
        maj = max(set(labels), key=labels.count)
        out.update(final=maj, side=side(maj), basis="two of three")
        return out
    out["needs_jc"] = True
    if jc is None:
        out.update(final=None, basis="waiting for JC")
        return out
    if jc.get("on_page") == "yes":
        final, basis = "n8n_docs", "JC: the key step is on the page"
    elif jc.get("knowledge") == "it":
        final, basis = "general_tech", "JC: common IT knowledge"
    elif jc.get("knowledge") == "n8n":
        human = [c for c in labels if side(c) == "human"]
        agree = [c for c in set(human) if human.count(c) >= 2]
        if agree:
            final, basis = agree[0], "JC: needs a human; two labels agree on the category"
        elif side(ct) == "human":
            final, basis = ct, "JC: needs a human; tie-breaker's category (flagged)"; out["flags"].append("category_from_tiebreaker")
        elif human:
            final, basis = human[0], "JC: needs a human; the only human-side label (flagged)"; out["flags"].append("category_from_single_label")
        else:
            final, basis = "undocumented_n8n", "JC: needs a human and n8n-specific; no label on that side (flagged)"; out["flags"].append("category_by_definition")
    else:
        final, basis = ct, "JC couldn't tell: tie-breaker's label (flagged; reported both ways)"; out["flags"].append("jc_cant_tell")
    out.update(final=final, side=side(final), basis=basis)
    return out
