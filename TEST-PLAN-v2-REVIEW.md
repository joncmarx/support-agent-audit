# Review of the support-agent test plan

Reviewed 30 September 2026. Sources: `TEST-PLAN-v2.md` (“T”) and `MODEL-LANDSCAPE-2026-09.md` (“M”), as supplied. Section references below refer to those files.

**Verdict: fix the measurement and execution rules before Build 1.** The proposed runs can support a useful comparison, but the current specification can attribute a harness repair to a better reviewer, change the winning system before confirmation, give different arms different judging standards, and undercount both trust incidents and grading work.

This review identifies **30 issues: 17 must-fix, 10 should-fix, and 3 minor**. Must-fix means a primary result could be misleading, a required decision is undefined, or the approved execution cannot be budgeted reliably. Should-fix means a material bias or overclaim can be reduced within the existing scope. Minor means a reporting or consistency correction that does not require another experiment.

The stored runs, original prompts, code, docs index, and actual question sets were not supplied. Accordingly, claims about the 27/30 retrieval result, individual labels, and historical API settings are **not independently verified** here. An explicit contradiction is distinguished from a missing safeguard or specification. Selected external sources were checked; this is not a complete re-audit of every model score in M.

## Must-fix

### M01. B versus historical A does not isolate the reviewer

**Where:** T §§1 finding 9, 2, 3; especially “only the reviewer changes.”

**Problem:** A uses stored v4 outputs produced with the old harness; B uses the repaired harness with a larger token allowance and different failure handling. Reusing drafts controls drafting, but it does not control the reviewer harness. Better results could come from the repair. The demonstrated 24/55 truncations were in the Google trial; the files do not establish how often the production v4 reviewer failed. That uncertainty does not make the comparison clean. Regenerating handoffs also introduces fresh generation variation.

**Concrete fix:** Keep historical v4 for the history chart, but make the causal A control a replay of the original low-cost reviewer on the same stored drafts and passages through the repaired harness. Hold the review prompt and decision schema constant across A and B. When the same draft is blocked and rewrite inputs are identical, reuse the same rewrite. Compare reviewer decisions separately from final reply quality. This repairs an existing control; it does not add a new research question.

### M02. G changes the system after the rule chooses its winner

**Where:** T §3 arm G and handoff-writer paragraph; §6 winner rule; §11 Build 3.

**Problem:** Section 6 says the best existing arm becomes v5. Section 3 says G can choose components separately and adds a new handoff template that none of the selection arms used. A winning collection of components is not necessarily a winning pipeline. The new template can change trust and resolution outcomes as well as handoff quality.

**Concrete fix:** Specify the eligible complete configurations. Select one on practice, apply the already-planned G handoff change, and evaluate that exact final configuration on practice before freezing it. Do not combine independently winning parts without evaluating the combination. Freeze the prompt, model, host, retrieval, retry policy, and outcome-code hashes before opening holdout labels. The holdout then evaluates exactly that frozen G.

### M03. “Sealed holdout” and “practice-only tuning” lack enforceable boundaries

**Where:** T §§2, 7, 9, 11.

**Problem:** Drawing about 100 threads from the same months leaves the eligible population, exclusions, random seed, exact size, and replacement policy unspecified. Excluding thread IDs does not stop duplicate questions, cross-posts, quoted solutions, or near-identical incidents from spanning practice, test, and holdout. Build 1 also exposes regraded test results before the later prompts and selections are finished. Calling later test results exploratory is correct, but does not enforce the stronger claim that all choices use practice only.

**Concrete fix:** Write the sampling query, exact target size, exclusion rules, seed, and failure/replacement rule before inspecting candidates. Group duplicate or directly linked versions of the same incident before splitting; do not group every question that merely uses the same legitimate technical fix. Seal holdout inputs and solutions separately and keep them out of builders’ and tuning agents’ contexts. Complete practice decisions before inspecting new-arm test scores. Explicitly acknowledge that old test results already informed this design. The planned second holdout run is permissible as a frozen secondary repeat: predeclare the first run as primary and never select between the two.

### M04. The time and leakage rules do not specify what a bot actually receives

**Where:** T §§4, 5, 9.

