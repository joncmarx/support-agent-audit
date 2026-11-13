"""Run manifest and preregistration (TEST-PLAN-v3 sections 8 and 11).

  python3 -m audit.manifest write            # (re)write runs/MANIFEST.json and print its hash
  python3 -m audit.manifest show             # print the hash of the current manifest

The manifest is hashed into runs/PREREGISTRATION.md before each paid batch, together with that batch's
predictions and its re-priced estimate. There is no git repo yet, so the code is pinned by a hash of
every tracked source file; the commit is added once the repo exists.
"""
import hashlib, json, sys, time
from pathlib import Path

from . import models
from .common import CACHE, DATA, ROOT, read_jsonl

MANIFEST = ROOT / "runs/MANIFEST.json"
PREREG = ROOT / "runs/PREREGISTRATION.md"
SEALED = ROOT / "sealed"
CODE_GLOBS = ["audit/*.py", "tests/*.py", "runs/ledger.py"]
PROMPT_FILES = ["rubric/RUBRIC-v3.md", "rubric/RUBRIC.md", "rubric/LABELING.md", "rubric/LABELING-v2.md",
                "prompts/F0F_SYSTEM.md", "prompts/F0F_USER.md", "prompts/F_REVIEW.md", "prompts/G_HANDOFF.md",
                "prompts/SAFE_HANDOFF.txt"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def code_tree():
    files = sorted({p for g in CODE_GLOBS for p in ROOT.glob(g)})
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT)).encode()); h.update(sha(p).encode())
    return {"git_commit": None, "note": "no git repo yet; tree hash covers " + ", ".join(CODE_GLOBS),
            "tree_sha256": h.hexdigest(), "files": len(files)}


def question_sets():
    rows = read_jsonl(CACHE / "questions_full.jsonl")
    usable = {r["id"] for r in read_jsonl(DATA / "reference_check.jsonl") if r["usable"]}
    out = {}
    for split, name in (("dev", "practice"), ("test", "test")):
        ids = sorted(r["id"] for r in rows if r["split"] == split and r["id"] in usable)
        text = "\n".join(json.dumps({k: r[k] for k in ("id", "title", "question", "accepted_answer")}, ensure_ascii=False)
                         for r in sorted(rows, key=lambda r: r["id"]) if r["id"] in ids)
        out[name] = {"n": len(ids), "ids_sha256": sha_text(",".join(map(str, ids))), "text_sha256": sha_text(text)}
    hold = SEALED / "SEAL.json"
    out["holdout"] = json.loads(hold.read_text()) if hold.exists() else None
    return out


def build():
    from .bot import CONFIGS, HANDOFF_PROMPT, REVIEW_PROMPT
    bot_prompts = {k: sha_text(v["system"]) for k, v in CONFIGS.items()}
    bot_prompts.update(review=sha_text(REVIEW_PROMPT), handoff=sha_text(HANDOFF_PROMPT))
    vec = CACHE / "docs_vectors.npy"
    m = {
        "plan": {"file": "TEST-PLAN-v3.md", "sha256": sha(ROOT / "TEST-PLAN-v3.md")},
        "models": models.MODELS,
        "roles": models.ROLES,
        "caps": {"default_thinking_models": models.DEFAULT_CAP, "timeout_seconds": models.DEFAULT_TIMEOUT,
                 "overrides": {f"{r}|{m}": v for (r, m), v in models.CAPS.items()},
                 "rule": "sized from the practice trials to at least 4x the longest reply, then frozen"},
        "attempts": models.ATTEMPTS,
        "batch_hosts": __import__("audit.batch", fromlist=["BATCH_HOSTS"]).BATCH_HOSTS,
        "sampling": {"temperature": "not sent (provider default)", "seed": "not sent",
                     "host_fallbacks": False, "note": "OpenAI models on OpenRouter take no temperature and Anthropic's take no seed, so reruns can't be forced identical"},
        "prompts": {p: (sha(ROOT / p) if (ROOT / p).exists() else None) for p in PROMPT_FILES},
        "bot_prompts_sha256": bot_prompts,
        "outcome_table_sha256": sha(ROOT / "audit/outcome.py"),
        "normalizer_sha256": sha(ROOT / "audit/normalize.py"),
        "output_formats": {"grade": "rubric/RUBRIC-v3.md section Output; parsed strictly by audit/grade3.py:parse_grade"},
        "retrieval": {"docs_commit": (DATA / "docs_commit.txt").read_text().strip(),
                      "index": {"docs_chunks.jsonl": sha(CACHE / "docs_chunks.jsonl"),
                                "docs_vectors.npy": sha(vec) if vec.exists() else None},
                      "mode": "hybrid (BM25 + bge-m3, reciprocal-rank fusion, pool 30)", "passages": 8,
                      "query": "title + question text + node types (v4 settings)",
                      "practice_and_test": "arms B, D, F0, F reuse the passages round one retrieved",
                      "community": {"top": 3, "cap_tokens": 1500, "section": "separate, labeled peer-written"}},
        "harvest_snapshot_sha256": None,
        "question_sets": question_sets(),
        "seeds": {"holdout_order": 20260929, "resampling": 20260930, "calibration_samples": 20260930},
        "trust_gate": {"practice_screen": "at most 1 confidently wrong of 43 (looser than 2%, stated)",
                       "holdout_gate": "at most 2 confidently wrong of exactly 100",
                       "unresolved": "counted as trust incidents under the conservative rule (section 7)"},
        "budget": {"key_limit_usd": 80, "headroom_multiplier": 1.3, "phase_overrun_stop": 1.3},
        "code": code_tree(),
    }
    return m


def manifest_hash(m):
    return sha_text(json.dumps(m, sort_keys=True, ensure_ascii=False))


def write():
    m = build()
    h = manifest_hash(m)
    MANIFEST.write_text(json.dumps({"sha256": h, "written": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **m}, indent=1, ensure_ascii=False))
    return h


def preregister(title, body, estimate=None):
    """Append a timestamped entry to runs/PREREGISTRATION.md: manifest hash, estimate, predictions."""
    h = write()
    if not PREREG.exists():
        PREREG.write_text("# Preregistration log (Test Plan v3)\n\nEach entry is written before the paid batch it names. "
                          "Entries are append-only; a correction is a new entry that says what it corrects.\n")
    lines = [f"\n## {time.strftime('%Y-%m-%d %H:%M:%S %Z')} — {title}\n", f"- Manifest sha256: `{h}`"]
    if estimate is not None:
        lines.append(f"- Re-priced estimate: ${estimate:.2f} (runs only if available >= ${estimate * 1.3:.2f})")
    lines.append(body.strip() + "\n")
    with open(PREREG, "a") as f:
        f.write("\n".join(lines))
    return h


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "write"
    print(write() if cmd == "write" else json.loads(MANIFEST.read_text())["sha256"])
