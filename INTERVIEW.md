# INTERVIEW.md — как понять проект и защитить его на собеседовании

Вакансия: **SAP — Working Student Corporate Finance Analytics (CPIT), Prague, hybrid, старт 1.12.2026**.
Проект: `finance-analytics-kit` — Python + SQL (SQLite), ~510 строк, синтетические данные.

---

## 1. Требование вакансии → где это в проекте

| Из вакансии | Где | Что показать |
|---|---|---|
| **Transformation to Business Data Cloud / Datasphere** | `finkit/warehouse.py` | слои: inbound → harmonization → star schema → analytic model (идея Datasphere) |
| **Migration to SAP Analytics Cloud (SAC)** frontend | `finkit/migration.py` | сверка legacy-отчёта и новой модели, каталог KPI |
| **Hands on in Joule Work Desktop – AI** | `finkit/assistant.py` | Joule-подобный помощник: вопрос → intent → SQL, governance |
| **Support Finance Analytics Scrum Team** in daily routines | `BACKLOG.md` | user stories, acceptance criteria, sprints, DoD, ceremonies |
| **Support on Roadmap definition** | `BACKLOG.md` → Roadmap | Now / Next / Later |
| **Good understanding of Database technology** | `warehouse.py`, `kpis.py` | SQL: JOIN, CTE, CASE, window function, views |
| **Data Warehouse technology** | `warehouse.py` | star schema, fact / dimension, data quality layer |
| **AI** | `assistant.py` | Claude API + validation + fallback, без генерации SQL моделью |
| **Microsoft Office Products** | `finkit/export.py` | Excel-файл с формулами (сам Office — это твой навык, проект его не доказывает) |
| **Software Engineering / IT studies** | твоё образование | Applied Informatics, ČZU |
| **English fluent** | — | C1 |

**Не закрывается проектом:** реальный опыт с SAP Datasphere / SAC / Joule (нужен доступ к SAP),
финансовое образование.

---

## 2. Теория с нуля

### 2.1 Corporate Finance Analytics
Финансовая аналитика для управления компанией: сколько заработали (**revenue**), сколько стоило
оказать услугу (**COGS**, cost of goods sold), операционные расходы (**OPEX**: зарплаты, маркетинг,
IT). **Gross profit** = revenue − COGS. **Operating profit (EBIT)** = gross profit − OPEX.
**Gross margin %** = gross profit / revenue.
**Actual vs Plan**: факт против бюджета. **Variance** = actual − plan. Для выручки «больше плана» —
хорошо (**favourable**), для затрат — плохо. **YTD** (year to date) — накопительно с начала года.

### 2.2 Основы бухгалтерских данных
- **G/L account** (general ledger) — счёт главной книги, например 400000 «выручка».
- **Company code** — юрлицо в SAP (у нас CZ01, DE01, US01).
- **Cost center** — подразделение, которое несёт затраты.
- **Posting / document** — одна проводка.
- **Local currency → group currency**: каждая страна в своей валюте, отчёт группы в EUR по курсу месяца.

### 2.3 Data Warehouse
Отдельная база для аналитики (не для операций). **Star schema**: в центре **fact** (числа: суммы),
вокруг **dimensions** (кто/что/когда: компания, счёт, период). Аналогия: чек в магазине — это fact,
а справочники «магазины», «товары», «даты» — dimensions.

### 2.4 SAP Datasphere и Business Data Cloud (BDC)
- **SAP Datasphere** — облачный data warehouse SAP (бывший Data Warehouse Cloud). Данные делятся на
  **spaces**, модели строятся слоями; верхний слой — **analytic model** с **measures** (числа) и
  **dimensions**, на которую смотрят отчёты.
- **Business Data Cloud** — новое объединение Datasphere, SAC, Databricks и «data products» SAP
  в одну платформу данных.
- В проекте те же идеи на SQLite: raw (inbound) → stg (harmonization) → fact/dim → `v_pnl`
  (analytic model). Честно: «Я воспроизвёл концепции, сам Datasphere не использовал».

### 2.5 SAP Analytics Cloud (SAC) и миграция
**SAC** — BI и планирование от SAP: **stories** (дашборды), модели, планирование бюджета.
Миграция отчётов = перенести старые отчёты (например, из BW / Analysis for Office) на новую модель
и SAC. Главный риск — **цифры не совпадут**. Поэтому **reconciliation**: старый отчёт и новый
считаются разными путями и сравниваются по каждой ячейке. Аналогия: два бухгалтера независимо
считают кассу — если суммы совпали, им можно верить.

