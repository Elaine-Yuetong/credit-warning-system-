"""
analyze_backtest.py — EXPLORATORY analysis of backtest_results.json.

Reads the point-in-time backtest report (produced by `python backtest.py --json
backtest_results.json`) and produces four exploratory analyses to understand WHICH
metrics drive distress catches versus healthy-control false positives, BEFORE any
threshold recalibration.

Everything here is EXPLORATORY and computed on a small sample (30 distressed, 15
healthy, 10 survivors). It describes the current model's behaviour on this case
library; it is not a validated statistical result.

Stdlib only: json, statistics, collections (+ a tiny in-file date-ordinal helper so
no datetime import is needed). No network, no extractor — reads the JSON only.

DATA NOTE: the backtest JSON records, per scored quarter, each non-suppressed metric's
ALERT-LEVEL ORDINAL (0=None,1=Watch,2=Flag,3=Stress,4=Critical) in `metric_alerts`, plus
the list of metrics at Stress+ (`stress_metrics`). Analysis 4 computes Cohen's d on those
alert-level ordinals (distressed at first signal vs healthy averaged over the window).
Alert levels are already sector/volatility normalized through threshold calibration, so no
size normalization is needed — a Stress alert means the same thing for a retailer and an
industrial.
"""

import json
import math
from collections import Counter, defaultdict
from statistics import mean, median, pstdev, stdev

REPORT = "backtest_results.json"
TAG = "EXPLORATORY — 30 distressed cases"


# --------------------------------------------------------------------------------------
# Tiny date helpers (proleptic Gregorian day ordinal — avoids a datetime import)
# --------------------------------------------------------------------------------------

