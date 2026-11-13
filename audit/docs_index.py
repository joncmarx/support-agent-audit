"""Chunk the n8n docs (pinned commit) and search them.

Build:  python3 -m audit.docs_index build --src /path/to/n8n-docs
        (clone: git clone https://github.com/n8n-io/n8n-docs && git checkout <data/docs_commit.txt>)
The docs are fetched, never copied into this repo: chunks live in .cache/ (git-ignored).
"""
import argparse, json, math, re, subprocess
from collections import Counter
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from .common import CACHE, DATA, read_jsonl, write_jsonl

CHUNKS = CACHE / "docs_chunks.jsonl"
MAX_WORDS = 350
INCLUDE_RE = re.compile(r'\{%\s*include\s+"([^"]+)"\s*%\}')


def load_reusable(src):
    """GitBook reusable-content IDs -> file text, via the repo's own index."""
    idx = (src / "REUSABLE_CONTENT_INDEX.md").read_text()
    files = {p.stem: p for p in (src / "docs/reusable-content").rglob("*.md")}
    out = {}
    for m in re.finditer(r"^\| `([A-Za-z0-9]+)` \| ([^|]+?) \|", idx, re.M):
        rid, name = m.group(1), m.group(2).strip()
        if name in files:
            out[rid] = files[name].read_text()
    return out


def split_front_matter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(text[3:end]) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, text[end + 4:]
    return {}, text


def resolve_includes(text, here, reusable, depth=0):
    def sub(m):
        target = m.group(1)
        if depth > 3:
            return ""
        rid = re.search(r"/reusable/([A-Za-z0-9]+)", target)
        if rid:
            body = reusable.get(rid.group(1), "")
        else:
            space_root = next((p for p in here.parents if (p / ".gitbook").exists()), here.parent)
            path = (space_root / target) if target.startswith(".gitbook") else (here.parent / target)
            body = path.read_text() if path.exists() else ""
        _, body = split_front_matter(body)
        return resolve_includes(body, here, reusable, depth + 1)
    return INCLUDE_RE.sub(sub, text)