### 2.6 Joule
**Joule** — AI-копилот SAP во всех продуктах. Пользователь пишет вопрос, Joule находит данные или
выполняет действие. В проекте: вопрос → **intent** (метрика, компания, период) → проверка по
**allow-list** → готовый **параметризованный SQL**. Модель никогда не пишет SQL сама (иначе риск
неверных цифр и SQL injection). Неизвестные темы — вежливый отказ.

### 2.7 Scrum
- **Product backlog** — список задач в виде **user stories** («As a … I want … so that …»)
  с **acceptance criteria**.
- **Sprint** — 1–4 недели. Церемонии: **daily stand-up**, **sprint planning**, **review** (демо),
  **retrospective**. **Definition of Done** — когда задача реально готова.
- Роли: Product Owner, Scrum Master, Developers. Working student помогает в рутине: обновляет
  backlog, готовит данные, проверяет отчёты, документирует.
- **Roadmap** — что делаем сейчас / дальше / позже, по темам, а не по датам до дня.

### 2.8 SQL, который тут используется
`JOIN`, `GROUP BY`, `CASE WHEN` (разложить строки P&L в колонки), **CTE** (`WITH`), **window
function** `SUM(...) OVER (PARTITION BY ... ORDER BY ...)` для YTD, views.

---

## 3. Архитектура

```
 raw_postings  raw_fx  raw_accounts  raw_companies          (inbound layer)
        \         |         |             /
         v        v         v            v
   quarantine  <- data quality ->  stg_postings  (EUR, P&L line)   (harmonization)
                                       |
                    fact_pnl + dim_company / dim_account / dim_period (star schema)
                                       |
                                     v_pnl   (analytic model)
                     /            |              |             \
               kpis.py      migration.py     assistant.py    export.py
               P&L, YTD,    legacy vs new    question->SQL    Excel
               variance     reconciliation   (Joule-style)    with formulas
```

---

## 4. Каждый файл: что и ЗАЧЕМ

- **`finkit/data.py`** — синтетика: 3 компании, 3 валюты, 8 счетов, 12 месяцев, факт и план.
  Три ошибки внесены нарочно. Зачем: реальные финансовые данные конфиденциальны.
- **`finkit/warehouse.py`** — всё на SQL. Зачем слои: если что-то сломалось, видно на каком шаге.
  Зачем quarantine: в финансах нельзя молча терять проводки — сумма отчёта будет неверной.
- **`finkit/kpis.py`** — KPI одним SQL. Зачем `favourable`: для выручки и затрат знак «хорошо» разный.
- **`finkit/migration.py`** — сверка. Зачем другой путь (pandas): если бы считали тем же SQL,
  ошибка повторилась бы в обоих отчётах и не была бы найдена.
- **`finkit/assistant.py`** — AI-помощник с governance.
- **`finkit/export.py`** — Excel: финансисты живут в Excel; формулы «живые», можно менять план.
- **`BACKLOG.md`** — Scrum и roadmap.
- **`tests/test_finkit.py`** — 9 тестов, включая «сломанный курс USD за июнь → сверка находит
  ровно US01, 2026-06».

---

## 5. Решения и компромиссы

| Решение | Почему | Цена |
|---|---|---|
| SQLite вместо HANA/Datasphere | запускается везде, бесплатно | нет колоночного хранения, нет spaces |
| Курс месяца (average rate) | стандарт для P&L | для balance sheet нужен курс на дату |
| Сверка с допуском 0,05 EUR | округление по каждой проводке | мелкие ошибки < 5 центов не видны |
| AI только для intent | цифры всегда из SQL, проверяемо | помощник понимает узкий набор вопросов |
| Синтетические данные | конфиденциальность | реальные данные «грязнее» |

---

## 6. Запуск + демо на 2 минуты

```bash
pip install -r requirements.txt
python main.py
python -m pytest -q
```

1. (20 с) «Мини-версия того, что делает Finance Analytics: модель данных, KPI, миграция, AI.»
2. (30 с) Quarantine: «3 плохие проводки — неизвестный счёт, нет курса GBP, дубль документа».
3. (30 с) Actual vs plan: «DE01 выручка +2,1 % к плану — favourable».
4. (20 с) Сверка: «36 месяцев × 3 показателя — 0 расхождений; в тесте ломаю курс USD за июнь, и
   сверка находит ровно эту ячейку».
