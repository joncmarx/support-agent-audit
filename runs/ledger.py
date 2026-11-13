"""Call ledger (TEST-PLAN-v3 section 13). Prices every call by phase, set, arm, role and route; counts each
reused reply or grade once; re-prices from measured costs; checks headroom before any paid batch.

  python3 runs/ledger.py report                 # phases 1-5, low/high, plan vs API route for grader 1
  python3 runs/ledger.py spent                  # measured spend so far (v3 rows in runs/cost_ledger.jsonl)
  python3 runs/ledger.py check <batch> [--n N]  # re-price one batch and apply the headroom rule

Headroom rule: a batch runs only if the smaller of (key limit remaining, account balance) covers its
estimate plus 30%. A phase that runs more than 30% over its estimate stops.
"""
import argparse, json, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from audit.models import MODELS  # noqa: E402

LEDGER = ROOT / "runs/cost_ledger.jsonl"
HEADROOM = 1.30

# Token profiles (input, output incl. thinking) per task, used until a measured mean exists. Grading starts
# from round one's measured 2.0 cents per Sonnet grade plus 40% for the larger rubric and packet (section 13).
PROFILE = {
    "grade": (8500, 900), "label_a": (3500, 350), "label_b": (9000, 700), "label_tb": (9000, 700),
    "doubt_tb": (6000, 200), "refcheck": (900, 120), "draft": (4430, 470), "draft_premium": (4430, 900),
    "review": (4310, 60), "review_new": (4400, 600), "handoff": (500, 170), "handoff_premium": (500, 300),
    "community_label": (6000, 300), "embed_harvest": (40_000_000, 0),
}
PRIOR_CENTS = {("grade", "anthropic/claude-sonnet-5.5"): 2.8, ("draft", "openai/gpt-5.4-mini"): 0.50,
               ("review", "openai/gpt-5.4-mini"): 0.39, ("handoff", "openai/gpt-5.4-mini"): 0.13,
               ("label_b", "anthropic/claude-sonnet-5.5"): 2.4, ("refcheck", "anthropic/claude-sonnet-5.5"): 0.33}
ROLE_TASK = {"grader1": "grade", "grader2": "grade", "tiebreaker": "grade", "screen": "grade", "plancheck": "grade",
             "labeler_a": "label_a", "labeler_b": "label_b", "label_tb": "label_tb"}

G1, OPUS = "anthropic/claude-sonnet-5.5", "anthropic/claude-opus-5.5"
GEM, MUSE, QWEN = "google/gemini-3.8-flash", "meta/muse-spark-1.3", "qwen/qwen3.8-max-0902"
MINI, SOL = "openai/gpt-5.4-mini", "openai/gpt-6.1-sol"
REVIEWER = "z-ai/glm-5.3"  # middle-priced candidate as the planning assumption until the trial picks one


def list_cents(task, model):
    i, o = PROFILE[task]
    pin, pout = MODELS[model]["price"]
    return (i * pin + o * pout) / 1e6 * 100


def measured():
    """Mean billed cents per successful logical call, by (model, role), from v3 rows. Failed attempts are
    added to the mean of the call they belong to, so retries are priced in."""
    by = defaultdict(float); n = defaultdict(int)
    if LEDGER.exists():
        for line in open(LEDGER):
            r = json.loads(line)
            if r.get("plan") != "v3" or r.get("kind") != "chat":
                continue
            key = (r["model"], r.get("role"))
            by[key] += (r.get("cost") or 0) * 100
            if r.get("ok"):
                n[key] += 1
    return {k: by[k] / n[k] for k in by if n[k]}


def unit(task, model, role=None, meas=None):
    meas = meas if meas is not None else measured()
    if role and (model, role) in meas:
        return meas[(model, role)], "measured"
    for (m, r), c in (meas or {}).items():  # same model, same task on another role
        if m == model and ROLE_TASK.get(r) == task:
            return c, "measured (same task)"
    if (task, model) in PRIOR_CENTS:
        return PRIOR_CENTS[(task, model)], "round one x plan"
    return list_cents(task, model), "list price x token profile"


