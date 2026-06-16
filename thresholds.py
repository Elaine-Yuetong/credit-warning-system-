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

import json
from dataclasses import dataclass
from typing import Optional

from metrics import MetricResult

# Alert level ordering for "take the more severe" logic.
_LEVELS = {None: 0, "Watch": 1, "Flag": 2, "Stress": 3, "Critical": 4}

# Near-term liquidity strength (cash + STI vs near-term debt) above which a sub-1.0
# current ratio is treated as working-capital structure, not solvency stress.
STRONG_NEARTERM_LIQUIDITY = 1.5


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

    # ── Sector carve-outs emitting the spec's 9 group names (SEGMENT_BENCHMARK_SPEC §2).
    # LABEL-only reclassification: each carve-out keeps the volatility/institution/liquidity/
    # de_group it had under its original broad block, so alert thresholds — and the backtest —
    # are unchanged. Carve-outs precede the broad ranges so the specific case wins. ──

    # Energy / Mining — petroleum refining carved from the manufacturing block.
    if 2910 <= sic <= 2911:
        return Classification("Energy / Mining", "Standard", "corporate", "retail_manufacturing", "standard")
    # Healthcare / Pharma — pharma/biotech & medical devices (from manufacturing), medical
    # wholesale (from retail), health services (from services). Source-block fields preserved.
    if 2830 <= sic <= 2836 or 3841 <= sic <= 3845:
        return Classification("Healthcare / Pharma", "Standard", "corporate", "retail_manufacturing", "standard")
    if sic == 5047:
        return Classification("Healthcare / Pharma", "Medial", "corporate", "retail_manufacturing", "standard")
    if 8000 <= sic <= 8099:
        return Classification("Healthcare / Pharma", "Standard", "corporate", "standard", "asset_light")
    # Media / Entertainment & Telecom / Utilities — broadcasting/cable vs communications, both
    # carved from the 4000-4899 transport block (all "Standard" volatility, capital-intensive).
    if 4830 <= sic <= 4841:                # radio / TV broadcasting, cable & pay-TV
        return Classification("Media / Entertainment", "Standard", "corporate", "standard", "capital_intensive")
    if 4800 <= sic <= 4899:                # telephone / radiotelephone / other communications
        return Classification("Telecom / Utilities", "Standard", "corporate", "standard", "capital_intensive")

    # ── Broad ranges ──
    if 100 <= sic <= 1499:                 # crude oil & gas, metal / coal mining
        return Classification("Energy / Mining", "Standard", "corporate", "standard", "standard")
    if 1500 <= sic <= 1799:
        return Classification("Construction", "Standard", "corporate", "standard", "standard")
    if 2000 <= sic <= 3999:
        # Manufacturing / Industrials — ambiguous Standard/Medial -> Standard (more conservative).
        return Classification("Manufacturing / Industrials", "Standard", "corporate", "retail_manufacturing", "standard")
    if 4000 <= sic <= 4799:                # rail / trucking / air / water freight -> industrials
        return Classification("Manufacturing / Industrials", "Standard", "corporate", "standard", "capital_intensive")
    if 4900 <= sic <= 4999:                # electric / gas / water utilities
        return Classification("Telecom / Utilities", "Low", "corporate", "utility", "capital_intensive")
    if 5000 <= sic <= 5999:
        return Classification("Retail / Wholesale", "Medial", "corporate", "retail_manufacturing", "standard")
    if 6500 <= sic <= 6799:
        return Classification("Real Estate", "Low", "corporate", "standard", "real_estate")
    if 7370 <= sic <= 7379:                # computer programming / data processing / software
        return Classification("Services / Technology", "Standard", "corporate", "standard", "asset_light")
    if 7000 <= sic <= 8999:                # hotels, business / professional / personal services
        return Classification("Business / Consumer Services", "Standard", "corporate", "standard", "asset_light")
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


def _current_alert(m: MetricResult, liquidity_sector: str, strong_liquidity: bool = False) -> Optional[str]:
    if m.value is None:
        return None
    bands = _CURRENT_BANDS
    if liquidity_sector == "utility":
        bands = [(c - 0.2, lvl) for c, lvl in _CURRENT_BANDS]  # utilities -0.2x (§ Dimension 1)
        m.flags.append("utility sector — current ratio thresholds adjusted -0.2x")
    elif strong_liquidity:
        # Cash-rich / low-working-capital firms (Apple, etc.) run current ratios just
        # below 1.0 by design — operating liabilities (payables, deferred revenue), not
        # debt, drive the shortfall. When cash + short-term investments cover near-term
        # DEBT >= 1.5x, a sub-1.0 current ratio is not solvency stress, so shift the bands
        # down 0.2x. LIQUIDITY.md endorses cross-referencing Available Liquidity Coverage
        # before escalating liquidity alerts. A genuine cash collapse (Rite Aid 0.02x
        # coverage) fails this gate and keeps the unadjusted, stricter bands.
        bands = [(c - 0.2, lvl) for c, lvl in _CURRENT_BANDS]
        m.flags.append("strong near-term liquidity (cash+STI cover near-term debt >=1.5x) — "
                       "current ratio thresholds adjusted -0.2x; sub-1.0 ratio not auto-Stress")
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


