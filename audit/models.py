"""Model registry for Test Plan v3 (sections 8 and 12): exact IDs, companies, host pins, thinking levels,
caps, timeouts and list prices. runs/MANIFEST.json copies this table, and its hash is preregistered
before each paid phase. Change a setting here only before a phase starts, never after results come in.

Thinking levels (TEST-PLAN-v3 section 8):
  - every model runs at its provider's default (reasoning=None means "send no setting");
  - the low-cost drafter keeps round one's setting. Round one sent no setting, and its billed completion
    tokens matched its visible text (median 211 tokens for 157 words), so that default is pinned
    explicitly as effort "none";
  - grader 1 (and its alternate) runs at high effort;
  - Qwen runs at medium, because its default is the highest and multiplies cost.
"""

MODELS = {
    # model id                      company      host pin (OpenRouter provider tag)  thinking            list $/M (in, out)
    "openai/gpt-5.4-mini":          dict(company="openai",    provider="openai",           reasoning={"effort": "none"},   price=(0.75, 4.50)),
    "openai/gpt-6.1-sol":           dict(company="openai",    provider="openai",           reasoning=None,                 price=(2.00, 10.00)),
    "anthropic/claude-sonnet-5.5":  dict(company="anthropic", provider="anthropic",        reasoning={"effort": "high"},   price=(2.00, 10.00)),
    "anthropic/claude-opus-5.5":    dict(company="anthropic", provider="anthropic",        reasoning={"effort": "high"},   price=(4.00, 20.00)),
    "google/gemini-3.8-flash":      dict(company="google",    provider="google-ai-studio", reasoning=None,                 price=(0.75, 3.75)),
    "meta/muse-spark-1.3":          dict(company="meta",      provider="meta",             reasoning=None,                 price=(1.25, 4.25)),
    "qwen/qwen3.8-max-0902":        dict(company="alibaba",   provider="alibaba",          reasoning={"effort": "medium"}, price=(2.00, 6.00)),
    "z-ai/glm-5.3":                 dict(company="zhipu",     provider="parasail/fp8",               reasoning=None,                 price=(1.40, 4.40)),
    "xiaomi/mimo-v2.6-pro":         dict(company="xiaomi",    provider="xiaomi/fp8",               reasoning=None,                 price=(0.435, 0.87)),
    "moonshotai/kimi-k3":           dict(company="moonshot",  provider="moonshotai/mxfp4",               reasoning=None,                 price=(3.00, 15.00)),
    "baai/bge-m3":                  dict(company="baai",      provider="deepinfra/fp32",   reasoning=None,                 price=(0.01, 0.0)),
}
# Reviewer hosts pinned 2026-10-13 (Build 2, before the reviewer trial), by section 8's rules: native precision, the
# full advertised context and output, no fallback, and a third-party host for GLM (Z.ai is on the US Entity List).
#   GLM-5.3 -> Parasail fp8 (1M context, full output; the host the model-landscape research named)
#   MiMo-V2.6-Pro -> Xiaomi's own fp8 endpoint (the lab's reference deployment)
#   Kimi K3 -> Moonshot's own mxfp4 endpoint (native 4-bit; the reference the Kimi Vendor Verifier checks against)

THINKING_MODELS = {"anthropic/claude-sonnet-5.5", "anthropic/claude-opus-5.5", "google/gemini-3.8-flash",
                   "meta/muse-spark-1.3", "qwen/qwen3.8-max-0902", "openai/gpt-6.1-sol",
                   "z-ai/glm-5.3", "xiaomi/mimo-v2.6-pro", "moonshotai/kimi-k3"}