def phase_lines(g2, g1_route, tb=None):
    """Every paid call in phases 1-5. (phase, what, model, role, task, calls, route)."""
    tb = tb or (MUSE if g2 == GEM else GEM)
    api = "api"; g1r = g1_route
    L = []
    add = lambda *x: L.append(x)
    # Phase 1: measuring stick (Build 1)
    add(1, "5-question dry run: v4 pipeline", MINI, "drafter", "draft", 5, api)
    add(1, "5-question dry run: review + handoff", MINI, "reviewer_A", "review", 5, api)
    add(1, "5-question dry run: grading (3 graders)", G1, "grader1", "grade", 5, api)
    add(1, "5-question dry run: grading (3 graders)", GEM, "grader2", "grade", 10, api)
    add(1, "screen: grader 1 on JC's 20", G1, "screen", "grade", 20, api)
    for m in (GEM, MUSE, QWEN):
        add(1, "screen: grader-2 candidates on JC's 20", m, "screen", "grade", 20, api)
    add(1, "plan check: API arm (50)", G1, "plancheck", "grade", 50, api)
    add(1, "plan check: two plan runs (100)", G1, "plancheck", "grade", 100, "plan")
    add(1, "labels v2: labeler 1, turn A", OPUS, "labeler_a", "label_a", 140, "plan")
    add(1, "labels v2: labeler 1, turn B", OPUS, "labeler_b", "label_b", 140, "plan")
    add(1, "labels v2: labeler 2, turn A", g2, "labeler_a", "label_a", 140, api)
    add(1, "labels v2: labeler 2, turn B", g2, "labeler_b", "label_b", 140, api)
    add(1, "labels v2: tie-breaks (~35%)", tb, "label_tb", "label_tb", 49, api)
    add(1, "labels v2: reference-doubt tie-breaks", tb, "label_tb", "doubt_tb", 15, api)
    add(1, "re-grade v1+v4 finals+drafts (403 unique): grader 1", G1, "grader1", "grade", 403, g1r)
    add(1, "re-grade: grader 2", g2, "grader2", "grade", 403, api)
    add(1, "re-grade: tie-breaks (~25%)", tb, "tiebreaker", "grade", 100, api)
    # Phase 2: judgment (Build 2)
    for m in ("z-ai/glm-5.3", "xiaomi/mimo-v2.6-pro", "moonshotai/kimi-k3"):
        add(2, "reviewer trial on 43 practice drafts", m, "reviewer", "review_new", 43, api)
    add(2, "trial: new handoffs", MINI, "handoff", "handoff", 15, api)
    add(2, "trial: grade new handoffs (g1)", G1, "grader1", "grade", 15, g1r)
    add(2, "trial: grade new handoffs (g2)", g2, "grader2", "grade", 15, api)
    add(2, "arm B on test: reviews", REVIEWER, "reviewer", "review_new", 97, api)
    add(2, "arm B: new handoffs", MINI, "handoff", "handoff", 10, api)
    add(2, "arm B: grading new replies (g1)", G1, "grader1", "grade", 10, g1r)
    add(2, "arm B: grading new replies (g2)", g2, "grader2", "grade", 10, api)
    add(2, "tie-breaks", tb, "tiebreaker", "grade", 10, api)
    # Phase 3: better drafter (arm D, 140 questions)
    add(3, "arm D drafts (GPT-6.1 Sol)", SOL, "drafter", "draft_premium", 140, api)
    add(3, "arm D reviews", REVIEWER, "reviewer", "review_new", 140, api)
    add(3, "arm D handoffs (Sol, ~60% blocked)", SOL, "handoff", "handoff_premium", 84, api)
    add(3, "arm D grading: finals + pre-review drafts (224 unique), g1", G1, "grader1", "grade", 224, g1r)
    add(3, "arm D grading, g2", g2, "grader2", "grade", 224, api)
    add(3, "arm D tie-breaks", tb, "tiebreaker", "grade", 56, api)
    # Phase 4: knowledge (F0, F)
    add(4, "harvest embeddings", "baai/bge-m3", "embed", "embed_harvest", 1, api)
    add(4, "community-availability labels (2 labelers)", OPUS, "labeler_b", "community_label", 140, "plan")
    add(4, "community-availability labels, labeler 2", g2, "labeler_b", "community_label", 140, api)
    add(4, "community-availability tie-breaks", tb, "label_tb", "community_label", 30, api)
    for arm in ("F0", "F"):
        add(4, f"arm {arm} drafts", MINI, "drafter", "draft", 140, api)
        add(4, f"arm {arm} reviews", REVIEWER, "reviewer", "review_new", 140, api)
        add(4, f"arm {arm} handoffs", MINI, "handoff", "handoff", 84, api)
        add(4, f"arm {arm} grading (224 unique), g1", G1, "grader1", "grade", 224, g1r)
        add(4, f"arm {arm} grading, g2", g2, "grader2", "grade", 224, api)
        add(4, f"arm {arm} tie-breaks", tb, "tiebreaker", "grade", 56, api)
    # Phase 5: final
    add(5, "G on practice: bad-news-fast handoffs", MINI, "handoff", "handoff", 30, api)
    add(5, "G on practice: grading, g1", G1, "grader1", "grade", 30, g1r)
    add(5, "G on practice: grading, g2", g2, "grader2", "grade", 30, api)
    add(5, "holdout reference check", G1, "refcheck", "refcheck", 105, api)
    add(5, "holdout labels, labeler 1 (A+B)", OPUS, "labeler_b", "label_b", 200, "plan")
    add(5, "holdout labels, labeler 2 (A+B)", g2, "labeler_b", "label_b", 200, api)
    add(5, "holdout label tie-breaks", tb, "label_tb", "label_tb", 35, api)
    add(5, "v4 on holdout (draft+review+handoff)", MINI, "drafter", "draft", 100, api)
    add(5, "v4 on holdout: review", MINI, "reviewer_A", "review", 100, api)
    add(5, "v4 on holdout: handoffs", MINI, "handoff", "handoff", 90, api)
    add(5, "v5 on holdout (planning assumption: a docs+harvest arm)", MINI, "drafter", "draft", 100, api)
    add(5, "v5 on holdout: review", REVIEWER, "reviewer", "review_new", 100, api)
    add(5, "v5 on holdout: handoffs", MINI, "handoff", "handoff", 60, api)
    add(5, "holdout grading of final replies, g1", G1, "grader1", "grade", 200, g1r)
    add(5, "holdout grading, g2", g2, "grader2", "grade", 200, api)
    add(5, "holdout tie-breaks", tb, "tiebreaker", "grade", 50, api)
    return L


