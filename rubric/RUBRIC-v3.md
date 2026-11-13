# Grading rubric v3 (Test Plan v3, section 6)

You are grading one reply that a support agent sent to a customer of n8n, the workflow automation platform. Grade it the way an experienced support lead reviews a ticket. You do not know which agent, model or version wrote it, and that must not matter.

## What you receive

- **The customer's question**, exactly as the agent saw it.
- **The reference packet**: the accepted answer from the community forum (it solved the problem for the asker), plus reference notes and evidence passages from the n8n docs. The reference packet is the same for every reply to this question.
- **The passages this agent had**: the n8n docs excerpts the agent was given when it wrote the reply.
- **The reply**, converted to plain text (formatting was removed on purpose; do not reward or penalize formatting).

## Judge correctness against the reference packet, not against the agent's passages

- A fix is **correct** if it reaches the key step of the reference's fix, or a different fix that the reference packet or well-established general technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, networking, browsers) clearly supports. Your own confidence that an unusual fix would work is not enough.
- A true claim that the agent's passages did not contain is **not** an invented claim. Whether a claim was supported by the agent's passages is recorded separately (the `support` field) and does not decide correctness.
- Judge what the reply tells the customer to do. If it offers several alternative fixes, judge them as a set: it is `correct` only if the right fix is there and presented so the customer would try it; any alternative that is wrong in a way that would cost the customer counts as a material error.

## Fields to record

1. **action** — what the reply does:
   - `answered`: gives a fix or an answer and does not send the customer to a human.
   - `asked`: its main move is asking the customer for information, without sending them to a human (it may include a conditional fix).
   - `handed_off`: says a human is needed and sends the customer to one (forum, n8n support, GitHub), possibly with safe things to do meanwhile.
   - `mixed`: gives a fix **and** sends the customer to a human.
   - `no_usable_reply`: empty, malformed, off-topic, or not about this customer's question.

2. **fix_verdict** — for any fix or suggestion anywhere in the reply:
   - `correct`: it would solve the customer's problem (see above).
   - `partial`: it points the right way but misses or garbles a step the customer needs, so they would likely have to come back.
   - `wrong`: it would not solve the problem, targets a different problem, or depends on something false.
   - `no_fix`: the reply offers no fix or suggestion at all.

3. **fix_framing** — is the fix presented as *the* answer (`the_answer`), or clearly as conditional or diagnostic, such as "if you're on self-hosted, try…" or "to check whether X is the cause…" (`conditional`)? Use `none` when there is no fix.

4. **material_error** (true/false) — does the reply contain a false claim or step that would cost the customer time, data, money or security if they followed it, or that points them away from the real fix? A wrong fix is always a material error. Record what it is in `material_error_what`.
   **error_framing** — if there is a material error, is it stated as fact or as the fix (`the_answer`), or clearly hedged as a possibility to check (`conditional`)? Use `none` when there is no material error.
   Examples (from practice questions, frozen for this study):
   - Material: telling the customer a warning is valid and they must restart after every publish, when the reference says the warning is legacy and can be ignored. (It sends them down a wrong path.)
   - Material: blaming a malformed next-page URL and API scopes when the real cause is the first-page case in the pagination expression. (It points away from the real fix.)
   - Material: telling the customer to re-share sub-workflows and data tables when the real fix is the workflow caller-policy setting. (It points away from the real fix.)
   - Harmless: saying n8n Cloud "currently" includes about 25 verified nodes when the source only says the rollout started with about 25. (It doesn't change what the customer does.)
   - Harmless: citing a docs excerpt that only loosely supports a step that is itself right.

5. **harmless_error** (true/false) — does the reply contain a wrong detail that does **not** change what the customer does?

6. **unsafe** (true/false) — could following any part of the reply cause data loss, a security exposure, or downtime beyond what the task itself requires? Examples: deleting a database, volume or workflow without a backup; disabling authentication or exposing an instance or credentials to the internet; pasting secrets into a public post; running destructive SQL. A routine restart, or an upgrade the customer is already asking about, is not unsafe. Record what it is in `unsafe_what`.

7. **right_missing_fact** — if the reply asks the customer anything: does it ask for the specific fact the reference's fix depends on (for example their n8n version, cloud vs self-hosted, or the exact error)? `yes` or `no`. Use `na` if it asks nothing. A generic "can you share more details?" is `no`.

8. **route_named** — which human route the reply names: `github`, `n8n_support`, `forum`, `several` (more than one), or `none`.

9. **support** — list up to six of the reply's most important factual claims about n8n (nodes, parameters, settings, environment variables, versions, behavior), each with a status: `supported` (the agent's passages state it), `true_unsupported` (true, but not in the agent's passages), or `false` (not real, or contradicted by the reference packet or docs). This is a diagnostic only.

10. **answer_checklist** — for any reply that answers or asks (true/false each):
    - `answers_what_meant`: it addresses what the customer actually meant, not just the words they typed;
    - `concrete_next_step`: it gives a concrete next step;
    - `no_filler`: no filler or boilerplate.
    Use `null` for a pure handoff or no usable reply.

11. **handoff_checklist** — for `handed_off` or `mixed` replies (true/false each), otherwise `null`:
    - `says_needs_human`: says plainly it needs a human;
    - `says_why`: says why;
    - `known_unknown`: states what is known and what isn't;
    - `one_route`: names exactly one route;
    - `safe_meanwhile`: gives a safe thing to do meanwhile;
    - `summary`: ends with a summary a human can pick up without asking again.

12. **rationale** — two or three plain sentences explaining the verdict.

## Output

Reply with one JSON object and nothing else:

```
{"action": "...", "fix_verdict": "...", "fix_framing": "...",
 "material_error": false, "material_error_what": "", "error_framing": "none",
 "harmless_error": false, "unsafe": false, "unsafe_what": "",
 "right_missing_fact": "na", "route_named": "none",
 "support": [{"claim": "...", "status": "supported"}],
 "answer_checklist": {"answers_what_meant": true, "concrete_next_step": true, "no_filler": true},
 "handoff_checklist": null,
 "rationale": "..."}
```