**Problem:** The harvest excludes evaluation thread IDs and checks answer posting/edit timestamps. It does not specify whether the customer-question text is its original version, whether later clarifications or solution-bearing edits enter that input, whether harvested wrappers contain future thread titles/edits, or whether acceptance itself occurred before the query. An answer posted earlier but only accepted later was not yet part of an operational “accepted answers” harvest. Labelers’ fix-derived searches would also leak the solution if those query strings or results were accidentally reused by the bot.

**Concrete fix:** Define one query-time input snapshot per case, containing only information available when the bot is supposed to respond. Keep accepted solutions and fix-derived search queries in the evaluation path only. For a historically replayed accepted-answer harvest, require both answer availability and accepted status before the query, with all supplied text valid at that cutoff. If acceptance histories cannot be recovered, state that this is a retrospective collection of eventually accepted answers and remove the claim that it exactly simulates what a team could have harvested then. Exclude cross-posts and copied evaluation solutions, not just matching thread IDs. Public questions can still have appeared in model training; describe the holdout as unseen by the project, not proven unseen by the models.

### M05. The outcome table is incomplete and can reward hedged wrong advice

**Where:** T §5 outcome table.

**Problem:** A question with a wrong fix can qualify as `right_question` merely because the fix is conditional. A handoff containing clearly unverified suggestions can avoid a trust incident even when the suggestion is false. Unsafe advice is explicitly handled in the handoff row but not consistently across all actions. Other combinations have no mapping: an irrelevant specific question, an answer with no fix, an empty reply, some mixed replies, or a malformed output. “Core,” “harmless,” and “clearly conditional” are undefined. The rows also have no precedence.

**Concrete fix:** Implement an exhaustive, ordered mapping before regrading. Check materially false or unsafe advice first, irrespective of whether it appears in an answer, question, or handoff. Safe diagnostic hypotheses may remain allowed, but hedging a false claim must not automatically earn credit. Add explicit no-progress and system-failure outcomes. Define material versus harmless errors with examples from practice. Require exactly one outcome per attempted question and retain separate safety flags. Validate the mapping against the combinations the rubric can emit.

### M06. The rubric conflates truth with retrieval support and gives arms different evidence

**Where:** T §5 grader inputs and “Invented claims”; §9 community section.

**Problem:** A real n8n behavior is called invented if it is absent from the supplied passages. That turns “the retriever did not supply evidence” into “the claim is false.” General technical knowledge is allowed elsewhere. In addition, F’s graders receive community evidence that F0’s graders do not, so an identical alternative fix could receive different correctness grades. The extra community section also reveals the knowledge condition even when the arm name is hidden.

**Concrete fix:** Separate factual correctness, support in the arm’s retrieved evidence, and compliance with its knowledge policy. Judge correctness using a common, frozen reference packet for the question across all arms; grade evidence support against the arm-specific passages in a separate field. A true but unsupported claim is not automatically an invented one. Remove model, arm, version, and reviewer metadata from grading packets, randomize item order, and state the residual limit to blinding where source availability is visible. Keep all reference-only evidence inaccessible to the bot.

### M07. Harvest answerability is collected but never used

**Where:** T §4 final question for harvest labels; §5 definition of bot-answerable; §6 unnecessary-handoff denominator.

**Problem:** `bot-answerable` remains only `n8n_docs` or `general_tech`. An `undocumented_n8n` question with a usable prior community solution is still classified as needing a human for F. F can therefore receive a `correct_handoff` where it had sufficient knowledge to answer, and the unnecessary-handoff metric excludes precisely the newly answerable cases the harvest is meant to create. A correct answer can still become `resolved`, so the error is specifically in handoff scoring and denominators, not a total inability to credit F.

**Concrete fix:** Keep the original category for the docs-gap analysis, but compute a separate arm-dependent `answerable_with_allowed_corpus` field. For F, include validated, temporally eligible community fixes that are in its allowed corpus; keep “retrieval found it” as a separate diagnostic. Privileged-action cases remain exceptions. Use the arm-dependent field in the outcome mapping and handoff denominator, and report the denominator. Retain all-question resolution and trust rates for directly comparable primary metrics.

### M08. There is no complete rule for producing one score from multiple graders

**Where:** T §§4, 5, 6, 7 company-independence exception.

