"""
check_total_debt.py
-------------------
Verifies the LongTermDebt double-count protection added to _total_debt() in metrics.py.

Tests the fix WITHOUT hitting the network — all inputs are constructed in-memory
using the same ResolvedValue and PeriodInputs dataclasses that the real code uses.

Run with:
    python check_total_debt.py

All tests should print PASS. Any FAIL indicates the fix was not applied correctly
or has a logic error.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Minimal stubs — mirror extractor.py dataclasses exactly so metrics.py imports
# work without modification. Import the real ones directly.
# ---------------------------------------------------------------------------
from extractor import ResolvedValue, PeriodInputs
from metrics import _total_debt

# ---------------------------------------------------------------------------
# Helper: build a minimal PeriodInputs with only the debt-relevant instant keys
# ---------------------------------------------------------------------------

def _rv(value: Optional[float], tags: list[str], flags: list[str] = None) -> ResolvedValue:
    return ResolvedValue(value=value, tags=tags, flags=flags or [], path="primary")


def _period(
    long_term_debt: Optional[ResolvedValue] = None,
    current_ltd: Optional[ResolvedValue] = None,
    short_term_debt: Optional[ResolvedValue] = None,
    debt_current: Optional[ResolvedValue] = None,
    debt_aggregate: Optional[ResolvedValue] = None,
    assets: Optional[ResolvedValue] = None,
) -> PeriodInputs:
    """Build a minimal PeriodInputs with only the keys _total_debt() reads."""
    instant = {}
    if long_term_debt is not None:
        instant["long_term_debt"] = long_term_debt
    if current_ltd is not None:
        instant["current_ltd"] = current_ltd
    if short_term_debt is not None:
        instant["short_term_debt"] = short_term_debt
    if debt_current is not None:
        instant["debt_current"] = debt_current
    if debt_aggregate is not None:
        instant["debt_aggregate"] = debt_aggregate
    if assets is not None:
        instant["assets"] = assets
    return PeriodInputs(
        period_end="2023-09-02",
        form_type="10-Q",
        filing_date="2023-10-01",
        instant=instant,
        quarterly={},
        ttm={},
    )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

passed = 0
failed = 0

def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        print(f"           → {detail}")
        failed += 1
    else:
        passed += 1


# ===========================================================================
# TEST 1 — LongTermDebtNoncurrent: NO subtraction should occur
# The primary tag is unambiguous. Even if current_ltd is present,
# we must NOT subtract it (LongTermDebtNoncurrent already excludes current).
# ===========================================================================
print("\n" + "="*70)
print("TEST 1 — LongTermDebtNoncurrent tag: subtraction must NOT fire")
print("="*70)
p = _period(
    long_term_debt=_rv(80_000.0, ["LongTermDebtNoncurrent"]),
    current_ltd=_rv(10_000.0, ["LongTermDebtCurrent"]),
    short_term_debt=_rv(5_000.0, ["ShortTermBorrowings"]),
)
total, src, flags, level = _total_debt(p)

check("level is 1 (disaggregated)",
      level == "1",
      f"got level={level}")
check("total = A(5000) + B(10000) + C(80000) = 95000",
      total == 95_000.0,
      f"got total={total}")
check("no double-count flag emitted",
      not any("subtracted" in f for f in flags),
      f"unexpected flags: {flags}")
check("source_tags contains LongTermDebtNoncurrent",
      "LongTermDebtNoncurrent" in src.get("long_term_debt", ""),
      f"src={src}")


# ===========================================================================
# TEST 2 — LongTermDebt tag WITH current_ltd present: subtraction MUST fire
# LongTermDebt is ambiguous — it often includes the current portion.
# Expected: c_val adjusted = 80000 - 10000 = 70000; total = 5000+10000+70000 = 85000
# ===========================================================================
print("\n" + "="*70)
print("TEST 2 — LongTermDebt tag + current_ltd present: subtraction MUST fire")
print("="*70)
p = _period(
    long_term_debt=_rv(80_000.0, ["LongTermDebt"]),
    current_ltd=_rv(10_000.0, ["LongTermDebtCurrent"]),
    short_term_debt=_rv(5_000.0, ["ShortTermBorrowings"]),
)
total, src, flags, level = _total_debt(p)

check("level is 1 (disaggregated)",
      level == "1",
      f"got level={level}")
check("total = 5000 + 10000 + (80000-10000) = 85000",
      total == 85_000.0,
      f"got total={total} — expected 85000")
check("double-count flag emitted",
      any("subtracted" in f for f in flags),
      f"no subtraction flag found in: {flags}")
check("flag mentions original raw value 80000",
      any("80000" in f or "80,000" in f for f in flags),
      f"flags: {flags}")
check("flag mentions subtracted amount 10000",
      any("10000" in f or "10,000" in f for f in flags),
      f"flags: {flags}")


# ===========================================================================
# TEST 3 — LongTermDebt tag WITHOUT current_ltd: NO subtraction
# If b_val is None (no current LTD), b_subtract = 0, so c_val unchanged.
# Expected: total = 0 + 0 + 80000 = 80000
# ===========================================================================
print("\n" + "="*70)
print("TEST 3 — LongTermDebt tag, NO current_ltd: subtraction must NOT fire")
print("="*70)
p = _period(
    long_term_debt=_rv(80_000.0, ["LongTermDebt"]),
    # no current_ltd, no short_term_debt
)
total, src, flags, level = _total_debt(p)

check("level is 1",
      level == "1",
      f"got level={level}")
check("total = 80000 (no subtraction when b_val is None)",
      total == 80_000.0,
      f"got total={total}")
check("no double-count flag emitted (b_subtract=0)",
      not any("subtracted" in f for f in flags),
      f"unexpected subtraction flag in: {flags}")


# ===========================================================================
# TEST 4 — LongTermDebt tag WITH current_ltd = 0: NO subtraction
# b_subtract = 0 → guard condition `b_subtract > 0` prevents subtraction.
# Expected: total = 80000
# ===========================================================================
print("\n" + "="*70)
print("TEST 4 — LongTermDebt tag + current_ltd=0: subtraction must NOT fire")
print("="*70)
p = _period(
    long_term_debt=_rv(80_000.0, ["LongTermDebt"]),
    current_ltd=_rv(0.0, ["LongTermDebtCurrent"]),
)
total, src, flags, level = _total_debt(p)

check("level is 1",
      level == "1",
      f"got level={level}")
check("total = 80000 (zero current_ltd does not subtract)",
      total == 80_000.0,
      f"got total={total}")
check("no double-count flag (b_subtract=0 guard)",
      not any("subtracted" in f for f in flags),
      f"unexpected flag: {flags}")


# ===========================================================================
# TEST 5 — LongTermDebtAndCapitalLeaseObligationsNoncurrent: NO subtraction
# This tag name contains "LongTermDebt" as a substring but the exact element
# "LongTermDebt" is NOT in the tags list. The `in` check on a list is exact.
# ===========================================================================
print("\n" + "="*70)
print("TEST 5 — LongTermDebtAndCapitalLeaseObligationsNoncurrent: no subtraction")
print("="*70)
p = _period(
    long_term_debt=_rv(80_000.0, ["LongTermDebtAndCapitalLeaseObligationsNoncurrent"]),
    current_ltd=_rv(10_000.0, ["LongTermDebtCurrent"]),
)
total, src, flags, level = _total_debt(p)

check("level is 1",
      level == "1",
      f"got level={level}")
check("total = 10000 + 80000 = 90000 (no subtraction)",
      total == 90_000.0,
      f"got total={total}")
check("no double-count subtraction flag",
      not any("subtracted" in f for f in flags),
      f"unexpected subtraction flag: {flags}")


# ===========================================================================
# TEST 6 — Level 2 path: LongTermDebt tag subtraction does NOT affect Level 2
# When Component C is None, we fall to Level 2 (aggregated tag).
# The LongTermDebt subtraction logic lives inside `if c_val is not None:` —
# Level 2 should be completely unaffected.
# ===========================================================================
print("\n" + "="*70)
print("TEST 6 — Level 2 path unaffected by the new logic")
print("="*70)
p = _period(
    # no long_term_debt (c_val = None → skip Level 1)
    current_ltd=_rv(10_000.0, ["LongTermDebtCurrent"]),
    debt_aggregate=_rv(95_000.0, ["DebtAndCapitalLeaseObligations"]),
)
total, src, flags, level = _total_debt(p)

check("level is 2 (aggregated fallback)",
      level == "2",
      f"got level={level}")
check("total = 95000 (aggregated tag)",
      total == 95_000.0,
      f"got total={total}")
check("Level 2 flag present",
      any("Level 2" in f for f in flags),
      f"flags: {flags}")
check("no double-count subtraction flag in Level 2",
      not any("subtracted" in f for f in flags),
      f"unexpected flag: {flags}")


# ===========================================================================
# TEST 7 — Realistic Rite Aid scenario (from our validation)
# Rite Aid at 2023-09-02: LongTermDebt=None (all reclassified to current),
# current_ltd=3,773,356,000, aggregated tag picks up the rest.
# This is existing behaviour — must not be broken by the new logic.
# ===========================================================================
print("\n" + "="*70)
print("TEST 7 — Rite Aid scenario: all debt in current_ltd, no LongTermDebt tag")
print("="*70)
p = _period(
    long_term_debt=_rv(None, []),          # None — all reclassified to current
    current_ltd=_rv(3_773_356_000.0, ["LongTermDebtCurrent"]),
    short_term_debt=_rv(None, []),
    debt_aggregate=_rv(3_785_074_000.0, ["DebtAndCapitalLeaseObligations"]),
)
total, src, flags, level = _total_debt(p)

check("level is 2 (Component C absent → aggregated)",
      level == "2",
      f"got level={level}")
check("total ~ 3.785B (aggregated tag wins)",
      abs(total - 3_785_074_000.0) < 1.0,
      f"got total={total}")
check("Component C absent flag present",
      any("Component C" in f for f in flags),
      f"flags: {flags}")
check("no double-count subtraction flag",
      not any("subtracted" in f for f in flags),
      f"unexpected flag: {flags}")


# ===========================================================================
# TEST 8 — Apple scenario: LongTermDebtNoncurrent present, no subtraction
# Apple uses LongTermDebtNoncurrent cleanly — this must not be disturbed.
# ===========================================================================
print("\n" + "="*70)
print("TEST 8 — Apple scenario: LongTermDebtNoncurrent, pristine Level 1")
print("="*70)
p = _period(
    long_term_debt=_rv(74_404_000_000.0, ["LongTermDebtNoncurrent"]),
    current_ltd=_rv(12_350_000_000.0, ["LongTermDebtCurrent"]),
    short_term_debt=_rv(8_000_000_000.0, ["CommercialPaper"]),
)
total, src, flags, level = _total_debt(p)

expected = 74_404_000_000.0 + 12_350_000_000.0 + 8_000_000_000.0

check("level is 1",
      level == "1",
      f"got level={level}")
check(f"total = {expected:,.0f}",
      abs(total - expected) < 1.0,
      f"got total={total:,.0f}")
check("no double-count subtraction flag",
      not any("subtracted" in f for f in flags),
      f"unexpected flag: {flags}")


# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "="*70)
print(f"SUMMARY — {passed} passed, {failed} failed")
print("="*70)
if failed == 0:
    print("All checks passed. The LongTermDebt double-count protection is working correctly.")
else:
    print(f"⚠️  {failed} check(s) failed. Review the FAIL messages above.")
    print("Most likely cause: the fix was not applied to _total_debt() in metrics.py,")
    print("or the tag check condition differs from what is expected.")