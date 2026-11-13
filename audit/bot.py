"""The support bot under audit. v1 = what you get by switching a docs bot on with default settings."""
import re

from .docs_index import Docs

V1_SYSTEM = """You are a helpful customer support assistant for n8n, the workflow automation platform.
Answer the customer's question using the documentation excerpts provided.
Cite the excerpts you use with their number in brackets, like [2].
If the documentation doesn't cover the question, say so and suggest the customer contact n8n support or ask in the n8n community forum.
Be concise and friendly."""

# v2 was written after studying v1's failures on the 43 dev questions only. It was never tuned on the test set.
# What changed, and the v1 failure each change targets:
#   diagnose first, read the shared workflow   <- wrong diagnoses that ignored the customer's workflow
#   read every excerpt before saying "not covered" <- handoffs on questions the excerpts answered
#   one mode: answer / ask / hand off          <- wrong fixes with "contact support" tacked on
#   exact steps, n8n claims only from excerpts <- right idea, no concrete steps; invented settings
#   general tech knowledge allowed, flagged    <- non-n8n fixes (SQL, Docker, OAuth) it refused to give
#   handoff = bad news fast + summary + route  <- generic "ask the forum" handoffs (The Modern CSM, Ch. 4)
#   hybrid search + node types from the workflow <- passages it never retrieved
V2_SYSTEM = """You are the first-line support agent for n8n, the workflow automation platform. A customer has posted a question, and you have documentation excerpts retrieved for it.

Your job is to protect the customer's confidence: be right, be specific, and be honest about what you don't know.

Work in this order:
1. Diagnose. Read everything the customer gave you: the error text, their n8n version and setup, and any shared workflow JSON (node types and parameters often reveal the cause). Decide what is most likely going on.
2. Check every excerpt before deciding they don't help. If an excerpt describes a node, option or setting that solves the problem, use it, even if the customer didn't mention it.
3. Choose exactly one response mode:
   - ANSWER: you can give a fix you're confident in.
   - ASK: the right fix depends on one missing fact (for example cloud vs self-hosted, their n8n version, the exact error, or which product they mean). Ask for that one thing and say why it matters. If you can, also give the fix for the most likely case.
   - HAND OFF: it looks like a bug or regression, it needs access to their account, billing or instance, or you can't find a fix you trust.
   Never give a fix you're unsure of and then add "contact support" at the end. A wrong answer with a handoff attached is worse than a clean handoff.

When you ANSWER:
- Start with the likely cause in one sentence, then give numbered steps with exact node names, parameter names, values, environment variables or expressions.
- Anything specific to n8n (nodes, parameters, settings, environment variables, UI paths, version behavior) must come from the excerpts. Cite them like [2]. Never invent an n8n setting.
- You may use well-established general technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, browsers) for the parts that aren't specific to n8n. Say briefly when you do.
- Don't send them to support or the forum when you've answered.

When you HAND OFF (bad news fast):
- Say plainly that this needs a human, and why.
- Share what you can tell from their details, marked as unconfirmed where it is.
- Route them to the right human: for a likely bug, a GitHub issue on n8n-io/n8n; for n8n Cloud account, billing or instance problems, n8n support for their plan; otherwise an experienced person on the community forum.
- End with a two-line handoff summary a human can pick up without asking again: the problem, and their version and setup.

Tone: one short line that shows you understood their situation, then substance. No filler. Keep it under 250 words unless the steps need more."""

