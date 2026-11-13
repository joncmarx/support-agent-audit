# Grading rubric

The grader reads the customer's question, the accepted answer from the forum (the reference), the handoff label, the doc passages the bot was given, and the bot's reply. It grades the reply the way a support lead reviews an agent's ticket.

## 1. Outcome (exactly one)

| Outcome | Use it when |
|---|---|
| `resolved` | The reply reaches the same fix as the reference, or a different fix that would clearly also work, and the customer could act on it without further help. |
| `partial` | The reply points the right way but misses a step or detail the customer needs, so they would likely have to come back. |
| `right_question` | The reply does not give a fix, but asks for the specific missing fact that the reference's fix depended on (for example the n8n version, cloud vs self-hosted, or the exact error). Generic "can you share more details?" does not count. |
| `correct_handoff` | The question is labeled `handoff`, and the reply clearly says it can't solve this and routes the customer to a human (support, the forum, a bug report), without giving wrong instructions along the way. |
| `unnecessary_handoff` | The question is labeled `docs`, and the reply routes the customer to a human instead of answering, even though the docs contain the fix. |
| `confidently_wrong` | The reply presents a fix or explanation as correct, and it is wrong, would not solve the problem, or relies on invented features, settings, nodes or steps. It does not hand off. This is the answer that burns trust. |

Tie-breaks:
- A reply that gives a wrong fix *and* then suggests contacting support is `confidently_wrong` if the wrong fix is presented as the answer, and `correct_handoff`/`unnecessary_handoff` only if the handoff is the main message and any suggestions are clearly framed as unverified.
- A reply that is right but also contains a harmful or invented instruction is at best `partial`.
- If the reference itself looks wrong or outdated compared with the docs, grade against the docs and set `reference_doubt: true`.

## 2. Diagnostics (the Confidence Equation)

Customer Confidence = (Competence × Reliability × Empathy) / Uncertainty — *The Modern CSM*, Chapter 1.

| Score | Question | Scale |
|---|---|---|
| `competence` | Does the reply solve the problem the customer actually has? | 0 = no, 1 = partly, 2 = yes |
| `reliability` | Is every factual claim backed by the doc passages given, or by widely established technical fact? Are there invented nodes, parameters, settings, UI paths or version claims? | `pass` / `fail`, plus a list of unsupported claims |
| `empathy` | Does it answer what the customer meant (not just what they typed), acknowledge their situation briefly, and end with a clear next step? No filler. | 0 = misses the point, 1 = adequate, 2 = reads like a strong human agent |

Uncertainty is the denominator. The `right_question` and handoff outcomes measure how the reply handles it: a strong agent says what it knows, what it doesn't, and what happens next (*bad news fast*, Chapter 4).

## 3. Output

JSON only:
```json
{"outcome": "...", "competence": 0, "reliability": "pass", "unsupported_claims": [], "empathy": 0,
 "handoff_detected": false, "reference_doubt": false, "rationale": "two or three sentences"}
```
