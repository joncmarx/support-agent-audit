"""Blind grader for Test Plan v3 (section 6). The rubric lives in rubric/RUBRIC-v3.md.

The same rendered text is used on every route (OpenRouter API, JC's Claude plan, JC's own blind page):
system = the rubric, user = the item. Graders never see the label, the arm, the model, the version or
the reviewer's decision.
"""
import hashlib, json, re

from . import llm
from .bot import customer_message
from .common import ROOT
from .normalize import normalize
from .outcome import outcome

RUBRIC_PATH = ROOT / "rubric/RUBRIC-v3.md"
RUBRIC = RUBRIC_PATH.read_text()
ENUMS = {
    "action": {"answered", "asked", "handed_off", "mixed", "no_usable_reply"},
    "fix_verdict": {"correct", "partial", "wrong", "no_fix"},
    "fix_framing": {"the_answer", "conditional", "none"},
    "error_framing": {"the_answer", "conditional", "none"},
    "right_missing_fact": {"yes", "no", "na"},
    "route_named": {"github", "n8n_support", "forum", "several", "none"},
}
BOOLS = ("material_error", "harmless_error", "unsafe")


def fmt_passages(chunks, tag=""):
    return "\n\n".join(f"[{tag}{i}] {c['page_title']} — {c['heading']} ({c['url']})\n{c['text']}"
                       for i, c in enumerate(chunks, 1)) or "(none)"


# ------------------------------------------------------------------ reference packets
def evidence_for_pages(docs, urls, query, per_page=2):
    """Round-one labels stored evidence *pages*, not passages. For the calibration steps (which run before
    labels v2 exist) the packet shows, for each evidence page, the passages of that page that best match the
    recorded key fix and accepted answer (keyword search, $0)."""
    out = []
    for url in dict.fromkeys(urls):
        page = [c for c in docs.chunks if c["url"] == url]
        if not page:
            continue
        if len(page) <= per_page:
            out.extend(page)
            continue
        from .docs_index import BM25
        bm = BM25([f"{c['heading']} {c['text']}" for c in page])
        out.extend(page[i] for i, _ in bm.search(query, per_page))
    return out


def packet_round1(q, lab, docs):
    ev = evidence_for_pages(docs, lab.get("evidence_urls") or [], f"{lab.get('key_fix') or ''} {q['accepted_answer'][:1500]}")
    return {"kind": "round1", "accepted_answer": q["accepted_answer"], "key_fix": lab.get("key_fix"), "evidence": ev}


def packet_v2(q, evidence_chunks):
    """Section 6: the accepted answer and the labelers' evidence passages (same for every arm)."""
    return {"kind": "labels_v2", "accepted_answer": q["accepted_answer"], "key_fix": None, "evidence": evidence_chunks}


def render_item(q, packet, bot_passages, reply):
    ref = [f"Accepted answer from the forum (it solved the problem for the asker):\n<<<\n{packet['accepted_answer'][:6000]}\n>>>"]
    if packet.get("key_fix"):
        ref.append(f"Reference note — key step of the fix, as recorded by the labeler: {packet['key_fix']}")
    ref.append("Evidence passages from the n8n docs:\n" + fmt_passages(packet["evidence"], "R"))
    return (f"## The customer's question\n<<<\n{customer_message(q)}\n>>>\n\n"
            f"## The reference packet\n" + "\n\n".join(ref) + "\n\n"
            f"## The passages this agent had\n{fmt_passages(bot_passages)}\n\n"
            f"## The reply (plain text)\n<<<\n{normalize(reply)}\n>>>\n\n"
            "Grade the reply. Return the JSON object described in the rubric, and nothing else.")


def item_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ------------------------------------------------------------------ parsing
def parse_grade(text):
    """Strict parse: every field the outcome table needs must be present with a valid value.
    Raises ValueError, which the call layer counts as a failed attempt (section 8)."""
    g = llm.parse_json(text)
    if not isinstance(g, dict):
        raise ValueError("not a JSON object")
    for k, allowed in ENUMS.items():
        v = g.get(k)
        if k == "error_framing" and v in (None, "", "null"):
            v = "none"
        if v not in allowed:
            raise ValueError(f"{k}={v!r}")
        g[k] = v
    for k in BOOLS:
        if not isinstance(g.get(k), bool):
            raise ValueError(f"{k} must be true/false, got {g.get(k)!r}")
    return g


def to_table(g):
    return {"action": g["action"], "fix_verdict": g["fix_verdict"], "fix_framing": g["fix_framing"],
            "material_error": g["material_error"],
            "error_framing": None if g["error_framing"] == "none" else g["error_framing"],
            "harmless_error": g["harmless_error"], "unsafe": g["unsafe"],
            "right_missing_fact": g["right_missing_fact"]}


def score(g, answerable=None):
    o, row, h = outcome(to_table(g), answerable)
    return o, row, h["harmonized"]


# ------------------------------------------------------------------ API route
def grade_api(model, item_text, *, role, author, phase, split, arm, rid):
    msgs = [{"role": "system", "content": RUBRIC}, {"role": "user", "content": item_text}]
    r = llm.call(model, msgs, role=role, author=author, phase=phase, split=split, arm=arm, item=rid,
                 json_mode=True, parse=parse_grade)
    rec = {"rid": rid, "grader": model, "route": "api", "ok": r["ok"], "attempts": r["attempts"],
           "failures": r["failures"], "cost": r["cost"], "provider": r.get("provider"),
           "reasoning_tokens": r.get("reasoning_tokens"), "seconds": r["seconds"], "item_hash": item_hash(item_text)}
    if r["ok"]:
        g = r["parsed"]
        o, row, notes = score(g)
        rec.update({"grade": g, "label_free": o, "row": row, "harmonized": notes})
    return rec
