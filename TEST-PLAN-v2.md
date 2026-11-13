---
title: Support Agent Audit — Test Plan v2
status: FINAL DRAFT (2026-09-30). All decisions recorded in section 17. Next: outside review, then Build 1. No model spend before Build 1.
replaces: the "Grading" and "Models" parts of PLAN.md for everything run from here on. PLAN.md stays as the record of v1–v4.
review: checked by an independent reviewer agent on 2026-09-30. Its number check confirmed every finding in section 1 except one (finding 3 couldn't be checked without the docs index; the author's own check gave 27 of 30). Its design critique changed sections 1, 3, 4, 5, 6, 7, 9, 10 and 11.
models: lineup updated 2026-09-30 from research/MODEL-LANDSCAPE-2026-09.md (current-state model research); assumptions register added as section 16.
---

# Support Agent Audit — Test Plan v2

## The plan in one paragraph

The first round of the audit (v1–v4) produced a bot that almost never bluffs, but its headline score tied a bot that hands every question to a human. Before spending more money, we checked the test itself. Several parts of the measuring stick turned out to be weak: the answer key, the empathy score, the headline metric, and the reviewer's own code. Test Plan v2 fixes the measuring stick first. Then it runs one clean experiment on a question support leaders face when they buy or build an AI agent: **is the bot held back by judgment (a smarter model) or by knowledge (what it's allowed to read)?** It tests both levers, adds two versions a company could run on its own servers (one Chinese and one Western open-weight), and confirms the final result on fresh questions nobody has looked at. Every step, including the flaws we found in our own test, becomes part of the case study.

---

## 1. What round one taught us (evidence, 97 test questions)

All numbers come from the stored run files. The ones marked "new" were computed on 2026-09-30 at no model cost, and an independent reviewer recomputed all of them except finding 3, which needs the docs index.

| # | Finding | Number |
|---|---|---|
| 1 | v4's "handled well" score equals the hand-off-everything baseline. | Both 69% (67 of 97) |
| 2 | v4's reviewer blocked almost everything. It stopped 17 of 18 bluffs, but also 9 of 13 correct answers, 22 of 24 partial answers and 5 of 5 good clarifying questions. It even blocked 34 of the 37 drafts that were already handoffs, and rewrote them. | 87 of 97 drafts blocked |
| 3 | Search is not the main bottleneck. (New.) For 27 of the 30 docs-answerable questions, the bot's search found the same doc page the labeler used as evidence. | 27 of 30 |
| 4 | The "needs a human" group is mixed. (New.) Of the 56 questions labeled "fix not in the docs", the v3 drafts fully solved 6 and partly solved 11, often with general technical knowledge the bot is allowed to use. But the same group also holds 15 of v3's 18 bluffs. Leaving out v2 (the version that bluffed 43% of the time), 17 of the 67 "needs a human" questions got at least a partial fix from some version. | 17 of 67 |
| 5 | The grader's reasoning names the label in 86 of v4's 97 grades. (New.) That is mostly by design: in 85 of those 86 the reply was a handoff, and the round-one rubric uses the label to decide whether a handoff was correct or unnecessary. So this shows how tightly grades are tied to the answer key, not proven bias. | 86 of 97 |
| 6 | The empathy score doesn't tell replies apart. Every version scored 1 on almost every reply. | v1: 96 of 97 scored 1 |
| 7 | Handoffs don't pick a route. (New.) 75 of v4's 90 handoffs point the customer to GitHub, n8n support and the forum at once. All 75 were written by v4's rewrite step, whose template lists the three routes. | 75 of 90 |
| 8 | v4's handoff writer is told "do not give ... steps to try." That contradicts *bad news fast* (The Modern CSM, Ch4), which ends with mitigation: what the customer can do now. | Design flaw |
| 9 | **The reviewer's code can fail silently.** (New.) It caps the reviewer's reply at 400 tokens, and when it can't read the reply three times it counts the draft as unsafe. In the round-one trial of a looser reviewer, 24 of the 55 calls to Google's model hit that ceiling. So the "looser reviewer let bluffing back in (14–16%)" result isn't clean either. | Harness flaw |
| 10 | One model (Claude Sonnet 5.5) wrote all labels and all 388 test grades. No second opinion and no human comparison was ever measured. JC's spot-checks were cut on 2026-09-29. | No agreement data |

**What this means:** the round-one headline ("69% of real questions need a human") may move once the answer key separates general technical fixes from truly undocumented ones. Some of those questions are answerable, and others are bluff traps. That's the reason we fix the measuring stick before we spend on new bot versions.

---

## 2. Weaknesses in the test, and the fix for each

