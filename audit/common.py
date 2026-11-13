"""Shared paths and helpers."""
import html, json, re, time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import os

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
DATA = ROOT / "data"
DRY = os.environ.get("AUDIT_DRY_RUN") == "1"
# Dry runs write somewhere harmless, so test output never mixes with real results.
RUNS = CACHE / "dryrun" / "runs" if DRY else ROOT / "runs"
OUT_DATA = CACHE / "dryrun" if DRY else DATA
FORUM = "https://community.n8n.io"
UA = "support-agent-audit/0.1 (portfolio research; github.com/joncmarx)"

_session = requests.Session()
_session.headers["User-Agent"] = UA


def get_json(url, tries=5, pause=1.2):
    """Polite GET with backoff. Sleeps `pause` seconds after every request."""
    for attempt in range(tries):
        try:
            r = _session.get(url, timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 10)) + 1)
                continue
            r.raise_for_status()
            time.sleep(pause)
            return r.json()
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def compact_workflow(raw):
    """URL-encoded n8n workflow JSON -> compact JSON a support agent would read (no ids, positions or credentials)."""
    from urllib.parse import unquote
    try:
        wf = json.loads(unquote(raw))
    except (ValueError, TypeError):
        return "(workflow could not be read)"
    nodes = [{"name": n.get("name"), "type": n.get("type"), "typeVersion": n.get("typeVersion"),
              "parameters": n.get("parameters", {})} for n in wf.get("nodes", [])]
    conns = {src: [[c.get("node") for c in branch or []] for branch in out.get("main", [])]
             for src, out in (wf.get("connections") or {}).items()}
    text = json.dumps({"nodes": nodes, "connections": conns}, ensure_ascii=False)
    return text if len(text) <= 6000 else text[:6000] + " …(truncated)"


TEMPLATE_LINES = [
    "Describe the problem/error/question", "What is the error message (if any)?",
    "Please share your workflow", "Share the output returned by the last node",
    "Information on your n8n setup", "n8n version:", "Database (default: SQLite):",
    "n8n EXECUTIONS_PROCESS setting (default: own, main):",
    "Running n8n via (Docker, npm, n8n cloud, desktop app):", "Operating system:",
]


def content_words(text):
    """Word count without the forum's question-template headings, images and code/workflow blocks."""
    t = re.sub(r"```.*?```", " ", text, flags=re.S)
    for line in TEMPLATE_LINES:
        t = t.replace(line, " ")
    return words(t.replace("[image]", " "))


def html_to_text(cooked):
    """Discourse 'cooked' HTML -> plain text that keeps code blocks and shared workflows, and marks images."""
    soup = BeautifulSoup(cooked or "", "html.parser")
    for q in soup.select("aside.quote, aside.onebox, div.onebox"):
        q.decompose()
    for demo in soup.find_all("n8n-demo"):
        demo.replace_with("\n```json (shared workflow)\n" + compact_workflow(demo.get("workflow")) + "\n```\n")
    for box in soup.select("div.lightbox-wrapper"):
        box.replace_with("[image]")
    for img in soup.find_all("img"):
        if "emoji" in (img.get("class") or []):
            img.replace_with(img.get("alt", ""))
        else:
            img.replace_with("[image]")
    for pre in soup.find_all("pre"):
        pre.replace_with("\n```\n" + pre.get_text() + "\n```\n")
    for code in soup.find_all("code"):
        code.replace_with("`" + code.get_text() + "`")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "div", "details"]):
        tag.insert_after("\n")
    text = html.unescape(soup.get_text())
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def words(text):
    return len(re.findall(r"\w+", text))


ES = set("el la de que y en los las un una por para con no es lo como pero más mi me se al del tengo estoy hola gracias ayuda cuando porque este esta nodo flujo".split())
EN = set("the and to is in it of for that with on my this have i you but not are be from".split())


def language(text):
    w = re.findall(r"[a-záéíóúñü]+", text.lower())
    es, en = sum(x in ES for x in w), sum(x in EN for x in w)
    return "es" if es > max(3, 1.5 * en) else "en"


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
