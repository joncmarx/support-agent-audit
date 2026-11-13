"""Draw and seal the holdout (TEST-PLAN-v3 section 4). Prints counts and reason codes only: no titles, no text.

  python3 -m audit.holdout draw     # resumable; run until it reports 'complete'
  python3 -m audit.holdout seal     # write the sealed files and their hashes

Rules (written before any candidate was looked at):
- Same pool (1,031 candidates) and seeded order (seed 20260929) as round one; continue past the 150 threads
  round one drew, taking the next threads that pass round one's filters (collect.extract, unchanged).
- The bot sees the ORIGINAL title and first post (forum edit history). The forum machine-translates some posts,
  so "English" is checked on the original text too; a thread whose original first post isn't English fails
  the English filter.
- Excluded (checked against all 150 threads round one drew, and against earlier holdout picks):
  L  links to, or is linked from, one of those threads;
  X  cross-post: same asker, created within 14 days, similar title (difflib ratio >= 0.6 or content-word
     Jaccard >= 0.5);
  C  accepted answer copies a practice/test solution (a shared run of >= 25 words, or >= 50% of the shorter
     answer's 8-word shingles).
  An excluded thread is replaced by the next in order; inside the holdout, the first of a pair is kept.
- 100 threads form the holdout, followed by an ordered reserve of 20, used only under a rule JC approves
  (see PREREGISTRATION.md).
"""
import difflib, json, random, re, sys, time
from datetime import datetime
from pathlib import Path

from .collect import SEED, candidates, extract
from .common import CACHE, FORUM, ROOT, get_json, language, words
from .history import original

N, RESERVE = 100, 20
SEALED = ROOT / "sealed"
FCACHE, RCACHE = SEALED / "forum", SEALED / "revisions"
LOG = SEALED / "draw_log.jsonl"
LINK = re.compile(r"(?:community\.n8n\.io)?/t/(?:[^/\s\"'<>]+/)?(\d{3,7})(?:[/?#\"'\s]|$)")
STOP = set("the a an and or to of in on for is it this that with as be are by at from how not n8n node my i".split())


def order():
    ids = candidates()
    o = sorted(ids, key=int)
    random.Random(SEED).shuffle(o)
    return o


def round_one():
    """Replay round one's loop over its cache: the 150 threads it drew, and where it stopped."""
    drawn, stop = {}, None
    for i, tid in enumerate(order()):
        p = CACHE / "forum" / f"{tid}.json"
        if not p.exists():
            raise SystemExit(f"round-one cache incomplete at position {i}")
        t = json.loads(p.read_text())
        if "_error" in t:
            continue
        row, why = extract(t)
        if why == "ok":
            drawn[int(tid)] = (t, row)
            if len(drawn) == 150:
                stop = i
                break
    return drawn, stop


def links_out(t):
    ids = set()
    for p in t["post_stream"]["posts"]:
        ids |= {int(m) for m in LINK.findall(p.get("cooked") or "")}
    return ids - {t["id"]}


def cwords(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP}


def cross_post(t, row, other_t, other_row):
    if t["post_stream"]["posts"][0]["username"] != other_t["post_stream"]["posts"][0]["username"]:
        return False
    a = datetime.fromisoformat(t["created_at"][:19]); b = datetime.fromisoformat(other_t["created_at"][:19])
    if abs((a - b).days) > 14:
        return False
    r = difflib.SequenceMatcher(None, row["title"].lower(), other_row["title"].lower()).ratio()
    ca, cb = cwords(row["title"]), cwords(other_row["title"])
    jac = len(ca & cb) / max(1, len(ca | cb))
    return r >= 0.6 or jac >= 0.5


def _w(text):
    return re.findall(r"\w+", text.lower())


_SH = {}


def _shingles(text):
    if text not in _SH:
        w = _w(text)
        _SH[text] = (w, {tuple(w[i:i + 8]) for i in range(len(w) - 7)})
    return _SH[text]


def copied(a, b):
    (wa, sa), (wb, sb) = _shingles(a), _shingles(b)
    if min(len(wa), len(wb)) < 8 or not (sa & sb):
        return False  # a shared 25-word run would share at least 18 eight-word shingles
    m = difflib.SequenceMatcher(None, wa, wb, autojunk=False).find_longest_match(0, len(wa), 0, len(wb))
    if m.size >= 25:
        return True
    return len(sa & sb) / max(1, min(len(sa), len(sb))) >= 0.5


def fetch(tid):
    FCACHE.mkdir(parents=True, exist_ok=True)
    p = FCACHE / f"{tid}.json"
    if not p.exists():
        try:
            p.write_text(json.dumps(get_json(f"{FORUM}/t/{tid}.json")))
        except Exception as e:
            p.write_text(json.dumps({"_error": str(e)[:200]}))
    return json.loads(p.read_text())


