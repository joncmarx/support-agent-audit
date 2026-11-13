import sys, json; sys.path.insert(0,'.')
from pathlib import Path
from audit.history import original, check_current_side
def rj(p): return [json.loads(l) for l in open(p) if l.strip()]
usable = {r["id"] for r in rj("data/reference_check.jsonl") if r["usable"]}
Q = [q for q in rj(".cache/questions_full.jsonl") if q["id"] in usable]
cache = Path(".cache/revisions")
ok = 0; res = {}; mism = []
for q in Q:
    t = json.load(open(f".cache/forum/{q['id']}.json"))
    if t["post_stream"]["posts"][0]["version"] <= 1: continue
    v = check_current_side(t, cache); ok += (v is True)
    if v is False: mism.append(q["id"])
    if v is None: mism.append(('unchecked', q['id']))
    res[q["id"]] = original(t, cache)
    print(q["id"], "done", flush=True)
print("current-side reproduces today's post:", ok, "ok; mismatch:", mism)
print("flags:", {k: v["flags"] for k, v in res.items() if v["flags"]})
print("title changed:", sum(o["title"] != json.load(open(f".cache/forum/{k}.json"))["title"] for k, o in res.items()))
json.dump(res, open(".cache/originals_practice_test.json", "w"))
print("ALL DONE")
