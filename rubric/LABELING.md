# Handoff labels

## Step 0: is the reference usable?

Some accepted answers contain no fix to compare against: only encouragement ("focus on the concept"), a bare link, a question back to the asker, or "it started working". Those threads are excluded from scoring, because there is nothing to grade a reply against. Claude Sonnet checks every thread with the rule in `audit/grade.py` (`reference_check`), and the excluded threads are listed with reasons in `data/reference_check.jsonl`. This step was added on 2026-09-29, after the first labels revealed such a thread and before any bot reply was graded.

## Step 1: the label

Every question gets one label **before any bot runs**, based on the accepted answer (written by someone other than the asker) and the pinned docs.

| Label | Meaning |
|---|---|
| `docs` | The pinned n8n docs contain the fix, or enough that a careful agent reading them would reach it. |
| `handoff` | A docs-grounded agent should route this to a human. |

A question is `handoff` if any of these hold:
1. **Bug or release:** the fix is a bug fix, a regression, or upgrading or downgrading to a specific version because of a defect.
2. **Access:** the fix needs something the bot can't see or do: the customer's account, billing, a cloud instance's admin settings, or action by n8n staff.
3. **Not in the docs:** the key step of the fix does not appear in the docs passages retrieved for it (the labeler searches with both the question and the accepted answer, so the docs get their best chance).

Otherwise the label is `docs`.

The label decides only one thing in grading: whether a handoff counts as `correct_handoff` or `unnecessary_handoff`. A bot that correctly solves a `handoff` question still scores `resolved`.

Claude Sonnet applies the rule with the evidence attached; JC spot-checks a random 20. Disagreements are recorded, and if more than 3 of 20 are wrong the rule gets rewritten and every label is redone.
