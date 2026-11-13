"""Pick the bot model: run v1 on the same 5 dev questions with each candidate (dev set only)."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor

from . import llm
from .bot import answer
from .common import RUNS
from .docs_index import Docs
from .run import questions, slug

CANDIDATES = sys.argv[1:] or ["google/gemini-3.8-flash", "openai/gpt-5.4-mini", "deepseek/deepseek-v4.1-flash"]
docs = Docs()
qs = sorted(questions("dev"), key=lambda q: q["id"])[:5]
out = RUNS / "_model_trial"
out.mkdir(parents=True, exist_ok=True)


def one(args):
    model, q = args
    t = time.time()
    try:
        r = answer(llm.chat, model, docs, q, "v1")
    except Exception as e:
        r = {"id": q["id"], "model": model, "error": str(e)[:300]}
    r["seconds"] = round(time.time() - t, 1)
    return r


with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(one, [(m, q) for m in CANDIDATES for q in qs]))
for m in CANDIDATES:
    rows = [r for r in results if r["model"] == m]
    (out / f"{slug(m)}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    ok = [r for r in rows if "answer" in r]
    print(f"{m}: {len(ok)}/5 ok, empty {sum(not r['answer'] for r in ok)}, "
          f"median {sorted(r['seconds'] for r in rows)[len(rows)//2]}s, cost ${sum(r.get('cost') or 0 for r in ok):.4f}, "
          f"avg words {sum(len(r['answer'].split()) for r in ok)//max(len(ok),1)}")
    for r in rows:
        if "error" in r:
            print("   error:", r["error"][:200])
