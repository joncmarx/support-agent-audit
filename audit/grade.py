"""Handoff labeler and rubric grader. Both read their rules from rubric/*.md, so the docs and the code can't drift."""
import re

from .bot import customer_message, format_passages
from .common import ROOT
from .llm import parse_json

JUDGE_MODEL = "anthropic/claude-sonnet-5.5"
RUBRIC = (ROOT / "rubric/RUBRIC.md").read_text()
LABELING = (ROOT / "rubric/LABELING.md").read_text()
OUTCOMES = {"resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "confidently_wrong"}


def ask_json(llm_chat, prompt, max_tokens, tag, tries=3):
    """Call the judge model and parse JSON; retry when the reply is empty or malformed."""
    last = None
    for _ in range(tries):
        text, usage = llm_chat(JUDGE_MODEL, [{"role": "user", "content": prompt}], max_tokens=max_tokens, json_mode=True, tag=tag)
        try:
            return parse_json(text), usage
        except (ValueError, KeyError) as e:
            last = f"{e}: {text[:200]!r}"
    raise ValueError(f"unparseable judge reply after {tries} tries: {last}")


def reference_check(llm_chat, q):
    """Is the accepted answer a usable reference (does it contain a concrete fix or answer)?"""
    prompt = f"""A forum thread's accepted answer will be used as the reference for grading support replies.
It is usable only if it contains a concrete fix, explanation or answer to the question.
It is NOT usable if it is only encouragement, only a link with no summary of what it says, only a question back to the asker,
or says the problem went away without explaining why.

Question title: {q['title']}
Question (first 1500 characters): {q['question'][:1500]}

Accepted answer: {q['accepted_answer'][:4000]}

Reply with JSON only: {{"usable": true or false, "why": "one sentence"}}"""
    out, usage = ask_json(llm_chat, prompt, 800, "refcheck")
    return {"id": q["id"], "usable": bool(out["usable"]), "why": out.get("why"), "cost": usage.get("cost")}


def label(llm_chat, docs, q):
    body = re.sub(r"```.*?```", " ", q["question"], flags=re.S)
    query = f"{q['title']}\n{body[:1200]}\n{q['accepted_answer'][:1500]}"
    passages = [c for c, _ in docs.hybrid(query, k=10)]
    prompt = f"""{LABELING}

Apply the rule above to this forum thread.

Customer question:
{customer_message(q)}

Accepted answer (written by another community member; it solved the problem for the asker):
{q['accepted_answer'][:6000]}

Doc passages retrieved for it:
{format_passages(passages)}

Reply with JSON only:
{{"label": "docs" or "handoff", "reason": "bug_release" | "access" | "not_in_docs" | "in_docs",
  "evidence": [numbers of the passages that contain the fix, if any], "key_fix": "the accepted answer's key step in one sentence",
  "rationale": "one or two sentences"}}"""
    out, usage = ask_json(llm_chat, prompt, 900, "label")
    ev = [passages[i - 1]["url"] for i in out.get("evidence", []) if isinstance(i, int) and 0 < i <= len(passages)]
    assert out["label"] in ("docs", "handoff"), out
    return {"id": q["id"], "label": out["label"], "reason": out.get("reason"), "key_fix": out.get("key_fix"),
            "evidence_urls": ev, "rationale": out.get("rationale"), "cost": usage.get("cost")}


def grade(llm_chat, docs_by_id, q, lab, ans):
    passages = [docs_by_id[i] for i in ans["passages"]]
    prompt = f"""{RUBRIC}

Grade this reply.

Customer question:
{customer_message(q)}

Reference: the accepted answer from the forum (it solved the problem for the asker):
{q['accepted_answer'][:6000]}

Handoff label: {lab['label']}  (key step of the fix, per the labeler: {lab.get('key_fix')})

Doc passages the bot was given:
{format_passages(passages)}

The bot's reply:
<<<
{ans['answer']}
>>>

Reply with the JSON object described in section 3, and nothing else."""
    out, usage = ask_json(llm_chat, prompt, 2000, "grade")
    if out.get("outcome") not in OUTCOMES:
        raise ValueError(f"bad outcome {out.get('outcome')}")
    out.update({"id": q["id"], "config": ans["config"], "model": ans["model"], "judge": JUDGE_MODEL, "cost": usage.get("cost")})
    return out
