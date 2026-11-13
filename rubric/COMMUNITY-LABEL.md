# Community-availability label (TEST-PLAN-v3 section 5; decision 19)

You are labeling an answer key for a support-bot test. You will see a customer's question from the n8n community forum, the answer that solved it (the accepted answer), and up to 20 answers that other users wrote on the forum to EARLIER questions, found by two searches.

Your only question: **is the key step of the fix in one of those earlier community answers?**

- The key step is the step without which the fix fails. If a key step is given, use it; otherwise take it from the accepted answer.
- Answer **yes** only if one earlier answer states that key step clearly enough that a support agent reading it could apply it to this customer's problem: the same setting, node, parameter, version change, workaround or command, for the same kind of problem. Name that answer's code (for example "S2-3").
- Answer **no** if the earlier answers are only related, only mention the same node or error without the fix, give a different fix, or would need a guess to connect to this customer's problem.
- Judge only what is written. Don't use your own knowledge to fill a gap.

Return only a JSON object:
{"available": true or false, "evidence": "S1-4" or null, "reason": "one sentence"}
