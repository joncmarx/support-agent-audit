"""Command line for the audit. Every step is resumable: rerun the same command to continue.

  python3 -m audit.run label                                   # handoff labels for all 150 questions
  python3 -m audit.run answer --config v1 --model <id> --split dev
  python3 -m audit.run grade  --config v1 --model <id> --split dev
  python3 -m audit.run score  --config v1 --model <id> --split dev
"""
import argparse, json, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import llm
from .bot import answer
from .common import CACHE, OUT_DATA, RUNS, read_jsonl
from .docs_index import Docs
from .grade import grade, label, reference_check

LABELS = OUT_DATA / "labels.jsonl"
REFCHECK = OUT_DATA / "reference_check.jsonl"


def slug(model):
    return model.replace("/", "_").replace(":", "_")


def questions(split):
    rows = read_jsonl(CACHE / "questions_full.jsonl")
    return [r for r in rows if split == "all" or r["split"] == split]


def done_ids(path):
    return {r["id"] for r in read_jsonl(path)} if path.exists() else set()


def parallel(items, fn, out_path, workers, max_seconds):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    todo = [x for x in items if x["id"] not in done_ids(out_path)]
    t0, n, errors = time.time(), 0, []
    with ThreadPoolExecutor(workers) as pool, open(out_path, "a") as f:
        futures = {}
        it = iter(todo)
        def submit():
            x = next(it, None)
            if x is not None and time.time() - t0 < max_seconds:
                futures[pool.submit(fn, x)] = x
        for _ in range(workers):
            submit()
        while futures:
            for fut in as_completed(list(futures)):
                x = futures.pop(fut)
                try:
                    f.write(json.dumps(fut.result(), ensure_ascii=False) + "\n"); f.flush(); n += 1
                except Exception as e:
                    errors.append((x["id"], str(e)[:200]))
                submit()
                break
    left = len(todo) - n
    print(f"{out_path.name} ({out_path.parent.name}): +{n} done, {left} left, {len(errors)} errors")
    for e in errors[:5]:
        print("  error", e)
    return left


def cmd_refcheck(a):
    parallel(questions("all"), lambda q: reference_check(llm.chat, q), REFCHECK, a.workers, a.max_seconds)


def usable_ids():
    return {r["id"] for r in read_jsonl(REFCHECK) if r["usable"]}


def cmd_label(a):
    docs = Docs()
    parallel(questions("all"), lambda q: label(llm.chat, docs, q), LABELS, a.workers, a.max_seconds)


def run_dir(a):
    return RUNS / f"{a.config}__{slug(a.model)}" / a.split


def cmd_answer(a):
    docs = Docs()
    keep = usable_ids()
    parallel([q for q in questions(a.split) if q["id"] in keep], lambda q: answer(llm.chat, a.model, docs, q, a.config),
             run_dir(a) / "answers.jsonl", a.workers, a.max_seconds)


def cmd_grade(a):
    docs = Docs()
    by_id = {c["id"]: c for c in docs.chunks}
    labels = {r["id"]: r for r in read_jsonl(LABELS)}
    answers = {r["id"]: r for r in read_jsonl(run_dir(a) / "answers.jsonl")}
    keep = usable_ids()
    qs = [q for q in questions(a.split) if q["id"] in answers and q["id"] in keep]
    parallel(qs, lambda q: grade(llm.chat, by_id, q, labels[q["id"]], answers[q["id"]]),
             run_dir(a) / "grades.jsonl", a.workers, a.max_seconds)


def cmd_score(a):
    keep = usable_ids()
    grades = [g for g in read_jsonl(run_dir(a) / "grades.jsonl") if g["id"] in keep]
    n = len(grades)
    c = Counter(g["outcome"] for g in grades)
    good = c["resolved"] + c["correct_handoff"] + c["right_question"]
    print(f"{a.config} on {a.model}, {a.split} set, n={n}")
    for k in ["resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "confidently_wrong"]:
        print(f"  {k:20s} {c[k]:3d}  {100 * c[k] / max(n, 1):5.1f}%")
    print(f"  helped or routed well: {100 * good / max(n, 1):.1f}%   confidently wrong: {100 * c['confidently_wrong'] / max(n, 1):.1f}%")
    print(f"  reliability fails: {sum(g['reliability'] == 'fail' for g in grades)}   "
          f"mean competence {sum(g['competence'] for g in grades) / max(n, 1):.2f}   mean empathy {sum(g['empathy'] for g in grades) / max(n, 1):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["refcheck", "label", "answer", "grade", "score"])
    ap.add_argument("--config", default="v1")
    ap.add_argument("--model")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-seconds", type=int, default=140)
    a = ap.parse_args()
    {"refcheck": cmd_refcheck, "label": cmd_label, "answer": cmd_answer, "grade": cmd_grade, "score": cmd_score}[a.cmd](a)
