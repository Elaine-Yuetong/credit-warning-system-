"""
thresholds.py — SIC classification + volatility-aware alert assignment (Phase 2).

Two responsibilities:
  1. classify(sic) -> sector_group, volatility_cat, institution_type, liquidity sector tag,
     from the SIC mapping table in spec/SECTION_6.md §6.2.
  2. assign_alerts(metrics) -> set MetricResult.alert_level using the correct per-metric
     threshold table for the issuer's volatility category, plus the special trigger rules
     (EBITDA<=0 Critical, EBIT<1.0x Critical, trend flags). Operates on the full series so
     quarter-over-quarter trend rules can be applied.

Alert levels (the §6.3 enum): None | Watch | Flag | Stress | Critical.
Threshold tables use the Formula-1 Adjusted columns: leverage +0.5x, coverage -0.5x.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from metrics import MetricResult

# Alert level ordering for "take the more severe" logic.
_LEVELS = {None: 0, "Watch": 1, "Flag": 2, "Stress": 3, "Critical": 4}


def _escalate(current: Optional[str], floor: Optional[str]) -> Optional[str]:
    return current if _LEVELS[current] >= _LEVELS[floor] else floor


# --------------------------------------------------------------------------------------
# SIC classification (§6.2)
# --------------------------------------------------------------------------------------

@dataclass
class Classification:
    sector_group: str
    volatility_cat: str           # Standard | Medial | Low | NA
    institution_type: str         # corporate | financial
    liquidity_sector: str         # standard | utility | retail_manufacturing
    de_group: str                 # asset_light | standard | capital_intensive | real_estate | NA


def classify(sic_code: Optional[str]) -> Classification:
    """Map a SIC code to sector/volatility/institution/D-E-group classifications (§6.2)."""
    try:
        sic = int(sic_code) if sic_code is not None else -1
    except (TypeError, ValueError):
        sic = -1

    if 6000 <= sic <= 6499:
        return Classification("Financial Institutions", "NA", "financial", "standard", "NA")
    if 100 <= sic <= 1499:
        return Classification("Agriculture / Mining", "Standard", "corporate", "standard", "standard")
    if 1500 <= sic <= 1799:
        return Classification("Construction", "Standard", "corporate", "standard", "standard")
    if 2000 <= sic <= 3999:
        # Manufacturing / Industrials — ambiguous Standard/Medial -> Standard (more conservative).
        return Classification("Manufacturing / Industrials", "Standard", "corporate", "retail_manufacturing", "standard")
    if 4000 <= sic <= 4899:
        return Classification("Transportation", "Standard", "corporate", "standard", "capital_intensive")
    if 4900 <= sic <= 4999:
        return Classification("Utilities", "Low", "corporate", "utility", "capital_intensive")
    if 5000 <= sic <= 5999:
        return Classification("Retail / Wholesale", "Medial", "corporate", "retail_manufacturing", "standard")
    if 6500 <= sic <= 6799:
        return Classification("Real Estate", "Low", "corporate", "standard", "real_estate")
    if 7000 <= sic <= 8999:
        return Classification("Services / Technology", "Standard", "corporate", "standard", "asset_light")
    # Unknown SIC -> Standard, the most conservative corporate default.
    return Classification("Unclassified", "Standard", "corporate", "standard", "standard")


# --------------------------------------------------------------------------------------
# Threshold tables (Formula-1 Adjusted)
# --------------------------------------------------------------------------------------

# Leverage (higher is worse). Band entry thresholds per volatility category, F1-adjusted
# (+0.5x). (significant_floor, aggressive_floor, highly_leveraged_floor):
#   value >= highly_leveraged_floor -> Stress
#   value >= aggressive_floor       -> Flag
#   value >= significant_floor      -> Watch
_LEVERAGE_BANDS = {
    "Standard": (3.5, 4.5, 5.5),
    "Medial":   (4.0, 5.0, 6.0),
    "Low":      (4.5, 5.5, 6.5),
}

# Interest coverage (lower is worse), applied to EBITDA coverage, F1-adjusted (-0.5x).
# (significant_ceiling, aggressive_ceiling, highly_leveraged_ceiling):
#   value < highly_leveraged_ceiling -> Stress
#   value < aggressive_ceiling       -> Flag
#   value < significant_ceiling      -> Watch
_COVERAGE_BANDS = {
    "Standard": (5.5, 3.5, 2.0),
    "Medial":   (4.0, 2.5, 1.25),
    "Low":      (2.5, 1.5, 1.0),
}

# Current ratio (Dimension 1) universal bands as (threshold, level), descending.
#   value < 0.8 Critical; <1.0 Stress; <1.2 Flag; <1.5 Watch; else None
_CURRENT_BANDS = [(0.8, "Critical"), (1.0, "Stress"), (1.2, "Flag"), (1.5, "Watch")]

# Quick ratio (Dimension 2) standard bands.
#   value < 0.4 Critical; <0.6 Stress; <0.8 Flag; <1.0 Watch; else None
_QUICK_BANDS_STANDARD = [(0.4, "Critical"), (0.6, "Stress"), (0.8, "Flag"), (1.0, "Watch")]
# Retail / manufacturing adjusted quick bands (explicit table, not a uniform shift).
_QUICK_BANDS_RETAIL_MFG = [(0.2, "Critical"), (0.3, "Stress"), (0.4, "Flag"), (0.6, "Watch")]


def _band_descending(value: float, bands: list[tuple[float, str]]) -> Optional[str]:
    """Bands as (ceiling, level) sorted ascending by ceiling; lower value = worse."""
    for ceiling, level in bands:
        if value < ceiling:
            return level
    return None


def _band_ascending(value: float, bands: list[tuple[float, str]]) -> Optional[str]:
    """Bands as (floor, level) sorted ascending by floor; higher value = worse.

    Returns the level of the highest floor that `value` meets or exceeds.
    """
    level = None
    for floor, lvl in bands:
        if value >= floor:
            level = lvl
    return level


# Debt-to-Equity bands per D/E threshold group (higher is worse), (floor, level).
_DE_BANDS = {
    "asset_light":      [(0.5, "Watch"), (1.0, "Flag"), (1.5, "Stress"), (2.5, "Critical")],
    "standard":         [(1.0, "Watch"), (1.5, "Flag"), (2.5, "Stress"), (3.5, "Critical")],
    "capital_intensive": [(1.5, "Watch"), (2.0, "Flag"), (2.75, "Stress"), (3.5, "Critical")],
    "real_estate":      [(1.5, "Watch"), (2.0, "Flag"), (3.0, "Stress"), (4.0, "Critical")],
}

# Asset coverage Dimension 1 (total) — lower is worse, (ceiling, level).
_ASSET_COVERAGE_BANDS = [(1.0, "Critical"), (1.2, "Stress"), (1.5, "Flag"), (2.0, "Watch")]
# Tangible asset coverage Dimension 2 — standard and asset-light-adjusted.
_TANGIBLE_BANDS_STANDARD = [(0.4, "Critical"), (0.7, "Stress"), (1.0, "Flag"), (1.5, "Watch")]
_TANGIBLE_BANDS_ASSET_LIGHT = [(0.05, "Critical"), (0.15, "Stress"), (0.3, "Flag"), (0.5, "Watch")]
# Near-term maturity coverage (cash-only, Phase 2) — mirrors LIQUIDITY Dimension 4.
_MATURITY_BANDS = [(0.2, "Critical"), (0.5, "Stress"), (1.0, "Flag"), (1.5, "Watch")]


# --------------------------------------------------------------------------------------
# Per-metric alert logic
# --------------------------------------------------------------------------------------

def _leverage_alert(m: MetricResult, prior: Optional[MetricResult], vol: str) -> Optional[str]:
    ebitda = m.extra.get("ebitda")
    if ebitda is not None and ebitda <= 0:
        return "Critical"  # EBITDA <= 0 -> automatic critical (LEVERAGE.md)
    if m.value is None:
        return None
    sig, agg, hl = _LEVERAGE_BANDS.get(vol, _LEVERAGE_BANDS["Standard"])
    if m.value >= hl:
        level = "Stress"
    elif m.value >= agg:
        level = "Flag"
    elif m.value >= sig:
        level = "Watch"
    else:
        level = None
    # Trend Flag: +1.0x or more in a single quarter -> at least Flag.
    if prior is not None and prior.value is not None and (m.value - prior.value) >= 1.0:
        m.flags.append(f"trend flag — leverage rose {m.value - prior.value:.1f}x QoQ")
        level = _escalate(level, "Flag")
    return level


def _coverage_alert(m: MetricResult, prior: Optional[MetricResult], vol: str) -> Optional[str]:
    ebit_cov = m.extra.get("ebit_coverage")
    # Absolute EBIT floor (independent of band / volatility): < 1.0x or negative -> Critical.
    if ebit_cov is not None and ebit_cov < 1.0:
        m.flags.append("EBIT coverage < 1.0x — cannot cover interest from operations (critical)")
        return "Critical"
    if m.value is None:
        return None
    sig, agg, hl = _COVERAGE_BANDS.get(vol, _COVERAGE_BANDS["Standard"])
    if m.value < hl:
        level = "Stress"
    elif m.value < agg:
        level = "Flag"
    elif m.value < sig:
        level = "Watch"
    else:
        level = None
    # Trend Flag: decline of 1.0x or more in a single quarter -> at least Flag.
    if prior is not None and prior.value is not None and (prior.value - m.value) >= 1.0:
        m.flags.append(f"trend flag — coverage fell {prior.value - m.value:.1f}x QoQ")
        level = _escalate(level, "Flag")
    return level


def _current_alert(m: MetricResult, liquidity_sector: str) -> Optional[str]:
    if m.value is None:
        return None
    bands = _CURRENT_BANDS
    if liquidity_sector == "utility":
        bands = [(c - 0.2, lvl) for c, lvl in _CURRENT_BANDS]  # utilities -0.2x (§ Dimension 1)
        m.flags.append("utility sector — current ratio thresholds adjusted -0.2x")
    return _band_descending(m.value, bands)


def _quick_alert(m: MetricResult, liquidity_sector: str) -> Optional[str]:
    if m.value is None:
        return None
    if liquidity_sector == "retail_manufacturing":
        m.flags.append("retail/manufacturing sector — quick ratio thresholds adjusted")
        return _band_descending(m.value, _QUICK_BANDS_RETAIL_MFG)
    return _band_descending(m.value, _QUICK_BANDS_STANDARD)


def _fcf_alert(m: MetricResult, history: list[MetricResult]) -> Optional[str]:
    """free_cash_flow alerts: consecutive-negative escalation + declining-trend Watch."""
    if m.value is None:
        return None
    series = [h.value for h in history if h.value is not None]
    # Count trailing consecutive negative quarters ending at this period.
    consec_neg = 0
    for v in reversed(series):
        if v < 0:
            consec_neg += 1
        else:
            break
    if consec_neg >= 3:
        m.flags.append(f"FCF negative {consec_neg} consecutive quarters — severe")
        return "Stress"
    if consec_neg >= 1:
        m.flags.append("FCF negative — company burning cash after capex")
        return "Flag"
    # Positive but declining for 3+ consecutive quarters -> Watch (earliest warning).
    if len(series) >= 3 and series[-1] < series[-2] < series[-3]:
        m.flags.append("FCF declining 3 consecutive quarters — upstream stress signal")
        return "Watch"
    return None


def _conversion_alert(m: MetricResult, history: list[MetricResult]) -> Optional[str]:
    """ocf_ebitda_conversion alerts (FREE_CASH_FLOW.md Input 5)."""
    if m.value is None:
        return None
    if m.value < 0:
        return "Stress"
    if m.value < 0.50:
        return "Flag"
    series = [h.value for h in history if h.value is not None]
    if len(series) >= 2 and series[-1] < 0.70 and series[-2] < 0.70:
        return "Watch"
    return None


def _de_alert(m: MetricResult, history: list[MetricResult], de_group: str) -> Optional[str]:
    if m.extra.get("negative_equity"):
        return "Critical"  # negative equity -> automatic Critical (any sector)
    if m.value is None:
        return None
    level = _band_ascending(m.value, _DE_BANDS.get(de_group, _DE_BANDS["standard"]))
    # Trend: D/E increasing for 3 consecutive quarters -> at least Flag.
    series = [h.value for h in history if h.value is not None]
    if len(series) >= 4 and series[-1] > series[-2] > series[-3] > series[-4]:
        m.flags.append("trend — D/E rising 3 consecutive quarters")
        level = _escalate(level, "Flag")
    return level


def _asset_coverage_alert(m: MetricResult, history: list[MetricResult]) -> Optional[str]:
    if m.value is None:
        return None
    level = _band_descending(m.value, _ASSET_COVERAGE_BANDS)
    series = [h.value for h in history if h.value is not None]
    if len(series) >= 4 and series[-1] < series[-2] < series[-3] < series[-4]:
        m.flags.append("trend — total asset coverage declining 3 consecutive quarters")
        level = _escalate(level, "Watch")
    return level


def _tangible_coverage_alert(m: MetricResult, de_group: str) -> Optional[str]:
    if m.value is None:
        return None
    if de_group == "asset_light":
        m.flags.append("asset-light sector — tangible coverage thresholds adjusted")
        return _band_descending(m.value, _TANGIBLE_BANDS_ASSET_LIGHT)
    return _band_descending(m.value, _TANGIBLE_BANDS_STANDARD)


def _ebitda_margin_alert(m: MetricResult, history: list[MetricResult]) -> Optional[str]:
    """EBITDA Margin Trend — Dimension 2 (trend) + negative-margin rules. Sector-independent."""
    if m.value is None:
        return None
    series = [h.value for h in history if h.value is not None]
    # Negative margin handling.
    if m.value < 0:
        if len(series) >= 2 and series[-2] < 0:
            return "Critical"   # negative for 2 consecutive quarters
        return "Stress"
    level: Optional[str] = None
    # Single-quarter compression magnitude.
    if len(series) >= 2:
        drop = series[-2] - series[-1]   # positive = compression (pp)
        if drop > 3.0:
            level = _escalate(level, "Flag")
        elif drop >= 1.0:
            level = _escalate(level, "Watch")
    # Consecutive-decline duration.
    declines = 0
    for i in range(len(series) - 1, 0, -1):
        if series[i] < series[i - 1]:
            declines += 1
        else:
            break
    if declines >= 4:
        level = _escalate(level, "Stress")
    elif declines == 3:
        level = _escalate(level, "Flag")
    elif declines == 2:
        level = _escalate(level, "Watch")
    return level


def _revenue_alert(m: MetricResult, history: list[MetricResult]) -> Optional[str]:
    """Revenue Trend — Dimension 1 (absolute YoY bands) + Dimension 2 (decline duration)."""
    if m.value is None:
        return None
    v = m.value
    # Dimension 1 absolute bands.
    if v < -10:
        level = "Critical"
    elif v < -5:
        level = "Stress"
    elif v < -2:
        level = "Flag"
    elif v < 2:
        level = "Watch"
    else:
        level = None
    # Dimension 2 consecutive YoY decline duration.
    series = [h.value for h in history if h.value is not None]
    declines = 0
    for val in reversed(series):
        if val < 0:
            declines += 1
        else:
            break
    if declines >= 6:
        level = _escalate(level, "Critical")
    elif declines >= 4:
        level = _escalate(level, "Stress")
    elif declines >= 3:
        level = _escalate(level, "Flag")
    return level


def _maturity_alert(m: MetricResult) -> Optional[str]:
    if m.value is None:
        return None
    return _band_descending(m.value, _MATURITY_BANDS)


def _covenant_proxy_alert(m: MetricResult) -> Optional[str]:
    """Phase-2 proxy: Flag when the underlying ratio crosses the leveraged-finance level."""
    if m.extra.get("breached"):
        return "Flag"
    return None


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def assign_alerts(metrics: list[MetricResult], cls: Classification) -> None:
    """Assign alert_level to every MetricResult in place, using the issuer classification."""
    by_metric: dict[str, list[MetricResult]] = {}
    for m in metrics:
        by_metric.setdefault(m.metric_name, []).append(m)

    for name, series in by_metric.items():
        series.sort(key=lambda x: x.period_end)
        for i, m in enumerate(series):
            if getattr(m, "suppressed", False) or getattr(m, "no_alert", False):
                m.alert_level = None  # suppressed / thresholds-N/A metrics never alert (§6.2)
                continue
            prior = series[i - 1] if i > 0 else None
            history = series[: i + 1]
            if name == "leverage":
                m.alert_level = _leverage_alert(m, prior, cls.volatility_cat)
            elif name == "interest_coverage":
                m.alert_level = _coverage_alert(m, prior, cls.volatility_cat)
            elif name == "current_ratio":
                m.alert_level = _current_alert(m, cls.liquidity_sector)
            elif name == "quick_ratio":
                m.alert_level = _quick_alert(m, cls.liquidity_sector)
            elif name == "free_cash_flow":
                m.alert_level = _fcf_alert(m, history)
            elif name == "ocf_ebitda_conversion":
                m.alert_level = _conversion_alert(m, history)
            elif name == "ebitda_margin":
                m.alert_level = _ebitda_margin_alert(m, history)
            elif name == "revenue_yoy_growth":
                m.alert_level = _revenue_alert(m, history)
            elif name == "debt_to_equity":
                m.alert_level = _de_alert(m, history, cls.de_group)
            elif name == "asset_coverage":
                m.alert_level = _asset_coverage_alert(m, history)
            elif name == "tangible_asset_coverage":
                m.alert_level = _tangible_coverage_alert(m, cls.de_group)
            elif name == "maturity_coverage_near_term":
                m.alert_level = _maturity_alert(m)
            elif name in ("covenant_headroom_leverage", "covenant_headroom_coverage"):
                m.alert_level = _covenant_proxy_alert(m)
            else:  # fcf_margin, loss_provisions_balance — stored, no Phase-2 threshold alert
                m.alert_level = None
