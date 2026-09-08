# Data Model: Silver & Gold Layers

## Overview

O pipeline produz dois tipos de artefatos dbt: modelos **intermediate (Silver)** que fazem o
parse e normalização dos JSONs brutos, e um modelo **mart (Gold)** que une os intermediates e
calcula KPIs. Todos os modelos lêem a partir das external tables de staging já existentes.

---

## Camada Intermediate (Silver)

### int_income_statement

**Grain**: `(symbol, fiscaldateending, report_type)` — um registro por empresa, período fiscal
e tipo de relatório, após deduplicação pela ingestão mais recente.

**Fonte**: `stg_income_statement` → `raw_data STRING` (JSON da Alpha Vantage)

| Coluna | Tipo | Origem JSON | Notas |
|--------|------|-------------|-------|
| `symbol` | STRING | `$.symbol` | Ticker da empresa |
| `report_type` | STRING | array key | `'annual'` ou `'quarterly'` |
| `fiscaldateending` | DATE | `$.fiscalDateEnding` | `SAFE.PARSE_DATE('%Y-%m-%d', ...)` |
| `fiscaldateending_raw` | STRING | `$.fiscalDateEnding` | Valor original pré-parse (auditoria) |
| `reportedcurrency` | STRING | `$.reportedCurrency` | Moeda do relatório |
| `gross_profit` | INT64 | `$.grossProfit` | |
| `total_revenue` | INT64 | `$.totalRevenue` | Base para net_margin e YoY |
| `cost_of_revenue` | INT64 | `$.costOfRevenue` | |
| `operating_income` | INT64 | `$.operatingIncome` | |
| `selling_general_and_administrative` | INT64 | `$.sellingGeneralAndAdministrative` | |
| `research_and_development` | INT64 | `$.researchAndDevelopment` | |
| `operating_expenses` | INT64 | `$.operatingExpenses` | |
| `net_interest_income` | INT64 | `$.netInterestIncome` | |
| `interest_income` | INT64 | `$.interestIncome` | |
| `interest_expense` | INT64 | `$.interestExpense` | |
| `depreciation_and_amortization` | INT64 | `$.depreciationAndAmortization` | Componente do ebitda_calc |
| `income_before_tax` | INT64 | `$.incomeBeforeTax` | |
| `income_tax_expense` | INT64 | `$.incomeTaxExpense` | |
| `net_income_from_continuing_operations` | INT64 | `$.netIncomeFromContinuingOperations` | |
| `ebit` | INT64 | `$.ebit` | Componente do ebitda_calc |
| `ebitda` | INT64 | `$.ebitda` | Campo direto da API |
| `net_income` | INT64 | `$.netIncome` | Base para ROE, net_margin, quality_of_earnings |
| `ebitda_calc` | INT64 | derivado | `COALESCE(ebitda, ebit + depreciation_and_amortization)` |
| `ingest_date` | DATE | partição | `DATE(partition_year, partition_month, partition_day)` |
| `partition_year` | INT64 | partição Hive | |
| `partition_month` | INT64 | partição Hive | |
| `partition_day` | INT64 | partição Hive | |

**Restrições**:
- `symbol` NOT NULL
- `fiscaldateending` NOT NULL (registros com parse falho são filtrados)
- `report_type` IN ('annual', 'quarterly')
- `(symbol, fiscaldateending, report_type)` UNIQUE

---

### int_balance_sheet

**Grain**: `(symbol, fiscaldateending, report_type)` — snapshot do balanço ao final do período.

**Fonte**: `stg_balance_sheet` → `raw_data STRING`

