---
title: Support Agent Audit — Test Plan v3
status: DRAFT for JC's review (2026-09-30, evening). Replaces TEST-PLAN-v2.md for everything run from here on. No model spend before Build 1.
replaces: TEST-PLAN-v2.md, which stays unchanged as the version the outside review checked (the review cites its section numbers). PLAN.md stays as the record of v1–v4.
review: v2 was reviewed by GPT-6 Astra (OpenAI) on 2026-09-30 — see TEST-PLAN-v2-REVIEW.md. It found 30 issues. Section 15 says what happened to each one. A draft of v3 was then checked by an independent agent that hadn't seen how it was written. It found 8 must-fix and 12 smaller problems, all folded in: the Build 1 order, gaps in the outcome table, who writes handoffs, how community answers are labeled, thinking levels, and the checkpoint budget math.
precedence: This file controls execution. research/MODEL-LANDSCAPE-2026-09.md is dated background research; where the two differ, this file wins. The exact settings live in runs/MANIFEST.json, written in Build 1 and frozen before each paid phase.
---

# Support Agent Audit — Test Plan v3

## The plan in one paragraph

Round one built a support bot that almost never bluffs, but its headline score tied a bot that hands every question to a human. Before spending more money, we audited the test itself and found that the measuring stick was weak. Test Plan v3 fixes the measuring stick, then answers one question that support leaders face when they buy or build an AI agent: **is the bot held back by judgment (a smarter model) or by knowledge (what it's allowed to read)?** We test each lever on the same questions, pick the best version on practice questions by a rule written down in advance, and confirm that version once on 100 fresh questions nobody has looked at. Finding and fixing the flaws in our own test, including the ones an outside reviewer found in this plan, is part of the case study.

---

## 1. What changed from v2

An outside model (GPT-6 Astra, from OpenAI) reviewed v2 and found 30 issues: 17 it called must-fix, 10 should-fix and 3 minor. v3 responds in two ways.

**It cuts the plan down to the question a support leader needs answered.** The two open-weight arms (Chinese and Western), the Opus reviewer arm, both ceiling checks, the label-sway check, the grader-1 model trial, the holdout repeat run and the re-grade of v2 and v3 are deferred (section 20). They answered research and procurement questions rather than the core one, and they caused most of the rule problems the review found.

**It writes down the rules the review found missing.** v3 adds:
- a complete outcome table that doesn't reward hedged wrong advice;
- a grading rule that separates "true" from "found by the bot's search";
- credit for the knowledge arm when the forum had already answered a question;
- a trust gate whose math matches the 2-per-100 budget;
- a defined fallback for every model call that fails;
- one rule for settling grader disagreements;
- a call-by-call budget.

**One of the review's concerns is answered by data.** The review worried that the reviewer-code bug (finding 9) might have distorted v4's own results, which would make arm B an unfair comparison. It didn't. v4's reviewer never came near its 400-token limit (its longest reply was 101 tokens), and none of its 87 blocks came from an unreadable reply. The bug only affected the looser-reviewer trial with Google's model.

**Expected spend:** about $53–61 if grader 1 runs on JC's Claude plan, and about $90–97 if it can't (section 13). The key's limit drops from $110 to $80.

---

## 2. What round one taught us (evidence, 97 test questions)

All numbers come from the stored run files. Findings 2 and 4 are the round-one grader's classifications; phase 1 re-takes them with the new measuring stick before anything depends on them.

| # | Finding | Number |
|---|---|---|
| 1 | v4's "handled well" score equals the hand-off-everything baseline. | Both 69% (67 of 97) |
| 2 | v4's reviewer blocked almost everything. It stopped 17 of 18 bluffs, but also 9 of 13 correct answers, 22 of 24 partial answers and 5 of 5 good clarifying questions. It even blocked 34 of the 37 drafts that were already handoffs, and rewrote them. | 87 of 97 drafts blocked |
| 3 | The bot's search usually found the right page. For 27 of the 30 docs-answerable questions, it returned the doc page the labeler used as evidence. Whether the exact passage with the fix reached the bot is checked in Build 1 at no cost. | 27 of 30 pages |
| 4 | The "needs a human" group is mixed. Of the 56 questions labeled "fix not in the docs", the v3 drafts fully solved 6 and partly solved 11, often with general technical knowledge the bot is allowed to use. The same group also holds 15 of v3's 18 bluffs. Across all versions except v2 (which bluffed 43% of the time), 17 of the 67 "needs a human" questions got at least a partial fix from some version. | 17 of 67 |
| 5 | The grader's reasoning names the label in 86 of v4's 97 grades. That is mostly by design (the round-one rubric used the label to judge handoffs), so it shows how tightly grades were tied to the answer key rather than proving bias. | 86 of 97 |
| 6 | The empathy score doesn't tell replies apart. | v1: 96 of 97 scored 1 |
| 7 | Handoffs don't pick a route. All 75 were written by v4's rewrite template, which lists three routes. | 75 of v4's 90 handoffs |
| 8 | v4's handoff writer is told "do not give ... steps to try," which contradicts *bad news fast* (The Modern CSM, Ch4): bad news ends with what the customer can do now. | Design flaw |
| 9 | **The reviewer code can fail silently.** It caps the reviewer's reply at 400 tokens and counts three unreadable replies as "unsafe." About half of the calls to Google's model in the looser-reviewer trial ran into that cap, so that trial's result isn't clean. **v4's own results were not affected** (checked 2026-09-30): its reviewer's longest reply was 101 tokens, and none of its 87 blocks came from an unreadable reply. | Harness flaw; v4 unaffected |
| 10 | One model (Claude Sonnet 5.5) wrote all labels and all 388 test grades. No second opinion and no human comparison was measured. | No agreement data |
| 11 | **Some questions were edited after posting.** (New, 2026-09-30.) 34 of the 140 evaluated questions had their first post edited later, and 4 of those now contain words like "solved" or "update." Round one used the edited text, so a few questions may carry a hint of the answer. Build 1 compares each one with its original version at no cost. | 34 of 140 edited |

**What this means:** the round-one headline ("69% of real questions need a human") may move once the answer key separates general technical fixes from truly undocumented ones. That's why the measuring stick is fixed before we spend on new bot versions.

---

## 3. The experiment: two levers

A support leader who wants a better AI agent has two places to spend money: a **smarter model** (judgment) or **better knowledge** (what the bot can read).

| Arm | Drafts written by | Reviewer | Knowledge | Answers the question |
|---|---|---|---|---|
| Baseline | — | — | — | What does handing off everything score? ($0, computed) |
| v1 (re-graded) | Low-cost model | None | Docs | What does a default bot do? |
| A = v4 (re-graded) | Low-cost model | The same low-cost model | Docs | Where are we now? |
| B. Smarter reviewer | v4's stored drafts | Best independent reviewer (practice trial) | Docs | Was v4's problem judgment? |
| D. Smarter drafter | Premium model (GPT-6.1 Sol) | B's reviewer | Docs | Would a better model write better answers? |
| F0. Knowledge control | Low-cost model | B's reviewer | Docs + an **empty** community section | Isolates the prompt change that F needs |
| F. Knowledge harvest | Low-cost model | B's reviewer | Docs + **solved community threads** | Was the problem knowledge? |
| G = v5 | The drafter, reviewer and knowledge of one complete arm above (A, B, D, F0 or F), chosen on practice | The same | The same | The best eligible version, with its handoff writer switched to *bad news fast* |

**Why each comparison is clean:**
- **A vs B.** B judges v4's stored drafts with v4's exact review prompt and answer format, on the repaired harness. When both reviewers block the same draft, B reuses v4's stored handoff. So B differs from v4 only in its pass-or-block decisions. We report those decisions (bluffs caught, correct answers let through) separately from the final replies.
- **B vs D.** D uses v4's drafting prompt, the exact passages v4 retrieved for each question, and B's reviewer. Only the drafting model changes.
- **F0 vs F.** Both use the same new prompt, which tells the bot and reviewer that community answers exist. Both get exactly the doc passages v4 retrieved. F also gets a separately capped community section; F0's is empty. So F minus F0 is the knowledge effect alone.
- **With and without a reviewer.** The pre-review drafts of D, F0 and F are graded too, so each lever is measured both with and without the reviewer. This also shows whether the reviewer blocks good answers that new knowledge made possible.
- **Paired.** Every arm answers the same 140 questions (43 practice and 97 test), so arms are compared question by question.

**Who writes the handoff when a reviewer blocks a draft.** In every arm, the arm's own drafting model rewrites the blocked draft as a handoff using v4's template, exactly as round one did.
- In B, the rewriter is the low-cost model, and v4's stored handoff is reused wherever v4 also blocked.
- In D, the rewriter is GPT-6.1 Sol.
- Only G switches to the *bad news fast* template.

No drafting model comes from a grader's company, so graders never score their own company's writing.

**Company independence** (checked automatically before any call):
- No model grades text written by its own company.
- No reviewer reviews drafts from its own company.
- No reviewer comes from a grader's company, because a reviewer that shares the grader's taste would pre-apply the grader's standard.

One exception, stated openly: arm A (v4) is re-graded as it was built, with the low-cost model reviewing its own drafts. v2's second exception (the Opus reviewer) is gone with that arm.

---

## 4. The data: question sets, the sealed holdout, and what the bot may see

**Sets:** practice 43 questions, test 97, holdout **exactly 100**.

**Drawing the holdout.** These rules are written before any candidate is looked at.
- It comes from the same pool and the same seeded random order round one used (seed 20260929, 1,031 candidates).
- It continues past the threads already used and takes the next 100 that pass round one's filters: Questions category; solved; created 2026-01-01 to 2026-09-15; accepted answer written by someone other than the asker (and not an auto-reply account); question at least 20 words (60 if it has images); answer at least 20 words; English.
- These are also excluded:
  - threads that link to, or are linked from, a practice or test thread;
  - cross-posts (the same asker as a practice or test thread, with a similar title within 14 days);
  - threads whose accepted answer copies a practice or test solution.
- An excluded thread is replaced by the next one in order. Duplicates inside the holdout keep only the first.

**Sealing the holdout.**
- The holdout's questions and solutions go into a separate git-ignored folder, and a hash of each file goes into `runs/PREREGISTRATION.md`.
- They stay out of every build and tuning session until v5 is frozen in Build 3. Holdout labels are made after the freeze.
- We say plainly that round-one test results shaped this design. For that reason, test-set results for the new arms count as exploratory, and the holdout is the primary result.
- The holdout is "unseen by this project," not "unseen by the models." Public forum text may be in a model's training data.

**What the bot sees: one snapshot per question, as of the moment it would answer.**
- **Holdout:** the original version of the thread title and of the first post, both taken from the forum's public edit history. Nothing posted or edited later. If a title's history isn't available, the current title is used with any "[SOLVED]" tag removed, and the question is flagged.
- **Practice and test:** every arm uses the same text round one used, so the arms stay comparable. In Build 1, the 34 edited questions are compared with their originals. Any whose edit adds solution content are flagged, and results are reported both with and without them.
- **Kept away from the bot:** accepted answers, the labelers' fix-based searches and their results. These exist only in the evaluation path; the bot pipeline never reads them.

**Docs retrieval.** The docs are pinned to one commit (`data/docs_commit.txt`) and the existing index. Retrieval uses v4's settings: hybrid search, 8 passages, and the query with node names. For practice and test, arms B, D, F0 and F reuse the passages round one retrieved for each question. The holdout runs retrieval fresh with the same settings.

**The community harvest (arm F only).**
- **Pool:** solved threads in the Questions category, created 2025-07-01 to 2026-09-15, collected from the forum's public data feed in thread-number order. The exact count is recorded.
- **Excluded:** all practice, test and holdout threads; threads by the same asker as the question being answered; cross-posts; and any thread whose accepted answer copies an evaluation solution.
- **Time rule:** for each question, only accepted answers **posted** before the question was posted are eligible (compared by full timestamp), and the answer must not have been edited after that moment. The forum doesn't record when an answer was marked accepted. So this is a collection, made afterward, of answers that were *eventually* accepted, and the case study says so. It doesn't claim to reproduce exactly what a team could have harvested at the time.
- **Retrieval:** each harvested thread is indexed by its title plus its accepted answer, using the same embedding model and hybrid search as the docs. F gets the top 3 eligible community answers, capped at 1,500 tokens in total, in a separate section labeled as peer-written answers, not official docs. The retrieved thread IDs and text are stored for every question.

---

## 5. The answer key (labels v2)

Every question gets one category, based on the **key step** of a verified fix (the step without which the fix fails). The accepted answer is the starting reference. A labeler may record a different fix only if a doc passage or well-established general knowledge supports it, and must cite that evidence. Labelers never see any bot reply. When more than one category fits, the first in this order wins:

| Order | Category | Meaning | Right move for a docs bot | Allowed handoff route | In the docs-gap report as |
|---|---|---|---|---|---|
| 1 | `account_access` | The fix needs a **privileged action the customer can't take themselves**: n8n staff, billing, or n8n Cloud infrastructure. Steps customers can take in their own instance once told how don't count. | Hand off | n8n support | Always needs a person |
| 2 | `n8n_docs` | The pinned n8n docs contain the key step, including release notes (for example "fixed in version X, upgrade"). | Answer | — | — |
| 3 | `general_tech` | The key step is standard technical knowledge outside n8n (SQL, HTTP, OAuth, Docker, JavaScript). | Answer (the bot's rules allow it) | — | Not a docs gap |
| 4 | `bug_or_release` | A bug or regression with no documented fix yet. | Hand off | GitHub (or n8n support, for a Cloud customer whose instance is affected) | Known issues the bot should be told about |
| 5 | `undocumented_n8n` | The key step depends on n8n behavior the docs don't describe. | Hand off | Community forum | Articles n8n could write |

**Each question also records:**
- the evidence passages and the three searches each labeler ran: the original question, one on the key fix alone, and an exact-term search for setting names and environment variables;
- the product version, if the question states one;
- **reference doubt**, which applies when the accepted answer is outdated, is a workaround, or conflicts with the docs for the stated version. It is recorded with the reason and the supporting passage.
- **community available:** was the key step in an eligible earlier community answer? If so, that thread's ID is recorded. This field is labeled in Build 3, once the harvest exists:
  - **Who:** the same two labelers.
  - **What they search:** each runs two searches over that question's eligible harvest (the question itself, and the key fix alone), using the same hybrid search, and reads the top 10 results.
  - **Answer:** yes, with the thread ID, or no.
  - **Disagreements:** the tie-breaker answers blind, and two of three decide.
  - **Holdout:** labeled after the freeze, only if v5 includes the harvest.

A negative finding is worded as "not found under the recorded search protocol," not "not in the docs," unless the relevant docs section was read in full.

**Answerable, per arm.** Each arm is scored against what it was allowed to read.
- For docs-only arms, "answerable with the allowed knowledge" means `n8n_docs` or `general_tech`.
- For F, it also includes questions where a community answer is available, except `account_access`.
- Whether F's search actually found that answer is reported separately, as a diagnostic.

The original five categories still drive the docs-gap report.

**Settling label disagreements:**
1. Two labelers from different companies label every question independently.
2. Where they disagree, the tie-breaker model labels the question without seeing either label.
3. **JC reads** every case where the three labels don't agree on whether the bot could answer or a human is needed, plus every three-way split. These are the cases that move the headline. He gets a side-by-side sheet (the accepted fix on one side, the closest doc passages on the other) and answers two plain questions:
   - Is the key step of this fix on this page?
   - If not, is it something anyone in IT would know, or something specific to how n8n works?

   **His answers decide which side the question is on**, and if it's answerable, whether the category is `n8n_docs` (on the page) or `general_tech` (common IT knowledge).
   - If a question he places on the human side has no two labels agreeing on the category, the tie-breaker's category is used and flagged. That affects only routing and the docs-gap report.
   - If he can't tell, the tie-breaker's label is used and flagged, and results are reported both ways.
4. All other disagreements (for example, bug versus undocumented behavior) are settled by the two-of-three majority.
5. **Reference doubt** is flagged by either labeler. The tie-breaker gives a blind yes or no, and two of three decide. Doubted questions stay in every denominator, and results are also reported without them.

Estimated load for JC: 15–35 items in Build 1 and 10–25 for the holdout in Build 3. Agreement is reported as Cohen's κ, an agreement score that removes the matches two labelers would get by luck. It is computed from the two original labels before any adjudication, and published with the table of disagreements.

---

## 6. The grading rubric (blind)

**What graders see:**
- the customer's question, as the bot saw it;
- the **reference packet**, which is the same for every arm: the accepted answer and the labelers' evidence passages. The community answer is deliberately left out, because the reference must be identical for arms graded before and after the harvest exists. F's grader still sees it among F's own passages.
- the passages this arm's bot actually had;
- the reply, normalized (see below).

**What graders don't see:** the label, the arm, the model, the version, or the reviewer's decision. Items are shuffled across arms.

One residual limit, stated openly: a grader can tell a reply came from arm F when its passages include a community section.

**Normalizing replies.** Replies are converted to plain text before grading, because model judges tend to favor Markdown formatting. In the study we rely on, four of five model judges preferred the Markdown version 73–97% of the time, compared with 57% for people, in a 30-pair comparison with two human annotators. The normalizer:
- removes only emphasis and heading markup;
- keeps code blocks, indentation, commands, URLs and table rows intact.

Originals are kept. JC's 20 human grades use the same normalized text.

**What graders record:**
1. **Action:** answered; asked a question; handed off; mixed (a fix plus a handoff); or no usable reply (empty, malformed or off-topic).
2. **Fix verdict,** for any fix or suggestion anywhere in the reply: correct, partial, wrong, or no fix. It is judged against the reference packet and general technical knowledge. A different fix counts as correct only if the reference packet or well-established general knowledge supports it; a grader's confidence alone isn't enough.
3. **Material error:** does the reply contain a false claim or step that would cost the customer time, data, money or security if followed, or that points them away from the real fix? A wrong detail that doesn't change what the customer does is harmless. A fix verdict of "wrong" always counts as a material error, because a wrong fix points the customer away from the real one (the scoring code enforces this). Examples of each are drawn from the practice set in Build 1 and frozen into the rubric.
4. **Unsafe:** could following any part of the reply cause data loss, a security exposure, or downtime?
5. **Framing:** is any fix presented as *the* answer, or as clearly conditional or diagnostic?
6. **Support:** for each factual n8n claim, is it supported by the passages this bot had, true but unsupported, or false (not real, or contradicted)? *A true claim the bot's search didn't supply is not an invented claim.* This field is reported as a diagnostic of the bot's evidence; it doesn't decide correctness.
7. **Right missing fact** (questions only): did the reply ask for the fact the fix depends on?
8. **Route named:** GitHub, n8n support, forum, several, or none.
9. **Answer checklist (yes/no):** answers what the customer meant; gives a concrete next step; no filler.
10. **Handoff checklist (yes/no), from *bad news fast* and the Playbook Router:** says plainly it needs a human; says why; states what's known and unknown; names **one** route, and that route is allowed for the category; gives a safe thing to do meanwhile; ends with a summary a human can pick up.

**The outcome table** is frozen before the phase-1 re-grade. It is checked in order, and the first matching row wins. Every question gets exactly one outcome per arm. Build 1 includes a test that feeds every combination of rubric fields through the table and confirms each one maps to exactly one outcome.

| Order | What the reply did | Outcome | Counts as |
|---|---|---|---|
| 1 | Any unsafe step, in any framing | `confidently_wrong` | Trust incident |
| 2 | A material error presented as *the* answer (in an answer, a question or a handoff) | `confidently_wrong` | Trust incident |
| 3 | A material error framed as conditional or diagnostic | `wrong_hedged` | No credit; reported separately |
| 4 | No usable reply, or an "answer" with no fix in it | `no_progress` | No credit |
| 5 | Action is "answered" (the fix framed either way), or any reply that presents a fix as *the* answer; the fix is correct | `resolved` | Headline |
| 6 | Same, but the fix is partial or has only a harmless error | `partial` | Some credit |
| 7 | Asked the right missing fact (any fix it offered is conditional) | `right_question` | Moved the ticket forward |
| 8 | Handed off (or mixed, with any fix framed as conditional), possibly with safe mitigation; the question needs a human for this arm | `correct_handoff` | Right call |
| 9 | Same, but the question was answerable with this arm's allowed knowledge | `unnecessary_handoff` | Work pushed onto humans |
| 10 | Anything else that offers a correct or partial fix (for example, a question that misses the key fact but suggests a correct conditional fix) | `partial` | Some credit |
| 11 | Anything else: a generic question ("share more details"), or a question that misses the key fact and offers no fix | `no_progress` | No credit (a stall, not a handoff) |

**Three changes from v2:**
- A hedged wrong fix no longer earns credit (row 3).
- A correct answer counts whether or not it hedges; hedging only softens the penalty when the answer is wrong.
- A generic question now counts as a stall, not a handoff (row 11).

**Flags** are kept alongside the outcome: unsafe, system failure, reference doubt, and unresolved grade.

All replies from v1 and v4 are re-graded this way on both practice and test, so the chart measures every arm with the same stick. The old grades stay in the repo as history.

---

## 7. Graders, disagreements, and the human anchor

**Grader 1: Claude Sonnet 5.5** (Anthropic), at a pinned effort level. It is the same model that graded round one, so the phase-1 re-grade changes the measuring stick without also changing the grader. It runs on JC's Claude plan if the plan check passes, and through the API otherwise.

v2's trial of Opus against Sonnet is dropped: 20 human grades can't reliably tell two strong graders apart.

**The calibration steps run before the new labels exist.** JC's 20 grades, the grader screens and the plan check happen in Build 1, before labels v2. So:
- Their reference packet is the accepted answer plus round one's recorded key fix and evidence pages.
- They compare the **label-free outcome**: the outcome table with rows 8 and 9 merged into "handoff," because only those two rows depend on the label.

**Grader 2 and the tie-breaker.** The candidates are Gemini 3.8 Flash (Google), Muse Spark 1.3 (Meta) and Qwen3.8 Max (Alibaba). All three grade JC's 20 replies. **Grader 2 is the cheapest candidate that passes the calibration screen, and the tie-breaker is the next-cheapest that passes.** Grader 2 is also labeler 2, in a separate session.
- If only one candidate passes, it becomes grader 2, and the next-cheapest becomes the tie-breaker, flagged.
- If none pass, we stop before the re-grade and decide together.

Public leaderboards were used only to make the shortlist; they don't break ties.

**The calibration screen** (the same for grader 1). On JC's verifiable items (those he didn't mark "can't verify"), the candidate must:
- match JC's label-free outcome on at least 70% of them; and
- flag every reply JC judged a trust incident.

**Grader 1 is screened first, before the plan check,** so the check always runs on the model that will actually grade.
- If Sonnet fails the screen, grader 1 becomes Claude Opus 5.5, screened the same way, and the ledger is re-priced for Opus.
- If Opus also fails, we stop and decide together.

**JC's 20 blind grades** are the human anchor.
- **Sampling:** 20 practice replies from v1–v4, one per question. They are stratified across outcome types (about 5 answers, 5 handoffs, 4 questions or mixed replies, and 6 that round one graded wrong, bluffed or partial). The groups and model names are hidden, and the order is shuffled.
- **What JC gets:** the same reference packet and normalized text the graders get, and he may answer "can't verify."
- **What they are used for:** these 20 choose the graders, so they are reported as a calibration set, not as an independent accuracy estimate.

**The Claude-plan check** decides grader 1's route.
- **Sample:** 50 practice replies in a fixed mix: 15 answers with fixes, 15 handoffs, 10 questions or mixed replies, and 10 that round one graded wrong or bluffed.
- **Runs:** each is graded three times: once through the API and twice on the plan, with the same model, effort and rubric.
- **Isolation:** every plan grade runs in a fresh, stateless session with no project folder, memory, tools or web access. It gets only the rubric and the item. Labeler and grader sessions are kept separate.
- **Pass rule:** at least 45 of 50 identical label-free outcomes between the API and the plan, **and** at least 45 of 50 between the two plan runs, **and** no disagreement on the trust-incident flag.
- **If it fails,** or isolation can't be guaranteed, grader 1 stays on the API.
- **If plan limits run out mid-phase,** that phase finishes on the API. The route of every grade is recorded, along with its API-equivalent cost.
- **This is a consistency check, not an accuracy claim.** It also measures how much of JC's plan allowance 50 grades use.

**Settling grader disagreements (the same rule for every primary comparison):**
1. Grader 1 and grader 2 grade every reply independently.
2. If their outcomes match, that's the grade.
3. If they differ, the tie-breaker grades the reply blind, and the outcome two of the three agree on wins.
4. A three-way split is `unresolved`, and so is any reply still missing a grade after retries.
5. **Unresolved replies**, as the main scoring rule:
   - They get no credit.
   - They count as a trust incident if any grader recorded an unsafe step or a material error presented as the answer.
   - Otherwise they count as `no_progress`.

   Best-case and worst-case readings are published alongside.

**Agreement** is computed from the original independent grades, before any tie-break. It is reported as Cohen's κ for action, fix verdict, material error and final outcome, together with the counts behind each and how common each class is. If κ can't be computed (because only one class occurs), raw agreement is reported with the reason.

---

## 8. Pipeline rules: failures, retries, and settings

| Role | Attempts | What counts as a failure | If every attempt fails |
|---|---|---|---|
| Drafter | 3 | Provider error, timeout, empty or unparseable reply | The customer gets a fixed safe handoff; flagged `system_failure` |
| Reviewer | 3 | The same, or no readable pass/block verdict | The customer gets the fixed safe handoff; flagged `system_failure`. The draft is never passed, and the failure is never counted as a genuine block |
| Handoff writer | 3 | The same | The fixed safe handoff |
| Grader | 3 | The same | Missing. It goes to the tie-breaker; if that also fails, `unresolved` |
| Labeler | 3 | The same | Treated as a disagreement (section 5) |

**More rules for failures and settings:**
- **The fixed safe handoff** is a static message. It says the question needs a person, asks for the n8n version and the execution log, and routes to the community forum. **JC writes it** in Build 1: it's five lines, it's his expertise, and it means no model company grades its own words. It is graded like any reply.
- **Thinking levels** are set in the manifest before any trial and aren't changed after results come in.
  - Every model runs at its provider's default level, as a buyer would use it out of the box.
  - Three exceptions:
    - The low-cost drafter keeps round one's setting. Round one sent no setting, so its default is pinned explicitly.
    - Grader 1 runs at high effort.
    - Qwen runs at its medium level, because its default is the highest and multiplies cost.
  - Reply caps are the only thing sized from the trials.
- **Every attempted question stays in every denominator.** For every arm, we report attempt-level and final failure rates, all billed tokens (including thinking), cost, and time.
- **Retries** use identical settings.
- **Reply caps and timeouts** start generous, at 8,000 tokens and 180 seconds for thinking models. They are then sized from the practice trials, to at least four times the longest reply measured there, and frozen.
- **The run manifest** (`runs/MANIFEST.json`) is hashed into `PREREGISTRATION.md` before each paid phase. It lists:
  - the exact model IDs;
  - host pins, with no fallback to other hosts;
  - thinking levels, reply caps, timeouts and retries;
  - prompt and rubric file hashes;
  - output formats;
  - the retrieval settings (docs commit, index hash, passage count, community cap);
  - the harvest snapshot hash;
  - question-set hashes;
  - the resampling seed for the range calculations (20260930);
  - the code commit.
- **Randomness.** OpenAI's models on OpenRouter don't accept a temperature setting, and Anthropic's don't accept a seed, so we can't force identical reruns. The case study says so.
- **Open-weight reviewers:**
  - run on a host at the model's native precision (Kimi K3 at 4-bit, GLM at fp8), with the full advertised context and output length;
  - use a host verified by the lab where a verifier exists, with no automatic fallback to another host;
  - have their host recorded;
  - for GLM, a third-party host rather than Z.ai's own endpoint, because Z.ai is on the US Entity List.

---

## 9. Choosing the reviewer and v5, and the trust gate

**The trust gate (decided by JC on 2026-09-30 and locked now, not at the checkpoint):**
- **Practice screen:** at most **1** confidently wrong answer out of 43. That is 2.3%, so it is a looser screen than the 2% budget, and we say so. On 43 questions, a strict 2% would allow zero, which one unlucky answer could trip.
- **Holdout gate:** at most **2** confidently wrong answers out of exactly 100, which is the 2-per-100 budget applied literally.
- **What counts:** unresolved replies that the conservative rule scores as trust incidents (section 7) count toward both limits.
- **Which questions:** all 43 practice questions count, including any flagged for edits after posting. The flagged ones are also reported separately.
- **Reporting:** observed counts come with an exact 95% range. The wording is "met (or missed) the gate we set in advance," never "proven safe at 2%." For example, 2 out of 100 is consistent with a true rate anywhere from about 0.2% to 7%.

**Choosing the reviewer** is done on practice, by a rule written down in advance.
1. **Common input:** every candidate reviews v4's 43 stored practice drafts, which have already been graded in phase 1.
2. **Scoring each candidate:**
   - drafts it passes keep their grade;
   - drafts it blocks become handoffs, reusing v4's handoff where v4 also blocked;
   - new handoffs are graded.
3. **Screen:** at most 1 confidently wrong answer and a final failure rate of 5% or less.
4. **Ranking** among those that pass, in this order:
   1. most `resolved` (correct drafts kept);
   2. then fewest unnecessary handoffs;
   3. then lowest measured cost per question;
   4. then a fixed order: MiMo, GLM-5.3, Kimi K3.
5. **If none passes,** we stop and decide together. Nothing is re-tuned to make one pass.

**Choosing v5 (G):**
1. **Eligible:** only complete configurations that were actually run: A, B, D, F0 and F. Parts from different arms are never combined without testing the combination.
2. **Screen and rank on practice:**
   - screen: at most 1 confidently wrong answer;
   - rank by most `resolved`;
   - then fewest confidently wrong;
   - then fewest unnecessary handoffs;
   - then lowest measured cost;
   - then arm letter.
3. **Apply the *bad news fast* handoff writer** to the chosen configuration. That is G. On practice, G reuses the chosen arm's drafts and reviewer decisions; only the handoffs are rewritten and re-graded.
   - If G still passes the screen, it becomes v5.
   - If the new handoffs push it over, v5 is the chosen configuration with v4's handoff writer.
4. **Freeze v5** by writing the hashes of its prompts, models, host, retrieval, retry rules and scoring code into `PREREGISTRATION.md` before the holdout is opened.
5. **Run once:** v5 and v4 run on the holdout.
   - If v5 misses the gate, that is the reported result, and nothing is re-tuned.
   - The v5 we report is "the best eligible configuration," and the case study says which configurations were eligible.

---

## 10. How results are reported

| Metric | What it tells a support leader |
|---|---|
| **Fully answered** per 100 questions (`resolved`) | Questions the bot answered correctly on its own, as judged by the graders against the accepted solution. This is the headline. Real ticket deflection isn't measured. |
| **Trust incidents** per 100 (`confidently_wrong`) | Confident wrong or unsafe answers, checked against the trust gate |
| Right question per 100 | Moved the ticket forward; the customer's reply may still need someone |
| Partial per 100 | Helpful, but the customer may come back |
| Hedged wrong per 100 (`wrong_hedged`) | Wrong suggestions that were flagged as uncertain |
| No progress per 100 | Stalls: generic questions, empty replies |
| **Unnecessary handoffs** per 100 answerable questions (denominator shown per arm) | Work the bot pushed onto humans for no reason |
| Handoff quality (checklist score; share with one allowed route) | Whether the human who picks it up starts ahead |
| System failure rate | Whether the harness itself worked |
| Grader agreement (κ, model vs model and model vs JC) | How much to trust all of the above |

**Comparing arms.** Every arm answers the same questions, so the difference between two arms is measured question by question. We resample the question list 10,000 times, with a fixed seed, keeping each question's results for every arm together, and report a 95% range for the difference. If the range excludes zero, the difference is called **clear**; otherwise it is **inconclusive**. Arms are never called tied just because their individual ranges overlap. Each arm's trust-incident rate gets an exact 95% range, because these are rare events.

**Choosing versus proving.** The choice of reviewer and v5 uses the rules in section 9, which work on counts. The case study keeps "chosen by rule" separate from "clearly better": it says a version was picked by the rule, and says it's clearly better only when the range shows that.

**The decision chart:** one dot per arm, with its range. Across: share fully answered. Up: trust incidents per 100. The hand-off-everything bot sits at zero on both. A good bot moves right without rising past the trust-gate line.

---

## 11. Predictions (written down before each paid run)

These are saved to `runs/PREREGISTRATION.md` with a timestamp before each paid phase (and committed to git once the repo exists).
- **Phase 1:** after re-labeling, the share of questions that need a human falls from 69% to between 50% and 65%.
- **Arm B:** the independent reviewer lets through at least 7 of the 13 correct test drafts (v4 let through 4), while letting through at most 2 of the 18 bluffs. These counts are re-taken from the phase-1 re-grade and saved before Build 2.
- **Arm F vs F0:** the harvest adds at least 5 fully answered questions out of 97. This is a prediction, not a significance threshold.
- **Arm D:** a numeric prediction is saved before Build 2.
- **v5 on the holdout:** saved before Build 3.

If a prediction misses, that goes on the page. If a lever doesn't help, that's the finding.

---

## 12. Model lineup

Shortlisted from the model landscape research, with each pick made on practice. Prices are OpenRouter list prices per million tokens (input / output) and are rechecked at build time.

| Role | Model | Company | Route | Alternate (and when it's used) |
|---|---|---|---|---|
| Low-cost drafter (v1, A, B, F0, F) and v4's reviewer (A only) | `openai/gpt-5.4-mini`, thinking pinned to round one's setting | OpenAI | OpenRouter | — |
| Reviewer trial (B), then the reviewer for D, F0 and F | Z.ai GLM-5.3 ($1.40 / $4.40, third-party host); Xiaomi MiMo-V2.6-Pro ($0.435 / $0.87); Moonshot Kimi K3 ($3 / $15) | Chinese labs other than Alibaba | OpenRouter, pinned host | GLM-5.3-Flash, only if no verified host serves GLM-5.3 |
| Premium drafter (D) | GPT-6.1 Sol ($2 / $10) | OpenAI | OpenRouter | GPT-6 Sol, only if 6.1 is unavailable |
| Labeler 1 | Claude Opus 5.5 | Anthropic | JC's Claude plan | Sonnet 5.5, if plan limits run out |
| Grader 1 | Claude Sonnet 5.5 | Anthropic | Plan if the check passes, otherwise OpenRouter | Opus 5.5, if Sonnet fails the calibration screen |
| Grader 2 and labeler 2 | The cheapest to pass the screen among Gemini 3.8 Flash ($0.75 / $3.75), Muse Spark 1.3 ($1.25 / $4.25) and Qwen3.8 Max ($2 / $6; thinking level always set explicitly) | Google, Meta or Alibaba | OpenRouter | — |
| Tie-breaker | The next-cheapest to pass | Google, Meta or Alibaba | OpenRouter | — |

The independence rules in section 3 hold for every possible outcome of the trials.

---

## 13. Budget and call ledger

Estimates start from round one's measured costs:
- grading: 2.0¢ per reply with Sonnet 5.5, plus 40% for the larger rubric and reference packet;
- labeling: 2.4¢ per question;
- the full v4 pipeline: about 1¢ per question;
- other models: list prices applied to round one's token counts.

Thinking models can use more tokens than estimated, so every practice trial measures real cost before the test set runs. The ledger script (`runs/ledger.py`, built in Build 1) prices every call by phase, set, arm, role and route. It counts each reused reply or grade only once: for example, a draft the reviewer passed is graded once, and a handoff reused from v4 is not re-graded.

| Phase | Work | Grader 1 on the plan (expected) | Grader 1 on the API |
|---|---|---|---|
| 1. Measuring stick | Seal the holdout; grader-2 screen on JC's 20; the plan check; labels for 140 questions; blind re-grade of v1 and v4 (final replies, plus v4's pre-review drafts); tie-breaks | $12–15 | $24–26 |
| 2. Judgment | Reviewer trial (3 candidates × 43 practice drafts); arm B on test; new handoffs; grading | ~$5 | ~$6 |
| 3. Better drafter | Arm D on 140 questions, with review and grading | $9–10 | $15–16 |
| 4. Knowledge | Harvest ($0); community-availability labels; arms F0 and F on 140 questions; grading | $16–18 | $27–30 |
| 5. Final | G on practice; holdout labels; v4 and v5 on the holdout; grading of final replies | $11–13 | $18–19 |
| **Total** | | **$53–61** | **$90–97** |

The low end assumes Gemini wins grader 2 and the high end assumes Muse Spark. A Qwen win, or Kimi K3 winning the reviewer trial, would raise costs; both are measured in the practice trials before anything larger runs. Grading is the largest cost.

**The key:** a new OpenRouter key with an **$80 limit**, replacing v2's $110, because JC's direction is to spend as little as possible without gutting the project. The old key is deleted. About **$35** of credit goes in before Build 1. That covers phase 1 even if grader 1 has to stay on the API and the phase runs its allowed 30% over. The rest is added at the checkpoint. The limit is the hard stop.

**Stop rules:**
- **Before each batch,** the ledger re-prices it with measured costs, and the batch runs only if the remaining limit covers its estimate plus 30%.
- **Any phase** that runs more than 30% over its estimate stops, and we decide together.
- **At the checkpoint,** if grader 1 couldn't move to the plan, the full plan on the API (about $90–97) doesn't fit under $80. Dropping arm D alone doesn't fix that: it would leave $74–82, and the headroom rule would still block the final phase. So the working option is raising the limit back to $110, which fits with headroom. JC decides at the checkpoint, with measured numbers in hand.

---

## 14. Session arc (four build sessions, then publish)

| Session | Work | JC's part |
|---|---|---|
| **Build 1: fix the measuring stick** | 1. Write the manifest, the ledger and the phase-1 predictions ($0). 2. Draw and seal the holdout ($0). 3. Repair the harness; build the normalizer and the outcome table with its all-combinations test; dry-run on 5 practice questions (pennies). 4. Write and freeze F0/F's prompt and G's *bad news fast* handoff template now, before any new arm has a score. 5. $0 checks: whether the fix passage reached the bot for the 30 docs-answerable questions; original versions of the 34 edited questions. 6. JC's 20 blind grades. 7. Screens on JC's 20: grader 1 first, then the three grader-2 candidates → grader 1, grader 2 and the tie-breaker. 8. The Claude-plan check on grader 1's model → grader 1's route. 9. Labels v2 → tie-breaks → JC's reading. 10. Blind re-grade of v1 and v4. 11. Start the harvest crawl ($0). | Write the five-line safe handoff. Grade 20 replies blind. Read label disagreements (15–35). |
| **Checkpoint** | Corrected baseline, grader agreement, the plan-check result, spend so far, re-priced ledger | Go or no-go on phases 2–5. Top up credit. The trust gate is already locked. |
| **Build 2: the judgment levers** | Save predictions → reviewer trial on practice → arm B on test → arm D | — |
| **Build 3: knowledge and final** | Save predictions → community-availability labels → arms F0 and F → choose v5 on practice → G on practice → freeze → holdout labels → holdout runs of v4 and v5 | Read holdout label disagreements (10–25). Optional: a QA verdict on five v5 handoffs for the video. |
| **Build 4: ship prep** | Results page, docs-gap report, case study, content drafts, video script | Review everything |
| **Publish** | Repo, Pages, video, posts | Approve and post; every public step stays his |

---

## 15. The outside review: what happened to each issue

"Fixed" means the rule is now written in this plan. "Cut" means the issue belonged to a deferred arm or step. "Wording" means we narrowed a claim.

| # | Issue | What we did | Where |
|---|---|---|---|
| M01 | B vs historical A might reflect the harness repair, not the reviewer | **Checked with data:** v4's reviewer never neared the cap (max 101 tokens; 0 unreadable). B uses v4's review prompt and format, reuses v4's handoff when both block, and reports decisions separately. No replay run needed. | §1, §3 |
| M02 | G changes the system after the winner is chosen | Fixed: only complete tested configurations are eligible; G is evaluated on practice and frozen before the holdout | §9 |
| M03 | Holdout and practice-only boundaries not enforceable | Fixed: sampling rule, seed, exact size, replacement, duplicate checks, sealing; old test results acknowledged; F0/F's prompt and G's template frozen in Build 1, before any new arm has a score | §4, §14 |
| M04 | Unclear what the bot receives at question time | Fixed: one snapshot per question; original post text on the holdout; the harvest described as retrospective | §4 |
| M05 | Outcome table incomplete; rewards hedged wrong advice | Fixed: ordered, exhaustive table; unsafe and material errors checked first; `wrong_hedged` and `no_progress` added; tested against every combination | §6 |
| M06 | Truth conflated with retrieval support; arms graded on different evidence | Fixed: correctness judged against a reference packet common to all arms; support is a separate diagnostic; blinding limit stated | §6 |
| M07 | Harvest answerability collected but not used | Fixed: answerability depends on each arm's allowed knowledge | §5 |
| M08 | No rule for combining graders | Fixed: two-of-three rule; a conservative policy for unresolved replies; agreement measured before adjudication | §7 |
| M09 | B+ and the Opus ceiling scored by a different panel | Cut (deferred to part 2) | §20 |
| M10 | Trust gate math doesn't implement 2 per 100 | Fixed (JC's decision): a stated looser practice screen, a literal 2 of 100 on the holdout, exact ranges, "met the gate" wording, locked now | §9 |
| M11 | Overlapping ranges used as a tie rule | Fixed: paired resampling of differences; "clear or inconclusive"; exact ranges for rare events; deterministic selection rules | §9, §10 |
| M12 | Selection and settings not executable | Fixed: written selection rules, the run manifest, alternates with triggers; the guessing-rate tie-break removed | §8, §9, §12 |
| M13 | Claude-plan check has no pass rule or isolation | Fixed: fixed sample mix, 45/50 thresholds, zero trust-flag disagreements, stateless sessions | §7 |
| M14 | E-CN lineup invalid under some trial outcomes | Cut (deferred to part 2) | §20 |
| M15 | Failure behavior undefined | Fixed: per-role attempts, the fixed safe handoff, flags, denominators | §8 |
| M16 | Budget undercounts grading; no ledger | Fixed: call ledger with reuse rules; re-priced before each batch; checkpoint choice defined | §13 |
| M17 | Harvest and retrieval not reproducible | Fixed: pinned docs, v4's passages reused, harvest pool and index defined, community slot capped separately | §4 |
| S01 | Human anchor used as both selection set and validation | Fixed: stratified 20, "can't verify" allowed, reported as calibration only | §7 |
| S02 | `account_access` confuses information with authority | Fixed: privileged actions only; allowed routes per category; verified alternative fixes | §5 |
| S03 | Page found ≠ fix passage supplied | Wording plus a $0 passage check in Build 1; negative labels worded by search protocol | §2, §5 |
| S04 | Closed-book guessing rate used as a tie-breaker | Removed; shortlist only | §7, §19 |
| S05 | E-CN vs E-US doesn't isolate model origin | Cut (deferred); the part-2 claim will be "these two pipelines," not "origin" | §20 |
| S06 | Direction of the docs-date asymmetry unproven | Wording: direction unknown; version recorded | §5, §16 |
| S07 | Label-sway check doesn't isolate its cause | Cut | §20 |
| S08 | "Resolved without a human" and "self-hostable" overstate | Wording: "fully answered (judged)"; deflection not measured; self-hosting deferred | §10, §16 |
| S09 | Reference doubt has no downstream policy | Fixed: trigger, evidence, adjudication, reported separately | §5, §7 |
| S10 | Normalization could alter content; publication rule | Fixed: normalizer keeps code and structure; pre-publish scan for copied thread text | §6, §16 |
| N01 | The two documents disagree | Fixed: precedence statement in the header | Header |
| N02 | Benchmark labels and numbers | Mostly moot after the cut; set sizes stated exactly; MODEL-LANDSCAPE is marked as background | Header, §4 |
| N03 | External evidence generalized | Wording: the formatting study's sample stated; the Mistral note moves to part 2 | §6, §20 |