**Problem:** The plan gives a tie-breaker a role in label disputes, but does not define how ordinary reply-grade disagreements are resolved, whether it votes on each rubric field or the derived outcome, or what happens when three models give three answers. For labels, a third model “weighs in” and JC reads “remaining” disagreements without defining remaining. For B+ and the Opus ceiling, disputes remain unresolved, but the chart still expects a point score. A builder must invent how these cases count toward the trust limit.

**Concrete fix:** Freeze separate procedures for label and reply disputes. For example: preserve all independent grades; obtain a blind third judgment on disputed outcomes; use a two-of-three result; mark three-way disputes unresolved. For unresolved cases, use a declared conservative primary policy—no resolution credit, and a trust incident if any grader identifies a material wrong/unsafe answer—and publish optimistic/pessimistic bounds as sensitivity results. Apply a single declared policy to all primary comparisons. Compute agreement from original independent grades, before adjudication.

### M09. B+ and the Opus ceiling change the judging panel as well as the tested model

**Where:** T §§3, 7, 8.

**Problem:** The Anthropic exceptions are explicitly approved; they are not covert violations of the written rule. The flaw is comparison: ordinary arms are scored by graders 1 and 2, while B+ and the Opus ceiling are scored by grader 2 and the tie-breaker, with different dispute handling. A score difference can reflect panel severity. Excluding B+ from selection also means the chosen v5 is best only among the eligible non-B+ configurations, not the best pipeline tested.

**Concrete fix:** Use the already-planned grader-2 results as the common primary scoring basis for B versus B+ and for comparisons involving the Opus ceiling. Show the second judges as sensitivity results and label the panels. Alternatively, use one common non-Anthropic panel on every directly compared arm, after budgeting it. Keep B+ excluded if that is the decision, but describe v5 as the best eligible configuration. Do not present mixed-panel aggregate scores as a clean frontier comparison.

### M10. The trust gate does not implement 2 per 100 or establish a population safety rate

**Where:** T §6; §7 predictions; §17 decision 4.

**Problem:** One error in 43 is **2.326%**, above 2%. Two errors in 97 are **2.062%**. “Two per approximately 100” can change the rule depending on the actual holdout size. More fundamentally, meeting an observed count threshold is not evidence that the underlying error rate is at most 2%. With zero errors in 100 independent questions, the exact one-sided 95% upper bound is about **2.95%**; with two, it is about **6.16%**. Model grading uncertainty makes the interpretation weaker still.

**Concrete fix:** For a literal empirical 2% rule use `allowed_errors = floor(0.02 × N)` with the actual fixed denominator: zero at N=43, one at N=97, two at N=100. If one practice error is intentionally tolerated, call it a separate, looser screening rule. Report observed counts and an exact binomial or Wilson interval; say “met the prespecified observed-count gate,” not “proved safe at 2%.” Keep the current sample sizes and accept that a population-level 2% guarantee cannot be established here. Do not revise the trust target at the checkpoint after seeing outcomes.

### M11. Overlapping individual intervals are not a valid comparison or tie rule

**Where:** T §§2, 6, 7 grader trials; M final discussion of grader-trial resolution.

**Problem:** The same questions appear in every arm, so comparisons are paired. Overlapping marginal intervals can accompany a clear paired difference; overlap does not establish equality. Overlap is also not transitive across three arms. Naive resampling of a zero-error sample always returns zero errors, giving a misleadingly degenerate trust interval. “Graders must differ by about 20 points” is not a universal property of 20 paired ratings. For example, a 4/20 advantage with only four discordant items has exact two-sided McNemar p=0.125.

**Concrete fix:** Bootstrap differences by resampling the same question IDs jointly across arms, with one question as the cluster for multiple replies and graders. Predeclare 95% intervals, the seed, and the resampling procedure. Use an exact/Wilson interval for rare trust rates. Report paired effects as clear or inconclusive, not “equal because the ranges overlap.” Operational selection can use point estimates plus a deterministic fallback, but must be distinguished from an evidence claim of superiority. Report per-field/outcome κ, confusion counts, and class prevalence; specify what happens if κ is undefined. Do not combine unrelated rubric fields into an unexplained single κ.

### M12. Model selection and runtime settings are not executable specifications

**Where:** T §§3, 6, 7, 8; M model recommendations.

