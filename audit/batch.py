"""OpenRouter batch mode (decision 13, 2026-10-01): half price, results within 24 hours.

Same rules as audit/llm.call (section 8): the company-independence check runs before submission, the host is
pinned (`provider.only`), thinking levels and caps come from audit/models.py, and each item gets up to 3
attempts with identical settings (a failed item is resubmitted in a new batch). Per-item cost isn't returned
by the batch API, so the batch's billed cost is allocated to its items in proportion to their tokens.

State lives in runs/v3plan/batches/<job>.json: one job = one logical batch run (one model, one role, many items).
"""
import json, time

import requests

from . import models as M
from .common import ROOT
from .llm import API, LEDGER, _headers, _lock, _log_v3

BDIR = ROOT / "runs/v3plan/batches"
BATCH_HOSTS = {"anthropic/claude-sonnet-5.5": "anthropic", "google/gemini-3.8-flash": "google-vertex/global",
               "openai/gpt-5.4-mini": "openai", "openai/gpt-6.1-sol": "openai"}  # gpt-5.4-mini has no batch endpoint (2026-10-13)
# Build 2 (2026-10-13, JC): the reviewer candidates have no batch route on their pinned hosts. MiMo has no batch
# endpoint at all; GLM-5.3's only batch host is DeepInfra fp4 and Kimi K3's is DeepInfra bf16 capped at 16,384 output
# tokens, both outside section 8's host rules. Reviewers therefore run over the API on their pinned hosts.


def _body(model, role, messages, json_mode):
    spec = M.MODELS[model]
    b = {"messages": messages, "max_tokens": M.cap(role, model), "usage": {"include": True}}
    if spec["reasoning"] is not None:
        b["reasoning"] = dict(spec["reasoning"])
    if json_mode:
        b["response_format"] = {"type": "json_object"}
    return b


def create_job(job, model, role, items, *, phase, split="", arm="", json_mode=True, authors=None, graders=None):
    """items: dict custom_id -> messages. authors: dict custom_id -> author model (for the independence check)."""
    BDIR.mkdir(parents=True, exist_ok=True)
    path = BDIR / f"{job}.json"
    if path.exists():
        return json.loads(path.read_text())
    for cid in items:
        M.check_independence(role, model, author=(authors or {}).get(cid), graders=graders, arm=arm)
    st = {"job": job, "model": model, "role": role, "phase": phase, "split": split, "arm": arm, "json_mode": json_mode,
          "items": {cid: {"messages": msgs, "attempts": 0, "status": "pending"} for cid, msgs in items.items()},
          "batches": []}
    path.write_text(json.dumps(st))
    return st


def _save(st):
    (BDIR / f"{st['job']}.json").write_text(json.dumps(st))


def load(job):
    return json.loads((BDIR / f"{job}.json").read_text())


def submit(job, chunk=200):
    """Submit every pending item that has attempts left, in batches of `chunk`."""
    st = load(job)
    todo = [cid for cid, it in st["items"].items() if it["status"] == "pending" and it["attempts"] < M.ATTEMPTS]
    for i in range(0, len(todo), chunk):
        ids = todo[i:i + chunk]
        payload = {"endpoint": "/v1/chat/completions", "model": st["model"], "completion_window": "24h",
                   "provider": {"only": [BATCH_HOSTS[st["model"]]]},
                   "requests": [{"custom_id": cid, "body": _body(st["model"], st["role"], st["items"][cid]["messages"], st["json_mode"])} for cid in ids]}
        r = requests.post(f"{API}/batches", headers=_headers(), json=payload, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"batch create failed {r.status_code}: {r.text[:400]}")
        b = r.json().get("data", r.json())
        for cid in ids:
            st["items"][cid]["attempts"] += 1; st["items"][cid]["status"] = "submitted"; st["items"][cid]["batch"] = b["id"]
        st["batches"].append({"id": b["id"], "n": len(ids), "status": b.get("status"), "submitted": time.strftime("%Y-%m-%dT%H:%M:%S")})
        _save(st)
    return st


def poll(job, parse=None, parse_item=None):
    """Collect finished batches. Items that failed (error, empty, unparseable) go back to pending for another
    attempt, until they have had 3. Returns counts."""
    st = load(job)
    price_in, price_out = (p / 2 / 1e6 for p in M.MODELS[st["model"]]["price"])
    for b in st["batches"]:
        if b.get("collected"):
            continue
        r = requests.get(f"{API}/batches/{b['id']}", headers=_headers(), timeout=120)
        if r.status_code == 404:  # a batch submitted seconds ago isn't visible yet; check it on the next poll
            continue
        r.raise_for_status()
        d = r.json().get("data", r.json())
        b["status"] = d.get("status"); b["request_counts"] = d.get("request_counts")
        if b["status"] not in ("completed", "failed", "expired", "cancelled"):
            continue
        results = d.get("results") or []
        batch_cost = float((d.get("usage") or {}).get("cost") or 0)
        rows, tok_total = [], 0
        seen = set()
        for res in results:
            cid = res.get("custom_id"); seen.add(cid)
            it = st["items"].get(cid)
            if it is None:
                continue
            body = ((res.get("response") or {}).get("body")) or {}
            usage = body.get("usage") or {}
            text = ""
            if body.get("choices"):
                text = ((body["choices"][0].get("message") or {}).get("content") or "").strip()
            err = None
            if res.get("error") or (res.get("response") or {}).get("status_code", 200) >= 400:
                err = f"provider_error: {str(res.get('error') or body)[:200]}"
            elif not text:
                err = "empty reply"
            parsed = None
            if err is None and (parse or parse_item):
                try:
                    parsed = parse_item(cid, text) if parse_item else parse(text)
                except (ValueError, KeyError, TypeError) as e:
                    err = f"unparseable: {str(e)[:150]}"
            est = (usage.get("prompt_tokens") or 0) * price_in + (usage.get("completion_tokens") or 0) * price_out
            tok_total += est
            rows.append((cid, err, usage, est, body.get("provider")))
            if err is None:
                it.update(status="ok", text=text, parsed=parsed, usage=usage, provider=body.get("provider"))
            else:
                it.update(status="pending" if it["attempts"] < M.ATTEMPTS else "failed", last_failure=err)
                it.setdefault("failures", []).append(err)
        for cid, it in st["items"].items():  # submitted to this batch but missing from its results
            if it.get("batch") == b["id"] and it["status"] == "submitted" and cid not in seen:
                it.update(status="pending" if it["attempts"] < M.ATTEMPTS else "failed", last_failure="missing from batch results")
                it.setdefault("failures", []).append("missing from batch results")
        scale = (batch_cost / tok_total) if tok_total else 0
        for cid, err, usage, est, prov in rows:
            _log_v3({"kind": "chat", "route": "batch", "batch": b["id"], "model": st["model"], "provider": prov, "phase": st["phase"],
                     "set": st["split"], "arm": st["arm"], "role": st["role"], "item": cid, "attempt": st["items"][cid]["attempts"],
                     "ok": err is None, "failure": err, "prompt_tokens": usage.get("prompt_tokens"),
                     "completion_tokens": usage.get("completion_tokens"),
                     "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                     "cost": round(est * scale, 8) if batch_cost else est, "cost_basis": "batch total allocated by tokens" if batch_cost else "estimate from tokens"})
        b.update(collected=True, cost=batch_cost or tok_total)
    _save(st)
    from collections import Counter
    c = Counter(it["status"] for it in st["items"].values())
    return {"job": job, "counts": dict(c), "batches": [(b["id"][-8:], b["status"], b.get("request_counts")) for b in st["batches"]]}
