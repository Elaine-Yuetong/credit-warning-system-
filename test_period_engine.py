"""
Unit tests for the highest-risk logic in extractor.py: the duration-fact period engine
(YTD -> quarterly subtraction) and TTM aggregation (§6.4 / FREE_CASH_FLOW.md Difference 3).

Run:  python -m unittest test_period_engine   (or)   python test_period_engine.py
No network — all inputs are synthetic companyfacts fixtures.
"""

import unittest

from extractor import (
    Concept,
    ResolvedValue,
    _classify_span,
    _derive_quarterly_series,
    _ttm,
)

TAG = "TestDurationTag"
CONCEPT = Concept(key="test", kind="duration", mode="first", tags=(TAG,))


def _entry(start, end, val, filed="2024-01-01", form="10-Q"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form,
            "accn": f"acc-{end}"}


def _facts(entries):
    """Wrap raw fact entries in the companyfacts JSON shape."""
    return {"facts": {"us-gaap": {TAG: {"units": {"USD": entries}}}}}


# A full fiscal year 2023 of cumulative (YTD) duration facts.
FY2023 = [
    _entry("2023-01-01", "2023-03-31", 100.0),  # Q1 standalone (3M)
    _entry("2023-01-01", "2023-06-30", 250.0),  # H1 YTD (6M)
    _entry("2023-01-01", "2023-09-30", 420.0),  # 9M YTD
    _entry("2023-01-01", "2023-12-31", 600.0, form="10-K"),  # FY
]


class TestSpanClassification(unittest.TestCase):
    def test_buckets(self):
        self.assertEqual(_classify_span("2023-01-01", "2023-03-31")[1], "Q")
        self.assertEqual(_classify_span("2023-01-01", "2023-06-30")[1], "H1")
        self.assertEqual(_classify_span("2023-01-01", "2023-09-30")[1], "9M")
        self.assertEqual(_classify_span("2023-01-01", "2023-12-31")[1], "FY")

    def test_instant_has_no_span(self):
        self.assertEqual(_classify_span(None, "2023-12-31"), (None, None))

    def test_unclassifiable_span(self):
        # ~2 months is not a recognised reporting window.
        days, bucket = _classify_span("2023-01-01", "2023-02-28")
        self.assertIsNone(bucket)
        self.assertEqual(days, 58)


class TestQuarterlyDerivation(unittest.TestCase):
    def test_subtraction_chain(self):
        series = _derive_quarterly_series(_facts(FY2023), CONCEPT)
        # Q1 used directly; Q2=H1-Q1; Q3=9M-H1; Q4=FY-9M.
        self.assertAlmostEqual(series["2023-03-31"].value, 100.0)
        self.assertAlmostEqual(series["2023-06-30"].value, 150.0)
        self.assertAlmostEqual(series["2023-09-30"].value, 170.0)
        self.assertAlmostEqual(series["2023-12-31"].value, 180.0)

    def test_paths_flagged_as_derived(self):
        series = _derive_quarterly_series(_facts(FY2023), CONCEPT)
        # Q1 is a genuine 3-month fact -> reported_quarterly; Q2-Q4 are derived by subtraction.
        self.assertEqual(series["2023-03-31"].path, "reported_quarterly")
        self.assertEqual(series["2023-06-30"].path, "derived_quarterly")
        self.assertEqual(series["2023-09-30"].path, "derived_quarterly")
        self.assertEqual(series["2023-12-31"].path, "derived_quarterly")
        self.assertTrue(any("Q2 derived" in f for f in series["2023-06-30"].flags))

    def test_derived_quarters_sum_to_annual(self):
        series = _derive_quarterly_series(_facts(FY2023), CONCEPT)
        total = sum(series[d].value for d in
                    ("2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31"))
        self.assertAlmostEqual(total, 600.0)  # equals the reported FY figure

    def test_reported_quarter_overrides_derivation(self):
        # A directly-reported Q2 (quarter-only, start = Q2 start) must win over H1-Q1.
        entries = FY2023 + [_entry("2023-04-01", "2023-06-30", 155.0)]
        series = _derive_quarterly_series(_facts(entries), CONCEPT)
        self.assertAlmostEqual(series["2023-06-30"].value, 155.0)
        self.assertEqual(series["2023-06-30"].path, "reported_quarterly")

    def test_missing_q1_falls_back_to_ytd(self):
        # Without Q1, Q2 cannot be derived — store H1 YTD with a flag, never guess.
        entries = [e for e in FY2023 if e["end"] != "2023-03-31"]
        series = _derive_quarterly_series(_facts(entries), CONCEPT)
        self.assertAlmostEqual(series["2023-06-30"].value, 250.0)  # H1 YTD retained
        self.assertTrue(any("Q1 unavailable" in f for f in series["2023-06-30"].flags))

    def test_no_duration_facts_returns_empty(self):
        self.assertEqual(_derive_quarterly_series(_facts([]), CONCEPT), {})

    def test_latest_filed_wins_on_restatement(self):
        # Same period filed twice; the later filing (restatement) should be used.
        entries = FY2023 + [_entry("2023-01-01", "2023-03-31", 111.0, filed="2024-06-01")]
        series = _derive_quarterly_series(_facts(entries), CONCEPT)
        self.assertAlmostEqual(series["2023-03-31"].value, 111.0)


class TestTTM(unittest.TestCase):
    def _series(self, values):
        """Build {end: ResolvedValue} from {end: value}."""
        return {end: ResolvedValue(v, [TAG], [], "derived_quarterly") for end, v in values.items()}

    def test_four_quarter_sum(self):
        ends = ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31",
                "2024-03-31"]
        series = self._series({e: 100.0 for e in ends})
        ttm = _ttm(series, ends)
        # First three ends lack 4 trailing quarters -> None.
        self.assertIsNone(ttm["2023-03-31"].value)
        self.assertIsNone(ttm["2023-09-30"].value)
        # Fourth end onward: rolling sum of 4 quarters.
        self.assertAlmostEqual(ttm["2023-12-31"].value, 400.0)
        self.assertAlmostEqual(ttm["2024-03-31"].value, 400.0)

    def test_rolling_window_uses_trailing_four(self):
        ends = ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"]
        series = self._series({"2023-03-31": 10, "2023-06-30": 20, "2023-09-30": 30,
                               "2023-12-31": 40, "2024-03-31": 50})
        ttm = _ttm(series, ends)
        self.assertAlmostEqual(ttm["2023-12-31"].value, 10 + 20 + 30 + 40)
        self.assertAlmostEqual(ttm["2024-03-31"].value, 20 + 30 + 40 + 50)  # drops oldest

    def test_missing_quarter_nulls_ttm(self):
        ends = ["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31"]
        series = self._series({"2023-03-31": 100, "2023-06-30": 100, "2023-12-31": 100})
        series["2023-09-30"] = ResolvedValue(None, [], ["missing"], "none")
        ttm = _ttm(series, ends)
        self.assertIsNone(ttm["2023-12-31"].value)
        self.assertTrue(any("trailing quarter is missing" in f for f in ttm["2023-12-31"].flags))


if __name__ == "__main__":
    unittest.main(verbosity=2)
