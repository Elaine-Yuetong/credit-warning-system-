"""
check_da_fallback.py
--------------------
Verifies the D&A derivation fallback added to _ebitda_ttm() and _ebitda_quarterly()
in metrics.py, and the two new concepts added to extractor.py.

Tests cover:
  A. New concepts exist in extractor.CONCEPTS
  B. _ebitda_ttm: normal path (dep_amort non-null) — fallback must NOT fire
  C. _ebitda_ttm: fallback fires when dep_amort null, Depreciation + Amort both present
  D. _ebitda_ttm: fallback fires with Depreciation only (Amort absent) — partial flag
  E. _ebitda_ttm: fallback does NOT fire when Depreciation also null — EBITDA stays null
  F. _ebitda_quarterly: same four scenarios as B-E
  G. Regression: Apple-like scenario — dep_amort present, fallback never reached
  H. Regression: Rite Aid-like scenario — dep_amort present, fallback never reached

Run with:
    python check_da_fallback.py

All tests must print PASS. Any FAIL means the changes were not applied correctly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from extractor import ResolvedValue, PeriodInputs, CONCEPTS
from metrics import _ebitda_ttm, _ebitda_quarterly

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rv(value: Optional[float], tags: list[str], flags: list[str] = None) -> ResolvedValue:
    return ResolvedValue(value=value, tags=tags, flags=flags or [], path="primary")


def _rv_null() -> ResolvedValue:
    return ResolvedValue(value=None, tags=[], flags=[], path="none")


def _period(
    oi_ttm: Optional[float] = 100.0,
    da_ttm: Optional[float] = 20.0,
    dep_ttm: Optional[float] = None,
    amort_ttm: Optional[float] = None,
    oi_q: Optional[float] = 25.0,
    da_q: Optional[float] = 5.0,
    dep_q: Optional[float] = None,
    amort_q: Optional[float] = None,
) -> PeriodInputs:
    """Build a minimal PeriodInputs with only the keys _ebitda_ttm/_ebitda_quarterly read."""

    def rv_or_null(val, tags):
        return _rv(val, tags) if val is not None else _rv_null()

    ttm = {
        "operating_income": rv_or_null(oi_ttm, ["OperatingIncomeLoss"]),
        "dep_amort":        rv_or_null(da_ttm,  ["DepreciationDepletionAndAmortization"]),
        "depreciation_only":       rv_or_null(dep_ttm,   ["Depreciation"]),
        "amortization_intangibles": rv_or_null(amort_ttm, ["AmortizationOfIntangibleAssets"]),
    }
    quarterly = {
        "operating_income": rv_or_null(oi_q,    ["OperatingIncomeLoss"]),
        "dep_amort":        rv_or_null(da_q,     ["DepreciationDepletionAndAmortization"]),
        "depreciation_only":       rv_or_null(dep_q,    ["Depreciation"]),
        "amortization_intangibles": rv_or_null(amort_q,  ["AmortizationOfIntangibleAssets"]),
    }
    return PeriodInputs(
        period_end="2023-09-30",
        form_type="10-Q",
        filing_date="2023-11-01",
        instant={},
        quarterly=quarterly,
        ttm=ttm,
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
# A. New concepts exist in extractor.CONCEPTS
# ===========================================================================
print("\n" + "="*70)
print("A. New concepts exist in extractor.CONCEPTS")
print("="*70)

check("'depreciation_only' in CONCEPTS",
      "depreciation_only" in CONCEPTS,
      "key missing — add concept to extractor.py")

check("'amortization_intangibles' in CONCEPTS",
      "amortization_intangibles" in CONCEPTS,
      "key missing — add concept to extractor.py")

if "depreciation_only" in CONCEPTS:
    check("depreciation_only uses 'Depreciation' tag",
          "Depreciation" in CONCEPTS["depreciation_only"].tags,
          f"tags={CONCEPTS['depreciation_only'].tags}")
    check("depreciation_only kind=duration",
          CONCEPTS["depreciation_only"].kind == "duration",
          f"kind={CONCEPTS['depreciation_only'].kind}")

if "amortization_intangibles" in CONCEPTS:
    check("amortization_intangibles uses 'AmortizationOfIntangibleAssets' tag",
          "AmortizationOfIntangibleAssets" in CONCEPTS["amortization_intangibles"].tags,
          f"tags={CONCEPTS['amortization_intangibles'].tags}")
    check("amortization_intangibles kind=duration",
          CONCEPTS["amortization_intangibles"].kind == "duration",
          f"kind={CONCEPTS['amortization_intangibles'].kind}")


# ===========================================================================
# B. _ebitda_ttm: normal path — dep_amort present, fallback must NOT fire
# ===========================================================================
print("\n" + "="*70)
print("B. _ebitda_ttm: normal path (dep_amort present) — fallback must NOT fire")
print("="*70)

p = _period(oi_ttm=100.0, da_ttm=20.0)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA = 120.0",
      ebitda == 120.0,
      f"got {ebitda}")
check("dep_amort key in source_tags",
      "dep_amort" in src,
      f"src={src}")
check("DepreciationDepletionAndAmortization in source_tags",
      "DepreciationDepletionAndAmortization" in src.get("dep_amort", ""),
      f"src={src}")
check("no derivation flag emitted",
      not any("derived" in f.lower() or "AmortizationOfIntangibleAssets" in f for f in flags),
      f"unexpected derivation flags: {flags}")


# ===========================================================================
# C. _ebitda_ttm: dep_amort null, BOTH Depreciation + Amort present
# ===========================================================================
print("\n" + "="*70)
print("C. _ebitda_ttm: dep_amort null, Depreciation=15 + Amort=7 → D&A=22")
print("="*70)

p = _period(oi_ttm=100.0, da_ttm=None, dep_ttm=15.0, amort_ttm=7.0)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA = 100 + 15 + 7 = 122.0",
      ebitda == 122.0,
      f"got {ebitda}")
check("derivation flag emitted",
      any("Depreciation + AmortizationOfIntangibleAssets" in f for f in flags),
      f"flags={flags}")
check("no partial D&A flag (both components present)",
      not any("depreciation-only" in f.lower() for f in flags),
      f"unexpected partial flag: {flags}")
check("dep_amort in source_tags contains Depreciation",
      "Depreciation" in src.get("dep_amort", ""),
      f"src={src}")
check("dep_amort in source_tags contains AmortizationOfIntangibleAssets",
      "AmortizationOfIntangibleAssets" in src.get("dep_amort", ""),
      f"src={src}")


# ===========================================================================
# D. _ebitda_ttm: dep_amort null, Depreciation present, Amort ABSENT
# ===========================================================================
print("\n" + "="*70)
print("D. _ebitda_ttm: dep_amort null, Depreciation=15 only → D&A=15, partial flag")
print("="*70)

p = _period(oi_ttm=100.0, da_ttm=None, dep_ttm=15.0, amort_ttm=None)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA = 100 + 15 = 115.0",
      ebitda == 115.0,
      f"got {ebitda}")
check("derivation flag emitted",
      any("Depreciation + AmortizationOfIntangibleAssets" in f for f in flags),
      f"flags={flags}")
check("partial D&A flag emitted (amort absent)",
      any("depreciation-only" in f.lower() or "AmortizationOfIntangibleAssets absent" in f
          for f in flags),
      f"no partial flag found in: {flags}")


# ===========================================================================
# E. _ebitda_ttm: dep_amort null AND Depreciation null → EBITDA stays null
# ===========================================================================
print("\n" + "="*70)
print("E. _ebitda_ttm: dep_amort null + Depreciation null → EBITDA must be null")
print("="*70)

p = _period(oi_ttm=100.0, da_ttm=None, dep_ttm=None, amort_ttm=5.0)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA is None (no dep_amort, no Depreciation — Amort alone not enough)",
      ebitda is None,
      f"got {ebitda} — fallback should require Depreciation to be non-null")
check("D&A unavailable flag emitted",
      any("D&A" in f or "d&a" in f.lower() for f in flags),
      f"flags={flags}")


# ===========================================================================
# F. _ebitda_quarterly: same four scenarios
# ===========================================================================
print("\n" + "="*70)
print("F. _ebitda_quarterly: normal path — dep_amort present")
print("="*70)

p = _period(oi_q=25.0, da_q=5.0)
result = _ebitda_quarterly(p)
check("quarterly EBITDA = 30.0",
      result == 30.0,
      f"got {result}")

print("\n" + "─"*70)
print("F2. _ebitda_quarterly: dep_amort null, Depreciation=4 + Amort=2 → 6")
print("─"*70)
p = _period(oi_q=25.0, da_q=None, dep_q=4.0, amort_q=2.0)
result = _ebitda_quarterly(p)
check("quarterly EBITDA = 25 + 4 + 2 = 31.0",
      result == 31.0,
      f"got {result}")

print("\n" + "─"*70)
print("F3. _ebitda_quarterly: dep_amort null, Depreciation=4 only → 4")
print("─"*70)
p = _period(oi_q=25.0, da_q=None, dep_q=4.0, amort_q=None)
result = _ebitda_quarterly(p)
check("quarterly EBITDA = 25 + 4 = 29.0 (depreciation only)",
      result == 29.0,
      f"got {result}")

print("\n" + "─"*70)
print("F4. _ebitda_quarterly: dep_amort null + Depreciation null → None")
print("─"*70)
p = _period(oi_q=25.0, da_q=None, dep_q=None, amort_q=2.0)
result = _ebitda_quarterly(p)
check("quarterly EBITDA is None (Amort alone not enough)",
      result is None,
      f"got {result}")


# ===========================================================================
# G. Regression: Apple-like (DepreciationDepletionAndAmortization present)
# ===========================================================================
print("\n" + "="*70)
print("G. Regression — Apple-like: DepreciationDepletionAndAmortization present")
print("="*70)

# Apple uses DepreciationDepletionAndAmortization cleanly; fallback must never fire.
p = _period(oi_ttm=120_000.0, da_ttm=12_000.0, dep_ttm=8_000.0, amort_ttm=2_000.0)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA = 132000 (dep_amort used, not fallback)",
      ebitda == 132_000.0,
      f"got {ebitda}")
check("no derivation flag (primary dep_amort tag was used)",
      not any("derived" in f.lower() or "AmortizationOfIntangibleAssets" in f for f in flags),
      f"unexpected derivation flag: {flags}")
check("source tag is DepreciationDepletionAndAmortization",
      "DepreciationDepletionAndAmortization" in src.get("dep_amort", ""),
      f"src={src}")


# ===========================================================================
# H. Regression: Rite Aid-like (dep_amort present via TTM series)
# ===========================================================================
print("\n" + "="*70)
print("H. Regression — Rite Aid-like: dep_amort present, negative operating income")
print("="*70)

p = _period(oi_ttm=-500.0, da_ttm=273.0)
ebitda, src, flags = _ebitda_ttm(p)

check("EBITDA = -227.0 (negative is correct — not suppressed)",
      ebitda == -227.0,
      f"got {ebitda}")
check("no derivation flag",
      not any("AmortizationOfIntangibleAssets" in f for f in flags),
      f"unexpected flag: {flags}")
check("dep_amort in source_tags",
      "dep_amort" in src,
      f"src={src}")


# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "="*70)
print(f"SUMMARY — {passed} passed, {failed} failed")
print("="*70)
if failed == 0:
    print("All checks passed. D&A derivation fallback is working correctly.")
    print("Both _ebitda_ttm and _ebitda_quarterly handle the three fallback cases:")
    print("  1. dep_amort present → use directly (normal path)")
    print("  2. dep_amort null, Depreciation + Amort present → derive sum")
    print("  3. dep_amort null, Depreciation only → derive with partial flag")
    print("  4. dep_amort null, Depreciation also null → EBITDA stays null")
else:
    print(f"⚠️  {failed} check(s) failed.")
    print("\nMost likely causes:")
    print("  A failures  → new concepts not added to extractor.py CONCEPTS dict")
    print("  B/G/H failures → fallback incorrectly fires when dep_amort is present")
    print("  C/D failures → fallback block not added to _ebitda_ttm() in metrics.py")
    print("  E failure   → fallback fires on Amort-only (Depreciation must be non-null guard missing)")
    print("  F failures  → fallback block not added to _ebitda_quarterly() in metrics.py")