| Coluna | Tipo | Origem JSON | Notas |
|--------|------|-------------|-------|
| `symbol` | STRING | `$.symbol` | |
| `report_type` | STRING | array key | `'annual'` ou `'quarterly'` |
| `fiscaldateending` | DATE | `$.fiscalDateEnding` | |
| `fiscaldateending_raw` | STRING | `$.fiscalDateEnding` | Auditoria |
| `reportedcurrency` | STRING | `$.reportedCurrency` | |
| `total_assets` | INT64 | `$.totalAssets` | |
| `total_current_assets` | INT64 | `$.totalCurrentAssets` | Base para current_ratio |
| `cash_and_cash_equivalents` | INT64 | `$.cashAndCashEquivalentsAtCarryingValue` | Componente de net_debt |
| `cash_and_short_term_investments` | INT64 | `$.cashAndShortTermInvestments` | |
| `inventory` | INT64 | `$.inventory` | |
| `current_net_receivables` | INT64 | `$.currentNetReceivables` | |
| `total_non_current_assets` | INT64 | `$.totalNonCurrentAssets` | |
| `property_plant_equipment` | INT64 | `$.propertyPlantEquipment` | |
| `intangible_assets` | INT64 | `$.intangibleAssets` | |
| `goodwill` | INT64 | `$.goodwill` | |
| `long_term_investments` | INT64 | `$.longTermInvestments` | |
| `short_term_investments` | INT64 | `$.shortTermInvestments` | |
| `total_liabilities` | INT64 | `$.totalLiabilities` | |
| `total_current_liabilities` | INT64 | `$.totalCurrentLiabilities` | Base para current_ratio |
| `current_accounts_payable` | INT64 | `$.currentAccountsPayable` | |
| `short_term_debt` | INT64 | `$.shortTermDebt` | Componente de total_debt |
| `total_non_current_liabilities` | INT64 | `$.totalNonCurrentLiabilities` | |
| `capital_lease_obligations` | INT64 | `$.capitalLeaseObligations` | |
| `long_term_debt` | INT64 | `$.longTermDebt` | Componente de total_debt |
| `current_long_term_debt` | INT64 | `$.currentLongTermDebt` | |
| `short_long_term_debt_total` | INT64 | `$.shortLongTermDebtTotal` | Preferido para total_debt |
| `other_current_liabilities` | INT64 | `$.otherCurrentLiabilities` | |
| `total_shareholder_equity` | INT64 | `$.totalShareholderEquity` | Base para ROE |
| `retained_earnings` | INT64 | `$.retainedEarnings` | |
| `common_stock` | INT64 | `$.commonStock` | |
| `common_stock_shares_outstanding` | INT64 | `$.commonStockSharesOutstanding` | |
| `total_debt` | INT64 | derivado | `COALESCE(short_long_term_debt_total, long_term_debt + short_term_debt)` |
| `net_debt` | INT64 | derivado | `total_debt - cash_and_cash_equivalents` |
| `ingest_date` | DATE | partição | |
| `partition_year` | INT64 | partição Hive | |
| `partition_month` | INT64 | partição Hive | |
| `partition_day` | INT64 | partição Hive | |

**Restrições**: mesmas de `int_income_statement`.

---

### int_cash_flow

**Grain**: `(symbol, fiscaldateending, report_type)` — fluxo de caixa do período.

**Fonte**: `stg_cash_flow` → `raw_data STRING`

| Coluna | Tipo | Origem JSON | Notas |
|--------|------|-------------|-------|
| `symbol` | STRING | `$.symbol` | |
| `report_type` | STRING | array key | |
| `fiscaldateending` | DATE | `$.fiscalDateEnding` | |
| `fiscaldateending_raw` | STRING | `$.fiscalDateEnding` | Auditoria |
| `reportedcurrency` | STRING | `$.reportedCurrency` | |
| `operating_cashflow` | INT64 | `$.operatingCashflow` | Base para FCF e quality_of_earnings |
| `capital_expenditures` | INT64 | `$.capitalExpenditures` | CapEx — componente do FCF |
| `depreciation_depletion_and_amortization` | INT64 | `$.depreciationDepletionAndAmortization` | |
| `dividend_payout` | INT64 | `$.dividendPayout` | |
| `stock_based_compensation` | INT64 | `$.stockBasedCompensation` | |
| `cashflow_from_investment` | INT64 | `$.cashflowFromInvestment` | |
| `cashflow_from_financing` | INT64 | `$.cashflowFromFinancing` | |
| `net_income` | INT64 | `$.netIncome` | |
| `free_cash_flow` | INT64 | derivado | `operating_cashflow - capital_expenditures` |
| `ingest_date` | DATE | partição | |
| `partition_year` | INT64 | partição Hive | |
| `partition_month` | INT64 | partição Hive | |
| `partition_day` | INT64 | partição Hive | |

