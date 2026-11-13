"""OpenRouter client with retries, cost logging, and a dry-run mode.

The key is read from OPENROUTER_API_KEY, or from a KEY=value file outside this repo:
  $AUDIT_KEY_FILE, ~/mnt/Keys/openrouter-support-audit.env, ~/Keys/openrouter-support-audit.env
Set AUDIT_DRY_RUN=1 to exercise the pipeline with canned replies and no network.
"""
import json, os, threading, time
from pathlib import Path

import requests

from .common import RUNS

API = "https://openrouter.ai/api/v1"
DRY = os.environ.get("AUDIT_DRY_RUN") == "1"
LEDGER = RUNS / "cost_ledger.jsonl"
_lock = threading.Lock()


def _key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"].strip()
    for p in [os.environ.get("AUDIT_KEY_FILE"), "~/mnt/Keys/openrouter-support-audit.env",
              "~/Keys/openrouter-support-audit.env"]:
        if p and Path(p).expanduser().exists():
            for line in Path(p).expanduser().read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise SystemExit("No OpenRouter key found. See audit/llm.py for where it is read from.")


def _headers():
    return {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/joncmarx/support-agent-audit", "X-Title": "support-agent-audit"}


def _log(kind, model, usage, tag):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "model": model, "tag": tag,
           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
           "cost": usage.get("cost")}
    with _lock, open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")


def _post(path, body, tries=6):
    for attempt in range(tries):
        try:
            r = requests.post(f"{API}{path}", headers=_headers(), json=body, timeout=150)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 4 * 2 ** attempt))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:500]}")
            data = r.json()
            if "error" in data:
                raise RuntimeError(f"OpenRouter error: {str(data['error'])[:500]}")
            return data
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("OpenRouter: retries exhausted")


def chat(model, messages, temperature=0.0, max_tokens=1200, json_mode=False, tag="", seed=7):
    """Return (text, usage)."""
    if DRY:
        text = ('{"outcome": "partial", "competence": 1, "reliability": "pass", "unsupported_claims": [], '
                '"empathy": 1, "handoff_detected": false, "reference_doubt": false, "label": "docs", '
                '"reason": "in_docs", "evidence": [], "rationale": "dry run"}') if json_mode else "Dry-run reply [1]."
        return text, {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0}
    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "seed": seed, "usage": {"include": True}}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = _post("/chat/completions", body)
    usage = data.get("usage", {})
    _log("chat", model, usage, tag)
    msg = data["choices"][0]["message"]
    return (msg.get("content") or "").strip(), usage


def embed(model, texts, tag=""):
    """Return a list of vectors."""
    if DRY:
        import hashlib
        return [[b / 255 for b in hashlib.sha256(t.encode()).digest()] for t in texts]
    data = _post("/embeddings", {"model": model, "input": texts})
    _log("embed", model, data.get("usage", {}), tag)
    return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]