# Section 8: reply caps and timeouts start generous for thinking models, then are sized from the practice
# trials (at least 4x the longest reply measured there) and frozen. Round-one caps stay for the low-cost drafter.
DEFAULT_CAP, DEFAULT_TIMEOUT = 8000, 180
CAPS = {  # (role, model) -> max_tokens, when it differs from the default
    ("drafter", "openai/gpt-5.4-mini"): 2000,        # round one's v3/v4 draft cap
    ("reviewer_A", "openai/gpt-5.4-mini"): 400,      # arm A = v4 as built (its longest review was 101 tokens)
    ("handoff", "openai/gpt-5.4-mini"): 500,         # round one's handoff cap
    # Build 2 (2026-10-13): GLM-5.3 hit the 8,000 starting cap on 11 of its first 34 practice reviews (empty reply,
    # finish=length), the round-one cap trap. Raised for all three candidates to 24,000: the most a single attempt can
    # produce inside the Mac's 3-minute command limit at GLM's ~160 tokens/s. MiMo (max 2,667) and Kimi (max 4,922)
    # never came near 8,000, so their finished reviews are unaffected.
    ("reviewer_B", "z-ai/glm-5.3"): 24000, ("reviewer_B", "moonshotai/kimi-k3"): 24000, ("reviewer_B", "xiaomi/mimo-v2.6-pro"): 24000,
    ("reviewer_I", "xiaomi/mimo-v2.6-pro"): 24000,  # follow-up arm I (2026-10-28): same reviewer and cap as arm B
}
ATTEMPTS = 3  # section 8: every role gets 3 attempts with identical settings

# Build 1 roles. Grader 2 and the tie-breaker are filled in by the calibration screen (section 7).
ROLES = {
    "grader1": "anthropic/claude-sonnet-5.5",
    "grader1_route": "api (batch mode where available; decision 13)",
    "grader2_candidates": ["google/gemini-3.8-flash", "meta/muse-spark-1.3", "qwen/qwen3.8-max-0902"],
    "grader2": "google/gemini-3.8-flash",            # decision 12 (2026-10-01): cross-company agreement on JC's 20
    "tiebreaker": "meta/muse-spark-1.3",             # decision 12
    "labeler1": "anthropic/claude-sonnet-5.5",       # decision 13: over the API (section 12's alternate), not JC's plan
    "labeler2": "google/gemini-3.8-flash",           # = grader 2, in a separate session
    "drafter_low": "openai/gpt-5.4-mini",
    "reviewer_A": "openai/gpt-5.4-mini",
    "embed": "baai/bge-m3",
}

AUTHORS = {"openai/gpt-5.4-mini": "openai", "openai/gpt-6.1-sol": "openai", "JC": "human", "harness": "human"}


def company(model):
    if model in AUTHORS:
        return AUTHORS[model]
    base = model.split(":")[0]
    if base in MODELS:
        return MODELS[base]["company"]
    raise ValueError(f"unknown model {model!r}: add it to audit/models.py before calling it")


def cap(role, model):
    return CAPS.get((role, model), DEFAULT_CAP if model in THINKING_MODELS else 2000)


class IndependenceError(RuntimeError):
    pass


def check_independence(role, model, author=None, graders=None, arm=None):
    """Section 3, checked automatically before every model call.
    - No model grades text written by its own company (graders, tie-breaker).
    - No reviewer reviews drafts from its own company (declared exceptions: arm A = v4 as built; follow-up arm H =
      arm A's structure with Sol, added 2026-10-28 after the final test).
    - No reviewer comes from a grader's company.
    Raises IndependenceError; the call is never made."""
    me = company(model)
    if role in ("grader", "grader1", "grader2", "tiebreaker", "screen"):
        if author is None:
            raise IndependenceError(f"{role} call on {model} has no author recorded for the text it grades")
        if company(author) == me:
            raise IndependenceError(f"{model} ({me}) may not grade text written by {author} ({company(author)})")
    if role.startswith("reviewer"):
        if author is None:
            raise IndependenceError(f"reviewer call on {model} has no draft author recorded")
        if company(author) == me and not ((arm == "A" and role == "reviewer_A") or (arm == "H" and role == "reviewer_H")):
            raise IndependenceError(f"reviewer {model} ({me}) may not review drafts from {author}")
        for g in graders or []:
            if g and company(g) == me:
                raise IndependenceError(f"reviewer {model} shares a company with grader {g}")
    return True
