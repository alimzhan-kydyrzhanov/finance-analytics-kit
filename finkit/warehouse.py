"""Layered data warehouse in SQLite, modelled on SAP Datasphere / Business Data Cloud ideas.

  inbound layer      raw_* tables, loaded as delivered by the source (no changes)
  harmonization      data quality -> quarantine, currency conversion to EUR, P&L mapping
  reporting layer    star schema: fact_pnl + dim_company / dim_account / dim_period
  analytic model     v_pnl view with measures, the single source for KPIs and stories
"""
import sqlite3

import pandas as pd

from . import data

SQL_HARMONIZE = """
DROP TABLE IF EXISTS quarantine;
CREATE TABLE quarantine AS
  SELECT p.*, 'unmapped_gl_account' AS reason FROM raw_postings p
   WHERE p.gl_account NOT IN (SELECT gl_account FROM raw_accounts)
  UNION ALL
  SELECT p.*, 'missing_fx_rate' FROM raw_postings p
   WHERE NOT EXISTS (SELECT 1 FROM raw_fx f WHERE f.period = p.period AND f.currency = p.currency)
  UNION ALL
  SELECT p.*, 'duplicate_document' FROM raw_postings p
   WHERE p.rowid NOT IN (SELECT MIN(rowid) FROM raw_postings GROUP BY doc_id, version);

DROP VIEW IF EXISTS stg_postings;
CREATE VIEW stg_postings AS
  SELECT p.doc_id, p.version, p.company_code, p.period, p.gl_account, p.cost_center,
         a.pnl_line, p.amount_lc, p.currency, ROUND(p.amount_lc * f.rate_to_eur, 2) AS amount_eur
    FROM raw_postings p
    JOIN raw_accounts a ON a.gl_account = p.gl_account
    JOIN raw_fx f       ON f.period = p.period AND f.currency = p.currency
   WHERE p.rowid IN (SELECT MIN(rowid) FROM raw_postings GROUP BY doc_id, version);

DROP TABLE IF EXISTS dim_company;  CREATE TABLE dim_company AS SELECT * FROM raw_companies;
DROP TABLE IF EXISTS dim_account;  CREATE TABLE dim_account AS SELECT * FROM raw_accounts;
DROP TABLE IF EXISTS dim_period;
CREATE TABLE dim_period AS
  SELECT DISTINCT period, CAST(substr(period, 1, 4) AS INT) AS year,
         CAST(substr(period, 6, 2) AS INT) AS month,
         'Q' || ((CAST(substr(period, 6, 2) AS INT) + 2) / 3) AS quarter
    FROM raw_fx;

DROP TABLE IF EXISTS fact_pnl;
CREATE TABLE fact_pnl AS
  SELECT version, company_code, period, gl_account, cost_center, SUM(amount_eur) AS amount_eur
    FROM stg_postings GROUP BY version, company_code, period, gl_account, cost_center;

DROP VIEW IF EXISTS v_pnl;
CREATE VIEW v_pnl AS
  SELECT f.version, f.company_code, c.company_name, f.period, d.quarter, d.month,
         a.pnl_line, a.account_name, f.cost_center, f.amount_eur
    FROM fact_pnl f
    JOIN dim_company c ON c.company_code = f.company_code
    JOIN dim_account a ON a.gl_account = f.gl_account
    JOIN dim_period d  ON d.period = f.period;
"""


def load_inbound(conn, actuals, plan, fx):
    raw = pd.concat([actuals.assign(version="ACT"), plan.assign(version="PLN")], ignore_index=True)
    raw.to_sql("raw_postings", conn, if_exists="replace", index=False)
    fx.to_sql("raw_fx", conn, if_exists="replace", index=False)
    data.ACCOUNTS.to_sql("raw_accounts", conn, if_exists="replace", index=False)
    data.COMPANIES.to_sql("raw_companies", conn, if_exists="replace", index=False)


def build(conn=None, actuals=None, plan=None, fx=None) -> sqlite3.Connection:
    conn = conn or sqlite3.connect(":memory:")
    fx = data.fx_rates() if fx is None else fx
    actuals = data.make_actuals(fx) if actuals is None else actuals
    plan = data.make_plan(fx) if plan is None else plan
    load_inbound(conn, actuals, plan, fx)
    conn.executescript(SQL_HARMONIZE)
    return conn


def quarantine(conn) -> pd.DataFrame:
    return pd.read_sql("SELECT doc_id, version, company_code, period, gl_account, currency, reason "
                       "FROM quarantine ORDER BY reason", conn)
