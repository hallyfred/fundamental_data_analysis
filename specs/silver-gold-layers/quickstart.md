# Quickstart: Validação das Camadas Silver & Gold

## Pré-requisitos

- Docker e Docker Compose instalados e rodando
- Variáveis de ambiente configuradas em `.env` (ver `.env.example`)
- Credenciais GCP em `config/gcp_credentials.json`
- Containers do projeto rodando: `docker-compose up -d --build`

## 1. Recriar External Tables

Antes de rodar os modelos, garantir que as external tables estejam atualizadas:

```bash
docker-compose exec airflow-webserver dbt run-operation dbt_external_tables.stage_external_sources \
  --project-dir src/transformations \
  --vars "ext_full_refresh: true"
```

Resultado esperado: 5 tabelas criadas/atualizadas no dataset `alphavantage` (ext_overview, ext_balance_sheet, ext_cash_flow, ext_income_statement, ext_earning).

## 2. Rodar a Camada Intermediate (Silver)

```bash
docker-compose exec airflow-webserver dbt run \
  --select intermediate \
  --project-dir src/transformations
```

Resultado esperado: 5 modelos construídos com status `OK`:
- `int_income_statement`
- `int_balance_sheet`
- `int_cash_flow`
- `int_earning`
- `int_overview`

## 3. Rodar a Camada Mart (Gold)

```bash
docker-compose exec airflow-webserver dbt run \
  --select marts \
  --project-dir src/transformations
```

Resultado esperado: 1 modelo construído com status `OK`:
- `fct_fundamental_kpis` materializado como TABLE no dataset `alphavantage`

## 4. Executar os Testes dbt

```bash
docker-compose exec airflow-webserver dbt test \
  --select intermediate marts \
  --project-dir src/transformations
```

Resultado esperado: todos os testes passam. Testes críticos:
- `not_null` em `symbol` e `fiscaldateending` para todos os intermediates
- `accepted_values` em `report_type` (annual, quarterly) para todos os intermediates
- `dbt_utils.unique_combination_of_columns` em `(symbol, fiscaldateending, report_type)` para todos os intermediates e para `fct_fundamental_kpis`
- `not_null` em `symbol`, `fiscaldateending`, `report_type` para `fct_fundamental_kpis`

Testes que podem retornar warnings mas NÃO devem falhar:
- NULL em colunas KPI (`roe`, `net_margin`, etc.) — comportamento esperado quando denominador é NULL/0

## 5. Validar o Grain da Mart

Query de verificação no BigQuery (via console GCP ou `bq` CLI):

```sql
-- Deve retornar 0 duplicatas
SELECT
  symbol,
  fiscaldateending,
  report_type,
  COUNT(*) as cnt
FROM `projetodbt-479518.alphavantage.fct_fundamental_kpis`
GROUP BY 1, 2, 3
HAVING cnt > 1
```

Resultado esperado: nenhuma linha retornada.

## 6. Validar KPIs com Amostra Manual

Escolha um ticker conhecido (ex: IBM) e valide manualmente 2–3 KPIs contra os dados da Alpha Vantage:

```sql
-- Amostra de KPIs para IBM, últimos 4 períodos anuais
SELECT
  symbol,
  fiscaldateending,
  report_type,
  net_margin,
  roe,
  current_ratio,
  free_cash_flow,
  revenue_yoy_growth
FROM `projetodbt-479518.alphavantage.fct_fundamental_kpis`
WHERE symbol = 'IBM'
  AND report_type = 'annual'
ORDER BY fiscaldateending DESC
LIMIT 4
```

Verificação manual esperada:
- `net_margin = net_income / total_revenue` — confirmar contra fonte
- `roe = net_income / total_shareholder_equity` — confirmar contra fonte
- `revenue_yoy_growth` para 2023 deve comparar com 2022 (LAG 1 para annual)

## 7. Gerar Documentação dbt

```bash
docker-compose exec airflow-webserver dbt docs generate \
  --project-dir src/transformations

docker-compose exec airflow-webserver dbt docs serve \
  --project-dir src/transformations \
  --port 8081
```

Acessar em: `http://localhost:8081`

Verificar:
- Todos os modelos intermediate e mart aparecem no lineage graph
- Nenhum modelo sem descrição de coluna
- Lineage mostra: `ext_*` → `stg_*` → `int_*` → `fct_fundamental_kpis`

## Critérios de Aceite da Validação

| Critério | Verificação |
|----------|-------------|
| 5 modelos intermediate construídos | `dbt run --select intermediate` sem erros |
| 1 modelo mart construído | `dbt run --select marts` sem erros |
| Todos os testes passam | `dbt test --select intermediate marts` sem falhas |
| Grain único na mart | Query de duplicatas retorna 0 linhas |
| KPIs validados manualmente | 2–3 KPIs conferidos para 1 ticker |
| Lineage completo no dbt docs | Todos os nós documentados |