| Weakness | Why it distorts results | Fix in v2 | Cost |
|---|---|---|---|
| **The reviewer harness fails silently** | Finding 9: a model that "thinks" before answering can run out of room, and every failure counts as a block. A premium or open-weight reviewer could look strict only because it was cut off. | Raise the reply cap to at least 4,000 tokens, then size it per model from practice use. Record "reviewer error" as its own result, retry it, and report the error rate for every arm. | $0 |
| **One label per question, from one model** | Finding 4: "not in the docs" lumps fixes a bot may answer (general tech) together with fixes that truly need a person. | New answer key with five categories and a precedence order (section 4), written by two labelers from different companies. A third model weighs in on disagreements, and JC reads the rest. | Money + JC time |
| **"Not in the docs" was decided from 10 search results** | The fix might sit on a doc page the labeler's search didn't surface. | Labelers get three searches: the original, one on the key fix alone, and an exact-term search for setting names and environment variables. | Pennies |
| **Grades are tied to the answer key** | Finding 5: if the key changes, every grade has to be redone, and a wrong label becomes a wrong grade. | **Blind grading.** Graders judge only what the reply did and whether its fix was right. The scoreboard applies the answer key afterward with a fixed table (section 5). A small check (20 grades with the label shown vs hidden) measures how much the label swayed round-one grades. | Money |
| **One grader, never compared with a person** | Nobody can say how often the grade is right. Two model graders can share the same blind spots. | Two graders from different companies grade every reply, and we publish their agreement. **JC grades 20 random replies blind, once**, as the human anchor. He's grading support replies, which is his expertise, not n8n trivia. | Money + JC time |
| **Empathy score collapsed to 1** | Finding 6. | Replace the 0–2 scale with yes/no checks a reader can verify (section 5). | $0 |
| **Handoff quality not scored** | Finding 7: a handoff naming three routes looks fine to the current rubric. | Handoff checklist built from *bad news fast* and the Playbook Router: one route, the right route, a summary, and a safe next step. | $0 |
| **"Handled well" counts a handoff as a win** | Finding 1: that's why doing nothing ties v4. | Retire it as the headline. New scoreboard (section 6), always plotted against the hand-off-everything baseline. | $0 |
| **The test set has been seen** | We designed v2 after studying test results, so new test scores aren't fully independent. | A **fresh holdout**: about 100 new solved threads from the same months, drawn and sealed before any other new work, used once to confirm the final version. Test-set results for new arms count as exploratory. | Money |
| **Choices made from test results** | Picking the "best reviewer" by its test score is tuning on the test. | Every choice (reviewer, drafter, prompts) is made on the 43 practice questions, by a rule written down in advance. | $0 |
| **Small numbers, one run each** | 30 docs-answerable questions is a small sample. At about 100 questions, the test can tell 1 bluff from 9, but not 1 from 3. | Report every rate with a range (resampling the questions; free). Treat arms whose ranges overlap as tied. Re-run the final version once as a sanity check on run-to-run variation. | Mostly $0 |
| **Loose predictions** | Predictions like "within a few points" can't fail. | **Pre-registration with numbers** (section 7), saved before each paid run. | $0 |
| **Forum questions are a biased sample** | People usually post after the docs failed them, so the forum overstates the docs gap compared with all support tickets. | Can't be fixed with public data. We state it on the page and in the case study. | $0 |
| **The accepted answer is treated as the truth** | Some accepted answers are workarounds or outdated. | Keep the "reference doubt" flag and count it. Graders may accept a different fix that clearly works. | $0 |

---

## 3. The experiment: two levers

A support leader who wants a better AI agent has two places to spend: a **smarter model** (judgment) or **better knowledge** (what the bot can read). Round one changed only prompts. Round two tests the levers directly.

| Arm | Drafts written by | Reviewer | Knowledge | Answers the question |
|---|---|---|---|---|
| A. Current (v4) | Low-cost model | Same low-cost model | Docs | Where we are (re-graded with the new stick) |
| B. Smarter reviewer | Low-cost model | **Strongest reviewer the independence rules allow** | Docs | Was v4's problem judgment? |
| D. Smarter drafter | **Premium closed model** | Best reviewer (picked on practice) | Docs | JC's question: would a better model have done a better job? |
| E-CN. All open-weight, Chinese | **Chinese open-weight model** | **Chinese open-weight model, different company** | Docs | Could a company run the whole thing on its own servers, using the models closest to the frontier? |
| E-US. All open-weight, Western | **Western open-weight model** | **Western open-weight model, different company** | Docs | What does a company give up if its security policy rules out Chinese-origin models? |
| F0. Knowledge control | Low-cost model | Best reviewer | Docs + an **empty** community section | Isolates the prompt change that F needs |
| F. Knowledge harvest | Low-cost model | Best reviewer | **Docs + solved community threads** | Was the problem knowledge? |
| B+. Frontier reviewer | Low-cost model | **Claude Opus 5.5** | Docs | Would the most capable (and pricier) reviewer do better? Scored only by grader 2 and the tie-breaker |
| G. Final (v5) | Chosen on practice | Chosen on practice | Chosen on practice | Best combination, with a *bad news fast* handoff writer |

"Open-weight" means the model's weights are published, so a company can run it on its own hardware and keep customer tickets in-house. That matters to companies with strict data rules, including in the EU. In this test, the open-weight models still run through OpenRouter, pinned to a single hosting provider so results stay consistent. The test shows what the model can do. It doesn't test a real server.

