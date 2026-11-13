"""Collect the question set from the n8n community forum.

Step 1 (candidates): search solved threads in the Questions category, month by month.
Step 2 (fetch): fetch threads in a seeded random order, keep those that pass the filters,
         until TARGET threads pass. Resumable: every fetched thread is cached.
Step 3 (build): write data/questions.jsonl (public: ids and metadata only) and
         .cache/questions_full.jsonl (private: question and accepted-answer text).

Filters (written before looking at results):
  - category Questions (id 12), created 2026-01-01 .. 2026-09-15
  - has an accepted answer written by someone other than the asker, and not by the forum's auto-reply account
  - question >= 20 words of its own text (not counting the forum's template headings, images or code); accepted answer >= 20 words
  - if the question contains images, at least 60 words of its own text (the bot can't see images)
  - shared workflows are kept as compact JSON, because a human support agent would read them
  (Filter fix 2026-09-29, before any bot run: template headings no longer count toward the word minimums.)
  - English (Spanish threads are kept aside for v1.1)
"""
import argparse, json, random, time
from datetime import date
from urllib.parse import quote

from .common import CACHE, DATA, FORUM, get_json, html_to_text, words, content_words, language, write_jsonl

QUESTIONS_CATEGORY = 12
START, END = "2026-01-01", "2026-09-15"
AUTO_ACCOUNTS = {"n8n", "system"}
TARGET = 150
SEED = 20260929
CAND = CACHE / "candidates.json"
TOPICS = CACHE / "forum"


def months():
    for m in range(1, 10):
        a = date(2026, m, 1).isoformat()
        b = date(2026, m + 1, 1).isoformat() if m < 9 else "2026-09-16"
        yield a, b


def candidates():
    if CAND.exists():
        return json.loads(CAND.read_text())
    ids = {}
    for a, b in months():
        for page in (1, 2, 3):
            q = f"status:solved category:questions after:{a} before:{b}"
            d = get_json(f"{FORUM}/search.json?q={quote(q)}&page={page}")
            for t in d.get("topics", []):
                if t.get("category_id") == QUESTIONS_CATEGORY:
                    ids[str(t["id"])] = t["created_at"][:10]
            if not d.get("grouped_search_result", {}).get("more_full_page_results"):
                break
        print(a, "candidates so far:", len(ids), flush=True)
    CAND.parent.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(ids))
    return ids


def extract(t):
    """Return (row, reason). row is None when the thread fails a filter."""
    if t.get("category_id") != QUESTIONS_CATEGORY:
        return None, "category"
    created = t["created_at"][:10]
    if not (START <= created <= END):
        return None, "date"
    op = t["post_stream"]["posts"][0]
    acc = (t.get("accepted_answers") or [None])[0]
    if not acc:
        return None, "no_accepted"
    if acc["username"] == op["username"]:
        return None, "self_answered"
    if acc["username"].lower() in AUTO_ACCOUNTS:
        return None, "auto_reply"
    q_text = html_to_text(op["cooked"])
    a_text = html_to_text(acc["cooked"])
    has_img = "[image]" in q_text
    qw = content_words(q_text)
    if qw < 20:
        return None, "question_short"
    if has_img and qw < 60:
        return None, "image_dependent"
    if words(a_text) < 20:
        return None, "answer_short"
    lang = language(t["title"] + " " + q_text)
    row = {
        "id": t["id"],
        "url": f"{FORUM}/t/{t['slug']}/{t['id']}",
        "title": t["title"],
        "created_at": created,
        "lang": lang,
        "has_images": has_img,
        "tags": t.get("tags", []),
        "question": q_text,
        "accepted_answer": a_text,
        "accepted_post_number": acc.get("post_number"),
    }
    return row, ("spanish" if lang == "es" else "ok")


def fetch(max_seconds):
    ids = candidates()
    order = sorted(ids, key=int)
    random.Random(SEED).shuffle(order)
    TOPICS.mkdir(parents=True, exist_ok=True)
    t0, passed, reasons = time.time(), [], {}
    for tid in order:
        path = TOPICS / f"{tid}.json"
        if not path.exists():
            if time.time() - t0 > max_seconds:
                break
            try:
                path.write_text(json.dumps(get_json(f"{FORUM}/t/{tid}.json")))
            except Exception as e:  # deleted or private thread
                path.write_text(json.dumps({"_error": str(e)}))
        t = json.loads(path.read_text())
        if "_error" in t:
            reasons["error"] = reasons.get("error", 0) + 1
            continue
        row, why = extract(t)
        reasons[why] = reasons.get(why, 0) + 1
        if why == "ok":
            passed.append(row)
            if len(passed) >= TARGET:
                break
    print("candidates:", len(ids), "| checked:", sum(reasons.values()), "| reasons:", reasons, flush=True)
    return passed


def build(passed):
    rows = sorted(passed, key=lambda r: r["id"])
    random.Random(SEED + 1).shuffle(rows)
    for i, r in enumerate(rows):
        r["split"] = "dev" if i < 50 else "test"
    write_jsonl(CACHE / "questions_full.jsonl", rows)
    public = [{k: r[k] for k in ("id", "url", "title", "created_at", "lang", "has_images", "split")} for r in rows]
    write_jsonl(DATA / "questions.jsonl", sorted(public, key=lambda r: (r["split"], r["id"])))
    print("wrote", len(rows), "questions:", sum(r["split"] == "dev" for r in rows), "dev /",
          sum(r["split"] == "test" for r in rows), "test")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seconds", type=int, default=150)
    args = ap.parse_args()
    passed = fetch(args.max_seconds)
    if len(passed) >= TARGET:
        build(passed)
    else:
        print(f"passed {len(passed)}/{TARGET} so far; run again to continue")