5. (20 с) Assistant: «вопрос про выручку DE01 в Q2 → ответ + SQL, на вопрос про сотрудников —
   честный отказ».

---

## 7. Слабые места и как масштабировать

- **Нет реального SAP.** Честно: «Datasphere, SAC и Joule я ещё не трогал руками. Я повторил их
  идеи, чтобы понимать, что происходит при миграции, и готов быстро освоить сами инструменты».
  Совет: до интервью пройди бесплатные курсы на learning.sap.com (Datasphere, SAC basics) —
  тогда сможешь честно сказать «изучаю».
- Нет forecast-версии, нет security по компаниям, нет реального источника (S/4HANA).
- Масштаб: колоночная БД, инкрементальная загрузка, мониторинг качества данных, SAC stories на
  analytic model.

---

## 8. Сделай сам (минимум 2 задачи)

1. Добавь в `kpis.py` **OPEX ratio** = OPEX / revenue и тест.
2. Добавь версию **FC (forecast)** в `data.py` и сравнение actual vs forecast.
3. Добавь в quarantine правило: **проводка в будущем периоде** (после 2026-12).
4. Научи помощника вопросу «**variance of revenue for DE01**» (подсказка: `kpis.variance`).
5. Добавь в Excel лист **«Quarantine»** со списком плохих проводок.

---

## 9. Вопросы и ответы

1. **Что такое data warehouse и star schema?** — Аналитическая БД; fact с числами + dimensions.
2. **Что знаешь о Datasphere / BDC?** — Облачный DWH SAP, spaces, слои, analytic model; BDC объединяет
   Datasphere, SAC, Databricks и data products. Руками не работал, повторил концепции.
3. **Что такое SAC?** — BI, планирование и stories от SAP.
4. **Как убедиться, что после миграции цифры те же?** — Reconciliation: независимый расчёт,
   сравнение по ключам (компания, период, показатель), допуск на округление, список KPI.
5. **Как считаешь YTD?** — `SUM() OVER (PARTITION BY company ORDER BY period)`.
6. **Чем WHERE отличается от HAVING?** — WHERE до группировки, HAVING после.
7. **Что такое CTE?** — Именованный подзапрос `WITH`, делает SQL читаемым.
8. **Как переводишь валюты?** — Курс месяца из таблицы FX; нет курса → quarantine.
9. **Gross margin vs operating profit?** — Margin = (revenue − COGS)/revenue; operating profit ещё минус OPEX.
10. **Favourable variance для затрат?** — Факт меньше плана.
11. **Что такое Joule и как сделать AI надёжным в финансах?** — Копилот SAP; allow-list, валидация,
    цифры только из модели, ответ показывает, как посчитан, отказ вне темы.
12. **Scrum: роли и церемонии?** — PO, SM, Developers; planning, daily, review, retro.
13. **Что такое user story и acceptance criteria?** — Требование от лица пользователя + проверяемые условия готовности.
14. **Как бы ты помог с roadmap?** — Собрать запросы стейкхолдеров, оценить ценность и сложность,
    разложить Now / Next / Later. Опыт интервью с персоналом клиники.
15. **Excel?** — Формулы, условное форматирование, сводные (расскажи честно, что умеешь сам).
16. **Почему финансы, если ты из IT?** — Данные финансов = язык, на котором управляется компания;
    точность данных — то, что я делал в клинике и отеле.
17. **Самая сложная ошибка в данных?** — Дубль документа: суммы раздуваются незаметно.
18. **Сколько часов в неделю можешь работать?** — Подготовь честный ответ (working student, обычно 15–20 ч).

---

## 10. Чек-лист «Я готов»

- [ ] Запустил `python main.py` и `pytest`, открыл `out/finance_report.xlsx`
- [ ] Могу объяснить revenue, COGS, OPEX, gross margin, variance, YTD
- [ ] Могу объяснить star schema и слои модели
- [ ] Знаю, что такое Datasphere, BDC, SAC, Joule (и честно — что руками не пробовал)
- [ ] Сделал 2+ задачи из раздела 8, залил на GitHub, CI зелёный
- [ ] (желательно) Начал бесплатный курс SAP Datasphere / SAC на learning.sap.com
