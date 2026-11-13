"""Build the public results page: site/index.html (full page for Cloudflare Pages) from site/template.html + graded runs.
Only our own material goes in: thread titles and links, the labeler's one-line summary of the fix, the bot's replies,
the reviewer's notes and the grader's reasoning. Forum post bodies stay out."""
import json, re
from collections import Counter

from .common import CACHE, DATA, RUNS, ROOT, read_jsonl

MODEL = "openai/gpt-5.4-mini"
SHOWN = ["v1", "v2", "v3", "v4"]
NAMES = {"v1": "Default settings", "v2": "Told to commit", "v3": "Triage first", "v4": "Draft, then review"}


def load(cfg, split):
    d = RUNS / f"{cfg}__{MODEL.replace('/', '_')}" / split
    return ({r["id"]: r for r in read_jsonl(d / "answers.jsonl")}, {r["id"]: r for r in read_jsonl(d / "grades.jsonl")})


def summary(grades):
    c = Counter(g["outcome"] for g in grades)
    n = len(grades)
    return {"n": n, **{k: c[k] for k in ["resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff", "confidently_wrong"]}}


def build():
    Q = {q["id"]: q for q in read_jsonl(CACHE / "questions_full.jsonl")}
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    labels = {r["id"]: r for r in read_jsonl(DATA / "labels.jsonl")}
    runs = {c: load(c, "test") for c in SHOWN}
    ids = sorted(i for i in runs["v1"][1] if i in usable)
    items = []
    for i in ids:
        q, lab = Q[i], labels[i]
        row = {"id": i, "url": q["url"], "title": q["title"], "date": q["created_at"], "label": lab["label"],
               "reason": lab["reason"], "fix": lab["key_fix"], "replies": {}}
        for c in SHOWN:
            a, g = runs[c][0][i], runs[c][1][i]
            r = {"text": a["answer"], "outcome": g["outcome"], "note": g["rationale"],
                 "competence": g["competence"], "empathy": g["empathy"], "reliability": g["reliability"]}
            if c == "v4":
                r.update({"blocked": not a.get("review_safe", True), "review": a.get("review_problem", ""),
                          "draft": a.get("draft", ""), "triage": a.get("triage", "")})
            row["replies"][c] = r
        items.append(row)
    dev = {c: summary([g for g in read_jsonl(RUNS / f"{c}__{MODEL.replace('/', '_')}/dev/grades.jsonl") if g["id"] in usable])
           for c in ["v1", "v2", "v3", "v4"]}
    test = {c: summary([runs[c][1][i] for i in ids]) for c in SHOWN}
    commit = (DATA / "docs_commit.txt").read_text().strip()
    spend = round(sum(r["cost"] or 0 for r in read_jsonl(RUNS / "cost_ledger.jsonl")), 2)
    meta = {"model": MODEL, "judge": "anthropic/claude-sonnet-5.5", "docs_commit": commit, "spend": spend,
            "collected": 150, "unusable": 150 - len(usable), "dev_n": dev["v1"]["n"], "test_n": len(ids),
            "test_labels": dict(Counter(labels[i]["label"] for i in ids)),
            "all_labels": dict(Counter(labels[i]["label"] for i in usable)), "names": NAMES}
    payload = {"meta": meta, "test": test, "dev": dev, "items": items}
    (ROOT / "site" / "data.json").write_text(json.dumps(payload, ensure_ascii=False))
    tpl = (ROOT / "site" / "template.html").read_text()
    frag = tpl.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    head, body = frag.split("<!--BODY-->", 1)
    t = D_TEST = test["v4"]
    desc = (f"An AI support bot tested on {len(ids)} real n8n community questions. Default settings: "
            f"{test['v1']['confidently_wrong']} confidently wrong. Told to commit: {test['v2']['confidently_wrong']}. "
            f"With a reviewer: {test['v4']['confidently_wrong']}.")
    og = (f'<meta name="description" content="{desc}">\n<meta property="og:title" content="How often is your AI support agent confidently wrong?">\n'
          f'<meta property="og:description" content="{desc}">\n<meta property="og:type" content="article">\n')
    full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + og + head + "</head>\n<body>\n" + body + "</body>\n</html>\n")
    (ROOT / "site" / "index.html").write_text(full)
    (ROOT / "site" / "artifact.html").write_text(frag.replace("<!--BODY-->", ""))
    print(f"items {len(items)} | data {len(json.dumps(payload)) // 1024} KB | test {test} | spend ${spend}")


if __name__ == "__main__":
    build()
