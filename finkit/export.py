"""Excel export for finance users (Microsoft Excel stays the daily tool next to SAC)."""
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill

HEAD = Font(bold=True)
EUR = '#,##0;[Red]-#,##0'


def _sheet(wb, title, df):
    ws = wb.create_sheet(title)
    ws.append(list(df.columns))
    for c in ws[1]:
        c.font = HEAD
    for row in df.itertuples(index=False):
        ws.append(list(row))
    ws.freeze_panes = "A2"
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(12, len(str(col[0].value)) + 2)
    return ws


def to_excel(path, pnl_df, variance_df, recon_df):
    wb = Workbook()
    wb.remove(wb.active)
    ws = _sheet(wb, "P&L Actual", pnl_df)
    for row in ws.iter_rows(min_row=2, min_col=3):
        for c in row:
            c.number_format = EUR

    v = variance_df[["company_code", "pnl_line", "actual", "plan"]]
    ws = _sheet(wb, "Actual vs Plan", v)
    ws["E1"], ws["F1"] = "variance", "variance_pct"
    ws["E1"].font = ws["F1"].font = HEAD
    n = len(v) + 1
    for r in range(2, n + 1):  # live Excel formulas, so users can change the plan and see the effect
        ws[f"E{r}"] = f"=C{r}-D{r}"
        ws[f"F{r}"] = f"=IF(D{r}=0,0,E{r}/D{r})"
        ws[f"F{r}"].number_format = "0.0%"
        for col in "CDE":
            ws[f"{col}{r}"].number_format = EUR
    ws.conditional_formatting.add(f"F2:F{n}", CellIsRule(operator="greaterThan", formula=["0.05"],
                                  fill=PatternFill("solid", fgColor="FFF2CC")))
    _sheet(wb, "Reconciliation", recon_df if len(recon_df) else
           recon_df.reindex([0]).fillna("no differences"))
    wb.save(path)
