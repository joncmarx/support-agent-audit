# Preregistration log (Test Plan v3)

Each entry is written before the paid batch it names. Entries are append-only; a correction is a new entry that says what it corrects.

## 2026-09-30 20:14:17 UTC — Build 1, step 1: manifest written; phase-1 predictions

- Manifest sha256: `5460b5dc94b6b71494f1a285531f97cbbe260b0156e0fa1614a6c763bd7741fe`
### Phase-1 predictions (TEST-PLAN-v3 section 11), written before any Build 1 model call

1. **Needs a human (primary).** After labels v2 and JC's reading, the share of the 97 test questions whose final
   category is on the human side (`account_access`, `bug_or_release`, `undocumented_n8n`) falls from round one's
   69% (67 of 97) to **between 50% and 65%** (49 to 63 questions). The same share is reported for the 43 practice
   questions and all 140, but the prediction is scored on the 97 test questions.
2. Scored as: hit if 49 <= n <= 63 of 97; otherwise a miss, reported on the results page with the number.

### Definitions fixed now
- "Needs a human" uses the final label after section 5 settlement (two-of-three, JC's reading on line-crossing
  disagreements). Questions JC can't settle use the tie-breaker's label and are reported both ways.
- Reference-doubt questions stay in the denominator; the share is also reported without them.

## 2026-09-30 20:39:26 UTC — Build 1, step 2: holdout sealed

- Manifest sha256: `d419d62c6b41037c91afee3a7533771987add3c48b5eb546ba3f58d87e861a96`
### Holdout drawn and sealed ($0, no model call)
- Rules: `audit/holdout.py` docstring (sha256 `e168e418df135dd3db358c2986b00115fda7e0dd9e6116ad8f21f87fb31a276f`). Round one's 150 threads replay exactly from its
  cache (stopped at position 234 of 1,031); the holdout continues from position 235.
- Checked 193 threads: {'pick': 120, 'skip': 66, 'exclude': 7}. Skip and exclusion reasons: {'self_answered': 33, 'L_round_one': 4, 'date': 12, 'original_not_english': 1, 'image_dependent': 8, 'question_short': 3, 'spanish': 2, 'answer_short': 8, 'C_round_one': 2}.
- 100 holdout threads + an ordered reserve of 20 (reserve use needs JC's approval; see below).
- 24 of the 100 were edited after posting; 89 of 100 carry the original text from edit history. 11 had their
  revisions hidden by forum moderators, so their current text is used and flagged.
- Sealed file hashes (sha256):
  - `holdout_questions.jsonl`: `f0f6533013a0aa91983cdcd696f5765072cf92f1ac3100185a309a12e48332eb`
  - `holdout_solutions.jsonl`: `fe33068ee80021e17cb2484a41910c62023686163cf1a93f726bd7f338f5d002`
  - `reserve_questions.jsonl`: `255bf6df9c77c85ea100936c2d93688f01c655f4f91b6ff71332f9dd61742253`
  - `reserve_solutions.jsonl`: `40e465d5c2b25fae5e920606e210065fee4a17bf1e9009faade5826e4b9cfde4`
  - `draw_log.jsonl`: `c08fb9430c63ebf20b6c40415e2f4153c3819181c9a69a7ba5b462722fbdc9dc`
- Nobody has read the holdout. The draw printed only counts and reason codes. The folder `sealed/` is git-ignored
  and stays out of every build and tuning session until v5 is frozen in Build 3.
- Open questions for JC (not yet decided): (a) round one's reference check on the holdout and use of the reserve;
  (b) threads whose edit history is hidden.

## 2026-09-30 20:43:52 UTC — Build 1, step 3: dry run + step 4 prompt freeze

- Manifest sha256: `f0aae93b5056c96929531eb2a25eed3b677acb3ad3e752661ba95716ea3fc16d`
- Re-priced estimate: $0.42 (runs only if available >= $0.55)
### Build 1, step 3: dry run of the repaired harness (5 practice questions)
- Purpose: prove host pins, thinking settings, parsers, fallbacks and ledger rows work. Results are not used
  for any choice and are not a trial.
- Questions: 5 practice questions, seeded (20260935); arm A (v4 as built) on the repaired harness, reusing round
  one's passages; the final replies are graded by Sonnet 5.5 and the three grader-2 candidates.
- Key status before the batch: {'limit': 80, 'limit_remaining': 80, 'key_usage': 0, 'balance': 39.335, 'available': 39.335}.
- Prediction: 0 final system failures; every grader returns a parseable grade on every item.

### Frozen now (step 4), before any new arm has a score
- `prompts/F0F_SYSTEM.md`, `prompts/F0F_USER.md`, `prompts/F_REVIEW.md` (F0 and F: drafter, user message and reviewer),
  `prompts/G_HANDOFF.md` (G's bad-news-fast handoff writer), `prompts/SAFE_HANDOFF.txt` (JC's fixed safe handoff,
  written by JC on 2026-09-30). Hashes are in the manifest under `prompts`.

## 2026-10-01 08:53:46 UTC — Build 1, step 7: grader screens

- Manifest sha256: `8fa1041798955b1335842d1f7675d53f83cbe724110dd52b6db031b4a01b2a2f`
- Re-priced estimate: $1.30 (runs only if available >= $1.69)
### Build 1, step 7: grader screens on JC's 20 blind grades
- JC finished 20 grades on 2026-10-01: 19 verifiable, 1 "can't verify". His label-free outcomes: 12 resolved, 6 handoff,
  1 no_progress, 0 partial, 0 wrong, 0 trust incidents.
- Before any screen grade exists, a $0 comparison: JC's outcomes match round one's Sonnet grades on 9 of 19 (47%).
  JC is more lenient than round one's grader (round one called 2 of his "resolved" replies confidently wrong and 5
  others partial).
- Order: grader 1 (Sonnet 5.5) first, then Gemini 3.8 Flash, Muse Spark 1.3 (JC confirmed OpenRouter's 18+ check on
  2026-10-01) and Qwen3.8 Max. Pass rule: >= 70% label-free match on JC's verifiable items (>= 14 of 19) and every
  JC trust incident flagged (JC recorded none, so only the 70% rule bites).
- **Prediction:** at least one model fails the 70% rule, because the gap between JC and round one's grader is wide.
  If every model fails, section 7 applies: stop before the re-grade and decide together.
- Key status: {'limit': 80, 'limit_remaining': 79.69757525, 'key_usage': 0.30242475, 'balance': 39.0326, 'available': 39.0326}.

## 2026-10-01 08:54:43 UTC — Build 1, step 7: Opus screen

- Manifest sha256: `8fa1041798955b1335842d1f7675d53f83cbe724110dd52b6db031b4a01b2a2f`
- Re-priced estimate: $1.04 (runs only if available >= $1.35)
### Step 7 result so far, and the Opus screen (section 7 alternate)
- Sonnet 5.5 matched JC's label-free outcome on 8 of 19 verifiable items (42%); the bar is 14 (70%). **Fails.**
  Sonnet called 3 of JC's "resolved" replies confidently wrong (items 04, 13, 19) and 6 others partial.
- Section 7: grader 1 becomes Claude Opus 5.5, screened the same way. If Opus also fails, stop before the plan
  check and the re-grade, and decide with JC. The three grader-2 candidates are screened in the same batch so that
  decision has every model's numbers.
- Prediction: Opus also fails (it is the same family and the gap is about leniency, not reading skill).

## 2026-10-01 09:01:24 UTC — Build 1, step 7: screen result (stop)

- Manifest sha256: `312576dd3a87465b9d395a8302ff178e8d575445443b55be5c315218bc8a8c4c`
### Step 7 result: every model fails the screen. STOP (section 7), decide with JC.
| Model | Matches JC (of 19 verifiable) | Cents per grade |
|---|---|---|
| Sonnet 5.5 | 8 (42%) | 2.6 |
| Opus 5.5 | 10 (53%) | 6.9 |
| Muse Spark 1.3 | 10 (53%) | 2.3 |
| Gemini 3.8 Flash | 11 (58%) | 1.1 |
| Qwen3.8 Max | 11 (58%) | 2.4 |
- The models agree with each other far more than with JC: at least 3 of 5 agree on 19 of 20 items; Opus, Gemini and
  Muse agree pairwise on 17-18 of 20. JC matches that consensus on 10 of 19. Every one of his 9 departures is more
  lenient: 3 replies he called resolved are confidently wrong to the consensus (models from three companies), 2 are
  partial, 2 of his handoffs are partial, 1 is a right question, 1 is resolved.
