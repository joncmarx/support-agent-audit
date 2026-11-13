# Build 1, step 5: $0 checks (2026-09-30)

## Edited questions (34 of 140 first posts edited after posting)
| Group | Count | What it means |
|---|---|---|
| Tag or category change only (mostly the forum's own auto-tagger); title and text unchanged | 20 | No effect on what the bot saw |
| Text changed, no solution content | 4 | Formatting (1); forum machine translation of a German post (1); asker added diagnostic output (2) |
| Edit history hidden by forum moderators | 10 | Can't compare. Current text shows no solution content; one (287340) is flagged as a possible hint |
| Confirmed solution leaks | 0 | |

Round one's "4 contain words like solved or update" came from original text (for example "fixed income", "partially updated state", SQL UPDATE), not from edits.
Reporting rule: practice/test results are reported with and without the flagged question, and with and without the 10 unverifiable ones.

## Did the fix passage reach the bot? (30 docs-answerable test questions, round-one labels)
| Result | Count | How it was judged |
|---|---|---|
| Yes | 21 | 17: the evidence passage that best matches the key fix (keyword search) was among v4's 8 passages; 4: Claude read the key fix against the evidence-page passages the bot had |
| Partly | 3 | The bot had part of the fix (for example the Form Ending passage but not the binary-buffer one) |
| No | 6 | 3: the evidence page was never retrieved; 3: the page was retrieved but not the passage with the fix |

Preliminary: round-one labels recorded evidence pages, not passages. Labels v2 record passages, and this check is recomputed mechanically from them at $0.
