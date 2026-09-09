# Implementation Plan: Silver & Gold Layers — Financial Fundamental Pipeline

**Branch**: `silver-gold-layers` | **Date**: 2026-09-07 | **Spec**: `specs/silver-gold-layers/spec.md`

**Input**: Feature specification from `specs/silver-gold-layers/spec.md`

---

## Summary

Implementar as camadas **Intermediate (Silver)** e **Mart (Gold)** do pipeline dbt de análise
fundamentalista. O pipeline já tem a camada Bronze (GCS) e os modelos de staging existentes.
Esta feature adiciona 5 modelos intermediate (parse/normalização dos JSONs por endpoint),
1 modelo mart (OBT com KPIs) e seus respectivos arquivos YAML de catálogo — sem modificar
nenhum arquivo existente.

---

## Technical Context

**Language/Version**: SQL (BigQuery dialect) + dbt 1.x (Fusion preview)

**Primary Dependencies**: dbt (`transformations` project), `dbt_utils` (unique_combination_of_columns), `dbt_external_tables` (já instalados)

**Storage**: BigQuery — `projetodbt-479518`, dataset `alphavantage`; GCS bucket `hallyson-bronze`

**Testing**: `dbt test` com testes declarativos nos YAMLs

**Target Platform**: Google Cloud Platform (BigQuery + GCS)

**Project Type**: Data pipeline — dbt transformation layer

**Performance Goals**: Mart materializada como TABLE; queries de KPI sem parse de JSON em tempo de execução

**Constraints**: Staging não pode ser modificado; sem `extra='forbid'` nos modelos dbt (N/A); `SAFE_CAST` obrigatório para todas as coerções

**Scale/Scope**: 35 tickers × 5 endpoints × histórico trimestral (~20 períodos/ticker) ≈ ~3.500 linhas na mart por `report_type`

---

## Constitution Check

| Princípio | Status | Evidência |
|-----------|--------|-----------|
| I. Separation of Concerns | ✅ | Staging intocado; parse somente em intermediate; KPIs somente em mart |
| II. Explicit Grain Contract | ✅ | Grain declarado em `data-model.md`; comentário SQL obrigatório por modelo |
| III. Safe-by-Default | ✅ | `SAFE_CAST` + `NULLIF` sentinel + `SAFE_DIVIDE` + `fiscaldateending_raw` |
| IV. Catalog-First | ✅ | Cada modelo tem `.yml` co-localizado com todas as colunas documentadas |
| V. Idempotent & Observable | ✅ | `ROW_NUMBER` dedup + `WHERE fiscaldateending IS NOT NULL` definidos |

Nenhuma violação. Gate aprovado.

---

## Project Structure

### Documentation (this feature)

```text
specs/silver-gold-layers/
├── plan.md          ← este arquivo
├── research.md      ← decisões técnicas (Phase 0)
├── data-model.md    ← entidades, campos, tipos, relações (Phase 1)
├── quickstart.md    ← guia de validação end-to-end (Phase 1)
└── tasks.md         ← tasks de implementação (gerado por /speckit.tasks)
```

### Source Code (dbt models a criar)

```text
src/transformations/models/
├── intermediate/
│   ├── int_income_statement.sql    ← parse + tipagem + dedup + ebitda_calc
│   ├── int_income_statement.yml    ← catálogo de colunas + testes
│   ├── int_balance_sheet.sql       ← parse + tipagem + dedup + total_debt + net_debt
│   ├── int_balance_sheet.yml
│   ├── int_cash_flow.sql           ← parse + tipagem + dedup + free_cash_flow
│   ├── int_cash_flow.yml
│   ├── int_earning.sql             ← parse + tipagem + dedup
│   ├── int_earning.yml
│   ├── int_overview.sql            ← parse + tipagem + dedup por symbol
│   └── int_overview.yml
└── marts/
    ├── fct_fundamental_kpis.sql    ← joins + KPIs calculados
    └── fct_fundamental_kpis.yml    ← catálogo completo + testes de grain
```

### Alteração em arquivo existente

```text
src/transformations/dbt_project.yml  ← adicionar intermediate (view) e marts (table)
```

---

## Design Decisions (from research.md)

| Decisão | Escolha |
|---------|---------|
| JSON flattening | `JSON_VALUE` + `SAFE_CAST` + `NULLIF` sentinel chain |
| Deduplicação | `ROW_NUMBER` por `ingest_date DESC`, filtro `fiscaldateending IS NOT NULL` |
| YoY Growth window | `LAG(4)` quarterly / `LAG(1)` annual |
| Join anchor da mart | `int_income_statement` como driving table (LEFT JOIN) |
| Colunas da mart | Apenas necessárias para KPIs + dimensões |
| Materialização | Intermediate = view; Mart = table |
| Overview join | Por `symbol` apenas (snapshot sem período fiscal) |

---

## KPI Reference

| KPI | Fórmula | Tipo |
|-----|---------|------|
| `roe` | `SAFE_DIVIDE(net_income, total_shareholder_equity)` | NUMERIC |
| `net_margin` | `SAFE_DIVIDE(net_income, total_revenue)` | NUMERIC |
| `ebitda_margin` | `SAFE_DIVIDE(ebitda_calc, total_revenue)` | NUMERIC |
| `net_debt_to_ebitda` | `SAFE_DIVIDE(net_debt, ebitda_calc)` | NUMERIC |
| `current_ratio` | `SAFE_DIVIDE(total_current_assets, total_current_liabilities)` | NUMERIC |
| `free_cash_flow` | `operating_cashflow - capital_expenditures` | INT64 |
| `quality_of_earnings` | `SAFE_DIVIDE(operating_cashflow, net_income)` | NUMERIC |
| `revenue_yoy_growth` | `SAFE_DIVIDE(rev - LAG(4/1)_rev, LAG(4/1)_rev)` | NUMERIC |
| `earnings_surprise_pct` | `surprise_percentage` de `int_earning` | NUMERIC |
| `pe_ratio` | `pe_ratio` de `int_overview` (snapshot) | NUMERIC |
| `ev_to_ebitda` | `ev_to_ebitda` de `int_overview` (snapshot) | NUMERIC |

---

## Implementation Order

1. Atualizar `dbt_project.yml` (intermediate + marts)
2. `int_income_statement.sql` + `.yml`
3. `int_balance_sheet.sql` + `.yml`
4. `int_cash_flow.sql` + `.yml`
5. `int_earning.sql` + `.yml`
6. `int_overview.sql` + `.yml`
7. `fct_fundamental_kpis.sql` + `.yml`
8. `dbt run --select intermediate` + `dbt test --select intermediate`
9. `dbt run --select marts` + `dbt test --select marts`
10. Validação manual com amostra (ver `quickstart.md`)

---

## Artifacts

- `specs/silver-gold-layers/research.md`
- `specs/silver-gold-layers/data-model.md`
- `specs/silver-gold-layers/quickstart.md`
- `specs/silver-gold-layers/plan.md` (este arquivo)
