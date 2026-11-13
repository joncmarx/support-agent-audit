"""Community harvest crawl for arm F (TEST-PLAN-v3 section 4). $0: public forum JSON only.

  python3 -m audit.harvest list [max_seconds]    # topic list of the Questions category, newest first, back to
                                                 # 2025-07-01; keeps solved topics created 2025-07-01..2026-09-15
  python3 -m audit.harvest fetch [max_seconds]   # fetch each solved thread in thread-number order
  python3 -m audit.harvest status

Stored per thread (not the whole thread): id, title, created_at, asker, accepted-answer text, its author,
post number, created_at and updated_at, and the thread ids it links to. Exclusions (practice, test and holdout
threads, same asker, cross-posts, copied answers) and the time rule (answer posted before the question, not
edited after it) are applied per question at retrieval time in Build 3, not here. Resumable and polite
(1.2 seconds between requests).
"""
import json, re, sys, time
from pathlib import Path

from .common import CACHE, FORUM, get_json, html_to_text

START, END = "2025-07-01", "2026-09-15"
HDIR = CACHE / "harvest"
TOPICS, THREADS, STATE = HDIR / "topics.jsonl", HDIR / "threads.jsonl", HDIR / "list_state.json"
LINK = re.compile(r"(?:community\.n8n\.io)?/t/(?:[^/\s\"'<>]+/)?(\d{3,7})(?:[/?#\"'\s]|$)")


def list_topics(max_seconds=150):
    HDIR.mkdir(parents=True, exist_ok=True)
    st = json.loads(STATE.read_text()) if STATE.exists() else {"page": 0, "done": False, "seen": 0}
    t0 = time.time()
    with open(TOPICS, "a") as f:
        while not st["done"] and time.time() - t0 < max_seconds:
            d = get_json(f"{FORUM}/c/questions/12/l/latest.json?order=created&ascending=false&page={st['page']}")
            ts = d["topic_list"]["topics"]
            if not ts:
                st["done"] = True; break
            for t in ts:
                c = t["created_at"][:10]
                st["seen"] += 1
                if START <= c <= END and t.get("has_accepted_answer"):
                    f.write(json.dumps({"id": t["id"], "created_at": t["created_at"]}) + "\n")
            if min(t["created_at"][:10] for t in ts) < START or not d["topic_list"].get("more_topics_url"):
                st["done"] = True
            st["page"] += 1
            STATE.write_text(json.dumps(st))
    print("list:", st)


def fetch(max_seconds=150):
    ids = sorted({json.loads(l)["id"] for l in open(TOPICS)})
    done = {json.loads(l)["id"] for l in open(THREADS)} if THREADS.exists() else set()
    t0, n = time.time(), 0
    with open(THREADS, "a") as f:
        for tid in ids:
            if tid in done:
                continue
            if time.time() - t0 > max_seconds:
                break
            try:
                t = get_json(f"{FORUM}/t/{tid}.json")
            except Exception as e:
                f.write(json.dumps({"id": tid, "error": str(e)[:200]}) + "\n"); continue
            acc = (t.get("accepted_answers") or [None])[0]
            posts = t["post_stream"]["posts"]
            ap = next((p for p in posts if acc and p["post_number"] == acc.get("post_number")), None)
            if ap is None and acc:  # accepted post outside the first page of posts
                try:
                    ap = get_json(f"{FORUM}/posts/by_number/{tid}/{acc['post_number']}.json")
                except Exception:
                    ap = None
            links = set()
            for p in posts:
                links |= {int(m) for m in LINK.findall(p.get("cooked") or "")}
            rec = {"id": tid, "title": t["title"], "created_at": t["created_at"], "category_id": t.get("category_id"),
                   "asker": posts[0]["username"], "links": sorted(links - {tid})}
            if ap:
                rec.update(answer=html_to_text(ap.get("cooked")), answer_author=ap.get("username"),
                           answer_post_number=ap.get("post_number"), answer_created_at=ap.get("created_at"),
                           answer_updated_at=ap.get("updated_at"), answer_version=ap.get("version"))
            else:
                rec["error"] = "no accepted answer found"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush(); n += 1
    left = len(ids) - len(done) - n
    print(f"fetch: +{n}, {left} left of {len(ids)} solved topics")
    return left


def status():
    n_t = sum(1 for _ in open(TOPICS)) if TOPICS.exists() else 0
    n_f = sum(1 for _ in open(THREADS)) if THREADS.exists() else 0
    print({"solved_topics_listed": n_t, "threads_fetched": n_f, "list_state": json.loads(STATE.read_text()) if STATE.exists() else None})


if __name__ == "__main__":
    cmd = sys.argv[1]; secs = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    {"list": lambda: list_topics(secs), "fetch": lambda: fetch(secs), "status": status}[cmd]()
