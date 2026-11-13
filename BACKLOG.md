# Product backlog, sprints and roadmap (Scrum)

How this project was planned, written the way a Finance Analytics Scrum team would.

## Product goal
Finance controllers get trusted P&L and actual-vs-plan numbers from one analytic model,
in a new reporting frontend, with an AI assistant for quick questions.

## Product backlog (user stories)

| ID | User story | Acceptance criteria | Size | Sprint |
|---|---|---|---|---|
| FA-1 | As a controller I want postings in EUR so I can compare companies | every posting has amount_eur; rate taken from the FX table of its month | 3 | 1 |
| FA-2 | As a data owner I want bad postings quarantined with a reason | unmapped G/L, missing FX rate, duplicate document go to `quarantine`; nothing silently lost | 3 | 1 |
| FA-3 | As an analyst I want a star schema / analytic model | fact_pnl + dim_company / dim_account / dim_period; v_pnl total = fact total | 5 | 1 |
| FA-4 | As a controller I want monthly P&L with gross margin and YTD operating profit | SQL with CTE + window function; YTD in December = sum of months | 3 | 2 |
| FA-5 | As a controller I want actual vs plan with favourable / unfavourable flag | 9 rows (3 companies x 3 lines); sign rules for revenue vs cost | 3 | 2 |
| FA-6 | As a business owner I want proof the migrated reports show the same numbers | legacy vs new reconciliation, tolerance 0.05 EUR, KPI catalog fully mapped | 5 | 2 |
| FA-7 | As a user I want to ask finance questions in plain English | allow-listed metrics, parameterized SQL, AI output validated, rule fallback, refuses other topics | 5 | 3 |
| FA-8 | As a controller I want an Excel file with live formulas | sheets P&L, Actual vs Plan (formulas), Reconciliation | 2 | 3 |
| FA-9 | As the team we want CI | pytest + demo run on every push | 1 | 3 |

**Definition of Done:** code reviewed, tests pass in CI, README updated, demo runs.

## Sprints (1 week each)
- **Sprint 1 — data foundation:** FA-1, FA-2, FA-3 (11 points)
- **Sprint 2 — finance KPIs and migration check:** FA-4, FA-5, FA-6 (11 points)
- **Sprint 3 — AI and delivery:** FA-7, FA-8, FA-9 (8 points)

Daily routine: daily stand-up (yesterday / today / blockers), backlog refinement mid-sprint,
sprint review with a demo of `main.py`, retrospective (keep / stop / try).

## Roadmap

| Horizon | Theme | Items |
|---|---|---|
| Now (Q4 2026) | Trusted numbers | layered model, data quality, P&L, variance, reconciliation |
| Next (Q1 2027) | New frontend + AI | stories on the analytic model, AI assistant with governance, Excel export |
| Later (Q2 2027) | Scale | more companies and currencies, forecast version, row-level security per company, real source connection |
