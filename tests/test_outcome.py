"""Feeds every combination of rubric fields through the outcome table (TEST-PLAN-v3 section 6) and
checks that each maps to exactly one outcome, plus the properties the plan promises. Run:
    python3 -m tests.test_outcome
"""
import sys
from collections import Counter

from audit.outcome import OUTCOMES, ROWS, all_combinations, label_free, outcome


def main():
    n, seen, fails = 0, Counter(), []
    by_key = {}
    for grade, ans in all_combinations():
        n += 1
        o, row, g = outcome(grade, ans)
        matches = [num for num, _d, pred, _o in ROWS if pred(g)]
        seen[o] += 1
        if matches[0] != row:
            fails.append(("first match", grade, ans))
        if ans is None:
            if o in ("correct_handoff", "unnecessary_handoff"):
                fails.append(("label-free produced a labelled handoff", grade))
        elif o not in OUTCOMES:
            fails.append(("unknown outcome", o, grade, ans))
        # Properties the plan states:
        if g["unsafe"] and o != "confidently_wrong":
            fails.append(("unsafe must be a trust incident", grade, ans, o))
        if g["fix_verdict"] == "wrong" and o not in ("confidently_wrong", "wrong_hedged"):
            fails.append(("a wrong fix must never earn credit", grade, ans, o))
        if o in ("resolved", "partial", "right_question", "correct_handoff", "unnecessary_handoff") and (g["material_error"] or g["unsafe"]):
            fails.append(("credit despite a material error", grade, ans, o))
        if o == "resolved" and not (g["fix_verdict"] == "correct" and not g["harmless_error"]):
            fails.append(("resolved needs a correct fix with no error", grade, ans))
        if (g["action"] == "asked" and g["right_missing_fact"] == "no" and g["fix_verdict"] == "no_fix"
                and not g["material_error"] and not g["unsafe"] and o != "no_progress"):
            fails.append(("a generic question must be a stall", grade, ans, o))
        if g["action"] == "answered" and g["fix_verdict"] == "correct" and not g["harmless_error"] \
                and not g["material_error"] and not g["unsafe"] and o != "resolved":
            fails.append(("a correct answer counts whether or not it hedges", grade, ans, o))
        by_key.setdefault(tuple(sorted(grade.items())), {})[ans] = o
    # The label may change only rows 8 and 9, and the label-free outcome must equal the merged labelled one.
    for key, outs in by_key.items():
        lf = outs[None]
        for ans in (True, False):
            if label_free(outs[ans]) != lf:
                fails.append(("label-free differs from merged labelled outcome", dict(key), ans, outs))
        if outs[True] != outs[False] and {outs[True], outs[False]} != {"correct_handoff", "unnecessary_handoff"}:
            fails.append(("the label changed something other than rows 8/9", dict(key), outs))
    unreachable = [o for o in OUTCOMES + ("handoff",) if seen[o] == 0]
    print(f"combinations: {n} | outcomes: {dict(seen)}")
    print(f"unreachable outcomes: {unreachable or 'none'} | failures: {len(fails)}")
    for f in fails[:10]:
        print("  FAIL", f)
    return 0 if not fails and not unreachable else 1


if __name__ == "__main__":
    sys.exit(main())
