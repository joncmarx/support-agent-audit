"""The Claude-plan route (TEST-PLAN-v3 section 7): items exported as files, graded or labeled by
`claude -p` in JC's own terminal, then ingested here.

Isolation for every plan call: a fresh session in an empty temporary folder (no project files or CLAUDE.md),
no settings sources, no tools (so no web access), no MCP servers, no session saved, the system prompt
replaced by the rubric. Isolation is then CHECKED, not assumed: each plan reply's billed input tokens are
compared with the API route's prompt tokens for the same item. Extra context (a CLAUDE.md, memory, tool
definitions) would show up as extra input tokens; if it does, isolation fails and grader 1 stays on the API.
"""
import hashlib, json, os, shutil
from pathlib import Path

from .common import ROOT

PLAN = ROOT / "runs/v3plan/plan"
RUNNER = PLAN / "run_plan.sh"


def export(batch, system_text, items, model, effort="high"):
    """items: list of (item_id, user_text). Writes PLAN/<batch>/{system.txt, items/*.txt, batch.json}."""
    d = PLAN / batch
    (d / "items").mkdir(parents=True, exist_ok=True)
    (d / "system.txt").write_text(system_text)
    for iid, text in items:
        (d / "items" / f"{iid}.txt").write_text(text)
    meta = {"batch": batch, "model": model, "effort": effort, "n": len(items),
            "system_sha256": hashlib.sha256(system_text.encode()).hexdigest(),
            "items_sha256": hashlib.sha256("".join(f"{i}\n{t}" for i, t in items).encode()).hexdigest()}
    (d / "batch.json").write_text(json.dumps(meta, indent=1))
    return d


def ingest(batch, run):
    """Parse Claude Code's JSON output for every item of one run. Returns {item_id: record}."""
    d = PLAN / batch / f"out_{run}"
    out = {}
    for p in sorted(d.glob("*.json")):
        iid = p.stem
        rec = {"item": iid, "ok": False, "text": "", "usage": {}, "models": [], "api_equiv_cost": None, "error": None}
        try:
            j = json.loads(p.read_text())
            rec["text"] = (j.get("result") or "").strip()
            rec["usage"] = j.get("usage") or {}
            rec["models"] = sorted((j.get("modelUsage") or {}).keys())
            rec["api_equiv_cost"] = j.get("total_cost_usd")
            rec["ok"] = not j.get("is_error") and bool(rec["text"])
            if j.get("is_error"):
                rec["error"] = (j.get("result") or j.get("subtype") or "error")[:300]
        except (ValueError, OSError) as e:
            rec["error"] = f"unreadable output: {e}"
        u = rec["usage"]
        rec["input_tokens_total"] = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        out[iid] = rec
    return out


RUNNER_SCRIPT = r'''#!/bin/bash
# Runs one exported batch through Claude Code on JC's Claude plan. Resumable: finished items are skipped.
# Usage: bash run_plan.sh <batch-folder-name> <run-name> [parallel]
# Every call: fresh session, empty working folder, no settings, no tools, no MCP servers, not saved.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BATCH="$HERE/$1"; RUN="$2"; PAR="${3:-3}"
MODEL="$(sed -n 's/.*"model": "\([^"]*\)".*/\1/p' "$BATCH/batch.json")"
EFFORT="$(sed -n 's/.*"effort": "\([^"]*\)".*/\1/p' "$BATCH/batch.json")"
command -v claude >/dev/null || { echo "Claude Code (the claude command) isn't installed on this Mac."; exit 1; }
echo "Batch $1, run $RUN: model $MODEL, effort $EFFORT, $(ls "$BATCH/items" | wc -l | tr -d ' ') items, $PAR at a time"
OUT="$BATCH/out_$RUN"; mkdir -p "$OUT"
export ISO="$(mktemp -d)"; export OUT BATCH MODEL EFFORT
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
one() {
  id="$1"; f="$BATCH/items/$id.txt"; o="$OUT/$id.json"
  [ -s "$o" ] && return 0
  [ -e "$OUT/STOP" ] && return 0
  for attempt in 1 2 3; do
    ( cd "$ISO" && claude -p --model "$MODEL" --effort "$EFFORT" --tools "" \
        --strict-mcp-config --mcp-config '{"mcpServers":{}}' --setting-sources "" \
        --no-session-persistence --max-turns 1 --output-format json \
        --system-prompt "$(cat "$BATCH/system.txt")" < "$f" ) > "$o.tmp" 2> "$o.err"
    if [ -s "$o.tmp" ] && grep -Eq '"is_error": ?false' "$o.tmp" && grep -Eq '"result": ?"' "$o.tmp"; then
      mv "$o.tmp" "$o"; rm -f "$o.err"; echo "done $id"; return 0
    fi
    if grep -qiE "limit|quota|usage" "$o.tmp" "$o.err" 2>/dev/null; then
      echo "PLAN LIMIT reached at $id: stopping this run"; touch "$OUT/STOP"; return 0
    fi
    sleep 5
  done
  mv "$o.tmp" "$OUT/$id.failed" 2>/dev/null; echo "failed $id after 3 attempts"
}
export -f one
ls "$BATCH/items" | sed 's/\.txt$//' | xargs -P "$PAR" -I{} bash -c 'one "$@"' _ {}
N=$(ls "$BATCH/items" | wc -l | tr -d ' '); D=$(ls "$OUT"/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "FINISHED: $D of $N items done in run $RUN"
[ -e "$OUT/STOP" ] && echo "Stopped early because the plan limit was reached."
rm -rf "$ISO"
'''


def write_runner():
    PLAN.mkdir(parents=True, exist_ok=True)
    RUNNER.write_text(RUNNER_SCRIPT)
    os.chmod(RUNNER, 0o755)
    return RUNNER
