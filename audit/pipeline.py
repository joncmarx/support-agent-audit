"""The bot pipeline on the repaired harness (TEST-PLAN-v3 section 8).

Round one's reviewer capped replies at 400 tokens and counted three unreadable replies as "unsafe". Here:
- every role gets 3 attempts with identical settings (audit/llm.call);
- a drafter, reviewer or handoff-writer failure gives the customer JC's fixed safe handoff and the flag
  `system_failure`; a reviewer failure never passes the draft and is never counted as a genuine block;
- every attempted question stays in every denominator, with attempt-level and final failures recorded.
"""
from . import llm as _llm
from .bot import HANDOFF_PROMPT, REVIEW_PROMPT, customer_message, format_passages, split_triage
from .common import ROOT

SAFE_HANDOFF = (ROOT / "prompts/SAFE_HANDOFF.txt").read_text().strip()
V4_USER = "Documentation excerpts:\n\n{passages}\n\n---\nCustomer question:\n{question}"


def _parse_draft(text):
    _tri, reply = split_triage(text)
    if not reply.strip():
        raise ValueError("empty reply after triage")
    return reply


def _parse_review(text):
    out = _llm.parse_json(text)
    if not isinstance(out.get("safe"), bool):
        raise ValueError(f"no readable pass/block verdict: {str(out)[:120]}")
    return out


def draft(call, model, q, passages, system, *, arm, phase, split, user_template=V4_USER, community=None):
    user = user_template.format(passages=format_passages(passages), question=customer_message(q),
                                community=community if community is not None else "(none found)")
    r = call(model, [{"role": "system", "content": system}, {"role": "user", "content": user}], role="drafter",
             arm=arm, phase=phase, split=split, item=q["id"], parse=_parse_draft)
    return r


def review(call, model, q, passages, reply, *, arm, phase, split, graders, template=REVIEW_PROMPT, community=None, role="reviewer"):
    fields = dict(question=customer_message(q), passages=format_passages(passages), reply=reply)
    if "{community}" in template:
        fields["community"] = community if community is not None else "(none found)"
    r = call(model, [{"role": "user", "content": template.format(**fields)}], role=role, author=drafter_of(arm),
             graders=graders, arm=arm, phase=phase, split=split, item=q["id"], json_mode=True, parse=_parse_review)
    return r


def handoff(call, model, q, problem, *, arm, phase, split, template=HANDOFF_PROMPT):
    return call(model, [{"role": "user", "content": template.format(problem=problem, question=customer_message(q))}],
                role="handoff", arm=arm, phase=phase, split=split, item=q["id"])


DRAFTERS = {"A": "openai/gpt-5.4-mini", "B": "openai/gpt-5.4-mini", "D": "openai/gpt-6.1-sol",
            "F0": "openai/gpt-5.4-mini", "F": "openai/gpt-5.4-mini", "G": None}


def drafter_of(arm):
    return DRAFTERS.get(arm) or "openai/gpt-5.4-mini"


def run(q, passages, *, arm, drafter, reviewer, system, graders, phase, split, call=None,
        review_template=REVIEW_PROMPT, handoff_template=HANDOFF_PROMPT, user_template=V4_USER, community=None,
        reviewer_role="reviewer"):
    """One question through draft -> review -> (handoff). Returns the record that gets graded."""
    call = call or _llm.call
    rec = {"id": q["id"], "arm": arm, "drafter": drafter, "reviewer": reviewer, "passages": [c["id"] for c in passages],
           "system_failure": None, "attempt_failures": {}, "cost": 0.0}
    d = draft(call, drafter, q, passages, system, arm=arm, phase=phase, split=split, user_template=user_template, community=community)
    rec["cost"] += d["cost"]; rec["attempt_failures"]["drafter"] = d["failures"]
    if not d["ok"]:
        rec.update(answer=SAFE_HANDOFF, draft=None, review_safe=None, system_failure="drafter", answer_source="safe_handoff")
        return rec
    rec["draft"] = d["parsed"]
    if reviewer is None:
        rec.update(answer=rec["draft"], answer_source="draft")
        return rec
    rv = review(call, reviewer, q, passages, rec["draft"], arm=arm, phase=phase, split=split, graders=graders,
                template=review_template, community=community, role=reviewer_role)
    rec["cost"] += rv["cost"]; rec["attempt_failures"]["reviewer"] = rv["failures"]
    if not rv["ok"]:
        # Never passed, never counted as a genuine block.
        rec.update(answer=SAFE_HANDOFF, review_safe=None, review_problem=None, system_failure="reviewer", answer_source="safe_handoff")
        return rec
    rec["review_safe"], rec["review_problem"] = rv["parsed"]["safe"], rv["parsed"].get("problem", "")
    if rec["review_safe"]:
        rec.update(answer=rec["draft"], answer_source="draft")
        return rec
    h = handoff(call, drafter, q, rec["review_problem"], arm=arm, phase=phase, split=split, template=handoff_template)
    rec["cost"] += h["cost"]; rec["attempt_failures"]["handoff"] = h["failures"]
    if not h["ok"]:
        rec.update(answer=SAFE_HANDOFF, system_failure="handoff", answer_source="safe_handoff")
        return rec
    rec.update(answer=h["text"].strip(), answer_source="handoff")
    return rec
