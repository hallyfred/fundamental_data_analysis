---
description: "Task list for Silver & Gold dbt layers — Financial Fundamental Pipeline"
---

# Tasks: Silver & Gold Layers — Financial Fundamental Pipeline

**Input**: Design documents from `specs/silver-gold-layers/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | quickstart.md ✅

**Organization**: Tasks grouped by user story — cada fase é um incremento independente e testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências incompletas)
- **[Story]**: User story correspondente (US1–US7)

---

## Phase 1: Setup (Infraestrutura Compartilhada)

**Purpose**: Configurações de projeto que habilitam todas as camadas downstream.

- [ ] T001 Adicionar configurações de `intermediate` (view) e `marts` (table) em `src/transformations/dbt_project.yml`

**Checkpoint**: `dbt parse --project-dir src/transformations` deve passar sem erros.

---

## Phase 2: Fundacional (Pré-requisitos Bloqueantes)

**Purpose**: Estrutura de diretórios e verificação de dependências dbt que TODA fase downstream precisa.

⚠️ **CRÍTICO**: Nenhuma user story pode começar até esta fase estar completa.

- [ ] T002 Criar o diretório `src/transformations/models/intermediate/` (pode ser criado com um `.gitkeep` ou diretamente com o primeiro arquivo SQL)
- [ ] T003 Criar o diretório `src/transformations/models/marts/` (idem)
- [ ] T004 Verificar que `dbt_utils` está disponível em `src/transformations/packages.yml` para o teste `unique_combination_of_columns` (adicionar se ausente)

**Checkpoint**: Estrutura de diretórios pronta; `dbt deps --project-dir src/transformations` passa.

---

## Phase 3: User Story 1 — Intermediate Income Statement (P1) 🎯 MVP

**Goal**: Modelo `int_income_statement` com flattening completo do JSON, tipagem, deduplicação e campo derivado `ebitda_calc`.

**Independent Test**: `dbt run --select int_income_statement` + `dbt test --select int_income_statement` passam; query no BigQuery retorna linhas com `symbol`, `fiscaldateending` e `ebitda_calc` populados.

- [ ] T005 [US1] Criar `src/transformations/models/intermediate/int_income_statement.sql` com CTEs: `raw_parsed` (JSON_VALUE + NULLIF sentinels + SAFE_CAST), `unnested_reports` (UNNEST annualReports/quarterlyReports), `deduped` (ROW_NUMBER por ingest_date DESC), `filtered` (WHERE fiscaldateending IS NOT NULL), campo derivado `ebitda_calc`
- [ ] T006 [US1] Criar `src/transformations/models/intermediate/int_income_statement.yml` com description do modelo, `name`/`data_type`/`description` de todas as colunas, testes `not_null` (symbol, fiscaldateending), `accepted_values` (report_type), `dbt_utils.unique_combination_of_columns` (symbol, fiscaldateending, report_type)

**Checkpoint**: `dbt run --select int_income_statement` OK; `dbt test --select int_income_statement` OK.

---

## Phase 4: User Story 2 — Intermediate Balance Sheet (P1)

**Goal**: Modelo `int_balance_sheet` com todos os campos do balanço patrimonial, campos derivados `total_debt` e `net_debt`.

**Independent Test**: `dbt run --select int_balance_sheet` + `dbt test --select int_balance_sheet` passam; `net_debt` e `total_debt` calculados corretamente para ao menos um ticker.

- [ ] T007 [US2] Criar `src/transformations/models/intermediate/int_balance_sheet.sql` com CTEs equivalentes ao int_income_statement, incluindo campos derivados `total_debt` (COALESCE) e `net_debt`
- [ ] T008 [US2] Criar `src/transformations/models/intermediate/int_balance_sheet.yml` com catálogo completo de colunas, testes `not_null`, `accepted_values`, `unique_combination_of_columns`

**Checkpoint**: `dbt run --select int_balance_sheet` OK; `dbt test --select int_balance_sheet` OK.

---

## Phase 5: User Story 3 — Intermediate Cash Flow (P1)

**Goal**: Modelo `int_cash_flow` com fluxo de caixa tipado e campo derivado `free_cash_flow`.

**Independent Test**: `dbt run --select int_cash_flow` + `dbt test --select int_cash_flow` passam; `free_cash_flow` calculado (ou NULL quando componentes ausentes).

- [ ] T009 [US3] Criar `src/transformations/models/intermediate/int_cash_flow.sql` com CTEs de parse, dedup, filtro e campo derivado `free_cash_flow = operating_cashflow - capital_expenditures`
- [ ] T010 [US3] Criar `src/transformations/models/intermediate/int_cash_flow.yml` com catálogo completo de colunas e testes

**Checkpoint**: `dbt run --select int_cash_flow` OK; `dbt test --select int_cash_flow` OK.

---

## Phase 6: User Story 4 — Intermediate Earning (P2)

**Goal**: Modelo `int_earning` com EPS e surpresa de resultados tipados, distinguindo registros anuais de trimestrais.

**Independent Test**: `dbt run --select int_earning` + `dbt test --select int_earning` passam; `reported_date` é NULL para registros anuais e populado para trimestrais.

- [ ] T011 [US4] Criar `src/transformations/models/intermediate/int_earning.sql` com CTEs para `quarterlyEarnings` (report_type='quarterly', reported_date populado) e `annualEarnings` (report_type='annual', reported_date NULL), UNION ALL, dedup e filtro
- [ ] T012 [US4] Criar `src/transformations/models/intermediate/int_earning.yml` com catálogo completo e testes

**Checkpoint**: `dbt run --select int_earning` OK; `dbt test --select int_earning` OK.

---

## Phase 7: User Story 5 — Intermediate Overview (P2)

**Goal**: Modelo `int_overview` com metadados e múltiplos de mercado, deduplicado para um snapshot por empresa.

**Independent Test**: `dbt run --select int_overview` + `dbt test --select int_overview` passam; grain é exatamente um registro por `symbol`.

- [ ] T013 [US5] Criar `src/transformations/models/intermediate/int_overview.sql` com parse dos campos STRING e NUMERIC, dedup `ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ingest_date DESC)`, filtro `WHERE rn = 1`
- [ ] T014 [US5] Criar `src/transformations/models/intermediate/int_overview.yml` com catálogo completo, teste `not_null` (symbol), teste `unique` (symbol)

**Checkpoint**: `dbt run --select int_overview` OK; `dbt test --select int_overview` OK; um registro por ticker.

---

## Phase 8: User Story 6 — Mart fct_fundamental_kpis (P1) 🏆 Gold Layer

**Goal**: OBT `fct_fundamental_kpis` com todos os KPIs calculados, materializada como TABLE no BigQuery.

**Independent Test**: `dbt run --select fct_fundamental_kpis` OK; `dbt test --select fct_fundamental_kpis` OK; query de duplicatas retorna 0 linhas; KPIs de IBM conferem com cálculo manual.

- [ ] T015 [US6] Criar `src/transformations/models/marts/fct_fundamental_kpis.sql` com:
  - CTEs que referenciam `int_income_statement`, `int_balance_sheet`, `int_cash_flow`, `int_earning`, `int_overview`
  - LEFT JOINs ancorados em `int_income_statement` por `(symbol, fiscaldateending, report_type)`; join com `int_overview` apenas por `symbol`
  - CTE `revenue_with_lag` para calcular `LAG(4)` quarterly e `LAG(1)` annual
  - SELECT final com dimensões, `overview_snapshot_date`, todos os KPIs via `SAFE_DIVIDE`
- [ ] T016 [US6] Criar `src/transformations/models/marts/fct_fundamental_kpis.yml` com description do modelo, catálogo completo de colunas (incluindo fórmula de cada KPI na description), testes `not_null` (symbol, fiscaldateending, report_type), `dbt_utils.unique_combination_of_columns` (symbol, fiscaldateending, report_type)

**Checkpoint**: `dbt run --select fct_fundamental_kpis` OK; `dbt test --select fct_fundamental_kpis` OK; grain único confirmado por query.

---

## Phase 9: User Story 7 — Validação End-to-End & Documentação (P2)

**Goal**: Pipeline completo executado e documentado; `dbt docs` sem nós sem descrição.

**Independent Test**: todos os passos do `quickstart.md` passam; lineage completo no `dbt docs serve`.

- [ ] T017 [US7] Executar `dbt run --select intermediate marts --project-dir src/transformations` e confirmar que todos os 6 modelos constroem sem erros
- [ ] T018 [US7] Executar `dbt test --select intermediate marts --project-dir src/transformations` e confirmar que todos os testes passam
- [ ] T019 [US7] Executar query de validação de grain da mart (ver `quickstart.md` seção 5) e confirmar 0 duplicatas
- [ ] T020 [US7] Executar validação manual de KPIs para ao menos 1 ticker (ver `quickstart.md` seção 6): conferir `net_margin`, `roe` e `revenue_yoy_growth` contra fonte Alpha Vantage
- [ ] T021 [P] [US7] Executar `dbt docs generate --project-dir src/transformations` e verificar que todos os modelos intermediate e mart aparecem no lineage sem nós sem descrição

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Ajustes finais e verificação de conformidade com a constituição.

- [ ] T022 [P] Verificar que nenhum modelo intermediate ou mart contém lógica de parse que deveria estar em outra camada (Princípio I da constituição)
- [ ] T023 [P] Verificar que todos os arquivos SQL têm comentário de grain no início (Princípio II da constituição)
- [ ] T024 Atualizar `README.md` com a nova estrutura de camadas (seção System Architecture) e os comandos de execução atualizados

---

## Dependencies & Execution Order

### Dependências entre Fases

- **Phase 1 (Setup)**: Sem dependências — pode começar imediatamente
- **Phase 2 (Fundacional)**: Depende de Phase 1 — **bloqueia todas as user stories**
- **Phases 3–7 (Intermediates)**: Dependem de Phase 2 — podem rodar em **paralelo entre si**
- **Phase 8 (Mart)**: Depende de **todas** as Phases 3–7 estarem completas
- **Phase 9 (Validação)**: Depende de Phase 8
- **Phase 10 (Polish)**: Depende de Phase 9

### Dependências entre User Stories

- **US1 (Income Statement)**: Sem dependências — inicia após Phase 2
- **US2 (Balance Sheet)**: Sem dependências — inicia após Phase 2, paralelo com US1
- **US3 (Cash Flow)**: Sem dependências — inicia após Phase 2, paralelo com US1/US2
- **US4 (Earning)**: Sem dependências — inicia após Phase 2, paralelo com US1/US2/US3
- **US5 (Overview)**: Sem dependências — inicia após Phase 2, paralelo com US1–US4
- **US6 (Mart)**: **Depende de US1, US2, US3, US4 e US5** — todos os intermediates devem estar completos
- **US7 (Validação)**: Depende de US6

### Oportunidades de Paralelismo

- T005/T007/T009/T011/T013 (SQL dos intermediates) podem rodar em **paralelo**
- T006/T008/T010/T012/T014 (YAMLs dos intermediates) podem rodar em **paralelo** com seus respectivos SQLs
- T015 (mart SQL) só começa após T005–T014 estarem todos completos

---

## Parallel Example: Intermediates (Phases 3–7)

```bash
# Após Phase 2 completa, lançar em paralelo:
Task T005: int_income_statement.sql
Task T007: int_balance_sheet.sql
Task T009: int_cash_flow.sql
Task T011: int_earning.sql
Task T013: int_overview.sql

