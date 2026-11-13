"""A small Joule-style AI assistant: answer finance questions in plain English.

Governance first: the AI (Claude API, if ANTHROPIC_API_KEY is set) only turns the
question into a structured intent. The intent is validated against an allow-list of
metrics and companies, and the SQL comes from a fixed, parameterized template, so the
model never writes SQL and every answer shows exactly how it was computed.
Without a key, or if the AI output is invalid, keyword rules are used.
"""
import json
import os
import re
import urllib.request

import pandas as pd

METRICS = {"revenue": "REVENUE", "cogs": "COGS", "opex": "OPEX"}
DERIVED = {"gross_profit": ("revenue", "cogs"), "operating_profit": ("revenue", "cogs", "opex")}
COMPANIES = ["CZ01", "DE01", "US01"]
WORDS = {"revenue": "revenue", "sales": "revenue", "cost of sales": "cogs", "cogs": "cogs",
         "opex": "opex", "operating expenses": "opex", "gross profit": "gross_profit",
         "operating profit": "operating_profit", "ebit": "operating_profit"}
TEMPLATE = ("SELECT pnl_line, SUM(amount_eur) AS eur FROM v_pnl WHERE version = :version "
            "AND company_code LIKE :company AND period BETWEEN :p_from AND :p_to GROUP BY pnl_line")


def _call_llm(prompt, key):
    body = json.dumps({"model": "claude-haiku-4-5", "max_tokens": 200,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())["content"][0]["text"]


def parse_rules(q: str) -> dict:
    ql = q.lower()
    metric = next((v for k, v in sorted(WORDS.items(), key=lambda kv: -len(kv[0])) if k in ql), None)
    comp = next((c for c in COMPANIES if c.lower() in ql), None)
    quarter = re.search(r"\bq([1-4])\b", ql)
    month = re.search(r"\b2026-(\d{2})\b", ql)
    if quarter:
        qn = int(quarter.group(1))
        p_from, p_to = f"2026-{3 * qn - 2:02d}", f"2026-{3 * qn:02d}"
    elif month:
        p_from = p_to = month.group(0)
    else:
        p_from, p_to = "2026-01", "2026-12"
    return {"metric": metric, "company": comp, "version": "PLN" if "plan" in ql else "ACT",
            "p_from": p_from, "p_to": p_to}


def valid(i: dict) -> bool:
    return (i.get("metric") in list(METRICS) + list(DERIVED) and i.get("company") in COMPANIES + [None]
            and i.get("version") in ("ACT", "PLN")
            and all(re.fullmatch(r"2026-(0[1-9]|1[0-2])", str(i.get(k))) for k in ("p_from", "p_to")))


def parse(q: str, key=None) -> dict:
    if key:
        try:
            i = json.loads(_call_llm(
                "Return JSON with keys metric (one of revenue,cogs,opex,gross_profit,operating_profit), "
                "company (CZ01, DE01, US01 or null), version (ACT or PLN), p_from, p_to (YYYY-MM, 2026). "
                f"Question: {q}\nJSON only.", key))
            if valid(i):
                return i
        except Exception:
            pass
    return parse_rules(q)


def ask(conn, question: str, key=None) -> dict:
    intent = parse(question, key or os.getenv("ANTHROPIC_API_KEY"))
    if not valid(intent):
        return {"answer": "Sorry, I can only answer about revenue, COGS, OPEX, gross profit and "
                          "operating profit for CZ01, DE01, US01 in 2026.", "intent": intent, "sql": None}
    params = {"version": intent["version"], "company": intent["company"] or "%",
              "p_from": intent["p_from"], "p_to": intent["p_to"]}
    lines = pd.read_sql(TEMPLATE, conn, params=params).set_index("pnl_line")["eur"].to_dict()
    vals = {m: lines.get(l, 0.0) for m, l in METRICS.items()}
    m = intent["metric"]
    value = vals[m] if m in METRICS else vals["revenue"] - sum(vals[x] for x in DERIVED[m][1:])
    scope = intent["company"] or "all companies"
    return {"answer": f"{m.replace('_', ' ').title()} ({intent['version']}, {scope}, "
                      f"{intent['p_from']}..{intent['p_to']}): EUR {value:,.0f}",
            "value": value, "intent": intent, "sql": TEMPLATE, "params": params}
