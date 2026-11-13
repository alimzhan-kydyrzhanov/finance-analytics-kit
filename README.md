# Finance Analytics Kit

A small corporate finance analytics project in **Python + SQL (SQLite)** on **synthetic data**:
a layered data warehouse modelled on **SAP Datasphere / Business Data Cloud** ideas, finance KPIs,
a **report migration check** (legacy report vs new analytic model, as in a move to **SAP Analytics
Cloud (SAC)**), a **Joule-style AI assistant** with governance, an Excel export and Scrum artifacts.

> No SAP software is used here. The project reproduces the concepts (layers, analytic model,
> reconciliation, governed AI) with open tools so they can be run and tested anywhere.

| Part | File | What it does |
|---|---|---|
| Synthetic data | `finkit/data.py` | 3 company codes (CZK, EUR, USD), 8 G/L accounts, 12 months actual + plan, monthly FX rates, injected data problems |
| Data warehouse | `finkit/warehouse.py` | inbound layer → harmonization (quarantine, FX to EUR, P&L mapping) → star schema → analytic model view |
| Finance KPIs | `finkit/kpis.py` | P&L, gross margin %, operating profit, YTD (window function), actual vs plan variance with favourable flag |
| Migration | `finkit/migration.py` | rebuilds the legacy report independently and reconciles it with the new model; KPI catalog mapping |
| AI assistant | `finkit/assistant.py` | plain-English questions → validated intent → parameterized SQL; Claude API optional, rules fallback |
| Excel | `finkit/export.py` | workbook with live formulas and conditional formatting |
| Scrum | `BACKLOG.md` | user stories, acceptance criteria, sprints, Definition of Done, roadmap |

## Run

```bash
pip install -r requirements.txt
python main.py        # demo + out/finance_report.xlsx
python -m pytest -q   # 9 tests
docker build -t finkit . && docker run --rm finkit
```

## Limits
Synthetic data; SQLite instead of SAP HANA / Datasphere; no SAC stories (the reconciliation
is the part of a migration that does not depend on the frontend); AI path tested with a mock.