def draw(max_seconds=165):
    t0 = time.time()
    r1, stop = round_one()
    r1_links = {tid: links_out(t) for tid, (t, _r) in r1.items()}
    done = {}
    if LOG.exists():
        for line in open(LOG):
            d = json.loads(line); done[d["id"]] = d
    picked = [d for d in done.values() if d["decision"] == "pick"]
    picked_rows = {}
    for d in picked:
        t = fetch(d["id"]); picked_rows[d["id"]] = (t, extract(t)[0])
    o = order()
    with open(LOG, "a") as log:
        for pos in range(stop + 1, len(o)):
            if len(picked) >= N + RESERVE:
                break
            tid = int(o[pos])
            if tid in done:
                continue
            if time.time() - t0 > max_seconds:
                print(f"paused at position {pos}: {len(picked)} picked so far; run again"); return False
            t = fetch(tid)
            rec = {"id": tid, "pos": pos}
            if "_error" in t:
                rec.update(decision="skip", reason="fetch_error")
            else:
                row, why = extract(t)
                if why != "ok":
                    rec.update(decision="skip", reason=why)
                else:
                    orig = original(t, RCACHE)
                    q_orig = orig["question"] if orig["question"] is not None else row["question"]
                    reasons = []
                    if language(orig["title"] + " " + q_orig) != "en" or t["post_stream"]["posts"][0].get("is_localized"):
                        reasons.append("original_not_english")
                    lo = links_out(t)
                    if lo & set(r1) or any(tid in s for s in r1_links.values()):
                        reasons.append("L_round_one")
                    if any(cross_post(t, row, ot, orow) for ot, orow in r1.values()):
                        reasons.append("X_round_one")
                    if any(copied(row["accepted_answer"], orow["accepted_answer"]) for _t, orow in r1.values()):
                        reasons.append("C_round_one")
                    for pid, (pt, prow) in picked_rows.items():
                        if tid in links_out(pt) or pid in lo or cross_post(t, row, pt, prow) or copied(row["accepted_answer"], prow["accepted_answer"]):
                            reasons.append("dup_in_holdout"); break
                    if reasons:
                        rec.update(decision="exclude", reason="+".join(reasons))
                    else:
                        rec.update(decision="pick", rank=len(picked) + 1, flags=orig["flags"], versions=orig["versions"])
                        picked.append(rec); picked_rows[tid] = (t, row)
            done[tid] = rec
            log.write(json.dumps(rec) + "\n"); log.flush()
    status = summary()
    print("complete" if len(picked) >= N + RESERVE else "pool exhausted", status)
    return True


def summary():
    from collections import Counter
    recs = [json.loads(l) for l in open(LOG)] if LOG.exists() else []
    c = Counter(r["decision"] for r in recs); reasons = Counter(r["reason"] for r in recs if r["decision"] != "pick")
    picks = [r for r in recs if r["decision"] == "pick"]
    return {"checked": len(recs), "decisions": dict(c), "reasons": dict(reasons),
            "flagged_originals": sum(bool(r.get("flags")) for r in picks[:N]),
            "edited_in_holdout": sum((r.get("versions") or 1) > 1 for r in picks[:N])}


def seal():
    import hashlib
    recs = [json.loads(l) for l in open(LOG)]
    picks = sorted((r for r in recs if r["decision"] == "pick"), key=lambda r: r["rank"])
    if len(picks) < N + RESERVE:
        raise SystemExit("draw is not complete")
    files = {}
    for name, group in (("holdout", picks[:N]), ("reserve", picks[N:N + RESERVE])):
        qs, sols = [], []
        for r in group:
            t = fetch(r["id"]); row, _ = extract(t)
            orig = original(t, RCACHE)
            acc = (t.get("accepted_answers") or [None])[0]
            ap = next((p for p in t["post_stream"]["posts"] if p["post_number"] == acc.get("post_number")), {})
            qs.append({"id": r["id"], "rank": r["rank"], "url": row["url"], "created_at": t["created_at"],
                       "title": orig["title"], "question": orig["question"] if orig["question"] is not None else row["question"],
                       "question_is_original": orig["question"] is not None, "flags": orig["flags"],
                       "has_images": row["has_images"], "tags": row["tags"], "split": name})
            sols.append({"id": r["id"], "accepted_answer": row["accepted_answer"], "accepted_post_number": row["accepted_post_number"],
                         "answer_created_at": ap.get("created_at"), "answer_updated_at": ap.get("updated_at")})
        for kind, rows in (("questions", qs), ("solutions", sols)):
            p = SEALED / f"{name}_{kind}.jsonl"
            p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
            files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    seal = {"sealed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": N, "reserve": RESERVE, "files": files,
            "draw_log_sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
            "rules_sha256": hashlib.sha256((ROOT / "audit/holdout.py").read_bytes()).hexdigest(),
            "summary": summary()}
    (SEALED / "SEAL.json").write_text(json.dumps(seal, indent=1))
    print(json.dumps(seal, indent=1))


if __name__ == "__main__":
    {"draw": lambda: draw(int(sys.argv[2]) if len(sys.argv) > 2 else 150), "seal": seal, "summary": lambda: print(summary())}[sys.argv[1]]()