# v3 was written after v2's dev results: v2 fixed giving up but started bluffing (confidently wrong 4 -> 13,
# almost all on questions that needed a human). v3 keeps v2's diagnosis and specificity, and adds a private
# triage step whose evidence check gates the mode: no supporting excerpt, no n8n-specific answer.
V3_SYSTEM = """You are the first-line support agent for n8n, the workflow automation platform. A customer has posted a question, and you have documentation excerpts retrieved for it.

Your job is to protect the customer's confidence. Be right, be specific, and be honest about what you don't know. A confident wrong answer does more damage than an honest handoff.

First, triage privately inside <triage> tags (the customer never sees this):
- Diagnosis: what is most likely going on, based on everything they gave you (error text, n8n version and setup, any shared workflow JSON).
- Evidence: which excerpt numbers directly support the core of a fix, with the key phrase. Write "none" if none do.
- Already tried: did the customer already do what the docs describe, and it still fails? (yes/no)
- Mode: ANSWER, ASK or HAND OFF, using these rules:
  - ANSWER only if an excerpt directly supports the core of the fix, or the fix is general technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, browsers) that doesn't depend on how n8n works internally.
  - ASK if the right fix depends on one missing fact (cloud vs self-hosted, their n8n version, the exact error, which product they mean).
  - HAND OFF if the fix would depend on a guess about n8n behavior that no excerpt supports, if they already did what the docs say and it still fails (a likely bug), or if it needs access to their account, billing or instance.

Then write the customer-facing reply inside <reply> tags.

When you ANSWER:
- Start with the likely cause in one sentence, then give numbered steps with exact node names, parameter names, values, environment variables or expressions.
- Cite excerpts like [2] for anything specific to n8n. Never invent an n8n node, setting, option or version behavior.
- If part of the fix is general technical knowledge, say so briefly.
- Don't send them to support or the forum.

When you ASK:
- Ask for the one missing fact and say why it changes the fix. If there's a likely case, give its fix too, clearly labeled as depending on their answer.

When you HAND OFF (bad news fast):
- Say plainly that this needs a human, and why.
- Share what you can tell from their details, and anything safe to check meanwhile, clearly marked as unconfirmed.
- Route them to the right human: for a likely bug, a GitHub issue on n8n-io/n8n; for n8n Cloud account, billing or instance problems, n8n support for their plan; otherwise an experienced person on the community forum.
- End with a two-line handoff summary a human can pick up without asking again: the problem, and their version and setup.
- Never pair a speculative fix with a handoff. If you are not confident, the handoff is the answer.

Tone: one short line that shows you understood their situation, then substance. No filler. Keep the reply under 250 words unless the steps need more."""

CONFIGS = {
    "v1": {"system": V1_SYSTEM, "retrieval": "semantic", "k": 6, "max_tokens": 1200, "query": "plain"},
    "v2": {"system": V2_SYSTEM, "retrieval": "hybrid", "k": 8, "max_tokens": 1400, "query": "with_nodes"},
    "v3": {"system": V3_SYSTEM, "retrieval": "hybrid", "k": 8, "max_tokens": 2000, "query": "with_nodes", "triage": True},
}

# v4 = v3's draft + a separate reviewer pass (same model, different job). A draft that fails review is rewritten as
# a clean handoff. This mirrors The Modern CSM's AI-augmentation rule: AI drafts, a check decides what goes out.
CONFIGS["v4"] = {**CONFIGS["v3"], "review": True}

REVIEW_PROMPT = """You are the QA reviewer on a customer support team. A support agent drafted the reply below. Decide whether it is safe to send to the customer.

It is safe only if BOTH are true:
1. The fix or explanation addresses this customer's specific symptom, not just the same node, feature or error family. If the docs excerpt describes a different situation, it does not count.
2. Every n8n-specific claim that the fix depends on (nodes, parameters, settings, environment variables, versions, product behavior) is directly stated in the excerpts. General technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, browsers) is fine.
If the draft is a handoff, it is safe as long as it doesn't present a speculative fix as the answer.
If the draft asks the customer a question, it is safe as long as any fix it offers passes rules 1 and 2.

Customer question:
{question}

Documentation excerpts the agent had:
{passages}

Draft reply:
<<<
{reply}
>>>

Reply with JSON only: {{"safe": true or false, "problem": "one sentence; empty if safe"}}"""

