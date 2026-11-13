import pandas as pd
import pytest
from openpyxl import load_workbook

from finkit import assistant, data, export, kpis, migration, warehouse


@pytest.fixture(scope="module")
def setup():
    fx = data.fx_rates()
    actuals, plan = data.make_actuals(fx), data.make_plan(fx)
    conn = warehouse.build(actuals=actuals, plan=plan, fx=fx)
    return conn, actuals, plan, fx


def test_quality_layer_quarantines_every_injected_problem(setup):
    conn, actuals, *_ = setup
    reasons = set(warehouse.quarantine(conn)["reason"])
    assert reasons == {"unmapped_gl_account", "missing_fx_rate", "duplicate_document"}
    clean = conn.execute("SELECT COUNT(*) FROM stg_postings WHERE version='ACT'").fetchone()[0]
    assert clean == len(actuals) - 3


def test_star_schema_and_analytic_model(setup):
    conn = setup[0]
    assert conn.execute("SELECT COUNT(*) FROM dim_period").fetchone()[0] == 12
    assert conn.execute("SELECT DISTINCT quarter FROM dim_period WHERE month=5").fetchone()[0] == "Q2"
    fact = conn.execute("SELECT ROUND(SUM(amount_eur),2) FROM fact_pnl").fetchone()[0]
    model = conn.execute("SELECT ROUND(SUM(amount_eur),2) FROM v_pnl").fetchone()[0]
    assert fact == model  # joins in the analytic model lose nothing


def test_currency_conversion(setup):
    conn = setup[0]
    row = conn.execute("SELECT amount_lc, amount_eur FROM stg_postings WHERE currency='CZK' LIMIT 1").fetchone()
    assert 0.038 < row[1] / row[0] < 0.042


def test_pnl_math_and_ytd_window(setup):
    p = kpis.pnl(setup[0])
    r = p.iloc[0]
    assert r.gross_profit == pytest.approx(r.revenue - r.cogs)
    assert r.gross_margin_pct == pytest.approx(100 * (r.revenue - r.cogs) / r.revenue, abs=0.01)
    de = p[p.company_code == "DE01"]
    assert de.operating_profit_ytd.iloc[-1] == pytest.approx(de.operating_profit.sum())


def test_variance_sign_and_favourable(setup):
    v = kpis.variance(setup[0])
    assert len(v) == 9  # 3 companies x 3 P&L lines
    for r in v.itertuples():
        assert r.variance == pytest.approx(r.actual - r.plan, abs=0.01)
        assert bool(r.favourable) == ((r.actual >= r.plan) if r.pnl_line == "REVENUE" else (r.actual <= r.plan))


def test_migration_reconciles_and_catches_a_broken_model(setup):
    conn, actuals, plan, fx = setup
    legacy = migration.legacy_report(actuals, fx)
    new = kpis.pnl(conn)[["company_code", "period", "revenue", "cogs", "opex"]]
    assert migration.reconcile(legacy, new).empty
    assert migration.unmapped_kpis(kpis.pnl(conn).columns) == []

    bad_fx = fx.copy()
    bad_fx.loc[(bad_fx.currency == "USD") & (bad_fx.period == "2026-06"), "rate_to_eur"] *= 1.1
    broken = warehouse.build(actuals=actuals, plan=plan, fx=bad_fx)  # e.g. wrong FX table after migration
    diffs = migration.reconcile(legacy, kpis.pnl(broken)[new.columns])
    assert set(diffs.company_code) == {"US01"} and set(diffs.period) == {"2026-06"}


def test_assistant_rules_and_governance(setup):
    conn = setup[0]
    r = assistant.ask(conn, "What was the revenue of DE01 in Q2?", key=None)
    expected = pd.read_sql("SELECT SUM(amount_eur) s FROM v_pnl WHERE version='ACT' AND company_code='DE01' "
                           "AND pnl_line='REVENUE' AND period BETWEEN '2026-04' AND '2026-06'", conn).s[0]
    assert r["value"] == pytest.approx(expected)
    assert r["intent"]["p_from"] == "2026-04" and r["sql"] is not None
    assert assistant.ask(conn, "How many employees do we have?", key=None)["sql"] is None  # refuses


def test_invalid_ai_output_falls_back_to_rules(monkeypatch, setup):
    monkeypatch.setattr(assistant, "_call_llm",
                        lambda p, k: '{"metric": "DROP TABLE fact_pnl", "company": "DE01"}')
    i = assistant.parse("opex of US01 in 2026-03", key="fake")
    assert i == {"metric": "opex", "company": "US01", "version": "ACT", "p_from": "2026-03", "p_to": "2026-03"}


def test_excel_export_has_live_formulas(tmp_path, setup):
    conn = setup[0]
    path = tmp_path / "r.xlsx"
    export.to_excel(path, kpis.pnl(conn), kpis.variance(conn), pd.DataFrame(columns=["measure"]))
    wb = load_workbook(path)
    assert wb.sheetnames == ["P&L Actual", "Actual vs Plan", "Reconciliation"]
    assert wb["Actual vs Plan"]["E2"].value == "=C2-D2"
