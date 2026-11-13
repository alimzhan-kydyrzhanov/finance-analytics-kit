"""Finance KPIs in SQL on the analytic model (CTEs, CASE, window functions)."""
import pandas as pd

PNL_SQL = """
WITH lines AS (
  SELECT company_code, period,
         SUM(CASE WHEN pnl_line = 'REVENUE' THEN amount_eur ELSE 0 END) AS revenue,
         SUM(CASE WHEN pnl_line = 'COGS'    THEN amount_eur ELSE 0 END) AS cogs,
         SUM(CASE WHEN pnl_line = 'OPEX'    THEN amount_eur ELSE 0 END) AS opex
    FROM v_pnl WHERE version = :version
   GROUP BY company_code, period
)
SELECT company_code, period, revenue, cogs, opex,
       revenue - cogs                                   AS gross_profit,
       ROUND(100.0 * (revenue - cogs) / revenue, 2)     AS gross_margin_pct,
       revenue - cogs - opex                            AS operating_profit,
       SUM(revenue - cogs - opex) OVER (PARTITION BY company_code ORDER BY period
                                        ROWS UNBOUNDED PRECEDING) AS operating_profit_ytd
  FROM lines ORDER BY company_code, period
"""

VARIANCE_SQL = """
WITH a AS (SELECT company_code, pnl_line, SUM(amount_eur) AS actual FROM v_pnl
            WHERE version = 'ACT' AND period <= :to_period GROUP BY 1, 2),
     p AS (SELECT company_code, pnl_line, SUM(amount_eur) AS plan FROM v_pnl
            WHERE version = 'PLN' AND period <= :to_period GROUP BY 1, 2)
SELECT a.company_code, a.pnl_line, ROUND(actual, 2) AS actual, ROUND(plan, 2) AS plan,
       ROUND(actual - plan, 2) AS variance,
       ROUND(100.0 * (actual - plan) / plan, 2) AS variance_pct,
       CASE WHEN a.pnl_line = 'REVENUE' THEN (actual >= plan) ELSE (actual <= plan) END AS favourable
  FROM a JOIN p USING (company_code, pnl_line)
 ORDER BY a.company_code, a.pnl_line
"""


def pnl(conn, version="ACT") -> pd.DataFrame:
    return pd.read_sql(PNL_SQL, conn, params={"version": version})


def variance(conn, to_period="2026-12") -> pd.DataFrame:
    """Year-to-date actual vs plan. Favourable = more revenue, or less cost, than planned."""
    return pd.read_sql(VARIANCE_SQL, conn, params={"to_period": to_period})