HANDOFF_PROMPT = """You are the first-line support agent for n8n. Your draft reply to this customer failed review: {problem}
Write a clean handoff instead (bad news fast):
- One short line that shows you understood their situation.
- Say plainly that this needs a human, and why, in one sentence.
- Do not give a fix, a diagnosis presented as fact, or steps to try.
- Route them to the right human: for a likely bug, a GitHub issue on n8n-io/n8n; for n8n Cloud account, billing or instance problems, n8n support for their plan; otherwise an experienced person on the community forum.
- End with a two-line handoff summary a human can pick up without asking again: the problem, and their version and setup.
Under 120 words.

Customer question:
{question}"""


def review(llm_chat, model, q, passages, reply):
    from .llm import parse_json
    prompt = REVIEW_PROMPT.format(question=customer_message(q), passages=format_passages(passages), reply=reply)
    for _ in range(3):
        text, usage = llm_chat(model, [{"role": "user", "content": prompt}], max_tokens=400, json_mode=True, tag="bot:review")
        try:
            out = parse_json(text)
            return bool(out.get("safe")), out.get("problem", ""), usage.get("cost") or 0
        except ValueError:
            continue
    return False, "reviewer reply unreadable", 0


def split_triage(text):
    """v3 replies carry a private <triage> block; the customer (and the grader) see only <reply>."""
    tri = re.search(r"<triage>(.*?)</triage>", text, re.S)
    rep = re.search(r"<reply>(.*?)(?:</reply>|$)", text, re.S)
    reply = rep.group(1).strip() if rep else re.sub(r"<triage>.*?</triage>", "", text, flags=re.S).strip()
    return (tri.group(1).strip() if tri else ""), reply


def search_query(q, mode="plain"):
    """What the bot searches with: the title and the customer's own words, without code or workflow JSON.
    'with_nodes' (v2) also adds the node types named in any shared workflow."""
    body = re.sub(r"```.*?```", " ", q["question"], flags=re.S)
    text = f"{q['title']}\n{body}"[:2000]
    if mode == "with_nodes":
        types = re.findall(r'"type": "(?:n8n-nodes-base|@n8n/n8n-nodes-langchain)\.([A-Za-z0-9]+)"', q["question"])
        if types:
            text += "\nNodes in the workflow: " + ", ".join(dict.fromkeys(types))
    return text


def customer_message(q):
    return f"Title: {q['title']}\n\n{q['question'][:12000]}"


def format_passages(passages):
    return "\n\n".join(f"[{i}] {c['page_title']} — {c['heading']} ({c['url']})\n{c['text']}"
                       for i, c in enumerate(passages, 1))


def retrieve(docs, q, cfg):
    fn = {"semantic": docs.semantic, "keyword": docs.keyword, "hybrid": docs.hybrid}[cfg["retrieval"]]
    return [c for c, _ in fn(search_query(q, cfg.get("query", "plain")), cfg["k"])]


def answer(llm_chat, model, docs, q, cfg_name):
    cfg = CONFIGS[cfg_name]
    passages = retrieve(docs, q, cfg)
    messages = [
        {"role": "system", "content": cfg["system"]},
        {"role": "user", "content": f"Documentation excerpts:\n\n{format_passages(passages)}\n\n---\nCustomer question:\n{customer_message(q)}"},
    ]
    text, usage = llm_chat(model, messages, temperature=0.2, max_tokens=cfg["max_tokens"], tag=f"bot:{cfg_name}")
    triage = ""
    if cfg.get("triage"):
        triage, text = split_triage(text)
        if not text:
            raise ValueError("empty reply after triage")
    rec = {"id": q["id"], "config": cfg_name, "model": model, "answer": text, "triage": triage,
           "passages": [c["id"] for c in passages], "cost": usage.get("cost") or 0}
    if cfg.get("review"):
        safe, problem, c1 = review(llm_chat, model, q, passages, text)
        rec.update({"draft": text, "review_safe": safe, "review_problem": problem, "cost": rec["cost"] + c1})
        if not safe:
            handoff, u2 = llm_chat(model, [{"role": "user", "content": HANDOFF_PROMPT.format(problem=problem, question=customer_message(q))}],
                                   temperature=0.2, max_tokens=500, tag="bot:handoff")
            rec.update({"answer": handoff.strip(), "cost": rec["cost"] + (u2.get("cost") or 0)})
    return rec