**Restrições**: mesmas de `int_income_statement`.

---

### int_earning

**Grain**: `(symbol, fiscaldateending, report_type)` — EPS e surpresa por período.

**Fonte**: `stg_earning` → `raw_data STRING`

| Coluna | Tipo | Origem JSON | Notas |
|--------|------|-------------|-------|
| `symbol` | STRING | `$.symbol` | |
| `report_type` | STRING | array key | `'annual'` (annualEarnings) ou `'quarterly'` (quarterlyEarnings) |
| `fiscaldateending` | DATE | `$.fiscalDateEnding` | |
| `fiscaldateending_raw` | STRING | `$.fiscalDateEnding` | Auditoria |
| `reported_date` | DATE | `$.reportedDate` | NULL para registros anuais |
| `reported_eps` | NUMERIC | `$.reportedEPS` | |
| `estimated_eps` | NUMERIC | `$.estimatedEPS` | |
| `surprise` | NUMERIC | `$.surprise` | |
| `surprise_percentage` | NUMERIC | `$.surprisePercentage` | → `earnings_surprise_pct` na mart |
| `ingest_date` | DATE | partição | |
| `partition_year` | INT64 | partição Hive | |
| `partition_month` | INT64 | partição Hive | |
| `partition_day` | INT64 | partição Hive | |

**Restrições**: mesmas de `int_income_statement`.

---

### int_overview

**Grain**: `(symbol)` — snapshot mais recente por empresa, sem dimensão de período fiscal.

**Fonte**: `stg_overview` → `raw_data STRING`

| Coluna | Tipo | Origem JSON | Notas |
|--------|------|-------------|-------|
| `symbol` | STRING | `$.Symbol` | |
| `asset_type` | STRING | `$.AssetType` | |
| `name` | STRING | `$.Name` | Nome da empresa |
| `exchange` | STRING | `$.Exchange` | NYSE, NASDAQ, etc. |
| `currency` | STRING | `$.Currency` | |
| `country` | STRING | `$.Country` | |
| `sector` | STRING | `$.Sector` | |
| `industry` | STRING | `$.Industry` | |
| `fiscal_year_end` | STRING | `$.FiscalYearEnd` | |
| `latest_quarter` | STRING | `$.LatestQuarter` | |
| `market_capitalization` | INT64 | `$.MarketCapitalization` | |
| `pe_ratio` | NUMERIC | `$.PERatio` | P/E atual (snapshot) |
| `peg_ratio` | NUMERIC | `$.PEGRatio` | |
| `book_value` | NUMERIC | `$.BookValue` | |
| `dividend_per_share` | NUMERIC | `$.DividendPerShare` | |
| `dividend_yield` | NUMERIC | `$.DividendYield` | |
| `eps` | NUMERIC | `$.EPS` | |
| `revenue_per_share_ttm` | NUMERIC | `$.RevenuePerShareTTM` | |
| `profit_margin` | NUMERIC | `$.ProfitMargin` | |
| `return_on_equity_ttm` | NUMERIC | `$.ReturnOnEquityTTM` | |
| `ev_to_revenue` | NUMERIC | `$.EVToRevenue` | |
| `ev_to_ebitda` | NUMERIC | `$.EVToEBITDA` | EV/EBITDA atual (snapshot) |
| `beta` | NUMERIC | `$.Beta` | |
| `trailing_pe` | NUMERIC | `$.TrailingPE` | |
| `forward_pe` | NUMERIC | `$.ForwardPE` | |
| `price_to_sales_ratio_ttm` | NUMERIC | `$.PriceToSalesRatioTTM` | |
| `price_to_book_ratio` | NUMERIC | `$.PriceToBookRatio` | |
| `ingest_date` | DATE | partição | Data do snapshot mais recente |
| `partition_year` | INT64 | partição Hive | |
| `partition_month` | INT64 | partição Hive | |
| `partition_day` | INT64 | partição Hive | |

**Restrições**:
- `symbol` NOT NULL e UNIQUE (após deduplicação por `ingest_date DESC`)

---

## Camada Mart (Gold)

### fct_fundamental_kpis

