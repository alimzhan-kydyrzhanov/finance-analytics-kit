"""End-to-end demo: build the warehouse, run KPIs, check the migration, ask the assistant."""
from pathlib import Path

from finkit import assistant, data, export, kpis, migration, warehouse


def main():
    out = Path("out")
    out.mkdir(exist_ok=True)
    fx = data.fx_rates()
    actuals, plan = data.make_actuals(fx), data.make_plan(fx)
    conn = warehouse.build(actuals=actuals, plan=plan, fx=fx)

    q = warehouse.quarantine(conn)
    print(f"Quarantined postings: {len(q)}\n{q.to_string(index=False)}\n")

    pnl = kpis.pnl(conn)
    print("P&L (DE01, first 3 months, EUR):")
    print(pnl[pnl.company_code == "DE01"].head(3).round(0).to_string(index=False), "\n")

    var = kpis.variance(conn)
    print("Actual vs plan, full year:")
    print(var.to_string(index=False), "\n")

    recon = migration.reconcile(migration.legacy_report(actuals, fx), pnl[["company_code", "period",
                                                                          "revenue", "cogs", "opex"]])
    print(f"Migration reconciliation: {len(recon)} differences "
          f"({len(pnl)} company-months x 3 measures compared)")
    print("Unmapped legacy KPIs:", migration.unmapped_kpis(pnl.columns) or "none", "\n")

    for question in ["What was the revenue of DE01 in Q2?", "operating profit plan for US01",
                     "gross profit 2026-07", "How many employees do we have?"]:
        r = assistant.ask(conn, question)
        print(f"Q: {question}\nA: {r['answer']}\n")

    export.to_excel(out / "finance_report.xlsx", pnl, var, recon)
    print("Excel report: out/finance_report.xlsx")


if __name__ == "__main__":
    main()
