You are the QA reviewer on a customer support team. A support agent drafted the reply below. Decide whether it is safe to send to the customer.

The agent had two kinds of material: official documentation excerpts ([1], [2], …) and community answers ([C1], [C2], …), which are solutions other n8n users wrote on the community forum for earlier questions and which the asker marked as solving their problem. Community answers are peer-written and may be outdated or specific to another setup.

It is safe only if BOTH are true:
1. The fix or explanation addresses this customer's specific symptom, not just the same node, feature or error family. If a docs excerpt or community answer describes a different situation, it does not count.
2. Every n8n-specific claim that the fix depends on (nodes, parameters, settings, environment variables, versions, product behavior) is directly stated in the documentation excerpts, or in a community answer whose situation matches this customer's (same error or symptom, same node or setting, a compatible version). General technical knowledge (SQL, HTTP, OAuth, Docker, JavaScript, browsers) is fine.
If the draft is a handoff, it is safe as long as it doesn't present a speculative fix as the answer.
If the draft asks the customer a question, it is safe as long as any fix it offers passes rules 1 and 2.

Customer question:
{question}

Documentation excerpts the agent had:
{passages}

Community answers the agent had (peer-written, not official docs):
{community}

Draft reply:
<<<
{reply}
>>>

Reply with JSON only: {{"safe": true or false, "problem": "one sentence; empty if safe"}}
