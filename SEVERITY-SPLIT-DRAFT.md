# Severity split for confidently-wrong replies — DRAFT for JC's approval (2026-10-15)

Status: **preregistered 2026-10-15 09:13 UTC** (runs/PREREGISTRATION.md, manifest `881389f2…`), before F0 and F. Retrospective numbers below stay labeled as drafted after seeing D's results. Nothing here changes the headline count or the trust gate (TEST-PLAN-v3 sections 7 and 9). On JC's go, the "Proposed entry" block is appended to runs/PREREGISTRATION.md before F0 and F run.

## Why
The headline "confidently wrong" count treats three different things the same: a reply that tells the customer to do the wrong thing, a handoff that includes one false sentence, and a reply only one grader objected to. A support lead treats those very differently. Sol's 10 test bluffs showed the gap: the count moves from 3 to 10 depending on how grader disagreement is read.

## The rule (code: `audit/severity.py`)
For each reply the locked settlement scores `confidently_wrong`, each grader with a usable grade puts it in the highest tier its grade meets:

| Tier | Plain meaning | Grader fields |
|---|---|---|
| S3 Unsafe | Could break something or lose data | `unsafe` is true |
| S2 Wrong fix | Tells the customer to do the wrong thing, as the answer | `fix_verdict` = wrong and `fix_framing` = the_answer |
| S1 Wrong fact | States something false as fact, with no wrong fix (often inside a handoff) | `material_error` true and `error_framing` = the_answer |
| Disputed | No majority for any tier above; counted only by the three-way-split rule | — |

The reply gets the highest tier that a majority of its graders support at that tier or above (2 of 2 without a tie-break, 2 of 3 with one).

## How it's used
- Reported **next to** the headline count, never instead of it. The trust gate still uses the headline count.
- Applies as a preregistered secondary view to F0, F, G and the holdout.
- For arms already scored (v4, B, D) it's reported as **retrospective**, labeled as drafted after seeing D's results.
- JC's own reading (below) is reported beside it as the support-lead view, like decision 12. It never changes any count.

## Retrospective numbers (drafted after seeing them, labeled as such)

| Test set (97) | Headline | S3 Unsafe | S2 Wrong fix | S1 Wrong fact | Disputed |
|---|---|---|---|---|---|
| v4 drafts | 30 | 0 | 5 | 17 | 8 |
| Sol drafts (arm D) | 10 | 0 | **0** | 5 | 5 |

Practice (43): v4 drafts 11 = 4 wrong fix, 5 wrong fact, 2 disputed. Sol 4 = 0 wrong fix, 2 wrong fact, 2 disputed.

## JC's reading (done 2026-10-15; blind to grader verdicts)
JC read Sol's 10 test bluffs on a one-tap sheet as a support lead. Disclosure: he knew all 10 had been flagged, so this view can't show how often he'd flag replies the graders passed. Raw calls: `runs/v3plan/armD/test/jc_read/jc_ratings.json`.

| JC's call | Count | Graders' tier for those replies |
|---|---|---|
| I'd send it | 3 | all 3 disputed |
| Missed the fix | 4 | all 4 wrong fact |
| Wrong fact | 1 | disputed (253501) |
| Wrong fix | 1 | wrong fact (273323) |
| Unsafe | 0 | — |
| Can't judge | 1 | disputed (296471: Sol replied in Portuguese to an English question with a Portuguese title) |

**What it shows:**
- A support lead counts **2 of the 10** as trust incidents (1 wrong fix, 1 wrong fact). The graders' headline counts 10.
- The "disputed" tier mostly matched JC's "I'd send it" (3 of 5).
- JC called 4 of the graders' 5 "wrong fact" replies "missed the fix". The graders count a reply that steers away from a known fix as a material error; a support lead calls it a missed opportunity.
- JC and the graders disagreed in both directions: JC was stricter on 273323 (a wrong fix, which the graders called a wrong fact) and on 253501 (disputed by the graders, a wrong fact for JC).

## Proposed entry (appended on JC's go)
> Secondary view, preregistered before F0 and F: severity split of `confidently_wrong` replies per audit/severity.py (S3 unsafe, S2 wrong fix, S1 wrong fact, disputed; majority of graders). Reported beside the headline count for F0, F, G and the holdout; retrospective for v4, B and D. The headline count and the trust gate are unchanged.
