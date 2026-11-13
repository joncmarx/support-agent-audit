"""Original (first-posted) versions of a thread's title and first post, from the forum's public edit history
(TEST-PLAN-v3 section 4). Discourse revision N shows version N-1 beside version N. The first revision that
changed the body holds, on its "previous" side, the body as first posted; the same goes for the title.
Moderators can hide revisions (HTTP 403); then the original can't be recovered, the current text is used,
and the question is flagged. Revisions are cached as fetched."""
import json
import re

from bs4 import BeautifulSoup

from .common import FORUM, get_json, html_to_text


def fetch_revision(post_id, n, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / f"{post_id}_r{n}.json"
    if not p.exists():
        try:
            p.write_text(json.dumps(get_json(f"{FORUM}/posts/{post_id}/revisions/{n}.json")))
        except Exception as e:  # hidden by a moderator (403) or deleted
            p.write_text(json.dumps({"_error": str(e)[:300]}))
    return json.loads(p.read_text())


def _side(html, which):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one(f"div.revision-content.--{which}") or soup.select_one(f"div.--{which}")
    if div is None:
        return None
    for tag in div.find_all("ins" if which == "previous" else "del"):
        tag.decompose()
    for tag in div.find_all("del" if which == "previous" else "ins"):
        tag.unwrap()
    # Cooked HTML separates top-level blocks with newlines; the diff view doesn't. Restore them so the
    # text conversion matches the way round one converted today's posts.
    return "\n".join(str(c) for c in div.children if str(c).strip())


def _revisions(op, cache_dir):
    return [(n, fetch_revision(op["id"], n, cache_dir)) for n in range(2, op.get("version", 1) + 1)]


def original(topic, cache_dir):
    """Return dict(title, question, versions, title_from_history, body_from_history, flags).
    question is None when the body's history is hidden; the caller then uses the current text and flags it."""
    op = topic["post_stream"]["posts"][0]
    out = {"versions": op.get("version", 1), "flags": []}
    if op.get("version", 1) <= 1:
        out.update(title=topic["title"], question=html_to_text(op["cooked"]), title_from_history=True, body_from_history=True)
        return out
    revs = _revisions(op, cache_dir)
    hidden = [n for n, r in revs if "_error" in r]
    title = body = None
    title_known = body_known = True
    for n, r in revs:  # oldest first
        if "_error" in r:
            # A hidden revision may hide the first change; nothing after it can prove the original text.
            if title is None:
                title_known = False
            if body is None:
                body_known = False
            break
        if title is None and r.get("title_changes"):
            title = BeautifulSoup(_side(r["title_changes"].get("side_by_side"), "previous") or "", "html.parser").get_text().strip()
        if body is None and r.get("body_changes"):
            prev = _side(r["body_changes"].get("side_by_side"), "previous")
            if prev is not None:
                body = html_to_text(prev)
    if title is None and title_known:
        title = topic["title"]            # the title was never edited
    if body is None and body_known:
        body = html_to_text(op["cooked"])  # only the title or tags were edited
    if title is None:
        title = re.sub(r"\s*\[solved\]\s*", " ", topic["title"], flags=re.I).strip()
        out["flags"].append("title history hidden: current title used, [SOLVED] removed")
    if body is None:
        out["flags"].append("first-post history hidden: current text used")
    if hidden:
        out["hidden_revisions"] = hidden
    out.update(title=title, question=body, title_from_history=title_known, body_from_history=body_known)
    return out


def check_current_side(topic, cache_dir):
    """Validation of the extraction: the 'current' side of the last revision that changed the body must
    reproduce today's first post after the same HTML-to-text conversion. Returns True, False or None
    (None = no visible body revision to check)."""
    op = topic["post_stream"]["posts"][0]
    for n in range(op.get("version", 1), 1, -1):
        r = fetch_revision(op["id"], n, cache_dir)
        if "_error" in r:
            return None
        if r.get("body_changes"):
            cur = _side(r["body_changes"].get("side_by_side"), "current")
            return cur is not None and html_to_text(cur) == html_to_text(op["cooked"])
    return None