def price(lines, meas=None):
    meas = measured() if meas is None else meas
    tot = defaultdict(float); rows = []
    for ph, what, model, role, task, n, route in lines:
        c, src = unit(task, model, role, meas)
        dollars = 0.0 if route == "plan" else c * n / 100
        tot[ph] += dollars
        rows.append((ph, what, model, route, n, c, src, dollars))
    return tot, rows


def key_status():
    """Free calls: key limit/usage and account balance. The key itself is never printed."""
    import requests
    from audit.llm import _headers
    k = requests.get("https://openrouter.ai/api/v1/key", headers=_headers(), timeout=30).json()["data"]
    c = requests.get("https://openrouter.ai/api/v1/credits", headers=_headers(), timeout=30).json()["data"]
    balance = c["total_credits"] - c["total_usage"]
    return {"limit": k["limit"], "limit_remaining": k["limit_remaining"], "key_usage": k["usage"],
            "balance": round(balance, 4), "available": round(min(k["limit_remaining"], balance), 4)}


def spent_by_phase():
    out = defaultdict(float)
    if LEDGER.exists():
        for line in open(LEDGER):
            r = json.loads(line)
            if r.get("plan") == "v3":
                out[str(r.get("phase") or "?")] += r.get("cost") or 0
    return dict(out)


