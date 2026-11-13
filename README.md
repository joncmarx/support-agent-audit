# Support Agent Audit

How often is an AI support agent confidently wrong? I built a support bot that answers from [n8n](https://n8n.io)'s public docs, set a trust budget before the final test (no more than 2 confidently wrong answers per 100 questions), and tested it on 240 real questions from the [n8n community forum](https://community.n8n.io). Every reply and every grade is published, with the graders' reasoning.

**Results page:** [joncmarx.github.io/support-agent-audit](https://joncmarx.github.io/support-agent-audit/) · **One-page case study:** [CASE-STUDY.md](CASE-STUDY.md) · **Docs-gap report:** [DOCS-GAP.md](DOCS-GAP.md)

## The result

On 100 questions sealed until the final version was frozen, that version was **confidently wrong 4 times** (exact 95% range 1.1 to 9.9 per 100). The budget was 2. It fully answered 5 questions on its own and handed 62 of the 71 answerable questions to a person.

Every version answered the same 97 test questions with the same docs. Only one thing changed at a time.

| Version (test set, 97 questions) | What changed | Fully answered | Confidently wrong | Unnecessary handoffs per 100 answerable |
|---|---|---|---|---|
| Hand off everything | Sends every question to a person | 0 | 0 | 100 |
| v1 | Default docs-bot instructions (gpt-5.4-mini) | 6 | 18 | 46 |
| v4 drafts | Private triage note before replying, no review | 19 | 30 | 18 |
| **v4 as built (final)** | Same-model reviewer; unverified drafts become handoffs | 6 | 2 | 91 |
| B | v4's drafts reviewed by MiMo-V2.6-Pro instead | 13 | 8 | 61 |
| D | GPT-6.1 Sol writes the drafts, v4's prompt, no reviewer | 24 | 10 | 33 |
| F0 | Rewritten prompt, no reviewer | 24 | 33 | 10 |
| F | F0 plus up to 3 earlier accepted forum answers | 27 | 29 | 7 |
| **Final version, sealed holdout (100)** | | 5 | **4** | 87 |

- **Two levers that clearly cut confident wrong answers:** v4's own reviewer (30 to 2, but fully answered fell from 19 to 6) and swapping the drafting model (D: 30 to 10 against v4's drafts, paired difference −20.6 per 100, 95% range −30.9 to −10.3, while still answering 24).
- **The levers that didn't:** a rewritten prompt (F0) and the forum's own past answers (F) made no clear difference. A friendlier handoff template (G, practice only) took confident wrong answers from 0 to 5 of 43.
- **Chosen by rule:** only v4 as built passed the practice screen (at most 1 confidently wrong of 43), so it became the final version. That is "chosen by rule", not "clearly better".
- **A support lead's read:** of the 10 replies the graders flagged for version D, I count 2 as trust incidents. Where the graders saw a material error stated as fact, I mostly saw a reply that missed the better fix, and three I'd send as written.

## Added after the final test (October 28)

The holdout result above stands. Afterward I tested the pieces the main run left out: a review step and a routing step for the stronger model. This had a small extra budget, its own predictions and a stop rule written before the runs (`runs/PREREGISTRATION.md`). Test set, 97 questions:

| Configuration | Fully answered | Confidently wrong |
|---|---|---|
| D: GPT-6.1 Sol writes the drafts, no reviewer (from the main run) | 24 | 10 |
| H: Sol checks its own drafts | 20 | 11 |
| I: a separate checker (MiMo-V2.6-Pro) reviews Sol's drafts | 23 | 10 |
| R: my routing rules decide first, then D answers | 9 | 9 |
| RH / RI: routing, then H or I | 7 / 8 | 9 / 9 |

- **Neither checker caught any of Sol's 14 bluffs** (practice and test). The same separate checker caught 23 of 30 from the cheaper model.
- **My routing rules sent 81 of 97 questions to a person**, including 53 of the 67 answerable ones. Six of its handoffs were graded confidently wrong: they told people with how-to questions to file a bug on GitHub. I read 5 of those 6 as trust incidents. I can forgive a missed fix; I can't forgive a reply that sends the customer the wrong way.
- **The stop rule wasn't met** (it needed fewer than 10 confidently wrong and at least 19 fully answered), so no follow-up configuration ran on the sealed questions.

Code: `audit/followup.py`, prompts in `prompts/ROUTER*.md`. Output: `runs/v3plan/followup/`.

## How it was tested

- **Questions:** solved threads from January to September 2026 whose accepted answer was written by someone other than the asker. 43 practice questions shaped round one's versions and screened the later ones; 97 test questions scored each version once; 100 holdout questions were drawn and sealed on 2026-09-30 and opened on 2026-10-16, after the freeze.
- **Answer key:** for each question, where the fix lived: n8n's docs, general technical know-how, n8n know-how the docs don't have, a known bug, or something only n8n staff can do. Two labelers (Claude Sonnet 5.5, Gemini 3.8 Flash) each ran three recorded searches; Muse Spark 1.3 broke ties blind; I read every disagreement that crossed the answerable / needs-a-human line. Rules: `rubric/LABELING-v2.md`.
- **Grading:** two graders from different companies (Claude Sonnet 5.5, Gemini 3.8 Flash) graded every reply blind to the version and the label; Muse Spark 1.3 broke ties. A three-way split counts as confidently wrong when any grader saw a material error stated as the answer. Rubric: `rubric/RUBRIC-v3.md`, built on the Confidence Equation from *The Modern CSM* (competence, reliability and empathy, divided by uncertainty). Outcome table: `audit/outcome.py`.
- **Rules fixed in advance:** the trust budget (at most 1 of 43 on practice, at most 2 of exactly 100 on the holdout), the selection rule, and predictions written before the runs they predict, all logged with timestamps in [`runs/PREREGISTRATION.md`](runs/PREREGISTRATION.md). 22 predictions about the results; 12 hit. Misses are reported, never re-tuned. The log also holds predictions about the measuring itself (parse rates, grader agreement).
- **The plan:** [`TEST-PLAN-v3.md`](TEST-PLAN-v3.md), written after round one and an outside review of the earlier plan ([`TEST-PLAN-v2-REVIEW.md`](TEST-PLAN-v2-REVIEW.md), 30 issues).

## Where things are

| Step | Code | Output |
|---|---|---|
| Collect solved threads | `audit/collect.py` | `data/questions.jsonl` (ids, titles, links) |
| Freeze and index the docs | `audit/docs_index.py` | `data/docs_commit.txt` |
| Seal the holdout | `audit/holdout.py` | `sealed/` (not published) |
| Answer key (labels v2) | `audit/labels2.py`, `audit/labelbatch.py`, `audit/labelrun.py` | `runs/v3plan/labels/final.jsonl` |
| Bot versions v1–v4 | `audit/bot.py`, `audit/pipeline.py` | `runs/v*__openai_gpt-5.4-mini/` |
| Blind re-grade and settlement | `audit/regrade.py`, `audit/grade3.py`, `audit/outcome.py`, `audit/severity.py` | `runs/v3plan/regrade/` |
| Reviewer trial and arm B | `audit/build2.py` | `runs/v3plan/build2/` |
| Arm D | `audit/armd.py` | `runs/v3plan/armD/` |
| Forum harvest, community labels, arms F0, F, DF, G | `audit/harvest.py`, `audit/community.py`, `audit/community_labels.py`, `audit/armf.py` | `runs/v3plan/armF/`, `runs/v3plan/community/labels/` |
| Holdout | `audit/holdoutrun.py` | `runs/v3plan/holdout/` |
| Follow-up tests (after the final test) | `audit/followup.py` | `runs/v3plan/followup/` |
| Results page data (re-derives every count and checks it against the score files) | `audit/site3.py` | `site/data/` |
| Results page and case study | `site/template3.html`, `site/build_page.py`, `site/case-study.html` | `site/index.html` |
| Docs-gap report | `audit/docsgap.py`, `data/docs_gap_themes.json` | `DOCS-GAP.md` |
| Pre-publish scan for copied forum text | `audit/forumscan.py` | |
| Spend | `runs/ledger.py` | `runs/cost_ledger.jsonl` |

Each module's docstring lists its commands. `audit/site.py` and `site/template.html` built round one's page and are kept for the record.

## Run it yourself

You need Python 3.10+ and your own [OpenRouter](https://openrouter.ai) key (`OPENROUTER_API_KEY`). Runs are billed to your key. Forum post text isn't in this repo, so start with `python3 -m audit.collect`, which fetches the threads into `.cache/`. n8n's docs are fetched at the pinned commit in `data/docs_commit.txt`, not copied.

## What's not here

- **Forum post text.** Posts belong to their authors. The repo keeps thread ids, titles, links and our own generated text: bot replies, reviewer notes, grader reasoning and the labelers' one-line fix summaries. Raw batch files, label inputs and the harvest are git-ignored. Before publishing, `audit/forumscan.py` checked every file for runs of 12 or more words found in forum posts and not in n8n's docs; what remains is long thread titles, error messages and short config lines that the bot or a grader repeated (the longest is 28 words, a code snippet).
- **The sealed holdout files**, for the same reason.

## Limits

- One product, in English. People post on a forum after the docs failed them, so these questions are harder than a typical support queue.
- "Fully answered" means the graders matched the reply to the accepted fix. No customer was asked whether their problem went away.
- The graders and labelers are models. Their reasoning is published with each grade so you can check it (Gemini left it blank on 104 of the 1,166 replies). On the 403-reply re-grade, the two graders agreed on the outcome 72% of the time before tie-breaks (κ 0.64).
- Each version ran once per question, and model runs can't be made exactly repeatable. 100 questions separate large differences, not small ones.
- Missing the budget on 100 questions doesn't prove the true rate is above 2 per 100, and meeting it wouldn't have proved it below.

## Cost

$80.94 in model calls through OpenRouter: $19.38 for round one, $53.74 for the rebuild under Test Plan v3, $7.82 for the follow-up tests. Every call is in `runs/cost_ledger.jsonl`.

## Thanks

To n8n's docs team for open, versioned docs, and to the forum members whose accepted answers made the answer key.

Built by Jonathan Marx.
