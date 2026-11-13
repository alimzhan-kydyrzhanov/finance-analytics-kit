"""Migration check: the new analytic model must show the same numbers as the legacy report.

When reports move to a new frontend (for example to SAP Analytics Cloud stories on a new
data model) finance users must trust that nothing changed. The legacy report is rebuilt
here with an independent code path (pandas instead of SQL) and compared cell by cell.
"""
import pandas as pd

from . import data

# Legacy KPI names -> measures of the new model. Every legacy KPI must be mapped.
KPI_CATALOG = {
    "Umsatz / Revenue": "revenue",
    "Cost of Sales": "cogs",
    "Operating Expenses": "opex",
    "Gross Profit": "gross_profit",
    "EBIT (operating)": "operating_profit",
}


def legacy_report(actuals: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """How the old system computed P&L lines in EUR (clean data only)."""
    df = actuals.drop_duplicates(subset=["doc_id"]).merge(fx, on=["period", "currency"])
    df = df.merge(data.ACCOUNTS, on="gl_account")
    df["amount_eur"] = (df["amount_lc"] * df["rate_to_eur"]).round(2)
    wide = df.pivot_table(index=["company_code", "period"], columns="pnl_line",
                          values="amount_eur", aggfunc="sum").reset_index()
    return wide.rename(columns={"REVENUE": "revenue", "COGS": "cogs", "OPEX": "opex"})


def reconcile(legacy: pd.DataFrame, new: pd.DataFrame, tol=0.05) -> pd.DataFrame:
    """Rows where any measure differs by more than `tol` EUR (rounding tolerance)."""
    m = legacy.merge(new, on=["company_code", "period"], how="outer", suffixes=("_legacy", "_new"),
                     indicator="found_in")
    out = []
    for r in m.to_dict("records"):
        if r["found_in"] != "both":  # a row exists only in one of the two reports
            out.append({"company_code": r["company_code"], "period": r["period"], "measure": "row",
                        "legacy": None, "new": None, "diff": None})
            continue
        for k in ("revenue", "cogs", "opex"):
            a, b = r[f"{k}_legacy"], r[f"{k}_new"]
            if abs(a - b) > tol:
                out.append({"company_code": r["company_code"], "period": r["period"], "measure": k,
                            "legacy": a, "new": b, "diff": round(b - a, 2)})
    return pd.DataFrame(out, columns=["company_code", "period", "measure", "legacy", "new", "diff"])


def unmapped_kpis(new_measures) -> list:
    return [k for k, v in KPI_CATALOG.items() if v not in set(new_measures)]