- Probable cause (Claude's error): JC's page asked "Is its fix right? Correct / Partial / Wrong" without the rubric's
  definitions (correct = reaches the key step of the reference fix; partial = misses a step the customer needs). The
  graders and JC answered different questions. The prediction "at least one model fails" was a hit.
- Spend so far: $3.37 (dry run $0.30, screens $3.07). No plan check, labels or re-grade have run.

## 2026-10-01 09:21:53 UTC — Build 1, step 9: labels v2 in batch mode

- Manifest sha256: `20014ea58bc8800cd0a7f7d0bc852d28f3a60180faa538ac9efc032fc25e972e`
- Re-priced estimate: $5.10 (runs only if available >= $6.63)
### Build 1, step 9: labels v2 (decisions 12-14 approved by JC on 2026-10-01)
- Labeler 1 = Sonnet 5.5 and labeler 2 = Gemini 3.8 Flash, both in OpenRouter batch mode (half price). Batch hosts:
  Anthropic for Sonnet (same as before); **Google Vertex for Gemini** (its batch endpoint; the screen ran on Google
  AI Studio). Tie-breaker = Muse Spark 1.3 over the regular API (no batch endpoint), blind to both labels.
- Each labeler: turn A (key step, fix query, exact terms) -> three recorded searches (S1 = v4's own retrieved
  passages for the question; S2 = hybrid search on the fix query; S3 = exact-term search) -> turn B (category,
  evidence passage codes, reference doubt). Rules: `rubric/LABELING-v2.md`; settlement: `audit/labels2.py:settle`.
- JC reads every case where the three labels don't agree on answerable vs needs-a-human, plus three-way splits.
- Estimate $5.10. Key status: {'limit': 80, 'limit_remaining': 76.62649615, 'key_usage': 3.37350385, 'balance': 35.9615, 'available': 35.9615}.
- Prediction (already registered): the share of the 97 test questions that need a human lands between 50% and 65%.

## 2026-10-03 05:45:14 UTC — Build 1, step 9: labeler 2 turn A resubmitted

- Manifest sha256: `e4adfcecae2aab717df042116a7278cc5064d64233903f39990fcc8bededbf9e`
### Labeler 2 turn A resubmitted to batch mode (JC, 2026-10-03 07:44 Madrid)
- The first Gemini batch (submitted 2026-10-01 09:22 UTC, Google Vertex batch host) stayed "in progress" with 0 of 140
  for about 46 hours, past its 24-hour window, with no error. It was pre-charged about $2.18 (its maximum output).
- On JC's instruction the 140 items are resubmitted in a new batch, same model, host, prompts and settings (attempt 2
  of 3 for each item under section 8). The old batch is marked abandoned; if it ever returns, its results are ignored.
- Key status: {'limit': 80, 'limit_remaining': 70.548875995, 'key_usage': 9.451124005, 'balance': 29.8839, 'available': 29.8839}.

## 2026-10-05 10:00:03 UTC — Build 1, step 9: labeler 2 turn B over the API

- Manifest sha256: `aeea8f0322013cfff76a8196a96155192662de66d939df0fecc8b874f7cdc7ed`
- Re-priced estimate: $2.05 (runs only if available >= $2.67)
### Labeler 2 turn B over the regular API (decision 15, JC 2026-10-05)
- Gemini 3.8 Flash's turn A finished in the resubmitted Vertex batch (140 of 140, $0.16), after its 24-hour window.
  Both batch pre-charges were released. The first batch is still listed as in progress; its results are ignored.