**Problem:** “Best reviewer” has a prediction but no complete practice selection algorithm balancing false passes, false blocks, errors, and cost. “Cheaper or self-hostable” is not a deterministic tie-break: those options can conflict. No rule handles all arms failing the trust screen, equivalent candidates, or activation of alternates. “Matched cost” has no target or tolerance; applying it to every model also conflicts with retaining round-one settings for the cheap drafter. Ceiling checks do not specify whether they are raw drafters or reviewed pipelines. Model aliases, effective reasoning settings, retrieval settings, and output schemas are not fully pinned.

**Concrete fix:** Write one run manifest before trials. For reviewer selection, use the common stored practice drafts: screen final outputs by the declared trust/error rules, maximize correct drafts retained, then use measured deployment API cost and a fixed final tie order. Specify a corresponding drafter rule. Choose an explicit priority between cost and self-hostability; do not decide after scores arrive. If no candidate passes, report no qualifying winner. State exactly what each ceiling run executes. List accepted API model IDs, hosts, effective parameters, token caps, prompts, schemas, retrieval configuration, and alternate triggers. Apply cost matching within a named role trial only; preserve the cheap-drafter comparability exception. Record API-equivalent cost even when an evaluation role runs on a subscription.

### M13. The Claude-plan equivalence check has no acceptance rule or isolation protocol

**Where:** T §10; §11 Build 1.

**Problem:** “Agrees closely” leaves an expensive routing decision to discretion. The 50 replies have no specified source or class mix. Agreement between plan and API routes does not prove either is correct. Labeler 1 and grader 1 may also be the same model on a persistent session; the instruction not to show graders labels or predictions is insufficient if earlier session history, memory, files, or tools expose them. Separate routes may have different hidden prompts or settings.

**Concrete fix:** Select all 50 from practice, with a frozen mix of fixes, handoffs, errors, and ambiguous cases. Use the same chosen model and visible settings. Before running, write a threshold—for example, at least 45/50 identical derived outcomes for both API–plan and plan–plan comparisons, and zero disagreements on the trust-incident flag. This is an operational consistency criterion, not an accuracy claim. Use isolated stateless calls or fresh clean sessions, without project history, solution files outside the supplied packet, browsing, or memory. If isolation or the threshold fails, use the API as already planned. Labeler and grader sessions must also be separate. State what route is used if subscription limits interrupt a phase.

### M14. The research lineup is not valid under every trial outcome

**Where:** M recommended-lineup table and independence claims; T §8 E-CN row.

**Problem:** M recommends MiMo as the E-CN drafter while allowing MiMo to win the reviewer trial. That combination violates the no-same-company-review rule. The updated T correctly says the E-CN drafter must come from a different company, but the implementation branch is not spelled out and M still claims universal validity. M’s E-CN reviewer company cell also remains Z.ai even when another company wins. The Gemma alternate must exclude Google from both grader 2 and the tie-breaker, not merely from the primary grader slot.

**Concrete fix:** Use this branch table and check it automatically before any call:

| Arm-B reviewer winner | Eligible E-CN drafter(s) |
|---|---|
| GLM-5.3 or GLM-5.3-Flash | MiMo or Kimi |
| MiMo | Kimi |
| Kimi | MiMo |

When only one drafter remains, there is no two-candidate trial. Treat “Google has no grading role” as including tie-breaking. Declare T §8 authoritative over stale M alternates, and validate authorship, review, and all scoring companies for the actual chosen configuration. A and B+ remain the stated exceptions, rather than accidental rule breaches.

### M15. Reviewer errors are logged, but terminal behavior remains undefined

**Where:** T §2 harness fix; §§6, 8, 10.

**Problem:** Raising the cap and saying “retry it” does not say how many attempts, when a timeout occurs, whether retries change settings, whether a failed review permits a draft through, or how exhausted attempts affect denominators. Different choices can make a model appear safer or more capable. A cap of 4,000 alone does not guarantee space for both reasoning and a parseable final verdict. Draft, rewrite, grader, and labeler failures also need a defined route.

**Concrete fix:** Freeze per-role attempt limits, timeouts, caps, and retry conditions from practice. For an exhausted reviewer error, deliver a fixed safe handoff and retain a `system_failure` flag; do not silently pass the draft, classify an error as a genuine safety rejection, or drop the case. Count every attempted question in primary denominators. Record attempt-level and final failure rates, all billed tokens, and elapsed time. A missing grader verdict remains missing until the declared recovery/adjudication procedure resolves it; it is not a favorable grade.

