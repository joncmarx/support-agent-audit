"""Agreement and range calculations (TEST-PLAN-v3 sections 5, 7 and 10)."""
import math, random
from collections import Counter


def cohen_kappa(a, b):
    """Cohen's kappa for two raters over the same items. Returns dict with kappa (or None and a reason when
    only one class occurs), raw agreement, n and the class counts behind it."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return {"kappa": None, "reason": "no paired items", "n": 0}
    po = sum(x == y for x, y in pairs) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    classes = sorted(set(ca) | set(cb))
    pe = sum(ca[c] * cb[c] for c in classes) / (n * n)
    out = {"n": n, "raw_agreement": round(po, 4), "classes_rater1": dict(ca), "classes_rater2": dict(cb)}
    if len(classes) < 2 or pe >= 1:
        out.update(kappa=None, reason="only one class occurs, so kappa is undefined; raw agreement reported")
    else:
        out["kappa"] = round((po - pe) / (1 - pe), 4)
    return out


def _betainc_inv(p, a, b):
    """Inverse regularized incomplete beta by bisection (enough precision for 95% ranges)."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _betainc(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _betainc(x, a, b):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbeta) * _cf(x, a, b) / a
    return 1 - math.exp(lbeta) * _cf(1 - x, b, a) / b


def _cf(x, a, b):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300); h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c; c = c if abs(c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c; c = c if abs(c) > 1e-300 else 1e-300
        de = d * c; h *= de
        if abs(de - 1) < 1e-12:
            break
    return h


def exact_range(k, n, alpha=0.05):
    """Clopper-Pearson exact 95% range for k events in n."""
    lo = 0.0 if k == 0 else _betainc_inv(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else _betainc_inv(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def paired_bootstrap(diffs, reps=10000, seed=20260930):
    """95% range of the mean of per-question differences, resampling questions (section 10)."""
    rng = random.Random(seed); n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


if __name__ == "__main__":
    print(exact_range(2, 100), exact_range(1, 43), exact_range(0, 43))
    print(cohen_kappa(list("aabbc"), list("aabcc")))