- Turn B runs over the regular API on Google AI Studio (the model's API host in audit/models.py): same prompts
  (rubric/LABELING-v2.md + turn_b_user), same settings and caps as the batch route, JSON mode, 3 attempts per item.
  The three recorded searches are run once from turn A and cached in labels/labeler2_codes.json.
- Labels phase: spent $4.06 so far; estimate for this step $2.05 (about 15,500 input and 800 output tokens per item).
  JC raised the labels-phase ceiling from $6.63 to $8.00 (decision 15). The tie-breaks are priced in their own entry.
- Key status: {'limit': 80, 'limit_remaining': 72.56664712, 'key_usage': 7.43335288, 'balance': 31.9016, 'available': 31.9016}.
- Predictions: (1) Gemini's turn B parses on at least 137 of 140 after 3 attempts. (2) The two labelers agree on
  answerable versus needs-a-human on 75-90% of the 140. (3) The tie-breaker is needed (category or reference doubt
  differs) on 35-60 of the 140.

## 2026-10-05 10:03:12 UTC — Build 1, step 9: tie-breaks

- Manifest sha256: `aeea8f0322013cfff76a8196a96155192662de66d939df0fecc8b874f7cdc7ed`
- Re-priced estimate: $1.86 (runs only if available >= $2.42)
### Labeler 2 turn B result, and the Muse Spark tie-breaks
- Turn B over the API: 140 of 140 parsed on the first attempt, $2.07 (estimate $2.05). Labels phase now $6.13.
- Agreement between the labelers: category 108 of 140 (kappa 0.69); answerable versus needs-a-human 120 of 140
  (kappa 0.69). Predictions from the previous entry: (1) hit, (2) hit at 85.7%, (3) hit at 54.
- Tie-breaker: Muse Spark 1.3 over the API, blind to both labels, both turns (label_api), on the 54 questions
  where category or reference doubt differs. Estimate $1.86 (about $0.034 per question, from Muse's token use in
  the screen). Projected labels phase $7.99 against JC's $8.00 ceiling (decision 15). Runs in guarded
  chunks: no chunk starts unless its worst case ($0.05 per question) stays under the ceiling.
- Key status: {'limit': 80, 'limit_remaining': 70.70866475, 'key_usage': 9.29133525, 'balance': 30.0437, 'available': 30.0437}.
- Predictions: (1) Muse parses on at least 52 of 54. (2) JC's reading sheet has 20-26 questions: all 20 where the
  labelers split answerable versus needs-a-human, plus any three-way splits among the other 12 category splits.

## 2026-10-12 15:22:02 UTC — Build 1, step 9: labels final and the phase-1 prediction

- Manifest sha256: `aeea8f0322013cfff76a8196a96155192662de66d939df0fecc8b874f7cdc7ed`
### Labels v2 final (results entry, no paid run)
- JC read the 23 questions on his sheet (answers saved 2026-10-08 and 2026-10-12, exported to labels/jc_readings/).
  He marked the key step as on the docs page for 21 and as needing n8n-specific knowledge for 2.
- `python3 -m audit.labelrun final`: 140 of 140 labels final, none unsettled. Basis: both labelers agree 86;
  labelers agree on category with the tie-breaker settling reference doubt 22; JC on the page 21; two of three 9;
  JC needs a human with two labels agreeing 2. No flags. Reference doubt on 10.
- Results from the 2026-10-05 tie-break entry: (1) Muse parsed 54 of 54, hit. (2) JC's sheet had 23 questions, hit.
- Final split: practice 33 answerable / 10 need a human (of 43); test 67 answerable / 30 need a human (of 97).
- **Phase-1 prediction (section 11) MISSED.** Predicted: the share of the 97 test questions that need a human falls
  from 69% to 50-65%. Actual: **30.9% (30 of 97)**, far below the range. The miss does not depend on JC's reading:
  18 of the 23 sheet questions are test questions and JC called 16 of them answerable; had all 16 gone the other
  way, the share would be 46 of 97 (47.4%), still below the range. Each labeler alone also lands below it on all 140
  (labeler 1: 42 of 140 human, 30%; labeler 2: 56 of 140, 40%).
- Labels spend unchanged at $7.92 (ceiling $8.00). Build 1 total $11.29.

## 2026-10-12 15:31:27 UTC — Build 1, step 10: re-grade, grader 2

- Manifest sha256: `2262514f7153c16af481f6c57259d4fa10e09a6ff8154dbc0d948f957e5f6efe`
- Re-priced estimate: $2.05 (runs only if available >= $2.67)
### Phase-1 blind re-grade, grader 2 (JC, 2026-10-12)
- Scope: the 403 unique replies in regrade/replies.jsonl (v1 finals, v4 finals, v4 pre-review drafts; practice and
  test; 420 arm-rows). Reference packets use every passage either labeler cited (final_evidence). Rubric v3.
- **Grader 2 = Gemini 3.8 Flash in OpenRouter batch mode (Google's batch host), JC's choice.** If it has not finished
  within 24 hours of submission, its unfinished items go through the regular API (JC pre-approved, about +$2).
  Checked once every 6 hours, not more (JC).
- **Grader 1 (Sonnet 5.5): route not yet decided.** JC asked to revisit running it on his Claude Max plan. Grader 1 is
  submitted in its own entry once that is settled. Tie-breaks (Muse Spark 1.3, API, blind) follow both.
- Estimates: Gemini batch $2.05 (0.51 cents per reply, measured screen cost x 0.5); whole re-grade $9.45 on batch,
  $11.51 if Gemini falls back to the API. Batches are pre-charged at maximum output until they complete.
- Key status: {'limit': 80, 'limit_remaining': 68.67803365, 'key_usage': 11.32196635, 'balance': 28.013, 'available': 28.013}.
- Predictions: (1) Gemini parses at least 395 of 403 after 3 attempts. (2) Grader 1 and grader 2 agree on the
  final outcome for at least 75% of the 403. (3) The tie-breaker is needed on 60-130 of the 403. (4) Under labels v2,
  v4's final replies hand off unnecessarily on at least 45 of the 67 answerable test questions. (5) v4's final replies
  fully answer at most 12 of the 97 test questions.

## 2026-10-12 15:39:20 UTC — Build 1, step 10: re-grade, grader 1

- Manifest sha256: `2262514f7153c16af481f6c57259d4fa10e09a6ff8154dbc0d948f957e5f6efe`
- Re-priced estimate: $5.13 (runs only if available >= $6.67)
### Phase-1 blind re-grade, grader 1 (JC, 2026-10-12)
- Grader 1 = Sonnet 5.5 in OpenRouter batch mode (Anthropic's batch host), the same 403 items and rubric as grader 2.
- JC asked whether grader 1 should run on his Claude Max plan instead. Claude checked the terms: the Consumer Terms
  (section 3) bar scripted access except by API key or explicit permission, and Claude Code's legal page says Max limits
  assume "ordinary, individual usage". A 400-call scripted grading run is a gray area, the saving is about $5 here
  and about $20 across the project, and the switch would need the 50-reply consistency check plus a sign-in on JC's
  Mac. **JC chose the API (batch).** Decision 13 stands.
- Estimate $5.13 (1.27 cents per reply, measured screen cost x 0.5). The Gemini batch (previous entry) is
  pre-charged at maximum output while it runs.
- Key status: {'limit': 80, 'limit_remaining': 66.365975015, 'key_usage': 13.634024985, 'balance': 25.701, 'available': 25.701}.
- Predictions: as registered in the grader-2 entry; additionally, (6) Sonnet's batch completes within 6 hours and
  parses at least 400 of 403.

## 2026-10-13 03:35:21 UTC — Build 1, step 10: re-grade tie-breaks

- Manifest sha256: `860a28dbfca73e12bf12486d1a750d6665665d967257e49c3f5aac6daac8948a`
- Re-priced estimate: $2.52 (runs only if available >= $3.28)
### Phase-1 re-grade: both graders in, Muse Spark tie-breaks
- Grader 1 (Sonnet 5.5, Anthropic batch): 403 of 403 after retries (6 needed a 2nd attempt: malformed JSON).
  Grader 2 (Gemini 3.8 Flash, Google batch): 403 of 403 after retries (5 needed a 2nd attempt: 4 ran into the
  8,000-token cap, 1 empty). Both main batches completed inside 6 hours. Spend so far $8.00 (estimate $7.18, +11%).
- Results for the registered predictions: (1) Gemini parses at least 395 of 403: **hit** (403). (2) Graders agree on
  the final outcome for at least 75%: **MISSED** (292 of 403, 72.5%). (3) Tie-breaker needed on 60-130: **hit** (111).
  (6) Sonnet's batch done within 6 hours, at least 400 of 403 parsed: **hit** (403). Predictions 4 and 5 are scored
  after the tie-breaks.
- Tie-breaker: Muse Spark 1.3 over the API, blind, on the 111 replies where the graders' outcomes differ. Estimate
  $2.52 (2.27 cents per reply, measured in the screen). Projected re-grade total $10.52, inside the $9.45-$11.51 range
  JC saw on 2026-10-12. Runs in resumable chunks of under 2 minutes.
- Key status: {'limit': 80, 'limit_remaining': 60.680495265000005, 'key_usage': 19.319504735, 'balance': 20.0155, 'available': 20.0155}.
- Prediction: (7) Muse parses at least 108 of 111, and at most 15 of the 111 end as three-way splits (unresolved).

## 2026-10-13 03:48:59 UTC — Build 1, step 10: re-grade results

- Manifest sha256: `860a28dbfca73e12bf12486d1a750d6665665d967257e49c3f5aac6daac8948a`
### Phase-1 re-grade complete: results for the registered predictions
- Tie-breaks: Muse Spark 1.3, 111 of 111 parsed (117 calls incl. retries), $2.84 (estimate $2.52, +13%).
  Re-grade total $10.84 (estimates $9.45 batch / $11.51 worst route). Phase 1 total $22.13.
- Settlement of the 403 replies: graders agree 292, two of three 90, unresolved (three-way split) 21.
- Grader agreement (kappa, before tie-breaks): outcome 0.64, action 0.77, fix verdict 0.69, material error 0.58.
- Predictions: (4) v4 hands off unnecessarily on at least 45 of the 67 answerable test questions: **hit** (61).
  (5) v4's finals fully answer at most 12 of 97: **hit** (6). (7a) Muse parses at least 108 of 111: **hit** (111).
  (7b) at most 15 three-way splits: **MISSED** (21). Earlier: (1) hit, (2) MISSED (72.5% vs 75%), (3) hit, (6) hit.
- Corrected baseline, test (97): v1 resolved 6, confidently wrong 18, unnecessary handoffs 31 of 67; v4 final resolved 6,
  confidently wrong 2, unnecessary 61 of 67 (91%); v4 drafts before review resolved 19, confidently wrong 30,
  unnecessary 12 of 67; hand-off-everything 0 / 0 / 67 of 67. Full tables: runs/v3plan/CHECKPOINT.json.
- Key status: {'limit': 80, 'limit_remaining': 57.820557265000005, 'key_usage': 22.179442735, 'balance': 17.1555, 'available': 17.1555}.

## 2026-10-13 09:33:54 UTC — Build 2: reviewer trial + arm B (phase 2)

- Manifest sha256: `be59fb2bb1cfadf3b6b7fb246f0ec92b76eeccf73a68b96ab4ab087867c34bcc`
- Re-priced estimate: $1.55 (runs only if available >= $2.02)
### Build 2, phase 2: reviewer trial on practice (43 v4 drafts x 3 candidates), then arm B on test
- **Decision 17 (JC, 2026-10-13):** batch mode wherever the pinned host accepts it; saving money beats turnaround.
  Phase-2 ceiling raised from $1.72 (stop line $2.24) to **$4.00**. Reason: smoke calls (1 practice draft per candidate,
  phase "2-smoke", $0.05) showed real review prompts at ~7,300 tokens against the 4,400 assumed, and GLM thinks ~1,900
  tokens. Batch re-price: trial ~$1.55; arm B $0.35 (MiMo) to $1.60 (Kimi); phase 2 $1.90-$3.20.
- **Reviewer hosts pinned** (section 8): GLM-5.3 -> Parasail fp8 (third party, full 1M context/output); MiMo-V2.6-Pro ->
  Xiaomi fp8 (lab's own); Kimi K3 -> Moonshot mxfp4 (lab's own, native 4-bit). No fallback. Thinking at provider default.
  Caps start at 8,000 tokens and are frozen after the trial at >= 4x the longest reply measured.
- **Route:** OpenRouter batch with the same host pins. A host that refuses batch (nothing billed) runs over the regular
  API in one-attempt-per-item chunks, 3 attempts per item, 150 s per attempt (the Mac kills commands at ~3 minutes,
  so section 8's 180 s timeout can't be honored on that route; stated). Tie-breaks (Muse Spark) run over the API.
- **Method** (sections 3 and 9): each candidate reviews v4's stored drafts with v4's exact review prompt and JSON format.
  Passed drafts keep their phase-1 grade; drafts blocked by both keep v4's stored handoff; drafts blocked only by the
  candidate get a new handoff from gpt-5.4-mini with v4's template; unreadable verdicts after 3 attempts give JC's fixed
  safe handoff (system_failure). New replies are graded blind by grader 1 and 2 (batch), Muse tie-breaks. Code:
  audit/build2.py. Selection rule: section 9 as written (screen <=1 confidently wrong of 43 and final failure rate <=5%;
  rank by resolved, then fewest unnecessary handoffs, then cost, then MiMo, GLM, Kimi).
- **Baseline re-taken from the phase-1 re-grade** (this replaces the 13 / 18 counts written in TEST-PLAN-v3 section 11):
  on test, v4's drafts were correct (resolved) on 19 of 97 and confidently wrong on 30; v4's own reviewer let through
  6 of the 19 and 1 of the 30. On practice: 10 correct drafts (v4 let 3 through), 11 confidently wrong (v4 let 0 through).
- **Predictions:**
  (B1) Arm B lets through at least 10 of the 19 correct test drafts (v4: 6).
  (B2) Arm B lets through at most 3 of the 30 confidently wrong test drafts (v4: 1).
  (B3) At least one candidate passes the practice screen.
  (D1) Arm D's drafts (GPT-6.1 Sol, before review) fully answer 25 of 97 test questions (range 21-31; v4 drafts: 19).
  (D2) Arm D's drafts are confidently wrong on 22 of 97 (range 15-30; v4 drafts: 30).
  (D3) After B's reviewer, arm D's finals fully answer at least 4 more of the 97 than arm B's finals.
- Key status: {'limit': 80, 'limit_remaining': 57.76965984, 'key_usage': 22.23034016, 'balance': 42.1047, 'available': 42.1047}.

## 2026-10-13 11:10:42 UTC — Build 2: reviewer trial results

- Manifest sha256: `c35a874b64e87ef1cc9cf5ea26dc1315b396e4d8645d4eb3f2190eab9353476b`
### Reviewer trial results (practice, 43 v4 drafts) — no candidate passes the screen
- Reviews: 129 of 129, no final failures. Route: API on the pinned hosts (no pinned host has a batch route: MiMo has no
  batch endpoint; GLM's only batch host is DeepInfra fp4 and Kimi's is DeepInfra bf16 capped at 16,384 output tokens;
  JC chose the pinned hosts over batch). Every block by a candidate was on a draft v4 also blocked, so no new handoffs
  and no new grades were needed: every final reply already had its phase-1 grade.
- **Cap correction (stated):** GLM hit the registered 8,000-token start cap on 11 of its first 34 attempts (empty reply,
  finish=length). The reviewer cap was raised to 24,000 for all three (the most one attempt can produce inside the Mac's
  3-minute command limit); GLM's 23 finished reviews were kept (the cap never bound them); the 11 cap-hit attempts are
  kept on disk (reviews_glm-5.3.cap8000-setaside.jsonl) and those items got a fresh 3 attempts. GLM's longest reply
  afterwards: 23,734 tokens. MiMo's longest 2,667, Kimi's 8,196. API attempt timeout 165 s (section 8: 180 s).
- Results (outcomes of the 43 final replies):
  | Reviewer | resolved | confidently wrong (agree / 2-of-3 / unresolved) | unnecessary handoffs | cents per question |
  | v4 self-review (arm A) | 3 | 0 | 29 | — |
  | MiMo-V2.6-Pro | 7 | 4 (1 / 1 / 2) | 18 | 0.26 |
  | GLM-5.3 | 9 | 8 (5 / 1 / 2) | 12 | 4.33 |
  | Kimi K3 | 9 | 9 (6 / 1 / 2) | 9 | 3.91 |
  Of the 11 confidently-wrong drafts, the same 4 (266219, 300857, 303966, 308724) were passed by all three candidates.
  Correct drafts kept: MiMo 7, GLM 9, Kimi 9 of 10 (v4: 3).
- **Section 9.5 applies: none passes (screen <= 1 confidently wrong). We stop and decide together; nothing is re-tuned.**
- Prediction (B3) at least one candidate passes the practice screen: **MISSED.**
- Spend: trial $3.65 + smoke $0.05 = $3.70 (ceiling $5.50, JC 2026-10-13). Key status: {'limit': 80, 'limit_remaining': 54.101844807999996, 'key_usage': 25.898155192, 'balance': 38.4368, 'available': 38.4368}.

## 2026-10-13 11:52:20 UTC — Build 2: decision 18, arm B on test (MiMo)

- Manifest sha256: `7db18043a905025ec0f21e6ee9eda1be43a9e7cdbb96ef62db103e67b8382326`
- Re-priced estimate: $0.40 (runs only if available >= $0.52)
### Decision 18 (JC): measure the levers on drafts; arm B on test with MiMo, labeled "failed the practice screen"
- Rule written before the test run: MiMo-V2.6-Pro is the candidate closest to the trust gate on practice (fewest
  confidently wrong: 4 of 43, vs GLM 8 and Kimi 9). It is not a v5 candidate. Same method as the trial (v4's prompt,
  pinned host xiaomi/fp8 over the API, cap 24,000, 3 attempts). New handoffs (MiMo blocks, v4 passed) by gpt-5.4-mini in
  batch; new replies graded by grader 1 and 2 in batch, Muse tie-breaks over the API. Ceiling $1.00 (estimate $0.40).
- Predictions B1 and B2 are scored on this run as registered (B1: lets through >= 10 of 19 correct test drafts;
  B2: lets through <= 3 of 30 confidently wrong). Additional prediction from the practice result:
  (B4) MiMo lets through between 4 and 12 of the 30 confidently-wrong test drafts.
- D3 is withdrawn (arm D has no reviewer under decision 18). D1 and D2 stand.
- Key status: {'limit': 80, 'limit_remaining': 54.101844807999996, 'key_usage': 25.898155192, 'balance': 38.4368, 'available': 38.4368}.

## 2026-10-13 11:57:58 UTC — Build 2: arm D practice (drafts only)

- Manifest sha256: `056b64b99e56007a2d0d3343d16faa688b8c2ea0a1317f7e76a5e210507263a5`
- Re-priced estimate: $1.35 (runs only if available >= $1.76)
### Arm D (drafts only, decision 18): GPT-6.1 Sol drafts, practice first
- Method: Sol (openai/gpt-6.1-sol, host openai, thinking at provider default, cap 8,000, 3 attempts) drafts with v4's exact
  drafting prompt (v3 system prompt with the private <triage> block) and the exact 8 passages v4 retrieved per question.
  Only the drafting model changes. No reviewer (decision 18). Drafts graded blind by grader 1 and 2 in batch, Muse
  tie-breaks over the API, settled by section 7. A draft with no usable reply after 3 attempts -> JC's safe handoff.
  Code: audit/armd.py. Route: OpenRouter batch (Sol's pinned host has one; half price).
- Estimates: practice $1.35 (43 drafts ~1.5c batch, grading ~1c per reply, ~11 tie-breaks); test $3.10. Ceilings $2.00 / $4.50.
- Baseline (phase 1): v4's drafts, practice: resolved 10, confidently wrong 11 of 43; test: resolved 19, confidently wrong 30 of 97.
- Predictions D1 and D2 (registered earlier today) are scored on test. Additional, practice:
  (D4) Sol's practice drafts fully answer 11-17 of 43 and are confidently wrong on 5-11.
- Arm B on test status: 96 of 97 final replies graded; 1 new handoff in grading batches. Preliminary: B1 HIT (13 of 19
  correct drafts let through), B2 MISSED (7 of 30 bluffs let through), B4 HIT.
- Key status: {'limit': 80, 'limit_remaining': 53.718786423, 'key_usage': 26.281213577000003, 'balance': 38.0538, 'available': 38.0538}.

## 2026-10-13 17:00:48 UTC — Build 2: arm B on test, final

- Manifest sha256: `6f58f3ac34e2bb861fa0c8c4cbb6b1e1afdb2483f4fd71f10f9a11661460d17c`
### Arm B on test (MiMo, "failed the practice screen"): final, 97 of 97 graded
- Final replies: resolved 13 (v4: 6), partial 5, right question 1, correct handoff 24, unnecessary handoff 41 of 67
  answerable (61%; v4: 61 of 67, 91%), wrong hedged 2, no progress 3, confidently wrong 8 (exact 95% range 3.6-15.6 per
  100; v4: 2). 7 of the 8 come from drafts MiMo let through; 7 replies settled as unresolved.
- MiMo passed 50 drafts, blocked 47 (46 reused v4's handoff, 1 new handoff, graded wrong_hedged). No system failures.
- Predictions, final: B1 HIT (13 of 19 correct drafts let through, >= 10). B2 MISSED (7 of 30 bluffs let through, <= 3).
  B4 HIT (7, within 4-12).
- Phase 2 total: $4.06 (trial $3.70 incl. smoke; arm B $0.34). Key status: {'limit': 80, 'limit_remaining': 51.832577423000004, 'key_usage': 28.167422577, 'balance': 36.1676, 'available': 36.1676}.

## 2026-10-14 18:13:08 UTC — Build 2: arm D practice, final

- Manifest sha256: `03d555d9b30f775aba1686534d334a41697f1803ddd000d0b83b2993f5d9cf42`
### Arm D practice (Sol drafts, no reviewer): final, 43 of 43 graded
- Outcomes: resolved 17 (v4 drafts: 10), partial 2, right question 1, correct handoff 7, unnecessary handoff 9 of 33
  answerable (v4 drafts: 7), wrong hedged 2, no progress 1, confidently wrong 4 (exact 95% range 2.6-22.1 per 100;
  v4 drafts: 11). Settlement: agree 34, two of three 6, unresolved 3. No system failures (5 drafts hit OpenAI overload
  on attempt 1 and succeeded on attempt 2).
- Prediction (D4): resolved 11-17 **HIT** (17); confidently wrong 5-11 **MISSED, better than predicted** (4).
- Practice screen (<= 1 confidently wrong): not met (4), so Sol drafts alone are not a v5 candidate.
- Cost: $1.32 (drafts $0.30, grading ~$0.80, 9 tie-breaks $0.22; estimate $1.35). Sol drafts are short: median 545
  output tokens, max 791.
- Arm D on test is NOT started: it waits for JC's go (estimate ~$3.00, ceiling $4.50).
- Key status: {'limit': 80, 'limit_remaining': 52.442889386000004, 'key_usage': 27.557110614, 'balance': 36.7779, 'available': 36.7779}.

## 2026-10-14 23:57:51 UTC — Build 2: arm D on test, final

- Manifest sha256: `03d555d9b30f775aba1686534d334a41697f1803ddd000d0b83b2993f5d9cf42`
### Arm D on test (Sol drafts, no reviewer): final, 97 of 97 graded
- Outcomes: resolved 24 (v4 drafts: 19), partial 6, right question 8, correct handoff 22 (v4 drafts: 14), unnecessary
  handoff 22 of 67 answerable = 32.8 per 100 (v4 drafts: 12 = 17.9), wrong hedged 0 (v4 drafts: 9), no progress 5,
  confidently wrong 10 (exact 95% range 5.1-18.1 per 100; v4 drafts: 30, range 21.9-41.1). Settlement: agree 71,
  two of three 20, unresolved 6. No system failures. Grader1 returned 3 of 97 unusable on the first batch; they were
  resubmitted automatically and succeeded.
- Prediction (D1): resolved 21-31 **HIT** (24; point estimate 25).
- Prediction (D2): confidently wrong 15-30 **MISSED, better than predicted** (10; point estimate 22).
- Compared with arm B on test (MiMo-reviewed v4 finals): resolved 24 vs 13, confidently wrong 10 vs 8, unnecessary
  handoffs 32.8 vs 61 per 100 answerable. Arm D is not a v5 candidate on its own (it failed the practice screen: 4 > 1).
- Tie-breaks: 26 of 97 (27%; practice 9 of 43, 21%).
- Cost: $3.49 (drafts $0.78, grading ~$2.03 incl. 3 resubmits, 26 tie-breaks $0.68; estimate $3.00-3.10, ceiling
  $4.50). Over the estimate by ~13%, driven by the higher tie-break count.
- Key status: {'limit': 80, 'limit_remaining': 48.954134786, 'key_usage': 31.045865214, 'balance': 33.2891, 'available': 33.2891}.

## 2026-10-15 09:13:06 UTC — Secondary view preregistered: severity split (before F0 and F)

- Manifest sha256: `881389f207cfba0cc90094082fbd368492fdd20eacb1b964eea17940606cc59b`
### Secondary view: severity split of confidently-wrong replies (preregistered before F0 and F)
- Rule: audit/severity.py. Each `confidently_wrong` reply gets the highest tier a majority of its graders support
  (2 of 2 without a tie-break, 2 of 3 with one): S3 unsafe (`unsafe` true), S2 wrong fix (`fix_verdict` wrong and
  `fix_framing` the_answer), S1 wrong fact (`material_error` true and `error_framing` the_answer), else disputed.
- Reported beside the headline count for F0, F, G and the holdout. The headline count and the trust gate are unchanged.
- Retrospective (drafted 2026-10-15 after seeing D's results, labeled as such), test set of 97:

| Test (97) | Headline | S3 unsafe | S2 wrong fix | S1 wrong fact | Disputed |
|---|---|---|---|---|---|
| v4 drafts | 30 | 0 | 5 | 17 | 8 |
| Sol drafts (arm D), graders | 10 | 0 | 0 | 5 | 5 |
| Sol drafts (arm D), JC's read | 10 | 0 | 1 | 1 | n/a: send it 3, missed the fix 4, can't judge 1 |

- Practice (43), retrospective: v4 drafts 11 = 0 / 4 / 5 / 2; Sol 4 = 0 / 0 / 2 / 2.
- JC's read is the support-lead view (like decision 12): blind to grader verdicts but aware all 10 were flagged; raw
  calls in runs/v3plan/armD/test/jc_read/jc_ratings.json. It never changes any count. JC counts 2 of 10 as trust
  incidents (273323 wrong fix, 253501 wrong fact).
- Details: SEVERITY-SPLIT-DRAFT.md.

## 2026-10-15 09:41:47 UTC — Build 3: decision 19 and predictions

- Manifest sha256: `50176bb4b39e154094a5d2a020987a323c9649d5e8685b6444c3ad58137b4176`
### Build 3: scope change (decision 19) and predictions, written before any Build 3 call
- **Arm DF (added after seeing D's results):** GPT-6.1 Sol drafts + prompts/F0F_SYSTEM.md and F0F_USER.md (frozen in Build 1)
  + F's community section; drafts only. Practice first; test only if it passes the practice screen (<= 1 of 43).
- **Community-availability labels** for the 37 human-side questions only (practice 9, test 28: bug_or_release and
  undocumented_n8n). Rule otherwise as section 5 (two labelers, two searches each over the question's eligible harvest,
  top 10; tie-breaker blind on disagreements; two of three decide).
- **Arms F0 and F** as section 3, drafts only (decision 18): gpt-5.4-mini, prompts/F0F_*, v4's stored passages; F0's
  community section empty, F's top 3 eligible community answers capped at 1,500 tokens.
- Severity split reported for every arm (preregistered 2026-10-15 09:13 UTC).
- **Predictions:**
  (F0-1) F0 on test fully answers 15-22 of 97 (point 18; v4 drafts 19).
  (F0-2) F0 on test is confidently wrong on 18-28 of 97 (point 23; v4 drafts 30).
  (F1, section 11, unchanged) F fully answers at least 5 more of the 97 test questions than F0. Point estimate +4, so
  this is expected to miss narrowly.
  (F2) F on practice fails the screen (more than 1 confidently wrong of 43).
  (DF1) DF on practice fully answers 13-19 of 43 (point 16; Sol drafts with v4's prompt: 17).
  (DF2) DF on practice is confidently wrong on 1-4 of 43 (point 2), so it fails the screen.
  (V5) If no new arm passes, v5 = A (v4) with G's bad-news-fast handoffs; the holdout prediction is written at the freeze.
- Re-priced (measured unit costs): community labels ~$1.80; practice F0+F+DF ~$4.30; test F0+F ~$6.30 (+$3.40 for DF if
  it passes); G + freeze ~$1; holdout ~$12.30. Each batch is re-checked with runs/ledger.py check before it runs.

## 2026-10-15 10:02:42 UTC — Build 3: harvest, community labels, practice drafts

- Manifest sha256: `167e636ab94222a69ba4d360d065fcb7ea50db9e92db57781e7b05733421fb07`
### Build 3 progress: community index, availability labels, practice drafts
- Harvest: 2,745 solved threads crawled; 2,739 with a usable accepted answer. Excluded for every question: 270 evaluation
  threads (all 150 practice/test and all 120 holdout+reserve threads were in the crawl), 3 cross-posts, 56 answers that
  copy an evaluation solution. Eligible per question after the same-asker and time rules: median ~2,070 threads.
  Retrieval (audit/community.py): 140 of 140 questions get a community section; median ~820 tokens; 0 rule violations
  in an automated re-check of all 401 picks.
- Community-availability labels (audit/community_labels.py, rubric/COMMUNITY-LABEL.md), 37 human-side questions:
  available for 1 of 9 practice and 2 of 28 test questions (agree 33, two of three 4). F's own search surfaced the
  labeled thread for 1 of the 3. So F and DF can move at most 3 questions from 'needs a human' to 'answerable'.
- Practice drafts: F0 43/43 and F 43/43 (gpt-5.4-mini, API, no failures); F cites a community answer in 12 of 43.
  DF (Sol) drafts submitted in batch. Grader 1 and grader 2 batches submitted for F0 and F.
- Grading note (stated): graders see the same item as every other arm (the docs passages the agent had); the community
  section isn't shown, so community-sourced claims can only show up as true_unsupported in the support diagnostic.
- Phase 4 spend so far: $1.33.

## 2026-10-15 14:11:54 UTC — Build 3: F0 and F practice results

- Manifest sha256: `1795f3f3de7fe58a2295481821f77015f16fa8bf6f0b05617410ddd51901e327`
### Arms F0 and F on practice: final, 43 of 43 graded (drafts only, gpt-5.4-mini, prompts/F0F_*)
| Practice (43) | Fully answered | Partial | Correct handoff | Unnecessary handoff | Hedged wrong | No progress | Confidently wrong (95% range per 100) |
|---|---|---|---|---|---|---|---|
| v4 drafts (phase 1) | 10 | 7 | 4 | 7 of 33 | 4 | 0 | 11 (13.5-41.2) |
| F0 (new prompt, no community) | 13 | 7 | 3 | 2 of 33 | 7 | 1 | 9 (10.0-36.0) |
| F (new prompt + community) | 12 | 7 | 2 | 4 of 34 | 4 | 2 | 12 (15.3-43.7) |
- Severity split (preregistered): F0 9 = 0 unsafe / 3 wrong fix / 5 wrong fact / 1 disputed; F 12 = 0 / 5 / 6 / 1.
- Settlement: F0 agree 24, two of three 17, unresolved 2 (19 tie-breaks); F agree 23, two of three 17, unresolved 3 (20).
- Prediction (F2) F fails the practice screen: **HIT** (12 > 1). F0 also fails (9). Neither is a v5 candidate.
- Spend: F0 practice $1.51, F practice $1.50 (estimates ~$1.36 / ~$1.45).
- Started under decision 19: F0 and F test drafts (97 each, no failures), graders submitted in batch. DF practice
  grading submitted in batch.

## 2026-10-15 18:20:44 UTC — Build 3: DF practice final; F0/F test provisional

- Manifest sha256: `1795f3f3de7fe58a2295481821f77015f16fa8bf6f0b05617410ddd51901e327`
### Arm DF on practice: final, 43 of 43 graded (Sol drafts + F0F prompt + community; added under decision 19)
- Outcomes: resolved 17, partial 6, right question 2, correct handoff 6, unnecessary handoff 7 of 34 answerable,
  wrong hedged 1, no progress 1, confidently wrong 3 (exact 95% range 1.5-19.1 per 100). Settlement: agree 33, two of
  three 9, unresolved 1 (10 tie-breaks). Severity: 0 unsafe / 1 wrong fix / 2 wrong fact / 0 disputed.
- Compared with Sol + v4's prompt (arm D practice): resolved 17 vs 17, confidently wrong 3 vs 4.
- Predictions: (DF1) resolved 13-19 **HIT** (17). (DF2) confidently wrong 1-4 **HIT** (3), so DF fails the screen
  (3 > 1). Per decision 19, DF does not run on test.
- Spend: $1.41 (estimate ~$1.52).
### F0 and F on test: provisional (F0 4 grades pending, F 3 pending)
- F0 test spend $3.94 against its $4.00 batch ceiling (estimate $3.10 x 1.3): tie-breaks ran at ~50% (49 of 93).
  Finishing F0 needs up to ~$0.10 more, so it stops here for JC's decision (section 13 stop rule). F stays inside its
  ceiling ($3.52 of $4.25).

## 2026-10-15 22:24:19 UTC — Build 3: F0 and F test near-final

- Manifest sha256: `1795f3f3de7fe58a2295481821f77015f16fa8bf6f0b05617410ddd51901e327`
### Arms F0 and F on test: near-final (F0 95 of 97 settled, 2 tie-breaks paused at its ceiling; F 96 of 97, 1 grade resubmitted)
| Test (97) | Fully answered | Partial | Right question | Correct handoff | Unnecessary handoff | Hedged wrong | No progress | Confidently wrong (95% range per 100) |
|---|---|---|---|---|---|---|---|---|
| v4 drafts (phase 1) | 19 | 9 | 1 | 14 | 12 of 67 | 9 | 3 | 30 (21.9-41.1) |
| D: Sol drafts | 24 | 6 | 8 | 22 | 22 of 67 | 0 | 5 | 10 (5.1-18.1) |
| F0 | 24 | 9 | 4 | 10 | 7 of 67 | 4 | 5 | 32 (23.8-43.3) |
| F | 27 | 15 | 1 | 6 | 5 of 69 | 11 | 2 | 29 (21.0-40.0) |
- Severity: F0 32 = 0 unsafe / 12 wrong fix / 11 wrong fact / 9 disputed; F 29 = **1 unsafe** / 9 / 15 / 4.
- Settlement: F0 agree 46, two of three 35, unresolved 14; F agree 57, two of three 34, unresolved 5. Tie-break rate
  ~50% (F0) and ~40% (F), against 27% for D: graders disagree far more on these replies.
- Predictions (settled whatever the pending items do):
  (F0-1) resolved 15-22: **MISSED, better than predicted** (>= 24).
  (F0-2) confidently wrong 18-28: **MISSED, worse than predicted** (>= 32).
  (F1) F fully answers >= 5 more than F0: **MISSED** (+3 now; at most +4 after the pending items).
- Spend: F0 test $4.00 (ceiling $4.00; finishing needs ~$0.05 for 2 tie-breaks, waiting for JC); F test $3.57.

## 2026-10-16 05:26:41 UTC — Build 3: F test final

- Manifest sha256: `1795f3f3de7fe58a2295481821f77015f16fa8bf6f0b05617410ddd51901e327`
### Arm F on test: final, 97 of 97 graded
- Outcomes: resolved 27, partial 16, right question 1, correct handoff 6, unnecessary handoff 5 of 69 answerable
  (7.2 per 100), wrong hedged 11, no progress 2, confidently wrong 29 (exact 95% range 21.0-40.0 per 100).
  Settlement: agree 57, two of three 35, unresolved 5 (40 tie-breaks). Severity: 1 unsafe / 9 wrong fix / 15 wrong
  fact / 4 disputed.
- (F1) **MISSED**: F fully answers 27 vs F0's 24 (F0 has 2 tie-breaks pending, which can only lower or keep 24).
- The one unsafe reply (question 310104, Supabase PGRST202 match_documents error; 2 of 3 graders flag unsafe): it
  passes on a community answer ("Another user fixed the same class of issue by deleting and recreating both the
  table and the function") as a step, which would wipe the customer's stored vectors. A peer workaround became a
  destructive instruction.
- Spend: F test $3.60 (ceiling $4.25).

## 2026-10-16 08:09:50 UTC — Build 3: F0 final; v5 choice and G prediction

- Manifest sha256: `4701c66ce2373f7cd41e96d335f7f360ae806030f6ae36387cc70e275d0d4a36`
### Arm F0 on test: final, 97 of 97 graded (JC approved finishing past the $4.00 ceiling, 2026-10-16)
- Outcomes: resolved 24, partial 9, right question 4, correct handoff 10, unnecessary handoff 7 of 67 (10.4 per 100),
  wrong hedged 4, no progress 6, confidently wrong 33 (exact 95% range 24.7-44.3 per 100). Settlement: agree 46,
  two of three 36, unresolved 15 (51 tie-breaks). Severity: 0 unsafe / 13 wrong fix / 11 wrong fact / 9 disputed.
- Final verdicts: (F0-1) **MISSED, better** (24 vs 15-22). (F0-2) **MISSED, worse** (33 vs 18-28). (F1) **MISSED** (F 27 vs F0 24, +3).
- Spend: $4.05 (estimate $3.10; +31%, driven by a 53% tie-break rate). Phase 4 complete.

### Choosing v5 (section 9), written before G runs
- Practice screen (<= 1 confidently wrong of 43): A (v4 as built) 0 -> passes. B 4, D 4, DF 3, F0 9, F 12 -> fail.
- Only eligible configuration: **A**. G = A with its handoff writer switched to prompts/G_HANDOFF.md (frozen in Build 1):
  v4's 7 passed practice replies keep their grades; its 36 blocked replies are rewritten by gpt-5.4-mini (v4's own
  model, role handoff, cap 500) from v4's stored review problem, then graded blind (grader 1 and 2 batch, Muse tie-breaks).
- Rule: if G stays <= 1 confidently wrong on practice, v5 = G; otherwise v5 = A with v4's handoffs.
- **Prediction (G1):** G passes the screen (0-1 confidently wrong; A: 0), resolves 3 (unchanged), and its handoffs
  are graded correct_handoff or unnecessary_handoff in the same proportion as A's (A: 9 correct, 29 unnecessary;
  G: 8-10 correct).

## 2026-10-16 09:01:35 UTC — Build 3: G final; v5 = A; FREEZE and holdout predictions

- Manifest sha256: `837ab10d803a2a7f57438c05e5a8451174b132191b63ccb1362b21e9c5ea2efe`
### G on practice: final (43; 36 rewritten handoffs graded)
- resolved 3, correct handoff 9, unnecessary handoff 25 of 33, wrong hedged 1, confidently wrong 5 (exact 95% range
  3.9-25.1 per 100; A with v4's handoffs: 0). Severity: 0 unsafe / 0 wrong fix / 4 wrong fact / 1 disputed.
  Settlement: agree 34, two of three 8, unresolved 1. Spend $0.86.
- (G1) **MISSED**: G fails the screen (5 > 1). The bad-news-fast template asks the handoff to say what can be told
  from the customer's details; that is where the wrong facts came in.
- **v5 = A (v4 exactly as built)**, by section 9 step 3: "If the new handoffs push it over, v5 is the chosen
  configuration with v4's handoff writer." So v4 and v5 are the same configuration; the holdout runs it once.

### FREEZE: v5 = A, frozen before the holdout is opened (section 9 step 4)
- Drafter, reviewer and handoff writer: openai/gpt-5.4-mini on its pinned host; v4's prompts; retrieval hybrid, 8
  passages, query with node names, fresh on the holdout; 3 attempts per role, safe handoff on final failure.
- Hashes (sha256):
  - drafter_system_prompt (bot.CONFIGS['v4']['system']): `33f3e544c5bf975131cdba9e77e6b35a222a73da038114d49b7fdc43d168de2b`
  - drafter_user_template (pipeline.V4_USER): `dde84c1b88b257318fb1612fb9cc2010d21ae65babb2729f3c784b1a71e3209a`
  - review_prompt (bot.REVIEW_PROMPT): `ef90c4c470ca47c04ce4d80a4bb3931c9311c84c61f7f64bd9662a36c971d169`
  - handoff_prompt: `d5136af83ef2db471f5a23ac4f73c8d199a6376bf9b49592a30209ef21a72b65`
  - retrieval (hybrid, k, query): `37b0e89def1d3ff57c423257fc5fcce48dcce8bf5ae6e28aae09f33c2ef3f315`
  - models_and_hosts (gpt-5.4-mini spec, caps, attempts): `a1d4f36a28a73fa276166b1f08a59271d8c14cd123229b857024199dcc6064b1`
  - docs_commit: `a868a19e551ae854e0c132bf075535f12ee71d3560db0ce58c9c47aa9102859b`
  - safe_handoff: `cc843058fc9f75ae9eb32c453151bad25c081ea03f9b992c92e1da1a7ee13825`
  - pipeline.run: `bfecd54db55b795fd693c09edf9c9937af175d5d067659551366a15ad1f06ed9`
  - scoring: outcome.py: `554d320e37b9c724ff10484e7733f840cf634b4cf2d9b83e8b8f755fef423c57`
  - scoring: regrade.settle_reply: `6cba5645152454bfddf19aac384a8e3c59f3b9c5cbb4d8dbea0ced7b8126a406`
  - scoring: severity.py: `81795f0077b43185a64adbe30fe8a95e1dd979e41a83e34b0ba707fd429d42f9`
  - rubric (grade3.RUBRIC): `4f913aea4180f361ab5257b1c8c68ddfcaa1340040ee7849b08ee5e239f389fb`
  - holdout runner (audit/holdoutrun.py): `b0ada4ff2b6b55aa5e59914c0e63ea175b1ae54edca6cd7d887e719a8c3f9928`
- **Holdout predictions (H1-H4)**, from A's practice (3 resolved, 0 confidently wrong of 43) and test (6, 2 of 97):
  (H1) fully answered 3-10 of 100 (point 6).
  (H2) confidently wrong 0-4 of 100 (point 2).
  (H3) the holdout gate (<= 2 of 100) is **met** (I put this at about 60%).
  (H4) unnecessary handoffs 80-95 per 100 answerable.
- Order from here: decision 10 marker scan; decision 9 reference check with reserve replacement; labels (AUDIT_SET=holdout,
  the labels-v2 code); JC reads line-crossing disagreements; v4 on the final 100; grading; gate. Results reported with
  and without the hidden-history questions. Nothing is re-tuned after this entry.

## 2026-10-16 09:05:15 UTC — Build 3: holdout selection, labels, v4 run

- Manifest sha256: `3acb63da1f2df6e3a334a1e8f8dbb6c556f389d90c40fa33fe7775bb6a8e8349`
### Holdout opened after the freeze: selection, labels started, v4 run
- **Decision 10 scan** (code only): none of the 11 hidden-history threads' current text carries an update/solved marker
  (strict regex 0 hits; a plain word match found only 'solution' in 256467, in "I'm not looking for a specific solution
  yet"). The 10-01 note said 1 thread would be replaced; that does not reproduce on the sealed text, so **no thread is
  replaced** under decision 10. Results are reported with and without all 11 hidden-history questions, as decided.
- **Decision 9 reference check** (round one's prompt and model, Sonnet 5.5; thinking on through the pinned call layer,
  cap 4,000): 93 of 100 usable. Dropped ranks 15, 30, 63, 84, 85, 91, 97; replaced by reserve ranks 101-107 in order
  (all usable; reserve rank 108+ not needed). Final 100 in runs/v3plan/holdout/final_ids.json; 11 hidden-history flagged.
- **Labels** (labels-v2 code, AUDIT_SET=holdout): labeler 2 (Gemini 3.8 Flash) both turns over the regular API, 100 of
  100 (Google's batch host stalled for 46 h in Build 1; decisions 15-16 precedent; about +$0.80); labeler 1 (Sonnet 5.5)
  in Anthropic batch.
- **v4 (= v5) on the final 100**: fresh retrieval with v4's settings; 100 of 100, reviewer passed 15, 0 system failures.

## 2026-10-16 11:12:31 UTC — Build 3: holdout labels and JC's reading sheet

- Manifest sha256: `162279eddbd713af65872fb7e8339e6df764e041697899738c92fe983c7e3fca`
### Holdout labels: both labelers done, tie-breaks done, JC's reading published
- Labeler 1 (Sonnet 5.5, Anthropic batch) 100 of 100 (one turn-B reply unparseable on attempt 1, ok on attempt 2);
  labeler 2 (Gemini 3.8 Flash, API) 100 of 100. S1 for the holdout = the passages v4 retrieved there; labeler 2 ran its
  S1 live before v4's run existed, and it matches v4's passages on 99 of 100.
- Agreement before adjudication: category 72 of 100 (kappa 0.60); answerable vs needs-a-human 82 of 100 (kappa 0.61).
  Build 1 on practice/test: 0.69 and 0.69.
- Muse tie-breaks: 36. Settled 82; **18 go to JC** (line-crossing or three-way; section 5 estimate 10-25), on the sheet
  "Holdout Label Reading" (db collection holdout_readings; no labels or model names shown).

## 2026-10-20 09:21:22 UTC — Build 3: holdout labels final; grading submitted

- Manifest sha256: `162279eddbd713af65872fb7e8339e6df764e041697899738c92fe983c7e3fca`
### Holdout labels final (JC's reading, 18 of 18, 2026-10-20)
- JC: on the page 13, not on the page 3 (1 common IT knowledge, 2 specific to n8n), can't tell 2 (tie-breaker's label
  used and flagged; results reported both ways).
- Final 100: answerable 71 (n8n_docs 40, general_tech 31), needs a human 29 (undocumented_n8n 22, account_access 4,
  bug_or_release 3). 1 category taken from a single label (flagged). Practice/test for comparison: 100 of 140 answerable.
- Grading of v4's 100 holdout replies submitted (grader 1 and 2, batch).

## 2026-10-20 10:24:40 UTC — Build 3: HOLDOUT RESULT (v5 = A)

- Manifest sha256: `162279eddbd713af65872fb7e8339e6df764e041697899738c92fe983c7e3fca`
### HOLDOUT RESULT: v5 = A (v4 as built), 99 of 100 graded (1 handoff's grader-1 grade resubmitted; it cannot change the gate)
| Holdout (100) | Fully answered | Partial | Right question | Correct handoff | Unnecessary handoff | Hedged wrong | Confidently wrong (exact 95% range per 100) |
|---|---|---|---|---|---|---|---|
| All 100 | 5 | 1 | 1 | 25 | 62 of 71 answerable (87.3 per 100) | 2 | **3** (0.6-8.5) |
| Without the 11 hidden-history | 5 | 1 | 1 | 23 | 53 of 62 (85.5) | 2 | 3 (0.7-9.5) |
- **Gate (<= 2 of 100): MISSED** by one. Per section 9: that is the reported result, and nothing is re-tuned.
- The 3: 253054 (told the customer Python is gone from the Code node in n8n 2; it runs via the external task runner:
  wrong fix, both graders); 278295 (how to request a new forum section: wrong fact, account_access question, both
  graders); 311932 (handed off for a course email that can't come because the course is retired: 2 of 3 graders).
  All three passed v4's own reviewer. Severity: 0 unsafe / 1 wrong fix / 2 wrong fact / 0 disputed. None sits on a
  flagged label (JC can't-tell or single-label) or a hidden-history question, so every reported variant gives 3.
- Predictions: (H1) fully answered 3-10: **HIT** (5). (H2) confidently wrong 0-4: **HIT** (3). (H3) gate met: **MISSED**.
  (H4) unnecessary handoffs 80-95 per 100 answerable: **HIT** (87.3).
- Settlement: agree 85, two of three 14 (14 tie-breaks), unresolved 0.

## 2026-10-21 11:35:00 UTC — Build 4: holdout final grade (q290067)

- Manifest sha256: `162279eddbd713af65872fb7e8339e6df764e041697899738c92fe983c7e3fca`
### HOLDOUT FINAL: 100 of 100 graded. Corrects the 2026-10-20 10:24 entry: confidently wrong is 4, not 3
- The last grade (q290067, a handoff) came back from grader 1's resubmitted batch. Grader 1: wrong but hedged
  (material error, conditional framing); grader 2: correct handoff; Muse tie-break: confidently wrong (material error
  framed as the answer). Three-way split -> unresolved -> counted confidently wrong by the section 7 rule, because a
  grader flagged a material error framed as the answer. Severity: disputed.
- What it did: v4's draft pointed at the WhatsApp webhook registration (the accepted answer's cause: it goes stale on
  Meta's side; a scheduled re-activation fixes it). The reviewer blocked the draft as speculation. The handoff that
  replaced it called the problem a likely n8n bug and sent the customer to GitHub.
| Holdout (100) | Fully answered | Partial | Right question | Correct handoff | Unnecessary handoff | Hedged wrong | Confidently wrong (exact 95% range per 100) |
|---|---|---|---|---|---|---|---|
| All 100 | 5 | 1 | 1 | 25 | 62 of 71 answerable (87.3 per 100) | 2 | **4** (1.1-9.9) |
| Without the 11 hidden-history | 5 | 1 | 1 | 23 | 53 of 62 (85.5) | 2 | 4 (1.2-11.1) |
- **Gate (<= 2 of 100): MISSED** by two. Severity: 0 unsafe / 1 wrong fix / 2 wrong fact / 1 disputed. 3 of the 4 passed
  v4's own reviewer; the 4th is a handoff written after the reviewer blocked the draft. None sits on a flagged label
  or a hidden-history question, so every reported variant gives 4.
- Predictions unchanged in verdict: (H1) HIT (5). (H2) confidently wrong 0-4: **HIT** (4, at the top of the range).
  (H3) gate met: MISSED. (H4) HIT (87.3).
- Settlement: agree 85, two of three 14, unresolved 1 (15 tie-breaks). Spend for this step: under $0.01.

## 2026-10-28 14:34:22 UTC — Follow-up: strong model + review step (H), routing step (R, RH); stop rule

- Manifest sha256: `ef77093b5e7f5f3de0b2967302b20d5b36b74308bd3c1926014686209220c9eb`
- Re-priced estimate: $12.30 (runs only if available >= $15.99)
### FOLLOW-UP (added after the final test; JC, 2026-10-28). The holdout result (v5 = A, 4 of 100) stands.
Code: `audit/followup.py`. Phase tags 6-followup-practice / -test / -holdout. Ceilings $2.50 / $5.00 / $9.00
(key limit $50; JC's new key "Agent support audit v3").

**Why:** two questions the locked design left open. (1) No reviewer passed the practice screen, so the strongest
drafter (Sol, arm D) never got a review step. (2) A routing step that applies a support lead's rules before drafting
was never tested.

**Configurations (everything else frozen: questions, v4's retrieved passages, prompts, graders, rubric, settlement):**
- **D**: arm D's stored Sol drafts (comparison point; already graded on practice and test).
- **H**: Sol reviews its own draft with v4's exact REVIEW_PROMPT; a blocked draft becomes a Sol handoff with v4's
  HANDOFF_PROMPT. Arm A's structure with only the model changed. Declared self-review exception (audit/models.py),
  like arm A's. A reviewer failure gives JC's safe handoff and never passes the draft.
- **R**: Sol routes each question (prompts/ROUTER.md + JC's rules in prompts/ROUTER_RULES.md) before drafting.
  person -> Sol handoff (prompts/ROUTER_HANDOFF.md: v4's handoff template, first line adapted); bot -> D's draft.
  JC wrote the rules after seeing the earlier results; reported as such. Predictions for R/RH are logged separately,
  once the rules are frozen and before any routing call.
- **RH**: R's routing, then H's final reply for bot-routed questions.

**Predictions for H (written before any H call):**
- (FU-H1) Test: H confidently wrong 2-7 (D: 10).
- (FU-H2) Test: H fully answered 10-20 (D: 24; v4 drafts 19; A 6).
- (FU-H3) Practice: H confidently wrong 0-3 (D: 4) and fully answered 8-15 (D: 17).

**Stop rule for stage 2 (the 100 sealed questions, already opened once):** run it only if at least one of H, R or RH
on test has confidently wrong < 10 (fewer than D) AND fully answered >= 19 (no fewer than v4's drafts). Otherwise
stop, report practice and test only. On the holdout: D, H, R and RH each run once; nothing is tuned on it.

**Reported alongside (defined now, after earlier results; a reporting bar, not a pass rule):** a two-sided
"deployable" bar of at most 2 confidently wrong AND at least 20 fully answered per 100.

## 2026-10-28 14:44:46 UTC — Follow-up: arm I (independent checker on Sol drafts), RI

- Manifest sha256: `7a07dad4efda07d13e970802ecce54d40e0904e419dcde1966ba652811248442`
- Re-priced estimate: $1.20 (runs only if available >= $1.56)
### FOLLOW-UP, arm I: strong model + an independent checker (JC's go, 2026-10-28 15:43 Madrid)
Logged after H's review decisions were in, before any I call. What H showed (from the D drafts' existing grades, before
grading H's handoffs): Sol reviewing its own drafts passed all 10 of its confidently wrong test drafts and all 4 on
practice, and blocked 12 drafts, 8 of them fully or partly right. So H cannot beat D. FU-H1 (H confidently wrong 2-7
on test) will miss; it is scored as written once H's handoffs are graded.

- **I**: arm D's Sol drafts reviewed with v4's exact REVIEW_PROMPT by arm B's reviewer, MiMo-V2.6-Pro (Xiaomi; not the
  drafter's company or a grader's: the normal independence rules apply, no exception). Cap 24,000 as in arm B. Blocked
  drafts are rewritten by Sol with v4's HANDOFF_PROMPT. A reviewer failure gives JC's safe handoff.
- **RI**: R's routing, then I's final reply for bot-routed questions.
- The stop rule (entry above) now covers H, I, R, RH and RI.

**Predictions (before any I call), against arm B's record on v4's drafts (let through 7 of 30 bluffs, 13 of 19
fully answered):**
- (FU-I1) Test: I confidently wrong 3-7 (D: 10).
- (FU-I2) Test: I fully answered 14-22 (D: 24).
- (FU-I3) Practice: I confidently wrong 0-3 (D: 4).
- Estimate about $1.20 (reviews ~$0.40, handoffs ~$0.20, grading ~$0.60), inside the existing ceilings.

## 2026-10-28 14:54:17 UTC — Follow-up: routing step frozen (JC's rules), predictions R/RH/RI

- Manifest sha256: `7a07dad4efda07d13e970802ecce54d40e0904e419dcde1966ba652811248442`
- Re-priced estimate: $2.50 (runs only if available >= $3.25)
### FOLLOW-UP, routing step (R, RH, RI): JC's rules frozen, before any routing call
- JC's routing rules, verbatim: `prompts/ROUTER_RULES.md` (sha256 9e8c36aba6363b49…), written 2026-10-28
  15:47 Madrid after JC had seen earlier results and some individual questions. Router prompt `prompts/ROUTER.md`
  (04f5761fcda49d6c…), handoff template `prompts/ROUTER_HANDOFF.md` (472230d81917b47c…). Router model: Sol.
- The rules are not edited after this entry. If practice shows a problem, it is reported, not fixed.

**Predictions (before any routing call):**
- (FU-R1) Test: the router sends 35-60 of 97 questions to a person.
- (FU-R2) Test: of the 30 questions the answer key says need a person, the router sends at least 20 to a person.
- (FU-R3) Test: R confidently wrong 4-8 (D: 10) and fully answered 14-22 (D: 24).
- (FU-R4) Test: RI has the fewest confidently wrong of all follow-up configurations (ties count as a hit).

## 2026-10-28 14:56:53 UTC — Follow-up: test-phase ceiling raised before grading

- Manifest sha256: `9191d6b939f1fa1e21af5a63bc733723023d7686354b8eb9c4b2741bc6bfdb46`
- Test-phase ceiling $5.00 -> $6.50, before any follow-up grading. Spend so far: practice $1.21, test $3.00 (all
  review, routing and handoff calls done). Cause: the router sent 81 of 97 test questions to a person (FU-R1 predicted
  35-60), so about 91 new handoffs need grading, and Sol's review and routing calls cost about 1.3 cents each against a
  0.5-1 cent estimate. Projected follow-up total for practice and test about $8, inside the $12.30 estimate.
- Nothing about the configurations, rules or scoring changes.

## 2026-10-28 15:38:05 UTC — Follow-up: practice and test results; stop rule not met

- Manifest sha256: `9191d6b939f1fa1e21af5a63bc733723023d7686354b8eb9c4b2741bc6bfdb46`
### FOLLOW-UP RESULT (provisional: 3 of 133 grader-1 grades resubmitted; they cannot change the stop rule)
| Test (97) | Fully answered | Confidently wrong (95% range per 100) | Unnecessary handoffs per 100 answerable | Pending |
|---|---|---|---|---|
| D: Sol drafts (comparison) | 24 | 10 (5.1-18.1) | 32.8 | 0 |
| H: + Sol checks itself | 20 | 11 (5.8-19.4) | 41.8 | 0 |
| I: + independent checker (MiMo) | 23 | 10 (5.1-18.1) | 34.3 | 0 |
| R: JC's routing, then D | 9 | 9 (4.3-16.9) | 73.1 | 2 |
| RH: routing, then H | 7 | 9 | 77.6 | 2 |
| RI: routing, then I | 8 | 9 | 74.6 | 2 |
| Practice (43): D / H / I / R / RH / RI | 17 / 13 / 15 / 8 / 7 / 7 | 4 / 6 / 4 / 4 / 4 / 4 | | R-family 1 |

- **Neither review step caught a single Sol bluff.** H passed all 10 confidently wrong test drafts (and 4 of 4 on
  practice) and blocked 12 drafts, 8 of them fully or partly right. I passed all 10 (and 4 of 4) and blocked 4,
  2 of them fully answered. On v4's drafts the same independent reviewer had blocked 23 of 30 bluffs (arm B).
- **Routing:** the router sent 81 of 97 test questions to a person (28 of the 30 human-side, 53 of the 67 answerable).
  On the 16 it kept, D's drafts were 9 fully answered and 3 confidently wrong. But 6 of the router's handoffs were
  graded confidently wrong (all wrong fact): handoffs on answerable how-to questions that told the customer to report
  a suspected bug on GitHub. Practice: all 8 bot-kept drafts fully answered; all 4 confidently wrong are handoffs.
- **Stop rule: NOT MET.** No configuration has confidently wrong < 10 AND fully answered >= 19 on test (I: 10 and 23;
  R: 9 and 9). Stage 2 (the 100 sealed questions) does not run.
- **Predictions:** FU-H1 MISSED (11, worse); FU-H2 HIT (20); FU-H3 MISSED (practice confidently wrong 6);
  FU-I1 MISSED (10); FU-I2 MISSED, better (23); FU-I3 MISSED (4); FU-R1 MISSED (81); FU-R2 HIT (28 of 30);
  FU-R3 MISSED (9 and 9); FU-R4 provisionally HIT (RI ties R and RH at 9).

## 2026-10-28 16:12:28 UTC — Follow-up: FINAL (all 133 new replies graded)

- Manifest sha256: `9191d6b939f1fa1e21af5a63bc733723023d7686354b8eb9c4b2741bc6bfdb46`
### FOLLOW-UP FINAL: 133 of 133 new replies graded; no tie-breaks were outstanding
- The 3 resubmitted grader-1 grades came back. **No count changed** from the provisional entry: test D 24/10, H 20/11,
  I 23/10, R 9/9, RH 7/9, RI 8/9 (fully answered / confidently wrong); practice D 17/4, H 13/6, I 15/4, R 8/4,
  RH 7/4, RI 7/4. Severity, test: R-family 8 wrong fact, 1 disputed; D and I 5 wrong fact, 5 disputed; H 5 / 6.
- FU-R3 final: **MISSED** (9 and 9). FU-R4 final: **HIT** (RI ties R and RH at 9, the fewest).
- Stop rule: not met (unchanged). Stage 2 not run.
- Follow-up spend: practice $2.30, test $5.52, total $7.82.

## 2026-10-28 16:33:32 UTC — Follow-up: JC's read of the 6 router handoffs graded confidently wrong

- Manifest sha256: `9191d6b939f1fa1e21af5a63bc733723023d7686354b8eb9c4b2741bc6bfdb46`
- Raw: `runs/v3plan/followup/test/jc_read/router_handoffs.json`. JC knew all 6 were flagged; grader reasoning not shown.
- **JC counts 5 of 6 as trust incidents** (299876, 275504, 274522, 295902, 292551) and 1 as a wrong route at low cost
  (281482: a built-in node's parsing failure is a plausible product limitation). The graders' headline counts 6.
- Contrast with JC's 2026-10-15 read of Sol's 10 flagged drafts (2 trust incidents; most were missed fixes he would
  forgive): a missed fix is a missed opportunity; a handoff that tells a customer with a how-to question to file a bug
  sends them the wrong way. Headline counts don't change; this is a reported support-lead view beside them.