**Where we disagreed with the review:** one place. It proposed replaying v4's reviewer through the repaired harness as a new control. The stored runs show the harness never affected v4's reviewer, so that run would add noise, not control. Everywhere else the review was right. We fixed the problem, cut the arm that had it, or narrowed the claim.

---

## 16. What we claim, and what we don't

- **"Fully answered,"** not "resolved without a human." Graders judge a reply against the accepted solution; nobody measured whether a real customer's problem went away.
- **"Met the trust gate we set in advance,"** not "proven safe."
- **"Chosen by rule,"** kept separate from "clearly better."
- **"The best eligible configuration,"** not "the best possible bot."
- **Search:** "found the labeler's page in 27 of 30 cases," not "search isn't a bottleneck," until the passage check is done.
- **Unseen:** "unseen by this project," not "unseen by the models."
- **The harvest:** "answers that were eventually accepted, posted before each question," not an exact reconstruction of what a team knew at the time.
- **Docs pinned to one recent commit:** this may help or hurt older questions. The direction is unknown, so there is no "underestimate" claim.
- **Before publishing,** every page and export is scanned for copied forum text. The site publishes thread IDs, credit to the community, and our own generated replies, not thread text.

---

## 17. What ships, where JC's frameworks show up, and the content bank

**What ships:**
- **Results page:** the decision chart, the two-levers result, the corrected answer key, a "what we got wrong" timeline (round one and this review), the docs-gap report, and every reply with both graders' verdicts.
- **Docs-gap report,** written constructively: articles n8n could write, known issues a bot should be told about, questions that always need a person, and questions general knowledge covers. It credits n8n's team and the forum community.
- **Tool build-out case study:**
  - the problem;
  - v1–v4;
  - the audit of our own test;
  - the outside review and what we changed;
  - the results;
  - what a support leader should do on Monday: set a trust budget, harvest solved threads, fix routing;
  - what broke and what changed.

  The one-page case study is the short version.
