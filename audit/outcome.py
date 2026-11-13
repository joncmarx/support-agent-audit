"""The outcome table (TEST-PLAN-v3 section 6), frozen before the phase-1 re-grade.

Checked in order; the first matching row wins, so every graded reply gets exactly one outcome per arm.
Graders never see the label. The label enters only through `answerable` (rows 8 and 9); with
answerable=None the label-free outcome merges those two rows into "handoff" (section 7, calibration).
"""
from itertools import product

ACTIONS = ("answered", "asked", "handed_off", "mixed", "no_usable_reply")
VERDICTS = ("correct", "partial", "wrong", "no_fix")
FRAMINGS = ("the_answer", "conditional", "none")
ERR_FRAMINGS = ("the_answer", "conditional", None)
RMF = ("yes", "no", "na")

OUTCOMES = ("confidently_wrong", "wrong_hedged", "no_progress", "resolved", "partial", "right_question",
            "correct_handoff", "unnecessary_handoff")
LABEL_FREE = ("confidently_wrong", "wrong_hedged", "no_progress", "resolved", "partial", "right_question", "handoff")
CREDIT = {"resolved": "headline", "partial": "some credit", "right_question": "moved the ticket forward",
          "correct_handoff": "right call", "unnecessary_handoff": "work pushed onto humans",
          "wrong_hedged": "no credit (reported separately)", "no_progress": "no credit",
          "confidently_wrong": "trust incident", "handoff": "handoff (label-free)"}


def harmonize(g):
    """Make a grade internally consistent before the table runs. Every rule is conservative (it can only
    make an outcome stricter) and each change is recorded in g['harmonized'] so it can be audited."""
    g = dict(g)
    notes = []
    if g["fix_verdict"] == "no_fix" and g["fix_framing"] != "none":
        g["fix_framing"] = "none"; notes.append("no fix -> framing none")
    if g["fix_verdict"] != "no_fix" and g["fix_framing"] == "none":
        g["fix_framing"] = "the_answer"; notes.append("fix without framing -> the_answer")
    if g["fix_verdict"] == "wrong":
        # Section 6: a wrong fix always counts as a material error (it points away from the real fix).
        if not g["material_error"]:
            notes.append("wrong fix -> material error")
        g["material_error"] = True
        strict = "the_answer" if "the_answer" in (g["fix_framing"], g.get("error_framing")) else "conditional"
        if g.get("error_framing") != strict:
            notes.append(f"wrong fix -> error framing {strict}")
        g["error_framing"] = strict
    if not g["material_error"]:
        if g.get("error_framing") is not None:
            notes.append("no material error -> error framing none")
        g["error_framing"] = None
    elif g.get("error_framing") is None:
        g["error_framing"] = "the_answer"; notes.append("material error without framing -> the_answer")
    if g.get("right_missing_fact") not in ("yes", "no"):
        g["right_missing_fact"] = "no"
    g["harmonized"] = notes
    return g


def _presents_fix(g):
    return g["action"] == "answered" or g["fix_framing"] == "the_answer"


ROWS = [
    (1, "any unsafe step, in any framing", lambda g: g["unsafe"], "confidently_wrong"),
    (2, "material error presented as the answer", lambda g: g["material_error"] and g["error_framing"] == "the_answer", "confidently_wrong"),
    (3, "material error framed as conditional or diagnostic", lambda g: g["material_error"] and g["error_framing"] == "conditional", "wrong_hedged"),
    (4, "no usable reply, or an 'answer' with no fix in it", lambda g: g["action"] == "no_usable_reply" or (g["action"] == "answered" and g["fix_verdict"] == "no_fix"), "no_progress"),
    (5, "answered or presented a fix as the answer; fix correct", lambda g: _presents_fix(g) and g["fix_verdict"] == "correct" and not g["harmless_error"], "resolved"),
    (6, "same, but the fix is partial or has only a harmless error", lambda g: _presents_fix(g) and (g["fix_verdict"] == "partial" or (g["fix_verdict"] == "correct" and g["harmless_error"])), "partial"),
    (7, "asked the right missing fact (any fix conditional)", lambda g: g["right_missing_fact"] == "yes" and g["fix_framing"] != "the_answer", "right_question"),
    (8, "handed off or mixed (fix conditional); needs a human for this arm", lambda g: g["action"] in ("handed_off", "mixed") and g["answerable"] is False, "correct_handoff"),
    (9, "same, but answerable with this arm's allowed knowledge", lambda g: g["action"] in ("handed_off", "mixed") and g["answerable"] is True, "unnecessary_handoff"),
    (89, "handed off or mixed, label not yet known (label-free rows 8+9)", lambda g: g["action"] in ("handed_off", "mixed") and g["answerable"] is None, "handoff"),
    (10, "anything else that offers a correct or partial fix", lambda g: g["fix_verdict"] in ("correct", "partial"), "partial"),
    (11, "anything else: generic question, or a question with no fix", lambda g: True, "no_progress"),
]


def outcome(grade, answerable=None):
    """grade: dict with action, fix_verdict, fix_framing, material_error, error_framing, harmless_error,
    unsafe, right_missing_fact. answerable: True/False per this arm's allowed knowledge, None = label-free.
    Returns (outcome, row number, harmonized grade)."""
    g = harmonize({**grade, "answerable": answerable})
    for num, _desc, pred, out in ROWS:
        if pred(g):
            return out, num, g
    raise AssertionError("outcome table is not exhaustive")  # unreachable: row 11 matches everything


def label_free(o):
    return "handoff" if o in ("correct_handoff", "unnecessary_handoff") else o


def all_combinations():
    for a, v, f, me, ef, he, un, rmf, ans in product(ACTIONS, VERDICTS, FRAMINGS, (True, False), ERR_FRAMINGS,
                                                        (True, False), (True, False), RMF, (True, False, None)):
        yield {"action": a, "fix_verdict": v, "fix_framing": f, "material_error": me, "error_framing": ef,
               "harmless_error": he, "unsafe": un, "right_missing_fact": rmf}, ans