def _is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _ordinal(iso):
    """Day count for an ISO date 'YYYY-MM-DD' (monotonic; only differences are used)."""
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    days = 365 * (y - 1) + (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400
    mdays = [31, 29 if _is_leap(y) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return days + sum(mdays[:m - 1]) + d


def _lead_months(event_iso, asof_iso):
    return (_ordinal(event_iso) - _ordinal(asof_iso)) / 30.44


# --------------------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------------------

def _load():
    with open(REPORT, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["distressed"], data["healthy"], data["stressed_survivors"]


def _all_metrics(*groups):
    s = set()
    for g in groups:
        for c in g:
            for sp in c["timeline"]:
                s.update(sp["stress_metrics"])
    return sorted(s)


def _sp_at(case, as_of):
    return next((sp for sp in case["timeline"] if sp["as_of"] == as_of), None)


def _hr():
    print("─" * 84)


# --------------------------------------------------------------------------------------
# Analysis 1 — False-positive decomposition
# --------------------------------------------------------------------------------------

def analysis_1(healthy):
    print(f"\nANALYSIS 1 — FALSE-POSITIVE DECOMPOSITION   [{TAG}]")
    print("Healthy controls that fired the ≥2-metric Stress+ confirmation, and which metrics drove it.")
    _hr()

    fired = [c for c in healthy if c["fp_dates"]]
    metric_quarters = Counter()    # total confirmed-quarter appearances across all controls
    metric_controls = Counter()    # distinct controls a metric appears in

    if not fired:
        print("  (no healthy control fired the ≥2-metric confirmation)")
        return metric_quarters, metric_controls, set()

    for c in fired:
        fp_set = set(c["fp_dates"])
        local = Counter()
        for sp in c["timeline"]:
            if sp["as_of"] in fp_set:
                for m in sp["stress_metrics"]:
                    local[m] += 1
        tag = "(annotated)" if c["status"] == "annotated" else ""
        print(f"\n  {c['name']} {tag}— fired on {len(fp_set)} confirmed quarter(s):")
        for m, q in sorted(local.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"      {m:<32} {q} qtr(s)")
            metric_quarters[m] += q
            metric_controls[m] += 1

    print("\n  RANKING — metrics by appearance in false-positive signals (across all controls):")
    print(f"      {'metric':<32}{'FP quarters':>12}{'# controls':>12}")
    for m, q in metric_quarters.most_common():
        print(f"      {m:<32}{q:>12}{metric_controls[m]:>12}")
    return metric_quarters, metric_controls, set(metric_quarters)


# --------------------------------------------------------------------------------------
# Analysis 2 — Metric presence at first distress signal
# --------------------------------------------------------------------------------------

def analysis_2(distressed):
    print(f"\n\nANALYSIS 2 — METRIC PRESENCE AT FIRST DISTRESS SIGNAL   [{TAG}]")
    print("For each distressed case, the metrics firing on the first ≥2-metric Stress+ date.")
    _hr()

    n = len(distressed)
    presence = Counter()
    scored = 0
    for c in distressed:
        fsd = c["first_stress_date"]
        if not fsd:
            continue
        sp = _sp_at(c, fsd)
        if sp is None:
            continue
        scored += 1
        for m in set(sp["stress_metrics"]):
            presence[m] += 1

    print(f"  {scored}/{n} distressed cases had a first confirmed signal.\n")
    print(f"      {'metric':<32}{'cases at first signal':>22}{'coverage':>11}")
    for m, cnt in sorted(presence.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"      {m:<32}{f'{cnt}/{n}':>22}{cnt / n:>10.0%}")
    return presence


# --------------------------------------------------------------------------------------
# Analysis 3 — Lead time per metric
# --------------------------------------------------------------------------------------

def analysis_3(distressed):
    print(f"\n\nANALYSIS 3 — LEAD TIME PER METRIC   [{TAG}]")
    print("First quarter each metric reached Stress+, in months before the event. Sorted by median lead.")
    _hr()

    n = len(distressed)
    leads = defaultdict(list)   # metric -> [lead_months per case where it ever fired]
    for c in distressed:
        ev = c["event_date"]
        if not ev:
            continue
        first_for = {}
        for sp in sorted(c["timeline"], key=lambda s: s["as_of"]):
            for m in sp["stress_metrics"]:
                if m not in first_for:
                    first_for[m] = sp["as_of"]
        for m, asof in first_for.items():
            leads[m].append(_lead_months(ev, asof))

    print(f"      {'metric':<32}{'coverage':>10}{'median':>9}{'min':>8}{'max':>8}   (months)")
    rows = []
    for m, vals in leads.items():
        rows.append((m, len(vals), median(vals), min(vals), max(vals)))
    rows.sort(key=lambda r: -r[2])
    for m, cov, med, mn, mx in rows:
        print(f"      {m:<32}{f'{cov}/{n}':>10}{med:>9.1f}{mn:>8.1f}{mx:>8.1f}")
    return {m: (cov, med, mn, mx) for m, cov, med, mn, mx in rows}


# --------------------------------------------------------------------------------------
# Analysis 4 — Cohen's d separation (on Stress+ firing-rate; see data limitation)
# --------------------------------------------------------------------------------------

def _distress_first_signal_levels(distressed, metrics):
    """Per metric -> list of alert-level ordinals at each case's first confirmed signal date."""
    out = defaultdict(list)
    for c in distressed:
        fsd = c["first_stress_date"]
        if not fsd:
            continue
        sp = _sp_at(c, fsd)
        if sp is None:
            continue
        ma = sp.get("metric_alerts", {})
        for m in metrics:
            out[m].append(ma.get(m, 0))
    return out


def _healthy_avg_levels(healthy, metrics):
    """Per metric -> list of per-control average alert-level ordinals over all scored quarters."""
    out = defaultdict(list)
    for c in healthy:
        tl = c["timeline"]
        if not tl:
            continue
        for m in metrics:
            vals = [sp.get("metric_alerts", {}).get(m, 0) for sp in tl]
            out[m].append(sum(vals) / len(vals))
    return out


def _cohens_d(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = mean(a), mean(b)
    sa, sb = stdev(a), stdev(b)
    pooled = (((len(a) - 1) * sa * sa + (len(b) - 1) * sb * sb) / (len(a) + len(b) - 2)) ** 0.5
    if pooled == 0:
        return 0.0 if ma == mb else float("inf")
    return (ma - mb) / pooled


def analysis_4(distressed, healthy, metrics):
    print(f"\n\nANALYSIS 4 — COHEN'S d SEPARATION   [exploratory — small sample]")
    print("Distressed (alert level at first confirmed signal) vs healthy (avg alert level over")
    print("the scored window), per metric, on the [0,4] alert-level ordinal.")
    print("NOTE: Alert levels are already sector/volatility normalized through threshold")
    print("calibration — Cohen's d measures separation on a [0,4] ordinal scale.")
    _hr()

    dlv = _distress_first_signal_levels(distressed, metrics)
    hlv = _healthy_avg_levels(healthy, metrics)
    rows = []
    for m in metrics:
        d = _cohens_d(dlv[m], hlv[m])
        rows.append((m, mean(dlv[m]) if dlv[m] else 0.0, mean(hlv[m]) if hlv[m] else 0.0, d))

    def _key(r):
        d = r[3]
        return -(float("inf") if d == float("inf") else abs(d) if d is not None else -1)

    rows.sort(key=_key)
    print(f"      {'metric':<32}{'dist lvl':>10}{'heal lvl':>10}{'Cohen d':>10}")
    cohen = {}
    for m, dm, hm, d in rows:
        ds = "  n/a" if d is None else ("   ∞" if d == float("inf") else f"{d:>+.2f}")
        print(f"      {m:<32}{dm:>10.2f}{hm:>10.2f}{ds:>10}")
        cohen[m] = d
    return cohen


# --------------------------------------------------------------------------------------
# Analysis 5 — Confidence intervals for Cohen's d
# --------------------------------------------------------------------------------------

_CITATION = (
    "  Statistical benchmarks: Cohen (1988) d guidelines: 0.2=small, 0.5=medium, 0.8=large.\n"
    "  Credit risk context: Altman (1968) found d≈1.2–2.5 for the strongest bankruptcy\n"
    "  predictors using discriminant analysis on 33+33 matched firms.")
_EXPLOR_NOTE = (
    "  EXPLORATORY — 30 distressed cases. Findings in the d=0.5–1.0 range have wide\n"
    "  confidence intervals and should be treated as hypothesis-generating only.")


def _nonnull_counts(distressed, healthy, metric):
    """n1 = distressed cases with a non-null alert level for `metric` at first signal;
    n2 = healthy controls with a non-null alert level for `metric` in any scored quarter."""
    n1 = 0
    for c in distressed:
        fsd = c["first_stress_date"]
        sp = _sp_at(c, fsd) if fsd else None
        if sp is not None and metric in sp.get("metric_alerts", {}):
            n1 += 1
    n2 = 0
    for c in healthy:
        if any(metric in sp.get("metric_alerts", {}) for sp in c["timeline"]):
            n2 += 1
    return n1, n2


def _interpret_ci(lo, hi):
    if hi < 0.0:
        return "negative — metric fires more on healthy than distressed"
    if lo > 0.8:
        return "large effect — conclusion"
    if lo > 0.5:
        return "medium-large effect — likely meaningful"
    if lo > 0.0:
        return "small-medium effect — exploratory"
    return "uncertain — inconclusive at this sample size"


def analysis_5(distressed, healthy, metrics, cohen):
    print(f"\n\nANALYSIS 5 — 95% CONFIDENCE INTERVALS FOR COHEN'S d   [exploratory — small sample]")
    print(_CITATION)
    print(_EXPLOR_NOTE)
    print("  SE(d) = sqrt((n1+n2)/(n1*n2) + d^2/(2*(n1+n2))); CI = d ± 1.96·SE(d)")
    _hr()

    print(f"      {'metric':<30}{'d':>8}{'CI_low':>9}{'CI_high':>9}   interpretation")
    rows = []
    for m in metrics:
        d = cohen.get(m)
        n1, n2 = _nonnull_counts(distressed, healthy, m)
        if d is None or d == float("inf") or n1 == 0 or n2 == 0:
            rows.append((m, d, None, None, "n/a — degenerate (perfect separation or empty cell)"))
            continue
        se = math.sqrt((n1 + n2) / (n1 * n2) + d * d / (2 * (n1 + n2)))
        lo, hi = d - 1.96 * se, d + 1.96 * se
        rows.append((m, d, lo, hi, _interpret_ci(lo, hi)))

    rows.sort(key=lambda r: -(r[1] if isinstance(r[1], float) and r[1] != float("inf") else -1))
    for m, d, lo, hi, interp in rows:
        if lo is None:
            print(f"      {m:<30}{'∞' if d == float('inf') else '   n/a':>8}{'':>9}{'':>9}   {interp}")
        else:
            print(f"      {m:<30}{d:>+8.2f}{lo:>+9.2f}{hi:>+9.2f}   {interp}")


# --------------------------------------------------------------------------------------
# Analysis 6 — Univariate logistic regression per metric (stdlib only, from scratch)
# --------------------------------------------------------------------------------------

def _sigmoid(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _logit_gd(xs, ys, iters=4000, lr=0.3):
    """Gradient-descent fit of b0 + b1*x on standardized xs. Returns (b0, b1)."""
    b0 = b1 = 0.0
    n = len(xs)
    for _ in range(iters):
        g0 = g1 = 0.0
        for x, y in zip(xs, ys):
            err = _sigmoid(b0 + b1 * x) - y
            g0 += err
            g1 += err * x
        b0 -= lr * g0 / n
        b1 -= lr * g1 / n
    return b0, b1


def _norm_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def analysis_6(distressed, healthy, metrics):
    print(f"\n\nANALYSIS 6 — UNIVARIATE LOGISTIC REGRESSION PER METRIC   [exploratory — small sample]")
    print(_CITATION)
    print(_EXPLOR_NOTE)
    print("  Predictor = alert-level ordinal (0–4); outcome = distressed(1)/healthy(0).")
    print("  Logistic regression fit from scratch (gradient descent); Wald-test p-values.")
    _hr()

    dlv = _distress_first_signal_levels(distressed, metrics)
    hlv = _healthy_avg_levels(healthy, metrics)

    print(f"      {'metric':<30}{'beta':>9}{'OR':>9}{'p-value':>11}  sig")
    rows = []
    for m in metrics:
        x_raw = list(dlv[m]) + list(hlv[m])
        ys = [1] * len(dlv[m]) + [0] * len(hlv[m])
        if len(x_raw) < 3:
            rows.append((m, None, None, None, "n/a"))
            continue
        mu, sd = mean(x_raw), pstdev(x_raw)
        if sd == 0:
            rows.append((m, 0.0, 1.0, 1.0, "ns"))   # predictor has no variance
            continue
        xs = [(x - mu) / sd for x in x_raw]
        b0, b1s = _logit_gd(xs, ys)
        beta = b1s / sd                                # slope on the original 0–4 scale
        # Wald SE from Fisher information on centered original-scale design [1, x-mu].
        sw = swx = swxx = 0.0
        for x, xstd in zip(x_raw, xs):
            p = _sigmoid(b0 + b1s * xstd)
            w = p * (1.0 - p)
            xc = x - mu
            sw += w
            swx += w * xc
            swxx += w * xc * xc
        det = sw * swxx - swx * swx
        if det <= 0:
            rows.append((m, beta, math.exp(beta), None, "n/a"))
            continue
        se = math.sqrt(sw / det)
        z = beta / se if se > 0 else float("inf")
        p = math.erfc(abs(z) / math.sqrt(2))           # = 2*(1-Phi(|z|))
        rows.append((m, beta, math.exp(beta), p, _stars(p)))

    rows.sort(key=lambda r: (r[3] if r[3] is not None else 2.0))
    for m, beta, orr, p, sig in rows:
        if beta is None:
            print(f"      {m:<30}{'n/a':>9}{'':>9}{'':>11}  {sig}")
        elif p is None:
            print(f"      {m:<30}{beta:>+9.2f}{orr:>9.2f}{'n/a':>11}  {sig}")
        else:
            print(f"      {m:<30}{beta:>+9.2f}{orr:>9.2f}{p:>11.4f}  {sig}")


def _stars(p):
    if p is None:
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


# --------------------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------------------

def _top5(pairs):
    return pairs[:5]


def summary(distressed, healthy, survivors, presence, leads, cohen, fp_quarters, fp_metrics):
    print("\n")
    print("EXPLORATORY STATISTICAL SUMMARY (30 distressed, 15 healthy, 10 survivors)")
    print("═" * 84)

    print("\nTop 5 metrics by distress coverage (fired in most bankruptcies):")
    for m, cnt in sorted(presence.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
        print(f"   {m:<32} {cnt}/{len(distressed)} cases at first signal ({cnt/len(distressed):.0%})")

    print("\nTop 5 metrics by lead time (earliest warning):")
    lead_rows = sorted(leads.items(), key=lambda kv: -kv[1][1])[:5]
    for m, (cov, med, mn, mx) in lead_rows:
        print(f"   {m:<32} median {med:.1f}mo lead   (fired in {cov}/{len(distressed)})")

    print("\nTop 5 metrics by Cohen's d separation:")
    def _absd(kv):
        d = kv[1]
        return float("inf") if d == float("inf") else (abs(d) if d is not None else -1)
    for m, d in sorted(cohen.items(), key=_absd, reverse=True)[:5]:
        ds = "∞" if d == float("inf") else (f"{d:+.2f}" if d is not None else "n/a")
        print(f"   {m:<32} d = {ds}")

    print("\nMetrics appearing most in false positives (recalibration candidates):")
    if fp_quarters:
        for m, q in fp_quarters.most_common(5):
            print(f"   {m:<32} {q} FP quarter(s)")
    else:
        print("   (none — no control fired the ≥2-metric confirmation)")

    print("\nMetrics that NEVER appear in false positives (most specific):")
    # Metrics that fired in ≥1 distressed first-signal but in no healthy FP signal.
    specific = sorted(m for m in presence if m not in fp_metrics)
    if specific:
        for m in specific:
            print(f"   {m:<32} fired in {presence[m]}/{len(distressed)} distressed, 0 FP")
    else:
        print("   (every distress-signal metric also appears in at least one false positive)")
    print("═" * 84)


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def main():
    distressed, healthy, survivors = _load()
    metrics = _all_metrics(distressed, healthy, survivors)

    print("═" * 84)
    print(f"  BACKTEST EXPLORATORY ANALYSIS   [{TAG}]")
    print(f"  {len(distressed)} distressed · {len(healthy)} healthy · {len(survivors)} survivors"
          f"  ·  {len(metrics)} distinct metrics seen at Stress+")
    print("═" * 84)

    fp_quarters, _fp_controls, fp_metrics = analysis_1(healthy)
    presence = analysis_2(distressed)
    leads = analysis_3(distressed)
    cohen = analysis_4(distressed, healthy, metrics)
    analysis_5(distressed, healthy, metrics, cohen)
    analysis_6(distressed, healthy, metrics)
    summary(distressed, healthy, survivors, presence, leads, cohen, fp_quarters, fp_metrics)


if __name__ == "__main__":
    main()