def parse_json(text):
    """Tolerant JSON extraction from a model reply."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start:end + 1])


# ---------------------------------------------------------------------------------------------
# Test Plan v3 call layer (section 8). Round one's chat() above stays for history; every new paid
# call goes through call(), which:
#   - runs the company-independence check before the request is made;
#   - pins the host (no fallback to other hosts) and the thinking level from audit/models.py;
#   - makes up to 3 attempts with identical settings; an attempt fails on a provider error, a timeout,
#     an empty reply or a reply the caller's parser rejects;
#   - never turns a failure into a verdict: the caller gets ok=False and applies the section-8 fallback;
#   - logs every attempt (billed or not) with phase, set, arm, role and route to runs/cost_ledger.jsonl.
# ---------------------------------------------------------------------------------------------
from . import models as _models

TRANSIENT = (429, 500, 502, 503, 504, 529)


def _log_v3(row):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "plan": "v3", "route": "api", **row}
    with _lock, open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")


def _one_request(body, timeout):
    """One attempt. Transport-level retries (rate limits, 5xx, dropped connections) happen inside the
    attempt with backoff, because they are not a model failure; they are capped so an attempt ends."""
    last = None
    for i in range(5):
        try:
            r = requests.post(f"{API}/chat/completions", headers=_headers(), json=body, timeout=(15, timeout))
        except requests.Timeout:
            return None, "timeout"
        except requests.RequestException as e:
            last = f"connection: {e}"[:300]
            time.sleep(3 * (i + 1))
            continue
        if r.status_code in TRANSIENT:
            last = f"http {r.status_code}: {r.text[:200]}"
            time.sleep(min(60, 4 * 2 ** i))
            continue
        if r.status_code >= 400:
            return None, f"provider_error http {r.status_code}: {r.text[:300]}"
        try:
            data = r.json()
        except ValueError:
            return None, "provider_error: non-JSON body"
        if "error" in data:
            return None, f"provider_error: {str(data['error'])[:300]}"
        return data, None
    return None, f"provider_error (transport retries exhausted): {last}"


def call(model, messages, *, role, author=None, graders=None, arm="", phase="", split="", item="",
         json_mode=False, parse=None, max_tokens=None, timeout=None, attempts=None, extra=None):
    """Returns a dict: ok, text, parsed, attempts, failures, cost, usage, provider, seconds.
    `parse` (optional) raises ValueError on an unusable reply, which counts as a failed attempt."""
    _models.check_independence(role, model, author=author, graders=graders, arm=arm)
    spec = _models.MODELS[model.split(":")[0]]
    body = {"model": model, "messages": messages, "usage": {"include": True},
            "max_tokens": max_tokens or _models.cap(role, model)}
    if spec["provider"]:
        body["provider"] = {"order": [spec["provider"]], "allow_fallbacks": False}
    if spec["reasoning"] is not None:
        body["reasoning"] = dict(spec["reasoning"])
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if extra:
        body.update(extra)
    timeout = timeout or _models.DEFAULT_TIMEOUT
    out = {"ok": False, "text": "", "parsed": None, "attempts": 0, "failures": [], "cost": 0.0,
           "usage": {}, "provider": None, "seconds": 0.0, "model": model}
    if DRY:
        text = '{"dry_run": true}' if json_mode else "Dry-run reply [1]."
        out.update(ok=True, text=text, parsed=(parse(text) if parse else None), attempts=1)
        return out
    for n in range(1, (attempts or _models.ATTEMPTS) + 1):
        t0 = time.time()
        data, err = _one_request(body, timeout)
        secs = round(time.time() - t0, 1)
        usage, text, provider, finish = {}, "", None, None
        if data is not None:
            usage = data.get("usage") or {}
            provider = data.get("provider")
            ch = (data.get("choices") or [{}])[0]
            finish = ch.get("finish_reason")
            text = ((ch.get("message") or {}).get("content") or "").strip()
            if not text:
                err = f"empty reply (finish_reason={finish})"
            elif parse:
                try:
                    out["parsed"] = parse(text)
                except (ValueError, KeyError, TypeError) as e:
                    err = f"unparseable: {str(e)[:200]}"
        cost = float(usage.get("cost") or 0)
        rt = ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))
        _log_v3({"kind": "chat", "model": model, "provider": provider, "phase": phase, "set": split, "arm": arm,
                 "role": role, "item": str(item), "attempt": n, "ok": err is None, "failure": err,
                 "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                 "reasoning_tokens": rt, "cost": cost, "seconds": secs, "finish": finish})
        out["attempts"], out["cost"] = n, out["cost"] + cost
        out["seconds"] += secs
        if err is None:
            out.update(ok=True, text=text, usage=usage, provider=provider, finish=finish, reasoning_tokens=rt)
            return out
        out["failures"].append(err)
        out["text"] = text  # kept for diagnosis only; never used as a verdict
    return out


def embed_v3(texts, *, phase="", split="", item=""):
    """Query embeddings for label and harvest searches, host-pinned like every other call."""
    if DRY:
        return embed("baai/bge-m3", texts)
    spec = _models.MODELS["baai/bge-m3"]
    body = {"model": "baai/bge-m3", "input": texts, "provider": {"order": [spec["provider"]], "allow_fallbacks": False}}
    last = None
    for i in range(_models.ATTEMPTS):
        try:
            r = requests.post(f"{API}/embeddings", headers=_headers(), json=body, timeout=(15, 120))
            if r.status_code in TRANSIENT:
                last = r.status_code; time.sleep(4 * 2 ** i); continue
            r.raise_for_status()
            data = r.json()
            _log_v3({"kind": "embed", "model": "baai/bge-m3", "provider": data.get("provider"), "phase": phase,
                     "set": split, "role": "embed", "item": str(item), "attempt": i + 1, "ok": True,
                     "prompt_tokens": (data.get("usage") or {}).get("prompt_tokens"),
                     "cost": float((data.get("usage") or {}).get("cost") or 0)})
            return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]
        except requests.RequestException as e:
            last = str(e)[:200]; time.sleep(3 * (i + 1))
    raise RuntimeError(f"embedding failed after {_models.ATTEMPTS} attempts: {last}")