# Simultaneamente com os SQLs:
Task T006: int_income_statement.yml
Task T008: int_balance_sheet.yml
Task T010: int_cash_flow.yml
Task T012: int_earning.yml
Task T014: int_overview.yml
```

---

## Implementation Strategy

### MVP First (US1 — Income Statement)

1. Completar Phase 1 + Phase 2
2. Completar Phase 3 (US1 — `int_income_statement`)
3. **PARAR e VALIDAR**: `dbt test --select int_income_statement`
4. Avançar para os demais intermediates

### Entrega Incremental

1. Setup + Foundacional → base pronta
2. US1 (Income) → testar → continuar
3. US2 (Balance) + US3 (Cash Flow) + US4 (Earning) + US5 (Overview) → em paralelo → testar
4. US6 (Mart) → testar → **Gold Layer funcional** 🏆
5. US7 (Validação E2E) → documentar

---

## Notes

- **[P]** = arquivos diferentes, sem dependências incompletas
- Cada intermediate pode ser validado independentemente antes de avançar para a mart
- `SAFE_CAST` obrigatório em toda coerção de tipo — nunca usar `CAST` direto
- `SAFE_DIVIDE` obrigatório em toda divisão de KPI — nunca usar `/` diretamente
- Sentinel values (`'None'`, `'-'`, `'N/A'`, `''`) devem ser removidos via `NULLIF` antes de qualquer cast
- Grain comment obrigatório no início de cada arquivo SQL (Constituição, Princípio II)
- Commit após cada fase ou par SQL+YAML