### M16. The budget has no reconciled workload and understates grader-1 volume

**Where:** T §3 pre-review grading; §10 budget and “about 1,500 grades”; §11.

**Problem:** Under the natural interpretation that each scheduled non-holdout arm runs on all 140 practice/test questions, the specified main workload is:

| Work | Reply slots scheduled for grading |
|---|---:|
| Regrade v1–v4 on 43 + 97 questions | 4 × 140 = 560 |
| B and B+ | 2 × 140 = 280 |
| D, E-CN, E-US | 3 × 140 = 420 |
| F0 and F, both before and after review | 4 × 140 = 560 |
| Two practice ceiling checks | 2 × 43 = 86 |
| Holdout v4, v5, and v5 repeat, assuming N=100 | 3 × 100 = 300 |
| **Total** | **2,206** |

Without explicit grade reuse, two grades each means **4,412 primary grading calls**. Excluding B+ and the Opus ceiling leaves **2,023 grader-1 calls**, before grader trials, candidate losers, label-sway runs, tie-breaks, the 50-reply route check, and evaluation of the modified G. At the stated 2¢ rate, those grader-1 calls alone correspond to $40.46, not the $30 implied by 1,500 calls. Identical pre/post-review replies with identical grading packets, or reused practice outputs, could reduce this count, but no such ledger is supplied. Labeling also needs separate rows for 140 original cases, about 100 holdout cases, community-availability labels, and adjudication.

**Concrete fix:** Generate one call ledger keyed by phase, question set, candidate, role, output stage, and route. State which exact responses and grades are reused and avoid double-counting them. Price the ledger using measured practice token usage, including reasoning, retries, the API half of the route check, and third-party host prices. Re-estimate for any winning configuration that changes cost, not only Qwen as grader 2. Reserve remaining cost before each batch under the $110 cap. The fallback estimate of $104 has only $6 of headroom; the approved 30% per-phase overrun allowance does not assure completion within it. Reconcile the required scope at the existing checkpoint, rather than silently omit runs or assume the subscription savings.

### M17. The harvest and reference searches are not reproducible retrieval specifications

**Where:** T §2 three labeler searches; §§3, 4, 8, 9.

**Problem:** A target of 1,000–2,000 threads and “three searches” does not tell a builder which threads are selected, how queries are formed, what text is indexed, how it is chunked or ranked, how many passages are supplied, or which tokens are truncated. It is unclear whether all accepted answers or only retrieved ones reach F. If community text displaces doc text, F–F0 includes a changed docs context as well as added knowledge. If models drive search differently, D–B is not solely a change in drafting given common evidence.

**Concrete fix:** Pin the docs commit, corpus snapshot, thread sampling/order rule and exact count, query generation, index/embedding method, chunking, ranking, top-k, and token budgets. Apply eligibility filters before retrieval and store the actual retrieved IDs and text per question. Keep identical doc passages in F and F0, with a separately capped community slot. Use the same retrieval inputs for model-only comparisons, or explicitly label model-controlled retrieval as part of the tested intervention. State how each labeler searches and how search results become the common evaluation packet. No new retrieval benchmark is needed.

## Should-fix

### S01. The human anchor is both a selection set and a weak accuracy check

**Where:** T §§2, 7, 11; M grader discussion.

**Problem:** Twenty random v1–v4 replies can be dominated by handoffs, omit rare wrong fixes, or include several versions of one question. They then select the graders and are reused to advertise agreement with a human, making that agreement an in-sample calibration result. Support expertise alone does not settle unfamiliar n8n technical correctness, despite the plan’s reassurance that the task is not n8n trivia.

**Concrete fix:** Keep the same 20-item workload but stratify it across distinct questions and response/error types; conceal the strata and model identities from JC. Supply the same evidence packet and allow `cannot verify`. Do not turn those uncertain items into asserted technical ground truth. Report the 20 as a calibration set used for selection, not an independent validation sample or a precise accuracy estimate. Report class-specific errors and actual sample composition. Do not claim representative prevalence from an enriched sample without weighting.

### S02. `account_access` and fixed routes confuse required information with required authority

**Where:** T §4 categories and precedence; §5 route rule.