**Grain**: `(symbol, fiscaldateending, report_type)` — âncora no `int_income_statement`.

**Materialização**: TABLE no dataset `alphavantage`.

**Estratégia de join**:
```
int_income_statement  (driving table)
  LEFT JOIN int_balance_sheet  ON (symbol, fiscaldateending, report_type)
  LEFT JOIN int_cash_flow      ON (symbol, fiscaldateending, report_type)
  LEFT JOIN int_earning        ON (symbol, fiscaldateending, report_type)
  LEFT JOIN int_overview       ON symbol
```

| Coluna | Tipo | Fórmula / Fonte | Pilar |
|--------|------|-----------------|-------|
| `symbol` | STRING | inc.symbol | Dimensão |
| `fiscaldateending` | DATE | inc.fiscaldateending | Dimensão |
| `report_type` | STRING | inc.report_type | Dimensão |
| `reportedcurrency` | STRING | inc.reportedcurrency | Dimensão |
| `ingest_date` | DATE | inc.ingest_date | Rastreabilidade |
| `sector` | STRING | ov.sector | Dimensão |
| `industry` | STRING | ov.industry | Dimensão |
| `country` | STRING | ov.country | Dimensão |
| `exchange` | STRING | ov.exchange | Dimensão |
| `overview_snapshot_date` | DATE | ov.ingest_date | Rastreabilidade |
| `roe` | NUMERIC | `SAFE_DIVIDE(inc.net_income, bs.total_shareholder_equity)` | Rentabilidade |
| `net_margin` | NUMERIC | `SAFE_DIVIDE(inc.net_income, inc.total_revenue)` | Rentabilidade |
| `ebitda_margin` | NUMERIC | `SAFE_DIVIDE(inc.ebitda_calc, inc.total_revenue)` | Rentabilidade |
| `net_debt_to_ebitda` | NUMERIC | `SAFE_DIVIDE(bs.net_debt, inc.ebitda_calc)` | Saúde/Risco |
| `current_ratio` | NUMERIC | `SAFE_DIVIDE(bs.total_current_assets, bs.total_current_liabilities)` | Saúde/Risco |
| `free_cash_flow` | INT64 | cf.free_cash_flow | Geração de Caixa |
| `quality_of_earnings` | NUMERIC | `SAFE_DIVIDE(cf.operating_cashflow, inc.net_income)` | Geração de Caixa |
| `revenue_yoy_growth` | NUMERIC | `SAFE_DIVIDE(inc.total_revenue - LAG(4/1), LAG(4/1))` | Crescimento |
| `earnings_surprise_pct` | NUMERIC | earn.surprise_percentage | Crescimento |
| `pe_ratio` | NUMERIC | ov.pe_ratio | Valuation |
| `ev_to_ebitda` | NUMERIC | ov.ev_to_ebitda | Valuation |

**Restrições**:
- `(symbol, fiscaldateending, report_type)` UNIQUE
- `symbol`, `fiscaldateending`, `report_type` NOT NULL
- Todos os KPIs NUMERIC podem ser NULL (denominador zero ou ausência de dado)

---

## Estrutura de arquivos dbt

```text
src/transformations/models/
├── source.yml                          # existente — não modificar
├── staging/                            # existente — não modificar
│   ├── stg_balance_sheet.sql
│   ├── stg_balance_sheet.yml
│   ├── stg_cash_flow.sql
│   ├── stg_cash_flow.yml
│   ├── stg_earning.sql
│   ├── stg_earning.yml
│   ├── stg_income_statement.sql
│   ├── stg_income_statement.yml
│   ├── stg_overview.sql
│   └── stg_overview.yml
├── intermediate/                       # a criar
│   ├── int_income_statement.sql
│   ├── int_income_statement.yml
│   ├── int_balance_sheet.sql
│   ├── int_balance_sheet.yml
│   ├── int_cash_flow.sql
│   ├── int_cash_flow.yml
│   ├── int_earning.sql
│   ├── int_earning.yml
│   ├── int_overview.sql
│   └── int_overview.yml
└── marts/                              # a criar
    ├── fct_fundamental_kpis.sql
    └── fct_fundamental_kpis.yml
```
