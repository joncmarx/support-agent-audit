# Answer key v2: labeling instructions (Test Plan v3, section 5)

You are labeling one solved thread from the n8n community forum. The label says what a support bot that reads n8n's official docs should do with this question. You never see any bot's reply.

## The key step

Start from the accepted answer (written by another community member; it solved the problem for the asker). The **key step** is the one step of the fix without which the fix fails. You may record a different fix only if a docs passage or well-established general technical knowledge supports it, and you must cite that evidence.

## Categories (when more than one fits, the first in this order wins)

1. `account_access`: the fix needs a **privileged action the customer can't take themselves**: n8n staff, billing, or n8n Cloud infrastructure. Steps a customer can take in their own instance once told how do NOT count.
2. `n8n_docs`: the n8n docs passages you were given contain the key step, including release notes (for example "fixed in version X, upgrade").
3. `general_tech`: the key step is standard technical knowledge outside n8n (SQL, HTTP, OAuth, Docker, JavaScript, networking, regular expressions, a third-party API's documented behavior).
4. `bug_or_release`: a bug or regression in n8n with no documented fix yet.
5. `undocumented_n8n`: the key step depends on n8n behavior the docs passages don't describe.

Judge `n8n_docs` only from the passages shown to you, found by the searches listed with them. If none of them contains the key step, the finding is "not found under the recorded search protocol", which is all a negative label claims.

## Also record

- **evidence**: the reference codes of the passages that contain the key step (for `n8n_docs`), or that best support your label otherwise. Use an empty list if none do.
- **version**: the n8n version the question states, or null.
- **reference_doubt**: true if the accepted answer is outdated, is only a workaround when a real fix exists, or conflicts with the docs for the stated version. Give the reason and, if a passage shows it, its code.

## Turn A output (before any search)

```
{"key_step": "one sentence", "fix_query": "a search query for the key fix alone",
 "exact_terms": ["exact setting names, environment variables, node or parameter names from the fix; at most 6"],
 "version": "stated n8n version or null"}
```

## Turn B output (after reading the search results)

```
{"category": "account_access | n8n_docs | general_tech | bug_or_release | undocumented_n8n",
 "key_step": "one sentence (may refine turn A)",
 "alternative_fix": null or "a different verified fix, with its evidence code",
 "evidence": ["S1-3", "S2-1"],
 "version": "stated n8n version or null",
 "reference_doubt": false, "doubt_reason": "", "doubt_passage": null,
 "rationale": "two sentences"}
```
