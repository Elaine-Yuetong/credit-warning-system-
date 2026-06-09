"""
db.py — SQLite persistence for the Credit Warning System (spec/SECTION_6.md §6.3).

Creates the six-table schema verbatim on first run and writes issuer + metric_values
(+ alerts) rows. metric_values is the core output table, keyed by the unique tuple
(cik, period_end_date, metric_name, formula_version); re-runs upsert in place.

time_series, maturity_schedule, and filings are created (ready for later phases/metrics)
but not populated by the Phase-2 four-metric pipeline.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from extractor import IssuerMetadata
from metrics import MetricResult
from thresholds import Classification

DB_PATH = "credit_warning.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS issuers (
    cik             TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    tickers         TEXT,
    sic_code        TEXT,
    sector_group    TEXT,
    volatility_cat  TEXT,
    fiscal_year_end TEXT,
    onboarded_date  TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS filings (
    accession_number    TEXT PRIMARY KEY,
    cik                 TEXT NOT NULL,
    form_type           TEXT,
    period_end_date     TEXT,
    filing_date         TEXT,
    processed           INTEGER,
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);

CREATE TABLE IF NOT EXISTS metric_values (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    filing_date     TEXT NOT NULL,
    form_type       TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    formula_version TEXT,
    value           REAL,
    value_unit      TEXT,
    alert_level     TEXT,
    flags           TEXT,
    source_tags     TEXT,
    audit_log       TEXT,
    extraction_path TEXT,
    created_at      TEXT,
    FOREIGN KEY (cik) REFERENCES issuers(cik),
    UNIQUE (cik, period_end_date, metric_name, formula_version)
);

CREATE TABLE IF NOT EXISTS time_series (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    value           REAL,
    yoy_change      REAL,
    qoq_change      REAL,
    trend_class     TEXT,
    FOREIGN KEY (cik) REFERENCES issuers(cik),
    UNIQUE (cik, metric_name, period_end_date)
);

CREATE TABLE IF NOT EXISTS maturity_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    as_of_date      TEXT NOT NULL,
    fiscal_year_end TEXT NOT NULL,
    maturity_year   INTEGER,
    amount_millions REAL,
    source          TEXT,
    patch_source    TEXT,
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cik             TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    alert_level     TEXT NOT NULL,
    prior_level     TEXT,
    trigger_reason  TEXT,
    created_at      TEXT,
    FOREIGN KEY (cik) REFERENCES issuers(cik)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def upsert_issuer(conn: sqlite3.Connection, meta: IssuerMetadata, cls: Classification,
                  notes: Optional[str] = None) -> None:
    conn.execute(
        """
        INSERT INTO issuers (cik, name, tickers, sic_code, sector_group, volatility_cat,
                             fiscal_year_end, onboarded_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cik) DO UPDATE SET
            name=excluded.name, tickers=excluded.tickers, sic_code=excluded.sic_code,
            sector_group=excluded.sector_group, volatility_cat=excluded.volatility_cat,
            fiscal_year_end=excluded.fiscal_year_end, notes=excluded.notes
        """,
        (meta.cik, meta.name, json.dumps(meta.tickers), meta.sic_code, cls.sector_group,
         cls.volatility_cat, meta.fiscal_year_end, _now(), notes),
    )
    conn.commit()


def write_metrics(conn: sqlite3.Connection, cik: str, metrics: list[MetricResult]) -> None:
    """Upsert metric_values rows and append alerts-history rows for any alerting metric."""
    for m in metrics:
        # metric_values columns filing_date/form_type are NOT NULL; default sensibly.
        filing_date = m.filing_date or ""
        form_type = m.form_type or ""
        conn.execute(
            """
            INSERT INTO metric_values
                (cik, period_end_date, filing_date, form_type, metric_name, formula_version,
                 value, value_unit, alert_level, flags, source_tags, audit_log,
                 extraction_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cik, period_end_date, metric_name, formula_version) DO UPDATE SET
                filing_date=excluded.filing_date, form_type=excluded.form_type,
                value=excluded.value, value_unit=excluded.value_unit,
                alert_level=excluded.alert_level, flags=excluded.flags,
                source_tags=excluded.source_tags, audit_log=excluded.audit_log,
                extraction_path=excluded.extraction_path, created_at=excluded.created_at
            """,
            (cik, m.period_end, filing_date, form_type, m.metric_name, m.formula_version,
             m.value, m.value_unit, m.alert_level, json.dumps(m.flags),
             json.dumps(m.source_tags), json.dumps(m.audit_log, default=str),
             m.extraction_path, _now()),
        )
        if m.alert_level:
            conn.execute(
                """
                INSERT INTO alerts (cik, metric_name, period_end_date, alert_level,
                                    prior_level, trigger_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (cik, m.metric_name, m.period_end, m.alert_level, None,
                 "; ".join(m.flags) if m.flags else None, _now()),
            )
    conn.commit()
