"""Dev-only: calibrate the reviewer on v3's dev drafts before locking v4. Prints projected outcomes per reviewer."""
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from . import llm
from .bot import customer_message, format_passages
from .common import DATA, RUNS, CACHE, read_jsonl
from .llm import parse_json

PROMPT_B = """You are the QA reviewer on a customer support team. Your job is to stop confident wrong answers from reaching customers, not to demand perfection.

Mark the draft UNSAFE only if one of these is true:
A. Wrong situation: the core fix targets a different problem than the customer's symptom (for example, an excerpt about the same node but a different error).
B. Unsupported product claim: the core fix depends on an n8n-specific claim (a node, parameter, setting, environment variable, version or behavior) that the excerpts don't state.
C. Guessing past a likely bug: the customer already did what the docs describe and it still fails, yet the draft presents a guess as the answer.

Otherwise mark it SAFE. Incomplete answers, answers that rely on general technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, browsers), clarifying questions and handoffs are all SAFE unless A, B or C applies.

Customer question:
{question}

Documentation excerpts the agent had:
{passages}

Draft reply:
<<<
{reply}
>>>

Reply with JSON only: {{"safe": true or false, "rule": "A", "B", "C" or "", "problem": "one sentence; empty if safe"}}"""

models = sys.argv[1:] or ["openai/gpt-5.4-mini", "google/gemini-3.8-flash"]
lab = {r["id"]: r["label"] for r in read_jsonl(DATA / "labels.jsonl")}
G3 = {g["id"]: g["outcome"] for g in read_jsonl(RUNS / "v3__openai_gpt-5.4-mini/dev/grades.jsonl")}
A3 = read_jsonl(RUNS / "v3__openai_gpt-5.4-mini/dev/answers.jsonl")
Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
chunks = {c["id"]: c for c in read_jsonl(CACHE / "docs_chunks.jsonl")}


def one(args):
    model, a = args
    q = Q[a["id"]]
    p = PROMPT_B.format(question=customer_message(q), passages=format_passages([chunks[i] for i in a["passages"]]), reply=a["answer"])
    for _ in range(3):
        t, _u = llm.chat(model, [{"role": "user", "content": p}], max_tokens=500, json_mode=True, tag="reviewtrial")
        try:
            return model, a["id"], bool(parse_json(t)["safe"])
        except Exception:
            pass
    return model, a["id"], False


with ThreadPoolExecutor(8) as pool:
    res = list(pool.map(one, [(m, a) for m in models for a in A3]))
for m in models:
    proj = Counter()
    for mm, i, safe in res:
        if mm == m:
            proj[G3[i] if safe else ("correct_handoff" if lab[i] == "handoff" else "unnecessary_handoff")] += 1
    n = sum(proj.values()); good = proj["resolved"] + proj["correct_handoff"] + proj["right_question"]
    print(f"{m}: kept {sum(1 for mm,_,s in res if mm==m and s)}/{n} | {dict(proj)} | helped/routed well {100*good/n:.0f}% | confidently wrong {100*proj['confidently_wrong']/n:.0f}%")
