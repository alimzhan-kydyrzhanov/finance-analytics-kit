"""Synthetic corporate finance data: GL actuals, plan, FX rates, master data.

Three company codes in three currencies, 12 months of 2026. A few raw postings are
broken on purpose (unmapped G/L account, missing FX rate, duplicate document) so the
data quality layer has something to catch. All numbers are invented.
"""
import random

import pandas as pd

YEAR = 2026
COMPANIES = pd.DataFrame([
    ("CZ01", "Company Czechia", "CZK"),
    ("DE01", "Company Germany", "EUR"),
    ("US01", "Company USA", "USD"),
], columns=["company_code", "company_name", "currency"])

ACCOUNTS = pd.DataFrame([
    (400000, "Cloud subscription revenue", "REVENUE"),
    (410000, "Services revenue", "REVENUE"),
    (500000, "Cost of cloud", "COGS"),
    (510000, "Cost of services", "COGS"),
    (600000, "Personnel expenses", "OPEX"),
    (610000, "Travel expenses", "OPEX"),
    (620000, "IT and licenses", "OPEX"),
    (630000, "Marketing", "OPEX"),
], columns=["gl_account", "account_name", "pnl_line"])

COST_CENTERS = ["CC-FIN", "CC-RND", "CC-SAL", "CC-MKT"]
BASE_EUR = {400000: 900_000, 410000: 300_000, 500000: 280_000, 510000: 190_000,
            600000: 380_000, 610000: 25_000, 620000: 60_000, 630000: 70_000}
SIZE = {"CZ01": 0.4, "DE01": 1.0, "US01": 0.8}
FX_BASE = {"EUR": 1.0, "CZK": 0.0400, "USD": 0.9200}  # 1 unit of currency in EUR


def fx_rates(seed=1) -> pd.DataFrame:
    rnd = random.Random(seed)
    rows = [(f"{YEAR}-{m:02d}", cur, round(base * (1 + rnd.uniform(-0.02, 0.02)), 6) if cur != "EUR" else 1.0)
            for m in range(1, 13) for cur, base in FX_BASE.items()]
    return pd.DataFrame(rows, columns=["period", "currency", "rate_to_eur"])


def _rows(version, seed, fx):
    rnd = random.Random(seed)
    rate = {(r.period, r.currency): r.rate_to_eur for r in fx.itertuples()}
    rows, doc = [], 0
    for c in COMPANIES.itertuples():
        for m in range(1, 13):
            period = f"{YEAR}-{m:02d}"
            for acc, base in BASE_EUR.items():
                eur = base * SIZE[c.company_code] * (1 + 0.02 * m) * (1 + rnd.uniform(-0.08, 0.08))
                doc += 1
                rows.append({"doc_id": f"{version[:1]}{doc:06d}", "company_code": c.company_code,
                             "period": period, "gl_account": acc, "cost_center": rnd.choice(COST_CENTERS),
                             "currency": c.currency,
                             "amount_lc": round(eur / rate[(period, c.currency)], 2)})
    return pd.DataFrame(rows)


def make_actuals(fx) -> pd.DataFrame:
    df = _rows("ACT", 11, fx)
    bad = pd.DataFrame([
        {"doc_id": "A900001", "company_code": "DE01", "period": "2026-03", "gl_account": 999999,
         "cost_center": "CC-FIN", "currency": "EUR", "amount_lc": 1234.0},          # unmapped account
        {"doc_id": "A900002", "company_code": "DE01", "period": "2026-04", "gl_account": 610000,
         "cost_center": "CC-SAL", "currency": "GBP", "amount_lc": 800.0},           # no GBP rate
    ])
    dup = df.iloc[[5]].copy()                                                       # double-loaded document
    return pd.concat([df, bad, dup], ignore_index=True)


def make_plan(fx) -> pd.DataFrame:
    return _rows("PLN", 22, fx)