**Why the arms are clean:**
- B reuses v4's stored drafts, so only the reviewer changes. The independence rules keep the two top labs (Anthropic and OpenAI) out of the reviewer seat, so B tests a stronger independent reviewer, about 10 points below the top of the main index, not a frontier one. Arm B+ (approved by JC) adds Claude Opus 5.5 as a frontier reviewer, scored only by grader 2 and the tie-breaker so no Anthropic model scores it. B+ is reported next to B; it is not eligible to become the "best reviewer" used downstream, because its results can't be scored by both graders.
- E-CN and E-US use the same prompts and host rules; only the models' origin differs. A model fine-tuned from a Chinese base model counts as Chinese, because procurement policies look at lineage.
- **Who writes the handoff when a reviewer blocks a draft:** in every arm, the drafter model rewrites it with v4's template, exactly as round one did, so a reviewer arm differs from v4 only in the reviewer's decision. In G, the drafter writes the handoff with the new *bad news fast* template. No drafter comes from a grader's company, so graders never score their own company's writing.
- Why two open-weight arms and no "open-weight reviewer only" arm: a company that self-hosts runs the whole pipeline, not just the reviewer, and model origin is a real procurement filter. In 2026, US lawmakers have been probing the use of Chinese AI models in US companies, and there are reports of a renewed push to restrict them.
- F0 and F use the same new prompt, which tells the bot and reviewer that community answers exist. The only difference between them is whether the community section has content. So F minus F0 is the knowledge effect alone.
- The pre-review drafts from F and F0 get graded too, which shows the knowledge effect with and without a reviewer.
- "Best reviewer" and every G choice come from the practice trial, never from test results.

---

## 4. The new answer key (labels v2)

Every question gets one category, based on the **key step** of the accepted fix (the step without which the fix fails). Labelers never see any bot reply. When more than one category fits, the first one in this order wins:

