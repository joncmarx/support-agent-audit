#!/bin/bash
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
