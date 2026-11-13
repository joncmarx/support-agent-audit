"""Guarded Muse tie-break chunk (decision 15): never start more questions than the $8.00 labels ceiling allows at a
worst case of $0.05 each."""
import sys
sys.path.insert(0, "runs")
import ledger as L
from audit.labelrun import load, needing_tb, run_api

CEILING, WORST = 8.00, 0.05
need = sorted(needing_tb() - set(load("label_tb")))
spent = L.spent_by_phase()["1-labels"]
n = min(len(need), int((CEILING - spent) / WORST))
print(f"labels phase ${spent:.2f}; tie-breaks left {len(need)}; this chunk may start {n}")
if n:
    run_api("label_tb", "meta/muse-spark-1.3", ids=set(need[:n]), max_seconds=int(sys.argv[1]) if len(sys.argv) > 1 else 100, workers=8)