| Order | Category | Meaning | Right move for a docs bot | Goes in the docs-gap report as |
|---|---|---|---|---|
| 1 | `account_access` | The fix needs the customer's account, billing or instance, or n8n staff. | Hand off to n8n support | **Always needs a person** |
| 2 | `n8n_docs` | The pinned n8n docs contain the key step, including release notes (for example "fixed in version X, upgrade"). | Answer | — |
| 3 | `general_tech` | The key step is standard technical knowledge outside n8n (SQL, HTTP, OAuth, Docker, JavaScript). | Answer (the bot's rules allow it) | Not a docs gap |
| 4 | `bug_or_release` | A bug or regression with no documented fix yet. | Hand off to GitHub | **Known issues the bot should be told about** |
| 5 | `undocumented_n8n` | The key step depends on n8n behavior the docs don't describe. | Hand off to the forum | **Articles n8n could write** |

For the knowledge-harvest arms, labelers also answer: *was the key step available in a community thread whose accepted answer was posted before this question?*

**How disagreements are settled:** two labelers from different companies label all 140 questions. Where they disagree, a third model gives its view. JC then reads each remaining disagreement in a side-by-side sheet, with the accepted fix on one side and the closest doc passages on the other. He answers two plain questions:
1. Is the key step of this fix on this page?
2. If not, is it something anyone in IT would know, or something specific to how n8n works?

These are reading and judgment checks, not n8n-expertise checks. We have no data yet on how many disagreements there will be. Plan for 20–40 items.

---

## 5. The new grading rubric (blind)

Graders see the customer's question, the accepted answer, every passage the bot had (doc passages and, in F arms, community passages), and the reply. They do **not** see the label. They record:

- **Action:** answered, asked a question, handed off, or mixed (a fix plus a handoff).
- **Fix verdict:** correct, partial, wrong, or no fix given.
- **Framing of any fix inside a handoff or question:** presented as *the* answer, or clearly marked as unverified or conditional.
- **Safe mitigation (handoffs):** a step that can't make things worse and doesn't claim to be the fix (for example "check your version", "share the execution log").
- **Right missing fact (questions):** did it ask for the fact the accepted fix depended on?
- **Route named:** GitHub, n8n support, forum, several, or none.
- **Invented claims:** any n8n node, setting or behavior that isn't real or isn't supported by the passages (the Reliability check).
- **Answer checklist (yes/no):** answers what the customer meant; gives a concrete next step; no filler.
- Replies are converted to plain text before grading, because a 2026 study found model judges prefer markdown formatting 73–97% of the time, against 57% for people.
- **Handoff checklist (yes/no), from *bad news fast* and the Playbook Router:** says plainly it needs a human; says why; states what's known and unknown; names **one** route; gives a safe thing to do meanwhile; ends with a summary a human can pick up.

**The outcome table** (frozen before the phase-1 re-grade). "Bot-answerable" means `n8n_docs` or `general_tech`. The other three categories need a human.

| What the reply did | → Outcome |
|---|---|
| Answered (or mixed with the fix presented as *the* answer), fix correct, no invented core claim | `resolved` |
| Same, fix partial, or correct but with a harmless invented detail | `partial` |
| Same, fix wrong, or the fix depends on an invented claim | `confidently_wrong` |
| Asked the right missing fact, and any fix it offered is correct or clearly conditional | `right_question` |
| Asked a question, but offered a wrong fix presented as the answer | `confidently_wrong` |
| Asked a generic question ("share more details") with no fix | Counted as a handoff (below) |
| Handed off, with no fix, or only safe mitigation / clearly-unverified suggestions, on a question that needs a human | `correct_handoff` |
| Same, on a bot-answerable question | `unnecessary_handoff` |
| Handed off, but a suggestion inside it is wrong and presented as the fix, or is unsafe | `confidently_wrong` |

Route correctness is computed by rule from the category: `bug_or_release` → GitHub, `account_access` → n8n support, `undocumented_n8n` → forum.

All four round-one versions get re-graded this way, on both the practice and test sets, so every version in the final chart is measured with the same stick. The old grades stay in the repo as history.

---

## 6. The scoreboard

**Trust budget first.** A support leader should decide how many confident wrong answers per 100 they'll accept before measuring anything else. JC set it at **2 per 100** on 2026-09-30 (v4 managed 1; the default bot, v1, had 9). It is confirmed at the checkpoint before phase 2.

| Metric | What it tells a support leader |
|---|---|
| **Resolved without a human** per 100 | Tickets the bot actually takes off the team (the headline) |
| **Right question** per 100 | Moved the ticket forward; the customer's reply may still need someone |
| **Partial** per 100 | Helpful, but the customer may come back |
| **Confidently wrong** per 100 | Trust incidents (checked against the trust budget) |
| **Unnecessary handoffs** per 100 bot-answerable questions | Work the bot pushed onto humans for no reason |
| **Handoff quality** (checklist score; share with one correct route) | Whether the human who picks it up starts ahead |
| **Reviewer error rate** | Whether the harness itself worked |
| **Grader agreement**, model vs model and model vs JC, reported as Cohen's κ (an agreement score that removes the matches two graders would get by luck), not raw percent | How much to trust all of the above |

**How the winner is chosen (written down before phase 2):** an arm passes the trust test if it has at most 1 confidently wrong answer on the 43 practice questions (the 2-per-100 budget, rounded up to a whole question). Among arms that pass, not counting B+ or the ceiling checks, the one with the most resolved without a human on practice becomes v5. If the ranges overlap, the arms are tied, and the tie goes to the cheaper or self-hostable option, because that's what a support leader would pick. On the holdout, v5 must stay within 2 confidently wrong answers per ~100 questions. If it doesn't, that is the reported result, and nothing is re-tuned.

**The decision chart:** one dot per arm, with its range. Across: share resolved without a human. Up: confidently wrong. The hand-off-everything bot sits at zero on both. A good bot moves right without moving up past the trust-budget line. This one picture replaces "9 → 42 → 1".

---

## 7. Rules that keep it honest

1. **Tune on practice questions only.** Every prompt, reviewer or model choice is made on the 43 practice questions.
2. **Write predictions down first, with numbers.** Before each paid run, the predictions and the winner rule are saved to `runs/PREREGISTRATION.md` with a timestamp (committed to git once the repo exists). Starting predictions:
   - Phase 1: after re-labeling, the share of questions that need a human falls from 69% to between 50% and 65%.
   - Arm B: the stronger independent reviewer lets through at least 7 of the 13 correct test drafts (v4 let through 4), while letting through at most 2 of the 18 bluffs. (These counts come from round one's grades; they are re-taken from the phase-1 re-grade and saved before Build 2.)
   - Arm F vs F0: the harvest adds at least 5 resolved questions out of 97.
   - Arm E-CN: the Chinese open-weight pipeline resolves no more than 3 fewer questions than arm D (same reviewer, premium closed drafter), within the trust budget.
   - Arm E-US: the Western open-weight pipeline resolves at least 3 fewer questions than E-CN, but stays within the same trust budget.
   - Grader trials: with only 20 human grades, graders must differ by about 20 points to be told apart. If their ranges overlap, the better-calibrated candidate wins (lower guessing rate on Artificial Analysis's closed-book test), then the cheaper one. If Qwen wins grader 2, every phase is re-estimated before the re-grade.
   - Numeric predictions for arm D, arm B+ and the two ceiling checks are saved before Build 2; the v5 holdout prediction is saved before Build 3.
3. **Confirm once on fresh questions.** The final version, v4 and the baseline run once on the sealed holdout. Those are the numbers the case study leads with.
4. **Publish nulls.** If a lever doesn't help, that's the finding, and it goes on the page.
5. **Company independence.** No model grades text written by its own company. No reviewer reviews drafts written by its own company. **No reviewer comes from a grader's company**, because a reviewer that shares the grader's taste would pre-apply the grader's standard and inflate the score. The tie-breaker comes from a company used nowhere else (section 8). **Two exceptions, stated openly:** arm A (v4) is re-graded as it was built, with the low-cost model reviewing its own drafts; and B+ and the Opus ceiling check involve an Anthropic model, so grader 1 doesn't score them. For those two, the tie-breaker grades every reply in grader 1's place, and disagreements between the two graders are reported as unresolved.

---

## 8. Model lineup

Chosen from the model landscape report (`research/MODEL-LANDSCAPE-2026-09.md`, 2026-09-30) and approved by JC the same day. Public leaderboards make the shortlist; the practice trials make the pick. Prices are OpenRouter list prices per million tokens (input / output).

| Role | Candidates (front-runner first) | Company | Why |
|---|---|---|---|
| Low-cost drafter (A, B, F0, F) | `openai/gpt-5.4-mini`, thinking pinned to round one's setting | OpenAI | Keeps round one comparable. Its public profile predicted round one: faithful when the docs cover a question (5.5% on Vectara's document-faithfulness test), a heavy guesser when they don't (90% on Artificial Analysis's closed-book test). |
| Labeler 1 | Claude Opus 5.5 on JC's plan; alternate Sonnet 5.5 | Anthropic | Top of the Artificial Analysis index (57.6) and the best long-document reader in the set. |
| Grader 1 | Trial: Opus 5.5 at medium effort vs Sonnet 5.5 at high effort | Anthropic | Compared at equal cost per task, not equal effort, because Sonnet loses far more quality at lower effort. |
| Grader 2 and labeler 2 | Trial: Meta's Muse Spark 1.3 ($1.25 / $4.25), Google's Gemini 3.8 Flash ($0.75 / $3.75), Alibaba's Qwen3.8 Max 0902 ($2 / $6) | Meta, Google or Alibaba | Muse Spark leads the three on public data. Gemini is cheapest and fastest. Qwen guesses least but costs about 4 times Gemini per task and defaults to its highest thinking level. |
| Tie-breaker | Runner-up of the grader-2 trial | Meta, Google or Alibaba | Already checked against JC's grades, and its company is used nowhere else. |
| Reviewer (arm B, and the "best reviewer" in D, F0, F and G) | Trial: Z.ai's GLM-5.3 ($1.40 / $4.40 on Z.ai's own endpoint; the third-party host's price is checked at build time), Xiaomi's MiMo-V2.6-Pro ($0.435 / $0.87), Moonshot's Kimi K3 ($3 / $15). Budget alternate: GLM-5.3-Flash | Chinese labs other than Alibaba | GLM-5.3 guesses least of the three (30%) and is fastest. MiMo scores highest and is cheapest. Kimi knows the most but guesses the most. **DeepSeek V4 Pro is dropped:** it has slipped to 36 on the index and guesses on about 89% of questions it can't answer. GLM runs on a third-party host, not Z.ai's own endpoint, because Z.ai is on the US Entity List. |
| Premium drafter (arm D) | GPT-6.1 Sol ($2 / $10); alternate GPT-6 Sol | OpenAI | Within about a point of OpenAI's flagship at a fraction of the cost per task. Very new, so no human-preference or faithfulness data yet. |
| Ceiling check (practice questions only) | GPT-6 Astra ($10 / $50) answers "would OpenAI's best do better?" Claude Opus 5.5 answers "would the most capable model do better?", scored only by grader 2 and the tie-breaker | OpenAI (+ Anthropic) | Astra is less than a point above Sol on the index; Opus 5.5 leads both main leaderboards. |
| E-CN pipeline | Drafter trial: MiMo-V2.6-Pro vs Kimi K3, from a different company than the reviewer. Reviewer: the arm-B winner | Chinese labs | Reusing arm B's reviewer means E-CN and B differ only in who drafts. |
| E-US pipeline | Drafter: Thinking Machines' Inkling ($1.00 / $4.05), alternate Inkling Small. Reviewer: NVIDIA's Nemotron 3 Ultra ($0.60 / $2.40) | Thinking Machines + NVIDIA | Western open-weight models trail Chinese ones by about 20 points on the index, but Nemotron 3 Ultra guesses no more often than GLM-5.3. **Dropped:** gpt-oss-120b and Muse Glimmer (weak), Mistral Medium 3.5 (its license bars companies with more than $20 million in monthly revenue), PrismML Bonsai (built on Qwen). |

**The lineage rule** (approved by JC) is "no Chinese-origin weights." Nemotron 3 Ultra's weights are NVIDIA's own, but NVIDIA discloses that some of its training data was generated by DeepSeek and Qwen models. Other Western labs don't disclose this at all, so a stricter rule would penalize the one transparent vendor. The case study states the rule and the caveat.

**Settings that must be pinned and recorded for every role:**
- **Thinking level,** set per model at matched cost from what the practice trials measure. Qwen's is always set explicitly, because its default is the highest level. Reply caps are sized from measured use in the trials.
- **Randomness.** OpenAI's models on OpenRouter don't accept a temperature setting, and Anthropic's don't accept a seed, so round one's "temperature 0.2" for the bot was likely ignored. We can't force identical reruns, which is why the repeat run matters.
- **Host for open-weight models:** the model's native precision (Kimi K3 is built to run at 4-bit; GLM ships at fp8), the full advertised context and output length, a host verified by the lab where a verifier exists, and no automatic fallback to other hosts. The host is recorded. Some hosts quietly cut context from 1 million to 262,000 tokens or cap output at 16,000.

Model names and prices will be rechecked at build time. Each candidate's practice trial records real cost per call, reviewer error rate and quality before anything touches the test set.

---

## 9. The knowledge-harvest design

JC's rule: no new articles; only content real users already wrote. So the harvest uses accepted answers from solved forum threads, as written.

- **Order of work:** the fresh holdout is drawn and sealed first, so the harvest crawl can exclude it.
- **Pool:** solved threads from n8n's Questions category, from mid-2025 through September 2026, excluding every practice, test and holdout thread. Target: 1,000–2,000 threads. Collecting them uses the forum's public data feed, costs nothing in model spend, and runs politely on JC's computer.
- **No looking into the future:** for each question, the bot may only see accepted answers **posted** before the question was posted, compared by full timestamp, not date. Answers edited after that moment are skipped. A real team can only harvest the past.
- **No leaks:** the question's own thread, and earlier threads by the same asker, are excluded.
- **Kept apart from the docs:** the bot, reviewer and graders see harvested answers in a separate "community answers" section, so everyone knows they're peer answers, not official documentation.
- **A stated asymmetry:** the docs are pinned to one recent commit, so they contain some "future" knowledge for early-2026 questions, while the harvest does not. That favors the docs-only arms, so the harvest result is, if anything, an underestimate.
- **Privacy and credit:** thread text stays in the git-ignored cache and is never published. The repo lists thread IDs. The page credits the community members whose solved threads make up the harvest.

This mirrors a real support practice called knowledge-centered service: turning solved cases into reusable knowledge. The result reads as "harvesting N solved threads moved the bot from X to Y resolved per 100."

---

## 10. Budget

Estimates use round-one costs (grading about 2¢ per reply with Claude Sonnet 5.5 and under 1¢ with Google's model; labeling about 2.4¢; the full v4 pipeline of draft, review and rewrite about 1.1¢ per question) and today's OpenRouter prices. Premium models that "think" before answering can use more tokens than estimated, so each practice trial measures real cost first.

| Phase | What | Estimate |
|---|---|---|
| 1. Measuring stick | Seal the holdout; grader-1 and grader-2 trials on JC's 20 grades; labels v2 by two labelers (140 questions); blind re-grade of v1–v4 on practice and test by two graders; the label-sway check; tie-breaks; reviewer harness fix | ~$28 |
| 2. Judgment | Reviewer practice trial, arm B, arm B+ (Opus reviewer), grading | ~$12 |
| 3. Model tier | Arm D (premium drafter), arms E-CN and E-US (all open-weight), practice and test; ceiling checks on the practice questions (GPT-6 Astra, Claude Opus 5.5); grading | ~$30 |
| 4. Knowledge | Harvest collection ($0), harvest labels, arms F0 and F on practice and test, grading | ~$22 |
| 5. Confirmation | Holdout (~100 questions): labels, v4 and v5 runs, grading; one repeat run of v5 on the holdout, reported only as run-to-run variation | ~$20 |
| **Total** | | **~$112** |

**Using JC's Claude plan for the Claude roles (approved by JC, 2026-09-30).** About two-fifths of the total (roughly $46) pays for Claude as labeler 1 and grader 1. Anthropic's help center says a Pro or Max plan may be used for personal scripts and automation through Claude Code, and that this draws from the plan's normal usage limits. So the Claude roles could run as Claude sessions on JC's plan instead of through OpenRouter:
- **Labeler 1 on the plan:** low risk. Labels are a one-time annotation published as a file. Saves about $8, and allows the stronger model (Opus 5.5) at no extra cost.
- **Grader 1 on the plan, only if a check passes:** in Build 1, 50 replies are graded both ways (through the API and on the plan), and the plan route is run twice to check its own consistency. If the plan route agrees closely with the API route, grader 1 moves to the plan for everything, saving about $38. If not, it stays on the API. The same check shows how much of JC's usage allowance 50 grades consume, so we can tell whether about 1,500 grades would crowd out his other Claude work.
- **Stays on OpenRouter no matter what:** every non-Anthropic role (drafters, reviewers, grader 2, open-weight models, the tie-breaker). Only labeler 1 and grader 1 can move to the plan. The B+ reviewer and the Opus ceiling check stay on OpenRouter, so they run with the same pinned settings as every other arm. The public repo documents the API route, so anyone can reproduce the results with their own key.
- Grader sessions get only the rubric and the items, never this plan or the predictions.

| Scenario | Estimated OpenRouter spend |
|---|---|
| If nothing ran on the plan | ~$112 |
| Labeler 1 on the Claude plan (decided) | ~$104 |
| Labeler 1 and grader 1 on the Claude plan (if the check passes) — the expected case | ~$66 |

**Grader 2's cost depends on the trial:** Gemini is the cheapest, Muse Spark costs somewhat more, and a Qwen win would raise grading costs noticeably (about 4 times Gemini per task).

**Where it can be cut:** phases 1, 2 and 4 are the core (about $62 on OpenRouter). Dropping phase 3 loses the open-weight (Chinese vs Western) and "better drafter" questions. Dropping phase 5 loses the fresh confirmation. The largest single saving is to have the second grader grade a random third of replies instead of all of them (this saves two-thirds of grader 2's cost; the dollar amount depends on which model wins the grader-2 trial), at the cost of a weaker agreement number.

**Stop rules:** a checkpoint with JC after phase 1, because the corrected answer key may change the story. Any phase that runs more than 30% over its estimate stops, and we decide together.

**Key (approved by JC):** a new key for round two with a **$110 limit**, saved in the same key file the code already reads; the old key (about $10.62 left of $30) is deleted. Credit is added in stages: about $30 before Build 1, topped up at the checkpoint. The limit is the hard stop: nothing can spend past it. The expected spend is about $66 with both Claude roles on the plan. If grader 1 has to stay on the API, the estimate is about $104, $6 under the cap, and at the checkpoint JC decides whether to keep the phase-3 ceiling checks or raise the cap for headroom.

---

## 11. Session arc (four build sessions, then publish)

| Session | Work | JC's part |
|---|---|---|
| Build 1: fix the measuring stick | Save phase-1 predictions → seal the holdout → fix the reviewer harness and dry-run the pipeline → JC's 20 blind grades (random practice-set replies from v1–v4) → grader-1 and grader-2 trials on those 20 → the 50-reply Claude-plan check → labels v2 (the third model in section 4 is the tie-breaker) → blind re-grade of v1–v4 → label-sway check → start the harvest crawl | Grade 20 random replies blind (the human anchor). Read the label disagreements (20–40 items). |
| Checkpoint | Corrected baseline, grader agreement, the Claude-plan grader check, spend so far | Confirm the trust budget (2 per 100). Go or no-go on phases 2–5. Top up credit. |
| Build 2: the levers | Save predictions → reviewer practice trial → arms B and B+; E-CN drafter trial; arms D, E-CN and E-US; ceiling checks (practice only) | — |
| Build 3: knowledge and final | Save predictions → arms F0 and F; pick v5 on practice; holdout labels → holdout run; repeat run | Read the holdout label disagreements (about 15–30). Optional: a QA verdict on five v5 handoffs for the video. |
| Build 4: ship prep | Rebuild the results page, docs-gap report, case study, content drafts, video script | Review everything |
| Publish | Repo, Pages, video, posts | Approve and post; all public steps stay his |

---

## 12. What ships (updated)

- **Results page:** the decision chart, the two-levers result, the corrected answer key, a "what we got wrong in round one" timeline, the docs-gap report, and every reply with both graders' verdicts.
- **Docs-gap report**, written constructively: articles n8n could write, known issues a bot should be told about, questions that always need a person, and questions general knowledge covers. It credits n8n's team and forum community.
- **Tool build-out case study:** the problem; what we built (v1–v4); the audit of our own test; Test Plan v2; results; what a support leader should do on Monday (set a trust budget, harvest solved threads, fix routing); what broke and what changed. The one-page case study is the short version.
- **Public repo**, two-minute video, Featured blurb: as before. The round-one drafts in `_internal/` are superseded and get rewritten in Build 4.

---

## 13. Where JC's frameworks show up

| Framework (source) | Where it's used |
|---|---|
| **Confidence Equation** (Modern CSM, Ch1) | The rubric: Competence = correct fix; Reliability = no invented claims; Empathy = the checklists, "hearing what they meant"; Uncertainty = asking or handing off. |
| **Escalation isn't weakness** and **bad news fast** (Ch4) | The handoff standard and checklist; the fix to v4's "no steps to try" rule. |
| **The Handoff** (Ch10) | "A sloppy handoff hits all four variables": the summary requirement. |
| **Leading indicators** (Ch9) and **Support Burden** (KPI Glossary) | Resolved-without-a-human and unnecessary handoffs are leading indicators of support burden. |
| **The Playbook Router** (Ch28) | A handoff is a routing decision. The course's own warning about routing without an owner is finding 7. |
| **Governance and Continuous Improvement** (Ch29) | "The goal is calibration." Auditing our own test before trusting it is this chapter applied to an AI agent. |
| **AI Augmentation Guardrails** (AI-Augmented CSM) | "AI drafts, humans decide" is the reviewer design. The automation spec (trigger → required fields → decision logic → human review → failure modes → privacy/consent) becomes the v5 spec card; privacy/consent is why the open-weight arms exist. |

New ideas that could become canon go on `01_canon/canon-backlog.md`.

---

## 14. Content bank (not a schedule)

Each finding is a candidate LinkedIn post. JC picks which, if any, to publish.

1. My AI support bot tied a bot that does nothing. Here's why that's the real finding.
2. The reviewer that caught 17 of 18 bluffs and blocked 9 of 13 right answers.
3. The bug in my own test: when the judge ran out of room, it counted as "unsafe."
4. Why my grader no longer sees the answer key.
5. An empathy score that gave everyone a 1, and how to measure empathy you can see.
6. A handoff with three routes is a router with no owner.
7. Bad news fast, for bots: why "don't suggest anything" broke the handoff.
8. Smarter judge or more knowledge? What actually moved the bot.
9. Chinese or Western open-weight: what a support team gives up for procurement comfort.
10. Set your trust budget before you measure deflection.
11. The cheapest knowledge base you already own: solved community threads.
12. Why every judge in my test came from a different company.
13. Writing down predictions before running an AI test, and which ones I got wrong.

---

## 15. Limitations we accept

- One product (n8n), English only (Spanish stays v1.1).
- Forum questions overstate the docs gap compared with all support tickets.
- Accepted answers are the reference, even though some are workarounds.
- The docs are pinned to one commit, while questions span January to September 2026.
- Graders are models. We measure their agreement with each other and with JC's 20 grades, but they aren't people.
- About 100 questions per set can separate big differences, not small ones. Close results are reported as ties.
- "Self-hostable" models are tested through a pinned, well-run host, which represents a good deployment, not a typical one.
- No public benchmark covers judging, reviewing or document faithfulness for most September 2026 models. The practice trials make those picks.

---

## 16. Assumptions register

Every assumption behind the test, whose it is, what the evidence says so far, and how the test checks it. This list goes on the results page and feeds the case study. Sources: the model landscape report and round-one data.

| # | Assumption | Whose | Evidence so far | How the test checks it |
|---|---|---|---|---|
| 1 | Chinese open-weight models are close to the frontier | JC | **Mixed.** Close on human preference (Kimi K3 is 21 points behind #1 on Arena), about 11 points behind on the main index, and far behind on knowledge reliability | Arms E-CN and B against the closed-model arms |
| 2 | Google, Mistral and xAI are below the frontier | JC | **Mistral supported; xAI mostly; Google mixed.** Gemini 3.8 Flash ranks #10 on Arena, above OpenAI's flagship, but lower on the main index | Google competes in the grader-2 trial. Grok is excluded as reviewer because its lineage has weak document faithfulness, not because of rank |
| 3 | A bigger or more expensive model makes a better reviewer | Claude (round-one framing) | **Contradicted.** The most expensive Claude guesses on 73% of questions it can't answer. The 2.8-trillion-parameter Kimi guesses more than the 1-trillion MiMo | Reviewer trial, arm B and arm B+ |
| 4 | A grader must come from a different company than the text it grades | Claude | **Supported, as insurance.** Blind grading removes most self-preference on its own | Blind grading plus the company rules; arm B+ is scored by non-Anthropic graders only |
| 5 | Hosted open-weight results represent self-hosting | Claude | **Mixed.** Valid for a pinned, native-precision, verified host; the host alone can move scores by up to 16.6 points | Host pinning and recording |
| 6 | More thinking makes a better judge and a more faithful bot | Common belief | **Mixed; contradicted for faithfulness.** Higher effort made several models slightly less faithful to documents | Thinking level set and recorded per role |
| 7 | General "intelligence" leaderboards predict grounding and judging | Common belief | **Contradicted.** The low-cost drafter scores 24 on the index but is among the most faithful to documents; judge rankings reshuffle across benchmarks | Practice trials pick every judge and reviewer |
| 8 | Forum questions stand in for support tickets | Round-one design | **Known bias.** People post after the docs fail them | Stated as a limitation |
| 9 | The accepted forum answer is the right fix | Round-one design | **Mostly true, not always.** Some are workarounds | "Reference doubt" flag, counted and published |
| 10 | Calibration (knowing when to say "not supported") matters more than raw capability for reviewers | Model landscape report | **Supported by round one:** 15 of v3's 18 bluffs were on questions the docs didn't cover | Arm B's pre-registered prediction counts both bluffs caught and correct answers let through |

---

## 17. Decisions (JC, 2026-09-30)

| # | Decision | Answer |
|---|---|---|
| 1 | Scope | Full plan: all five phases, including the fresh holdout |
| 2 | Budget | A new OpenRouter key with a $110 limit; credit added in stages (about $30 before Build 1). Expected spend about $66; about $104 if grader 1 must stay on the API |
| 3 | JC's Build 1 time | Both: read the label disagreements (20–40) and grade 20 random replies blind |
| 4 | Trust budget | 2 confident wrong answers per 100 |
| 5 | Claude plan | Labeler 1 runs on JC's plan; grader 1 moves to the plan only if the 50-reply check passes |
| 6 | Arm B+ | Yes: Claude Opus 5.5 as a frontier reviewer, scored only by the non-Anthropic graders |
| 7 | Lineage rule | "No Chinese-origin weights," with Nemotron's training-data caveat disclosed |
| 8 | Model lineup | Section 8 approved as written, including both ceiling checks |
