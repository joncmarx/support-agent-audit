"""Re-grade tie-breaks in chunks that finish inside one shell call: no new call starts after 45 s."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import functools, audit.jobs as J, audit.regrade as R
J.run_jobs.__defaults__ = (20, 50)  # max_seconds=50: no new call after 50 s, so in-flight calls finish before the shell limit
uniq, _ = R.load(); labs = R.final_labels(); G1, G2, TB = R.grades("grader1"), R.grades("grader2"), R.grades("tiebreaker")
need = {rid for rid, r in uniq.items() if R.settle_reply(rid, labs[r["qid"]]["side"] == "answerable", G1.get(rid), G2.get(rid), None)["status"] == "needs_tiebreak"}
left = need - set(TB)
print("need", len(need), "left before", len(left))
if left:
    R.grade("tiebreaker", "meta/muse-spark-1.3", rids=left, workers=20)
print("done now", len(set(R.grades("tiebreaker")) & need))