def check(estimate_dollars, label=""):
    ks = key_status()
    need = estimate_dollars * HEADROOM
    ok = ks["available"] >= need
    print(f"[headroom] {label}: estimate ${estimate_dollars:.2f} x 1.3 = ${need:.2f} | available ${ks['available']:.2f} "
          f"(key remaining ${ks['limit_remaining']:.2f}, balance ${ks['balance']:.2f}) -> {'GO' if ok else 'STOP'}")
    return ok, ks


def report():
    meas = measured()
    print("Measured unit costs (cents per logical call, incl. retries):",
          {f"{m.split('/')[-1]}:{r}": round(c, 3) for (m, r), c in sorted(meas.items())} or "none yet")
    for g1_route in ("plan", "api"):
        lo, _ = price(phase_lines(GEM, g1_route), meas)
        hi, _ = price(phase_lines(MUSE, g1_route), meas)
        print(f"\nGrader 1 on the {g1_route.upper()}  (low = Gemini wins grader 2, high = Muse Spark wins)")
        for ph in range(1, 6):
            print(f"  phase {ph}: ${lo[ph]:6.2f} - ${hi[ph]:6.2f}")
        print(f"  total  : ${sum(lo.values()):6.2f} - ${sum(hi.values()):6.2f}")


# ---------------------------------------------------------------- decision 13 (2026-10-01): all API, batch where available
BATCHABLE = {"anthropic/claude-sonnet-5.5", "anthropic/claude-opus-5.5", "google/gemini-3.8-flash", "openai/gpt-5.4-mini",
             "openai/gpt-6.1-sol", "z-ai/glm-5.3", "moonshotai/kimi-k3"}


def lines_d13(g2=GEM, tb=MUSE):
    """Phases 2-5 (and what's left of 1) under decisions 12-13. route 'batch' = half of the API price."""
    out = []
    for ph, what, model, role, task, n, route in phase_lines(g2, "api", tb=tb):
        if ph == 1 and any(x in what for x in ("dry run", "screen", "plan check")):
            continue
        if model == OPUS:  # labeler 1 moved to Sonnet over the API (decision 13)
            model = G1
        out.append((ph, what, model, role, task, n, "batch" if model in BATCHABLE else "api"))
    return out


def price_d13(lines, meas=None):
    meas = measured() if meas is None else meas
    tot = defaultdict(float); rows = []
    for ph, what, model, role, task, n, route in lines:
        c, src = unit(task, model, role, meas)
        if route == "batch" and "batch" not in src:
            c, src = c / 2, src + " x 0.5 (batch)"
        tot[ph] += c * n / 100
        rows.append((ph, what, model, route, n, c, src, c * n / 100))
    return tot, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["report", "spent", "status", "lines", "d13"])
    ap.add_argument("--g2", default=GEM)
    ap.add_argument("--route", default="api")
    a = ap.parse_args()
    if a.cmd == "report":
        report()
    elif a.cmd == "spent":
        print(json.dumps(spent_by_phase(), indent=1))
    elif a.cmd == "d13":
        tot, rows = price_d13(lines_d13())
        for ph in sorted(tot):
            print(f"  phase {ph}: ${tot[ph]:6.2f}")
        print(f"  remaining total: ${sum(tot.values()):6.2f}")
    elif a.cmd == "status":
        print(json.dumps(key_status(), indent=1))
    else:
        _, rows = price(phase_lines(a.g2, a.route))
        for ph, what, model, route, n, c, src, d in rows:
            print(f"{ph} | {what[:58]:58s} | {model.split('/')[-1]:18s} | {route:4s} | {n:4d} x {c:6.3f}c = ${d:6.2f} | {src}")