- **Public repo, two-minute video, and Featured blurb.** The drafts in `_internal/` are superseded and get rewritten in Build 4.

**Where JC's frameworks show up** (unchanged from v2):

| Framework (source) | Where it's used |
|---|---|
| **Confidence Equation** (Modern CSM, Ch1) | The rubric: Competence = correct fix; Reliability = no false claims; Empathy = the checklists, "hearing what they meant"; Uncertainty = asking or handing off |
| **Escalation isn't weakness** and **bad news fast** (Ch4) | The handoff standard and checklist; the fix to v4's "no steps to try" rule |
| **The Handoff** (Ch10) | "A sloppy handoff hits all four variables": the summary requirement |
| **Leading indicators** (Ch9) and **Support Burden** (KPI Glossary) | Fully answered and unnecessary handoffs are leading indicators of support burden |
| **The Playbook Router** (Ch28) | A handoff is a routing decision; one allowed route per category |
| **Governance and Continuous Improvement** (Ch29) | "The goal is calibration." Auditing our own test, then having it audited from outside |
| **AI Augmentation Guardrails** (AI-Augmented CSM) | "AI drafts, humans decide" is the reviewer design; the automation spec becomes the v5 spec card |

New framework ideas go on `01_canon/canon-backlog.md`.

**Content bank** (candidate posts, not a schedule; JC picks which, if any):
1. My AI support bot tied a bot that does nothing. Here's why that's the real finding.
2. The reviewer that caught 17 of 18 bluffs and blocked 9 of 13 right answers.
3. The bug in my own test: when the judge ran out of room, it counted as "unsafe." (And the check that showed it didn't touch v4.)
4. Why my grader no longer sees the answer key.
5. An empathy score that gave everyone a 1, and how to measure empathy you can see.
6. A handoff with three routes is a router with no owner.
7. Bad news fast, for bots: why "don't suggest anything" broke the handoff.
8. Smarter judge or more knowledge? What actually moved the bot.
9. Set your trust budget before you measure deflection.
10. The cheapest knowledge base you already own: solved community threads.
11. Why every judge in my test came from a different company.
12. Writing down predictions before running an AI test, and which ones I got wrong.
13. **New:** I asked a model from another company to tear apart my test plan. It found 30 problems. Here's what I fixed, what I cut, and the one place I pushed back.
14. **New:** A hedged wrong answer is still wrong: closing the loophole in my own scoring.

---

## 18. Limitations we accept

- One product (n8n), in English only. Spanish stays v1.1.
- Forum questions overstate the docs gap compared with all support tickets, because people usually post after the docs failed them.
- Accepted answers are the reference, even though some are workarounds. The reference-doubt flag counts them.
- The docs are pinned to one commit, while questions span January to September 2026.
- The graders are models. We measure their agreement with each other and with JC's 20 grades, but they aren't people, and 20 grades is a calibration check, not a validation.
- 100 questions can separate large differences, not small ones. We report the difference and its range, and call it inconclusive when the range includes zero.
- Meeting the trust gate on 100 questions doesn't prove the true rate is below 2%.
- The harvest uses answers that were eventually accepted. We can't recover when each one was marked accepted.
- Model runs can't be made exactly repeatable. There is no repeat run in this plan (section 20).

---

## 19. Assumptions register

This register goes on the results page and feeds the case study.

| # | Assumption | Whose | Evidence so far | How the test checks it |
|---|---|---|---|---|
| 1 | A bigger or more expensive model makes a better reviewer | Claude (round-one framing) | **Not supported by public data:** price and rank don't track how often a model guesses | Reviewer trial and arm B |
| 2 | A grader must come from a different company than the text it grades | Claude | Kept as insurance; blind grading removes most self-preference on its own | Company rules, checked before every call |
| 3 | More thinking makes a better judge and a more faithful bot | Common belief | **Mixed in public data** | Not tested; thinking level pinned and recorded |
| 4 | General "intelligence" leaderboards predict grounding and judging | Common belief | **Weak:** round one's low-cost drafter ranks low on the main index but high on document faithfulness | Practice trials pick every judge and reviewer |
| 5 | Forum questions stand in for support tickets | Round-one design | **Known bias** | Stated as a limitation |
| 6 | The accepted forum answer is the right fix | Round-one design | Mostly true, not always | Reference-doubt policy (§5, §7) |
| 7 | Knowing when to say "not supported" matters more than raw capability for reviewers | Model landscape research | **Consistent with round one:** 15 of v3's 18 bluffs were on questions the docs didn't cover | Arm B's prediction counts both bluffs caught and correct answers let through |
| 8 | Model graders can stand in for an expert's judgment | Round-one design | **Unmeasured until now** | Calibration on JC's 20; agreement between graders |
| 9 | The question text is what the customer first wrote | Round-one design | **Not always:** 34 of 140 first posts were edited later | Build 1 compares them with the originals; the holdout uses originals only |

The rows about open-weight models and self-hosting move to part 2 with those arms.

---

## 20. Deferred to part 2 (a follow-up piece, after v5 ships)

| Deferred | Why | What it would need |
|---|---|---|
| E-CN and E-US (all open-weight pipelines, Chinese and Western) | A procurement question, not the core lever; it carried the lineage branches (M14) and claims about model origin (S05) and self-hosting (S08) | The branch table from the review; the claim phrased as "these two pipelines under these settings"; a dependency inventory before any self-hosting claim; the Mistral license described accurately (a separate commercial license is available) |
| B+ (Opus as reviewer) and both ceiling checks | Needed a different grading panel, so their scores weren't comparable (M09) | One common non-Anthropic panel for every arm it's compared with, budgeted |
| Label-sway check | Finding 5 already tells the story; the check couldn't isolate its cause (S07) | Paired calls, the same model and rubric, only label visibility changed |
| Re-grading v2 and v3 | History, not a decision input; their round-one grades stay, clearly labeled | About $3–10 |
| Grader-1 trial (Opus vs Sonnet) | 20 human grades can't separate two strong graders | A larger human sample |
| Repeat run of v5 on the holdout | Nice to have for run-to-run variation; not needed for the decision | About $5 |

The model landscape research stays in `research/` as background for part 2.

---

## 21. Decisions

| # | Date | Decision | Answer |
|---|---|---|---|
| 1 | 2026-09-30 (evening) | Scope | Cut to the core: baseline, v1, A, B, D, F0, F, v5 and the holdout. Everything in section 20 is deferred. (Replaces v2 decision 1, "full plan.") |
| 2 | 2026-09-30 (evening) | Trust gate | At most 1 of 43 on practice (a looser screen, stated as such); at most 2 of exactly 100 on the holdout; locked now |
| 3 | 2026-09-30 (evening) | Budget | Spend as little as possible without gutting the project: an $80 key limit, about $35 before Build 1, re-priced before each batch. (Replaces v2 decision 2, $110.) |
| 4 | 2026-09-30 | JC's Build 1 time | Grade 20 replies blind; read label disagreements |
| 5 | 2026-09-30 | Claude plan | Labeler 1 runs on JC's plan; grader 1 moves to the plan only if the check passes |
| 6 | 2026-09-30 | Arm B+ | Deferred to part 2 (was: yes) |
| 7 | 2026-09-30 | Lineage rule | Moves to part 2 with the open-weight arms |
| 8 | 2026-09-30 | Model lineup | Section 12 (reduced from v2 section 8) |
| 9 | 2026-10-01 | Holdout reference check (gap found while sealing; section 4 lists round one's collection filters but not its reference check) | In Build 3, right after v5 is frozen, run round one's reference check on the holdout. Replace each thread whose accepted answer has no usable fix with the next reserve thread, in order, so the holdout stays exactly 100 gradable questions and no model reads it before the freeze. 20 reserve threads were sealed with the holdout. (JC) |
| 10 | 2026-10-01 | Holdout threads whose edit history is hidden (section 4 covers only titles) | Forum moderators hid the edit history of 11 of the 100. Use their current text, flag them, and report holdout results with and without them. Replace only the 1 whose current text carries an "update" or "solved" marker (found by an automated scan; nobody read it) with the next reserve thread. (JC) |
| 11 | 2026-10-01 | Muse Spark access | OpenRouter requires an 18+ confirmation before serving Meta's model. JC confirmed it; the grader-2 candidates are unchanged. |
| 12 | 2026-10-01 | Calibration screen (section 7) | Every model failed the 70% screen against JC's 20 blind grades (Sonnet 8 of 19, Opus 10, Muse Spark 10, Gemini 11, Qwen 11). The main cause was JC's grading form, which left "correct" and "partial" undefined while the graders had exact definitions (Claude's error). JC's 20 grades become a published finding (a support lead's view versus strict correctness), not a gate. Grader 2 and the tie-breaker are chosen by cross-company agreement on the same 20 replies: **Gemini 3.8 Flash** is grader 2 and labeler 2 (agrees with the other four models' majority on 16 of 20; the cheapest) and **Muse Spark 1.3** is the tie-breaker (16 of 20). **Sonnet 5.5 stays grader 1.** (JC) |
| 13 | 2026-10-01 | Route (replaces decision 5) | No Claude-plan check and no terminal work for JC. Every call runs over OpenRouter; large batches use OpenRouter's batch mode (half price, results within 24 hours) where the model has a batch endpoint. Labeler 1 becomes Sonnet 5.5 over the API (section 12's named alternate). Projected total about $51 including spend so far, under the $80 limit. (JC) |
| 14 | 2026-10-01 | JC's reading (section 5) | JC reads the label disagreements that cross the answerable/needs-a-human line on a fast sheet (one item per screen, one-tap answers); his answers decide as written in section 5. (JC) |
| 15 | 2026-10-05 | Labeler 2's route, and the labels phase over its estimate (section 13's 30% stop) | Google's Vertex batch host for Gemini stalled twice: the first turn-A batch never ran, and the resubmitted one finished after its 24-hour window (140 of 140, $0.16). Both batch pre-charges were released. Gemini's turn B (category and evidence) runs over the **regular API on Google AI Studio**: same model, prompts, settings and caps, with turn A's outputs taken from the Vertex batch. The labels phase was estimated at $5.10 (stop line $6.63); turn B's prompts carry all the search results and were underpriced, and the projection with the Muse tie-breaks is $7.10–$7.80. JC raised the labels-phase ceiling to **$8.00**. (JC) |
| 16 | 2026-10-12 | Re-grade routes (step 10), and the Claude Max plan question | Labels v2 are final (140 of 140). The phase-1 prediction missed: 30.9% of the 97 test questions need a human, against a predicted 50-65%. **Grader 2 (Gemini 3.8 Flash) goes back to OpenRouter batch mode on Google's host**, checked once every 6 hours; if it hasn't finished within 24 hours, the unfinished items run over the regular API (about +$2, pre-approved). JC asked whether Claude roles should run on his Max plan. The Consumer Terms bar scripted access except by API key or explicit permission, and Max limits assume "ordinary, individual usage" of Claude Code, so a scripted 400-call grading run is a gray area. The saving is about $5 here and about $20 across the project. **Grader 1 (Sonnet 5.5) stays on the API in batch mode**; decision 13 stands. (JC) |
| 17 | 2026-10-13 | Build 2 route and the phase-2 ceiling | **Batch mode wherever the pinned host accepts it**: saving money matters more than turnaround. Smoke calls showed real review prompts at about 7,300 tokens (4,400 assumed), so phase 2 re-prices to $1.90–$3.20 on batch. The ceiling rises from $1.72 to **$4.00**. Reviewer hosts are pinned: GLM-5.3 on Parasail fp8, MiMo on Xiaomi fp8, Kimi K3 on Moonshot mxfp4. A host that refuses batch runs over the API at 150 s per attempt. (JC) |
| 18 | 2026-10-13 | No reviewer passed the practice screen (section 9.5) | **Measure the levers on drafts.** (1) Arm B on test runs once with MiMo-V2.6-Pro, labeled "failed the practice screen". MiMo is chosen because it came closest to the trust gate (fewest confidently wrong, 4 of 43); this rule is written down before the test run. It is a data point for the decision chart, not a v5 candidate. (2) Arms D, F0 and F run drafts only, graded before review; no reviewer pass, so 'B's reviewer' drops out of D, F0 and F. (3) v5 (G) is chosen by section 9 from complete configurations that pass the practice screen: A (v4), and any drafts-only arm that passes on its own. Saves ~$7 against the original plan; remaining ~$17. Predictions D1 and D2 stand; D3 (D finals vs B finals) is withdrawn because D has no reviewer. (JC) |
| 19 | 2026-10-15 | Build 3 scope, after arm D | (1) **Arm DF added**: GPT-6.1 Sol drafts with F's frozen prompt (prompts/F0F_*) and F's community section, drafts only, no reviewer. Added after seeing arm D's results, and labeled that way. It runs on practice; it runs on test only if it passes the practice screen (<= 1 confidently wrong of 43). If it passes, it is an eligible v5 configuration under section 9. (2) **Community-availability labels only for the 37 questions on the human side** (bug_or_release and undocumented_n8n; practice 9, test 28), the only ones where the label can change F's or DF's answerable denominator. The other 103 are not labeled; the 'did F's search find it' diagnostic is reported for the 37 only. (3) Re-priced remaining spend about $25.70 (about $29 if DF runs on test) against a $33.29 balance; **JC adds $10 of credit before the holdout** to keep the 30% headroom on the holdout batches. The handoff's earlier 'G + holdout about $4' was an underestimate (measured rates give about $13.30). (JC) |