def clean(md):
    md = re.sub(r'<a href="#[^"]*" id="[^"]*"></a>', "", md)
    md = re.sub(r'\{%\s*hint[^%]*%\}', "Note: ", md)
    md = re.sub(r'\{%\s*tab title="([^"]*)"\s*%\}', r"\n\1:\n", md)
    md = re.sub(r'\{%\s*embed url="([^"]*)"[^%]*%\}', r"(\1)", md)
    md = re.sub(r'\{%\s*(end\w+|tabs|content[^%]*|stepper|step|endstep|endstepper|columns|column|endcolumn|endcolumns)\s*%\}', "", md)
    md = re.sub(r'\{%[^%]*%\}', "", md)
    if "<table" in md or "<td" in md:
        def table(m):
            soup = BeautifulSoup(m.group(0), "html.parser")
            rows = [" | ".join(c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])) for tr in soup.find_all("tr")]
            return "\n".join(rows)
        md = re.sub(r"<table.*?</table>", table, md, flags=re.S)
    md = re.sub(r"<figure>.*?</figure>", "", md, flags=re.S)
    md = re.sub(r"</?(kbd|strong|em|b|i|code|br|p|div|span|details|summary|mark)[^>]*>", "", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def page_url(meta, rel):
    url = meta.get("url") or meta.get("originalUrl")
    if url:
        return str(url).strip()
    path = re.sub(r"(README)?\.md$", "", rel).rstrip("/")
    return f"https://docs.n8n.io/{path}"


def _pieces(para):
    """Split an oversized paragraph (big table or list) by lines."""
    if len(para.split()) <= MAX_WORDS:
        return [para]
    out, cur, n = [], [], 0
    for line in para.splitlines():
        w = len(line.split())
        if cur and n + w > MAX_WORDS:
            out.append("\n".join(cur)); cur, n = [], 0
        cur.append(line); n += w
    if cur:
        out.append("\n".join(cur))
    return out


def chunk_page(title, url, body):
    """Pack a page's paragraphs, in order, into chunks of up to MAX_WORDS.
    Each chunk records the heading it starts under, and a new ## heading starts a new chunk
    once the current one is at least half full."""
    units, heading = [], ""
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", block)
        if m:
            if len(m.group(1)) == 1 and not title:
                title = m.group(2).strip()
            else:
                heading = m.group(2).strip()
                units.append(("H", heading, block))
            rest = block[m.end():].strip()
            if not rest:
                continue
            block = rest
        for piece in _pieces(block):
            units.append(("P", heading, piece))
    chunks, cur, n, cur_heading = [], [], 0, ""
    for kind, h, text in units:
        w = len(text.split())
        if cur and (n + w > MAX_WORDS or (kind == "H" and n >= MAX_WORDS // 2)):
            chunks.append((cur_heading, "\n\n".join(cur))); cur, n = [], 0
        if not cur:
            cur_heading = h
        cur.append(text); n += w
    if cur:
        chunks.append((cur_heading, "\n\n".join(cur)))
    return [{"url": url, "page_title": title, "heading": h, "text": t} for h, t in chunks if len(t.split()) >= 8]


def build(src):
    src = Path(src)
    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    reusable = load_reusable(src)
    rows = []
    for path in sorted((src / "docs").rglob("*.md")):
        rel = str(path.relative_to(src / "docs"))
        if "/.gitbook/" in f"/{rel}" or rel.startswith("reusable-content/") or path.name == "SUMMARY.md":
            continue
        meta, body = split_front_matter(path.read_text())
        body = clean(resolve_includes(body, path, reusable))
        title = str(meta.get("title") or "").strip()
        for i, c in enumerate(chunk_page(title, page_url(meta, rel), body)):
            c["id"] = f"{rel}#{i}"
            rows.append(c)
    write_jsonl(CHUNKS, rows)
    (DATA / "docs_commit.txt").write_text(f"https://github.com/n8n-io/n8n-docs/tree/{commit}\n")
    print(f"commit {commit[:12]} | reusable blocks {len(reusable)} | chunks {len(rows)} | pages {len({r['url'] for r in rows})}")


# ---------- search ----------
TOKEN = re.compile(r"[a-z0-9_$.]+")
STOP = set("the a an and or to of in on for is it this that with as be are by at from you your can if not use using".split())


def tokens(text):
    return [t.strip(".") for t in TOKEN.findall(text.lower()) if t.strip(".") and t not in STOP]


class BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        self.docs = [Counter(tokens(d)) for d in docs]
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b
        self.index = {}
        for i, d in enumerate(self.docs):
            for t in d:
                self.index.setdefault(t, []).append(i)

    def search(self, query, k=10):
        scores = Counter()
        for t in set(tokens(query)):
            for i in self.index.get(t, []):
                tf = self.docs[i][t]
                scores[i] += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return scores.most_common(k)


EMBED_MODEL = "baai/bge-m3"  # multilingual, so a Spanish question can find an English page (v1.1)
VECTORS = CACHE / "docs_vectors.npy"


def chunk_text(c):
    return f"{c['page_title']} — {c['heading']}\n{c['text']}"


def embed_all(batch=64, max_seconds=160):
    """Embed every chunk once (resumable, saves partial progress)."""
    import time
    import numpy as np
    from .llm import embed
    chunks = read_jsonl(CHUNKS)
    part = CACHE / "docs_vectors_partial.npy"
    done = np.load(part) if part.exists() else np.zeros((0, 0), dtype=np.float32)
    t0 = time.time()
    rows = [done] if done.size else []
    n = len(done) if done.size else 0
    while n < len(chunks) and time.time() - t0 < max_seconds:
        vecs = np.array(embed(EMBED_MODEL, [chunk_text(c)[:6000] for c in chunks[n:n + batch]], tag="docs"), dtype=np.float32)
        rows.append(vecs)
        n += len(vecs)
        np.save(part, np.vstack(rows))
    if n >= len(chunks):
        m = np.vstack(rows)
        m /= np.linalg.norm(m, axis=1, keepdims=True)
        np.save(VECTORS, m)
        print(f"embedded all {n} chunks with {EMBED_MODEL}")
    else:
        print(f"embedded {n}/{len(chunks)}; run again to continue")


class Docs:
    """Loads chunks; keyword search always, embedding search once vectors exist."""
    def __init__(self):
        self.chunks = read_jsonl(CHUNKS)
        self.bm25 = BM25([f"{c['page_title']} {c['heading']} {c['text']}" for c in self.chunks])
        self.vectors = None
        if VECTORS.exists():
            import numpy as np
            self.vectors = np.load(VECTORS)

    def keyword(self, query, k=6):
        return [(self.chunks[i], s) for i, s in self.bm25.search(query, k)]

    def semantic(self, query, k=6):
        import numpy as np
        from .llm import embed
        if self.vectors is None:
            from .common import DRY
            if DRY:
                return self.keyword(query, k)
            raise SystemExit("No doc embeddings yet: run `python3 -m audit.docs_index embed`.")
        q = np.array(embed(EMBED_MODEL, [query[:6000]], tag="query")[0], dtype=np.float32)
        q /= np.linalg.norm(q)
        sims = self.vectors @ q
        top = np.argsort(-sims)[:k]
        return [(self.chunks[i], float(sims[i])) for i in top]

    def hybrid(self, query, k=6, pool=30):
        """Reciprocal-rank fusion of keyword and semantic results."""
        scores = {}
        for results in (self.keyword(query, pool), self.semantic(query, pool)):
            for rank, (c, _) in enumerate(results):
                scores[c["id"]] = scores.get(c["id"], 0) + 1 / (60 + rank)
        by_id = {c["id"]: c for c in self.chunks}
        return [(by_id[i], s) for i, s in sorted(scores.items(), key=lambda x: -x[1])[:k]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "embed"])
    ap.add_argument("--src")
    a = ap.parse_args()
    build(a.src) if a.cmd == "build" else embed_all()