def _rcf_net_debt_alert(m: MetricResult) -> Optional[str]:
    """RCF/Net Debt alert (Moody's Formula-2 companion ratio). Flag < 5%, Stress < 2%, Critical < 0%."""
    if m.value is None:
        return None
    if m.value < 0.0:
        return "Critical"
    if m.value < 0.02:
        return "Stress"
    if m.value < 0.05:
        return "Flag"
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
    """Covenant headroom alert. Honors the LLM-computed level (real thresholds + compliance
    overrides) when present; otherwise the Phase-2 proxy (Flag when the ratio crosses the
    leveraged-finance level)."""
    if "llm_alert" in m.extra:
        return m.extra["llm_alert"]
    if m.extra.get("breached"):
        return "Flag"
    return None


# Thresholds loosened based on empirical calibration against 15 healthy IG controls
# (exploratory, n=30 distressed). Healthy IG industrials with high goodwill averaged
# 0.93 on this metric — inside the old Flag band. Cohen's d = +0.74, CI [+0.12, +1.36]
# (medium effect, wide CI — treat as hypothesis). Threshold adjustment is empirical,
# not a statistical conclusion. Review when n≥50.
def _liquidation_coverage_alert(m: MetricResult) -> Optional[str]:
    """Liquidation coverage alert (ASSET_COVERAGE.md Dimension 3) — most severe across both
    scenarios. Base: <0.5 Flag, <0.35 Stress, <0.2 Critical. Conservative: <0.35 Stress, <0.2 Critical.
    (Loosened from base <0.7/<0.5/<0.3 and conservative <0.5/<0.3 — see note above.)"""
    if m.value is None:
        return None
    level: Optional[str] = None
    base = m.extra.get("base_coverage")
    cons = m.extra.get("conservative_coverage")
    if base is not None:
        if base < 0.2:
            level = _escalate(level, "Critical")
        elif base < 0.35:
            level = _escalate(level, "Stress")
        elif base < 0.5:
            level = _escalate(level, "Flag")
    if cons is not None:
        if cons < 0.2:
            level = _escalate(level, "Critical")
        elif cons < 0.35:
            level = _escalate(level, "Stress")
    return level


def _loss_provisions_alert(m: MetricResult, llm_lp: Optional[dict]) -> Optional[str]:
    """Loss-provisions alert from the LLM contingency extraction (LOSS_PROVISIONS.md Dim 3):
    highest ASC 450 tier across matters drives severity. regulatory_investigation alone maps
    to Stress (not Critical) — Critical requires Tier 5 (a recorded provision).

      Tier 5                          -> Critical
      Tier 4, or regulatory (no T5)   -> Stress
      Tier 3                          -> Flag
      Tier 2                          -> Watch
      Tier 1 only / no matters        -> existing XBRL absolute thresholds (currently none)
    """
    if llm_lp is None:
        return None  # no LLM extraction -> existing behaviour (no alert)
    try:
        matters = json.loads(llm_lp.get("matters_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        matters = []
    tiers = [mt.get("tier") for mt in matters if isinstance(mt, dict) and mt.get("tier") is not None]
    highest = max(tiers) if tiers else None
    regulatory = llm_lp.get("regulatory_investigation") == 1

    if highest == 5:
        return "Critical"
    if highest == 4 or regulatory:
        return "Stress"
    if highest == 3:
        return "Flag"
    if highest == 2:
        return "Watch"
    return None  # Tier 1 only / no matters -> existing absolute thresholds (none defined)


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def assign_alerts(metrics: list[MetricResult], cls: Classification,
                  llm_lp: Optional[dict] = None) -> None:
    """Assign alert_level to every MetricResult in place, using the issuer classification.
    `llm_lp` is the issuer's most recent llm_loss_provisions row (Group 4), used for the
    loss-provisions tier-based alert; None falls back to no loss-provisions alert."""
    by_metric: dict[str, list[MetricResult]] = {}
    for m in metrics:
        by_metric.setdefault(m.metric_name, []).append(m)

    # Per-period near-term liquidity strength (cash+STI vs near-term debt), used to relax
    # the current-ratio bands for cash-rich firms (see _current_alert).
    strong_liq_by_period = {
        m.period_end: (m.value is not None and m.value >= STRONG_NEARTERM_LIQUIDITY)
        for m in by_metric.get("maturity_coverage_near_term", [])
    }

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
                m.alert_level = _current_alert(m, cls.liquidity_sector,
                                               strong_liq_by_period.get(m.period_end, False))
            elif name == "quick_ratio":
                m.alert_level = _quick_alert(m, cls.liquidity_sector)
            elif name == "free_cash_flow":
                m.alert_level = _fcf_alert(m, history)
            elif name == "moody_adjusted_fcf":
                m.alert_level = _fcf_alert(m, history)  # same bands as free_cash_flow
            elif name == "rcf_net_debt":
                m.alert_level = _rcf_net_debt_alert(m)
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
            elif name == "liquidation_asset_coverage":
                m.alert_level = _liquidation_coverage_alert(m)
            elif name == "maturity_coverage_near_term":
                m.alert_level = _maturity_alert(m)
            elif name in ("covenant_headroom_leverage", "covenant_headroom_coverage"):
                m.alert_level = _covenant_proxy_alert(m)
            elif name == "loss_provisions_balance":
                m.alert_level = _loss_provisions_alert(m, llm_lp)
            else:  # fcf_margin — stored, no Phase-2 threshold alert
                m.alert_level = None