**Problem:** A fix requiring access to the customer’s instance may be executable by the customer after receiving instructions; it does not automatically need n8n staff. “Always needs a person” conflates a person carrying out bot-provided steps with escalation to a support agent. Likewise, a bug can require private diagnostics before GitHub, and an undocumented question need not have the forum as its only acceptable route. Categorizing the accepted fix alone also misses valid alternative solutions.

**Concrete fix:** Define `account_access` as a necessary privileged action unavailable to the requester/bot, not ordinary customer-side access. Distinguish “needs a missing fact” from “needs privileged intervention.” Permit a small set of justified routes based on the case’s actual access/privacy constraints. Define answerability using any verified feasible solution, with the accepted answer as the starting reference. Adjust the docs-gap wording accordingly.

### S03. Search results do not establish presence or absence at the required level

**Where:** T §1 finding 3; §2 labeler searches; §4 docs-gap report.

**Problem:** Finding the same page in 27/30 cases does not prove the necessary passage survived chunking and truncation, was supplied to the model, or described the applicable version. Conversely, failing to find a step in three searches does not establish that the docs do not contain it. The three residual misses are 10% of docs-answerable cases, enough to matter relative to several planned small effects.

**Concrete fix:** Inspect the actual retrieved passages already recorded for these cases, rather than only page IDs. For negative labels use “not found under the recorded search protocol” unless the relevant documentation section was checked sufficiently to support a stronger statement. Keep uncertain labels flagged through adjudication. Reword “search is not the main bottleneck” as a limited observed retrieval result until that passage check is done.

### S04. Closed-book guessing is an unsupported tie-breaker for judging and reviewing

**Where:** T §7 grader rule; §8 rationales; §16 assumptions; M introduction and conclusion.

**Problem:** The plan rejects general leaderboards as judge selectors, then lets a different public benchmark decide most close grader trials. That benchmark measures factual recall and abstention, not whether a reviewer catches false claims while allowing correct ones, or whether a judge agrees with the rubric. Rates are also quoted at different reasoning settings from the proposed grader configurations. Low guessing can be achieved by excessive abstention, the same broad failure mode the audit is trying to correct. Grok’s current suitability is inferred partly from different predecessor models.

**Concrete fix:** Use public scores for shortlisting and clearly labeled hypotheses only. Break uncertain grader ties using the predefined task-specific safety-error criterion and measured cost, with a deterministic fallback. Measure reviewer false passes and false blocks on the existing practice trial. Replace “contradicted,” “calibration is nearly independent,” and similar causal/general claims with conclusions the data actually establish. No additional models need to be added.

The official AA definition is incorrect answers divided by all non-correct responses, including partial answers and non-attempts; it is not a direct measure of reviewer skill or probability calibration. [External source 1]

### S05. E-CN versus E-US does not isolate model origin

**Where:** T §3 “only the models’ origin differs”; §16 assumptions.

**Problem:** The two arms change drafter, reviewer, capacity, training, tokenizer, reasoning behavior, and likely hosting economics. Matching prompts and host rules does not isolate nationality or weight origin. E-CN additionally benefits from the main reviewer-selection process, whereas the specified E-US pair is effectively fixed.

**Concrete fix:** Rephrase the comparison as “these two selected pipelines under these settings and procurement constraints.” Report their concrete quality and cost trade-off. Do not infer that the observed difference is caused by origin or estimates all Western versus Chinese models. Keep the two existing arms; no expanded factorial design is necessary for this narrower claim.

### S06. The temporal asymmetry has no proven direction

**Where:** T §9 “favors the docs-only arms” and “if anything, an underestimate.”

**Problem:** Both F and F0 receive the recent docs. Future documentation may make old community fixes redundant, but it can also conflict with historical versions or change which answers graders consider correct. Without establishing those relationships, the asymmetry is not guaranteed to lower the measured harvest effect. Models themselves may also contain later knowledge.

**Concrete fix:** Keep the pinned-doc design, but state that the effect is conditional on a recent docs snapshot and a historically filtered community corpus; its bias direction is unknown. Record the question’s product version when available and judge version-dependent advice accordingly. Remove the lower-bound claim instead of undertaking a historical-doc rebuild.

### S07. The label-sway check does not isolate the claimed cause

**Where:** T §2 blind-grading row; §10 phase 1; §11 Build 1.

