# Testing an AI support agent against a trust budget

*Case study · Jonathan Marx · October 2026*

I built a support bot for n8n, set a limit on confident wrong answers before the final test, and published every reply. On 100 sealed questions, the safest version gave 4 confident wrong answers against a budget of 2.

## The problem

Teams buy AI support agents on deflection rates. The number that decides whether customers keep trusting the channel is a different one: how often the bot is confidently wrong. I wanted to measure it on real questions, with the bar set before the test so the result couldn't be argued after it.

## What I built

- A support bot for n8n, the workflow-automation tool, that answers from n8n's public docs.
- 240 real questions from n8n's community forum, each with an accepted answer from another member: 43 to practice on, 97 to test each version, 100 sealed until the end.
- An answer key for where each fix lived (the docs, general know-how, or only a person), set by two AI labelers from different companies, a tie-breaker, and my reading of their disagreements.
- Blind grading by models from three companies other than the bot's, with a rubric from my book *The Modern CSM*: competence, reliability and empathy, divided by uncertainty.
- Versions built one change at a time: a reviewer, an outside reviewer, a stronger model, a rewritten prompt, the forum's own past answers, friendlier handoffs.

## The result

On the 100 sealed questions, the safest version was confidently wrong 4 times, twice the budget. It answered only 5 on its own and handed 87% of the questions it could have answered to a person. Two levers clearly cut confident wrong answers on the same 97 questions. A reviewer cut them from 30 to 2 but blocked 13 of the 19 right answers. A stronger drafting model cut them from 30 to 10 while still answering 24. A rewritten prompt and the forum's past answers made no clear difference. Reading the stronger model's 10 flagged replies as a support lead, I'd call 2 of them trust incidents; where the graders saw material errors, I mostly saw missed fixes.

| | |
|---|---|
| Confidently wrong on the sealed holdout | **4 per 100** (budget 2) |
| Fully answered with no person involved | 5 of 100 |
| Answerable questions handed to a person anyway | 87% |
| Confident wrong answers after swapping the drafting model (test, 97) | 30 → 10 |
| Flagged replies a support lead would count as trust incidents | 2 of 10 |
| Graded replies published with their grades | 1,166 |
| Total model spend, including $8 of follow-up tests run after the final test | $81 |

## What broke, and what I changed

- My first scoreboard rewarded caution: the round-one bot tied a bot that hands off everything. I rebuilt the test before touching the bot, and an outside AI review of the plan found 30 problems.
- My answer key was wrong. It said 69% of test questions needed a person; the corrected key says 31%.
- My grading form left "correct" undefined, so no model came close to my own grades (8 to 11 matches out of 19). My grades became a finding, not a gate.
- Fixes broke things too. A friendlier handoff template brought bluffs back (0 to 5 on practice), and a forum workaround became the only unsafe reply: an instruction that would delete the customer's data.
- I wrote down 22 predictions about the results before the runs. 10 missed, and every miss is published.

## What I'd tell a support leader

1. Set your trust budget before you measure deflection.
2. Test the model that writes the answers before adding layers on top of it.
3. Read your escalations. 69 of these 240 questions needed something the docs don't have: 47 point to articles to write, 15 to known bugs a bot should be told about ([DOCS-GAP.md](DOCS-GAP.md)).

---

Results page with every reply and grade: [joncmarx.github.io/support-agent-audit](https://joncmarx.github.io/support-agent-audit/) · Code: this repository · Contact: joncmarx@gmail.com
