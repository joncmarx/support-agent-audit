"""$0 test of every section-8 failure path, with a fake model call. Run: python3 -m tests.test_pipeline"""
import sys

from audit import models, pipeline


def fake(script):
    """script: role -> list of (ok, text) per call. Returns a call() with llm.call's signature."""
    def call(model, messages, *, role, author=None, graders=None, arm="", parse=None, **kw):
        models.check_independence(role, model, author=author, graders=graders, arm=arm)
        ok, text = script[role].pop(0)
        out = {"ok": ok, "text": text if ok else "", "parsed": None, "attempts": 3 if not ok else 1,
               "failures": [] if ok else ["timeout"] * 3, "cost": 0.0}
        if ok and parse:
            out["parsed"] = parse(text)
        return out
    return call


Q = {"id": 1, "title": "t", "question": "q"}
P = [{"id": "x#0", "page_title": "p", "heading": "h", "url": "u", "text": "passage text"}]
KW = dict(arm="A", drafter="openai/gpt-5.4-mini", reviewer="openai/gpt-5.4-mini", system="s",
          graders=["anthropic/claude-sonnet-5.5"], phase="test", split="dev", reviewer_role="reviewer_A")
DRAFT = "<triage>x</triage><reply>Do the thing [1].</reply>"


def main():
    cases = {
        "passed draft":      ({"drafter": [(True, DRAFT)], "reviewer_A": [(True, '{"safe": true, "problem": ""}')]}, "draft", None),
        "blocked -> handoff": ({"drafter": [(True, DRAFT)], "reviewer_A": [(True, '{"safe": false, "problem": "p"}')], "handoff": [(True, "Handoff text")]}, "handoff", None),
        "drafter fails":     ({"drafter": [(False, "")]}, "safe_handoff", "drafter"),
        "reviewer fails":    ({"drafter": [(True, DRAFT)], "reviewer_A": [(False, "")]}, "safe_handoff", "reviewer"),
        "handoff fails":     ({"drafter": [(True, DRAFT)], "reviewer_A": [(True, '{"safe": false, "problem": "p"}')], "handoff": [(False, "")]}, "safe_handoff", "handoff"),
    }
    bad = 0
    for name, (script, source, failure) in cases.items():
        r = pipeline.run(Q, P, call=fake(script), **KW)
        ok = r["answer_source"] == source and r["system_failure"] == failure
        if failure:
            ok = ok and r["answer"] == pipeline.SAFE_HANDOFF
        if failure == "reviewer":
            ok = ok and r["review_safe"] is None  # never passed, never a genuine block
        print(f"{'ok ' if ok else 'BAD'} {name}: source={r['answer_source']} failure={r['system_failure']}")
        bad += not ok
    # Independence: a same-company reviewer outside arm A must be refused before any call.
    try:
        pipeline.run(Q, P, call=fake({"drafter": [(True, DRAFT)], "reviewer": [(True, '{"safe": true}')]}),
                     **{**KW, "arm": "B", "reviewer_role": "reviewer"})
        print("BAD independence not enforced"); bad += 1
    except models.IndependenceError as e:
        print("ok  independence enforced:", e)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