**Problem:** “20 grades with the label shown vs hidden” does not define paired items, rubric, grader, ordering, or whether 20 means pairs or total calls. If the old rubric legitimately uses the label to judge handoffs, removing it changes available task information. If the new rubric is used instead, the result does not measure what caused round-one grades. Changing the rubric or model at the same time confounds the comparison.

**Concrete fix:** Specify paired fresh calls on the same practice replies, same model, same evidence, and same rubric, changing only label visibility. Measure changes in the label-independent fields—action, fix verdict, invented claims—not outcomes that intentionally depend on answerability. Describe the result as sensitivity to label visibility under that setup, not a quantified explanation of all round-one bias. Clarify and budget the exact number of calls.

### S08. “Resolved without a human” and “whole pipeline self-hostable” overstate what is observed

**Where:** T §§3, 6, 12, 15.

**Problem:** Offline model grades against accepted answers do not show customer success, actual ticket deflection, or absence of follow-up. A correct-looking answer may depend on unavailable access or an unstated condition. A hosted test of open-weight drafting/review also does not establish that retrieval and every production dependency can run locally, or that a self-hosted deployment has the same cost and performance. The existing limitations acknowledge part, but not all, of this mismatch.

**Concrete fix:** Label the headline “judged fully answered” or “estimated resolvable from this reply” and define the feasibility conditions for that judgment. Present actual deflection as unmeasured. Inventory the already-used production dependencies and narrow “whole pipeline” to the components whose local availability is established. Report measured hosted API cost; do not treat subscription evaluation savings or hosted costs as self-hosting economics. No live customer trial or server benchmark is required for those narrower claims.

### S09. “Reference doubt” has no downstream policy

**Where:** T §§2, 5, 15, 16.

**Problem:** Counting doubtful accepted answers does not stop a questionable reference from choosing graders, labeling a docs gap, selecting v5, or causing a trust-budget failure. “A different fix that clearly works” also leaves the evidentiary standard to each judge. Two labelers and two graders can agree on the same bad reference, especially when the same models occupy both roles.

**Concrete fix:** Define what triggers reference doubt and record the supporting passage/version. Adjudicate it before using that case for selection where possible. If unresolved, retain the case and denominator but publish bounded/sensitivity scores under a frozen policy rather than silently exclude it after seeing which arm benefits. Allow an alternative solution when supported by the common evaluation evidence, not merely by a grader’s confidence. Report unresolved reference cases separately from model disagreement.

### S10. Text normalization and publication need content-preserving rules

**Where:** T §5 plain-text conversion; §9 privacy; §12 every reply published.

**Problem:** Blindly stripping Markdown can alter code indentation, command syntax, tables, links, or distinctions between examples and instructions. That can change the answer being judged. “Thread text is never published” also conflicts operationally with publishing every generated reply when an answer quotes its sources, and with accidental inclusion of cached passages in logs or grades.

**Concrete fix:** Use a deterministic normalizer that preserves code, indentation, URLs, table associations, and text content; retain originals. Give human calibration and model graders the same normalized material. Preserve original presentation when separately assessing usability. Before publication, inspect the generated page/export for copied source text and identifiers against the plan’s own publication rule; publish IDs/attribution and permitted derived material only. This is a check on already-planned outputs, not a new evaluation track.

## Minor

### N01. The two documents disagree about approved candidates and exceptions

**Where:** M opening, lineup, “Nine changes”; T §§7, 8, 17.

**Problem:** M first says drop DeepSeek from both trials, then retains it as a last-resort E-CN drafter. Its optional Opus ceiling is approved in T. Its claim that the lineup meets every independence rule omits T’s explicit A/B+ exceptions. It also includes Gemma and a reviewer swap that T’s approved table does not include. These are not necessarily new violations by T, but they are dangerous if a builder treats both files as executable instructions.

**Concrete fix:** Add a short precedence statement: T’s approved manifest controls execution; M is dated background research. Remove or clearly mark superseded alternates and update the exceptions. Do not silently restore a dropped candidate.

### N02. Some benchmark labels and numeric comparisons are misleading

**Where:** M main model table, matched-cost paragraph, ceiling discussion; T §§8, 15.

**Problem:** “Vectara faithfulness” labels a hallucination/error percentage, where lower is better. The proposed “equal cost” Opus-medium/Sonnet-high illustration costs $1.34 versus $1.08—**24.1% more**, not equal. The Astra–Sol AA gap is 0.9 at maximum effort but 0.7 at high effort; the narrative does not consistently identify which settings underlie the cost and score comparison. “About 100 questions per set” also obscures that practice has only 43.

**Concrete fix:** Rename the Vectara column to “hallucination rate, lower is better”; label the cost pair as approximate and measure actual role-specific costs. Attach model/version/effort/snapshot to each comparative number. State the actual set sizes. The listed Elo arithmetic itself is reasonable and does not need correction.

### N03. External evidence is occasionally generalized beyond its source

**Where:** T §5 formatting rationale; §8 Mistral rationale; M related passages.

**Problem:** The cited Markdown study’s 73–97% result was for **four of five judges**, on a 30-pair human comparison with two annotators; the fifth judge was near the human preference rate. The free Mistral license does exclude companies above the stated monthly-revenue threshold, but also explicitly offers a route to request a separate commercial license. “Bars companies” is too broad if read as an absolute prohibition. Neither issue requires adding Mistral or abandoning formatting normalization.

**Concrete fix:** State the study’s sample and exception. Describe the model as excluded from this test because its standard free license does not cover the intended companies; acknowledge that a separate commercial agreement may be available. Archive exact source revisions for facts used to eliminate candidates. [External sources 2–3]

## Arithmetic that checks out, and what remains unverified

| Claim | Audit result |
|---|---|
| v4 blocked 87 of 97 | Listed blocked categories sum to 17 + 9 + 22 + 5 + 34 = 87. Their underlying counts sum to 18 + 13 + 24 + 5 + 37 = 97. Raw classifications remain unverified. |
| 388 historical test grades | 4 × 97 = 388. Correct. The new practice-plus-test regrade is 560 replies and 1,120 calls at two graders each. |
| 69% = 67/97 | 69.07%, correctly rounded. |
| 17 of 67 got at least a partial fix | Numerically possible; the aggregate statement cannot be independently reconstructed without the stored run rows. |
| Phase budget | 28 + 12 + 30 + 22 + 20 = 112. Correct. |
| Discount scenarios | 112 − 8 = 104; 112 − 8 − 38 = 66. Correct arithmetic; the savings assumptions need the call ledger. |
| Core phases | 28 + 12 + 22 = 62. Correct before the plan-route discounts. |
| F gains five out of 97 | Equivalent to 5.15 percentage points. It is a prediction, not a justified power or significance threshold. |
| Trust gate | 1/43 = 2.326%; 2/97 = 2.062%; 2/100 = 2%. The same integer cutoff does not implement the same percentage at different sizes. |
| 16/20 grader agreement interval | A standard 95% Wilson interval is approximately 58.4–91.9%, consistent with M. It does not establish a universal 20-point separability rule. |

The labels 17/18 bluffs caught and 9/13 correct answers blocked are conditional on the old grader’s decisions. Publish them as historical classifications until phase 1 recomputes them; do not assume they are independently established truth.

## Minimal revision order

1. Freeze the split/data-access rules, complete outcome mapping, answerability logic, common grading evidence, and adjudication policy before any paid regrade.
2. Pin selection and execution rules, including errors, the Claude-plan check, company compatibility, and the repaired A control.
3. Build the call ledger and resolve it against the approved cap at the existing checkpoint.
4. Complete practice selection, evaluate the exact final G, freeze it, then run the primary and secondary holdout runs as declared.
5. Narrow causal and deployment claims to what the existing experiments measure.

These changes do not require more products, languages, model families, live tickets, a new benchmark, or a larger holdout. The corrected A comparison and practice evaluation of the changed G are necessary because the existing causal comparison and winner definition are otherwise broken.

## External sources checked

1. [Artificial Analysis: AA-Omniscience methodology and metric definition](https://artificialanalysis.ai/evaluations/omniscience). Used only to check what the guessing-rate proxy measures, not to independently endorse every model value in M.
2. [Soumik: Judging the Judges, arXiv 2604.23178](https://arxiv.org/html/2604.23178), especially the style-bias discussion and Appendix G. Supports the narrower formatting-study description above.
3. [Mistral Medium 3.5 license](https://huggingface.co/mistralai/Mistral-Medium-3.5-128B/raw/main/LICENSE). Supports the free-license restriction and separate commercial-license route.

Confidence-bound and workload calculations were recomputed locally. No source data or plans were modified by this review.
