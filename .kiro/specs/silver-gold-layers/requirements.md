# Requirements Document

## Introduction

Este documento especifica os requisitos para a evolução do pipeline dbt do projeto `fundamental_data_analysis`, cobrindo as camadas **intermediate (Silver)** e **marts (Gold)**.

As responsabilidades de cada camada são explícitas e não se sobrepõem:

- **Staging (existente, sem alteração):** cria as external tables no BigQuery apontando para os JSONs brutos no GCS particionados por `year/month/day`. Expõe apenas `raw_data STRING` e as colunas de partição. Nenhum parse ou flattening ocorre aqui.
- **Intermediate (Silver — a implementar):** responsável por fazer o flattening dos JSONs via `JSON_VALUE()`, tipar as colunas, tratar sentinel values, deduplica por ingestão mais recente e calcular campos derivados reutilizáveis. Cada modelo intermediate deve ter um arquivo YAML de catálogo de colunas correspondente (`.yml`).
- **Marts (Gold — a implementar):** responsável pelos joins entre os modelos intermediate e pelo cálculo dos KPIs fundamentalistas, entregando uma One Big Table (OBT). O modelo mart deve ter um arquivo YAML de catálogo de colunas correspondente (`.yml`).

O pipeline já possui os modelos de staging implementados para cinco endpoints da Alpha Vantage: `OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW` e `EARNINGS`. Esses modelos não serão modificados. O objetivo desta feature é implementar completamente as camadas intermediate e marts.

---

## Glossary

- **Pipeline**: O conjunto de modelos dbt que transforma dados Bronze em Gold.
- **Staging_Model**: Modelo dbt existente, materializado como view, que cria a external table no BigQuery e expõe apenas `raw_data STRING` e colunas de partição `year`, `month`, `day`. Não realiza nenhum parse.
- **Intermediate_Model**: Modelo dbt que lê de um `Staging_Model` e realiza flattening via `JSON_VALUE()`, tipagem, tratamento de sentinel values, deduplicação e cálculo de campos derivados. Deve ter arquivo YAML de catálogo de colunas.
- **Mart_Model**: Modelo dbt materializado como table que une os `Intermediate_Models` e calcula KPIs de negócio. Deve ter arquivo YAML de catálogo de colunas.
- **YAML de catálogo**: Arquivo `.yml` co-localizado com o modelo SQL, contendo `description` do modelo, e `name`, `data_type` e `description` de cada coluna, além dos testes dbt declarados.
- **OBT (One Big Table)**: Tabela desnormalizada com grain de um registro por (`symbol`, `fiscaldateending`, `report_type`), contendo todas as colunas financeiras e KPIs calculados.
- **KPI**: Indicador-chave de performance financeiro calculado a partir dos demonstrativos.
- **raw_data**: Campo `STRING` das external tables contendo o payload JSON bruto da Alpha Vantage.
- **fiscaldateending**: Data de encerramento do período fiscal de cada relatório.
- **report_type**: Classificação do relatório como `'annual'` ou `'quarterly'`.
- **symbol**: Ticker da ação (ex: `'IBM'`, `'AAPL'`).
- **ingest_date**: Data de ingestão calculada como `DATE(partition_year, partition_month, partition_day)`.
- **Deduplicação**: Seleção do registro com o maior `ingest_date` quando múltiplas ingestões contêm o mesmo `(symbol, fiscaldateending, report_type)`.
- **Grain**: Conjunto de colunas que identifica unicamente cada linha em uma tabela.
- **EBITDA**: Lucro antes de juros, impostos, depreciação e amortização — calculado como `ebit + depreciationAndAmortization` quando o campo direto for NULL.
- **FCF (Free Cash Flow)**: Fluxo de caixa livre — `operatingCashflow - capitalExpenditures`.
- **LAG()**: Função de janela SQL usada para comparar um valor com o período anterior.
- **CapEx**: `capitalExpenditures` do endpoint `CASH_FLOW`.
- **Sentinel value**: String que representa ausência de dado na API Alpha Vantage: `'None'`, `'-'`, `'N/A'` ou string vazia `''`.

---

## Clarifications

### Session 2026-09-07

- Q: Para `revenue_yoy_growth`, a comparação deve ser com o mesmo período do ano anterior ou com o período imediatamente anterior? → A: Mesmo período do ano anterior — `LAG(4)` para quarterly, `LAG(1)` para annual.
- Q: Quando `fiscaldateending` falha no parse e fica NULL, o registro deve ser incluído ou excluído do join na mart? → A: Excluir na intermediate com `WHERE fiscaldateending IS NOT NULL` após deduplicação — só descarta datas corrompidas na origem, não dados trimestrais válidos.
- Q: O join de `int_earning` na mart deve usar `(symbol, fiscaldateending, report_type)` ou apenas `(symbol, fiscaldateending)`? → A: Join completo por `(symbol, fiscaldateending, report_type)` — consistente com o grain da mart; NULLs em `earnings_surprise_pct` para períodos sem match são aceitáveis e esperados.
- Q: Quando um período existe apenas no `int_balance_sheet` mas não no `int_income_statement`, esse período deve aparecer na mart? → A: Não — anchor exclusivo no income statement com LEFT JOIN para os demais; períodos sem income statement não entram na OBT.
- Q: A mart deve incluir todas as colunas brutas dos intermediates ou apenas as necessárias para calcular os KPIs? → A: Apenas as colunas necessárias para calcular os KPIs definidos + metadados — tabela enxuta (~20-25 colunas), sem prefixação de colunas brutas.



---

### Requisito 1: Intermediate — Flattening e tipagem do Income Statement

**User Story:** Como analista de dados, quero que o modelo `int_income_statement` exponha todas as colunas financeiras do demonstrativo de resultados em colunas tipadas, para que eu possa usar os dados sem realizar parse manual de JSON em camadas downstream.

#### Critérios de Aceite

1. QUANDO o `Intermediate_Model` processar `stg_income_statement`, O `Intermediate_Model` SHALL extrair `symbol` via `JSON_VALUE(raw_data, '$.symbol')` retornando-o como `STRING`.
2. QUANDO o `Intermediate_Model` processar cada elemento de `annualReports` e `quarterlyReports` do array JSON, O `Intermediate_Model` SHALL produzir uma linha por relatório com `report_type` igual a `'annual'` para `annualReports` e `'quarterly'` para `quarterlyReports`.
3. THE `Intermediate_Model` SHALL extrair `fiscaldateending` como `DATE` via `SAFE.PARSE_DATE('%Y-%m-%d', JSON_VALUE(report, '$.fiscalDateEnding'))`, retornando `NULL` se o parse falhar.
4. THE `Intermediate_Model` SHALL preservar `fiscaldateending_raw STRING` com o valor original de `fiscalDateEnding` antes do parse, para auditoria.
5. THE `Intermediate_Model` SHALL extrair os seguintes campos numéricos como `INT64` via `SAFE_CAST(NULLIF(NULLIF(NULLIF(NULLIF(JSON_VALUE(...), 'None'), '-'), 'N/A'), '') AS INT64)`: `gross_profit`, `total_revenue`, `cost_of_revenue`, `operating_income`, `selling_general_and_administrative`, `research_and_development`, `operating_expenses`, `net_interest_income`, `interest_income`, `interest_expense`, `depreciation_and_amortization`, `income_before_tax`, `income_tax_expense`, `net_income_from_continuing_operations`, `ebit`, `ebitda`, `net_income`.
6. THE `Intermediate_Model` SHALL incluir `reportedcurrency STRING` extraído via `JSON_VALUE(report, '$.reportedCurrency')`.
7. THE `Intermediate_Model` SHALL incluir `partition_year INT64`, `partition_month INT64`, `partition_day INT64` e `ingest_date DATE` calculada como `DATE(partition_year, partition_month, partition_day)`.
8. THE `Intermediate_Model` SHALL calcular `ebitda_calc INT64` como `COALESCE(ebitda, ebit + depreciation_and_amortization)`, retornando `NULL` se todos os componentes forem `NULL`.
9. THE `Intermediate_Model` SHALL ser materializado como `view` no BigQuery.
10. THE `Intermediate_Model` SHALL ter um arquivo YAML de catálogo com `description` do modelo e `name`, `data_type` e `description` de cada coluna.

---

### Requisito 2: Intermediate — Flattening e tipagem do Balance Sheet

**User Story:** Como analista de dados, quero que o modelo `int_balance_sheet` exponha todas as colunas do balanço patrimonial em colunas tipadas, para que eu possa calcular indicadores de saúde financeira sem parse manual.

#### Critérios de Aceite

1. QUANDO o `Intermediate_Model` processar `stg_balance_sheet`, O `Intermediate_Model` SHALL extrair `symbol` via `JSON_VALUE(raw_data, '$.symbol')` como `STRING` e produzir uma linha por relatório de `annualReports` com `report_type = 'annual'` e uma linha por relatório de `quarterlyReports` com `report_type = 'quarterly'`.
2. THE `Intermediate_Model` SHALL extrair `fiscaldateending` como `DATE` via `SAFE.PARSE_DATE('%Y-%m-%d', ...)`, retornando `NULL` se o parse falhar, e preservar `fiscaldateending_raw STRING` com o valor original.
3. THE `Intermediate_Model` SHALL extrair os seguintes campos como `INT64` via `SAFE_CAST` com tratamento de sentinel values: `total_assets`, `total_current_assets`, `cash_and_cash_equivalents`, `cash_and_short_term_investments`, `inventory`, `current_net_receivables`, `total_non_current_assets`, `property_plant_equipment`, `intangible_assets`, `goodwill`, `long_term_investments`, `short_term_investments`, `total_liabilities`, `total_current_liabilities`, `current_accounts_payable`, `short_term_debt`, `total_non_current_liabilities`, `capital_lease_obligations`, `long_term_debt`, `current_long_term_debt`, `short_long_term_debt_total`, `other_current_liabilities`, `total_shareholder_equity`, `retained_earnings`, `common_stock`, `common_stock_shares_outstanding`.
4. THE `Intermediate_Model` SHALL calcular `total_debt INT64` como `COALESCE(short_long_term_debt_total, long_term_debt + short_term_debt)`, retornando `NULL` se todos os componentes forem `NULL`.
5. THE `Intermediate_Model` SHALL calcular `net_debt INT64` como `total_debt - cash_and_cash_equivalents`; IF qualquer componente for `NULL`, THEN `net_debt` SHALL ser `NULL`.
6. THE `Intermediate_Model` SHALL incluir `reportedcurrency STRING`, `partition_year INT64`, `partition_month INT64`, `partition_day INT64` e `ingest_date DATE`.
7. THE `Intermediate_Model` SHALL ser materializado como `view` e ter um arquivo YAML de catálogo com descrição do modelo e de cada coluna.

---

### Requisito 3: Intermediate — Flattening e tipagem do Cash Flow

**User Story:** Como analista de dados, quero que o modelo `int_cash_flow` exponha colunas tipadas do fluxo de caixa, para que eu possa calcular Free Cash Flow e Quality of Earnings sem parse manual.

#### Critérios de Aceite

1. QUANDO o `Intermediate_Model` processar `stg_cash_flow`, O `Intermediate_Model` SHALL extrair `symbol` como `STRING` e produzir uma linha por relatório de `annualReports` com `report_type = 'annual'` e uma linha por relatório de `quarterlyReports` com `report_type = 'quarterly'`.
2. THE `Intermediate_Model` SHALL extrair `fiscaldateending` como `DATE` com `SAFE.PARSE_DATE`, preservando `fiscaldateending_raw STRING`.
3. THE `Intermediate_Model` SHALL extrair os seguintes campos como `INT64` via `SAFE_CAST` com tratamento de sentinel values: `operating_cashflow`, `capital_expenditures`, `depreciation_depletion_and_amortization`, `dividend_payout`, `stock_based_compensation`, `cashflow_from_investment`, `cashflow_from_financing`, `net_income`.
4. THE `Intermediate_Model` SHALL calcular `free_cash_flow INT64` como `operating_cashflow - capital_expenditures`; IF qualquer componente for `NULL`, THEN `free_cash_flow` SHALL ser `NULL`.
5. THE `Intermediate_Model` SHALL incluir `reportedcurrency STRING`, `partition_year INT64`, `partition_month INT64`, `partition_day INT64` e `ingest_date DATE`.
6. THE `Intermediate_Model` SHALL ser materializado como `view` e ter um arquivo YAML de catálogo com descrição do modelo e de cada coluna.

---

### Requisito 4: Intermediate — Flattening e tipagem do Earnings

**User Story:** Como analista de dados, quero que o modelo `int_earning` exponha colunas tipadas de EPS e surpresa de resultados, para que eu possa calcular Earnings Surprise % sem parse manual.

#### Critérios de Aceite

1. QUANDO o `Intermediate_Model` processar `stg_earning`, O `Intermediate_Model` SHALL extrair `symbol` como `STRING` e produzir uma linha por elemento de `quarterlyEarnings` com `report_type = 'quarterly'` e uma linha por elemento de `annualEarnings` com `report_type = 'annual'`.
2. THE `Intermediate_Model` SHALL extrair `fiscaldateending` como `DATE` com `SAFE.PARSE_DATE`, preservando `fiscaldateending_raw STRING`.
3. THE `Intermediate_Model` SHALL extrair `reported_date DATE` via `SAFE.PARSE_DATE` para registros trimestrais, e retornar `NULL` para registros anuais onde o campo não existe.
4. THE `Intermediate_Model` SHALL extrair `reported_eps`, `estimated_eps`, `surprise`, `surprise_percentage` como `NUMERIC` via `SAFE_CAST` com tratamento de sentinel values.
5. THE `Intermediate_Model` SHALL incluir `partition_year INT64`, `partition_month INT64`, `partition_day INT64` e `ingest_date DATE`.
6. THE `Intermediate_Model` SHALL ser materializado como `view` e ter um arquivo YAML de catálogo com descrição do modelo e de cada coluna.

---

### Requisito 5: Intermediate — Flattening e tipagem do Overview

**User Story:** Como analista de dados, quero que o modelo `int_overview` exponha os metadados e métricas snapshot da empresa em colunas tipadas, para que eu possa enriquecer a OBT com setor, indústria e múltiplos de mercado atuais.

#### Critérios de Aceite

1. QUANDO o `Intermediate_Model` processar `stg_overview`, O `Intermediate_Model` SHALL extrair uma linha por registro de `(symbol, ingest_date)`, onde `ingest_date = DATE(partition_year, partition_month, partition_day)`.
2. THE `Intermediate_Model` SHALL extrair como `STRING` via `JSON_VALUE`: `symbol`, `asset_type`, `name`, `exchange`, `currency`, `country`, `sector`, `industry`, `fiscal_year_end`, `latest_quarter`.
3. THE `Intermediate_Model` SHALL extrair como `INT64` via `SAFE_CAST` com tratamento de sentinel values: `market_capitalization`.
4. THE `Intermediate_Model` SHALL extrair como `NUMERIC` via `SAFE_CAST` com tratamento de sentinel values: `pe_ratio`, `peg_ratio`, `book_value`, `dividend_per_share`, `dividend_yield`, `eps`, `revenue_per_share_ttm`, `profit_margin`, `return_on_equity_ttm`, `ev_to_revenue`, `ev_to_ebitda`, `beta`, `trailing_pe`, `forward_pe`, `price_to_sales_ratio_ttm`, `price_to_book_ratio`.
5. THE `Intermediate_Model` SHALL incluir `partition_year INT64`, `partition_month INT64`, `partition_day INT64` e `ingest_date DATE`.
6. THE `Intermediate_Model` SHALL ser materializado como `view` e ter um arquivo YAML de catálogo com descrição do modelo e de cada coluna.

---

### Requisito 6: Intermediate — Deduplicação por ingestão mais recente

**User Story:** Como engenheiro de dados, quero que cada modelo intermediate retenha apenas o registro mais recente para cada período fiscal por empresa, para que os joins na mart nunca multipliquem linhas silenciosamente.

#### Critérios de Aceite

1. THE `Intermediate_Model` de cada demonstrativo SHALL aplicar `ROW_NUMBER() OVER (PARTITION BY symbol, fiscaldateending, report_type ORDER BY ingest_date DESC, partition_day DESC, partition_month DESC)` e reter somente o registro com `row_num = 1`.
2. THE `Intermediate_Model` SHALL aplicar `WHERE fiscaldateending IS NOT NULL` após a deduplicação, descartando apenas registros cujo campo `fiscalDateEnding` era inválido ou ausente na origem (ex: `'None'`, `''`). Registros com datas válidas — incluindo todos os trimestrais — NÃO são afetados.
3. THE `Intermediate_Model` SHALL garantir que a combinação `(symbol, fiscaldateending, report_type)` seja única após a deduplicação.
3. THE `Intermediate_Model` de `int_overview` SHALL aplicar `ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ingest_date DESC)` e reter somente o registro mais recente por `symbol`, pois o overview é um snapshot sem dimensão de período fiscal.

---

### Requisito 7: Intermediate — Alinhamento de grain entre demonstrativos

**User Story:** Como engenheiro de dados, quero que todos os modelos intermediate compartilhem a mesma chave de join, para que os joins na mart sejam seguros e sem geração de linhas extras.

#### Critérios de Aceite

1. THE `Intermediate_Model` de `income_statement`, `balance_sheet`, `cash_flow` e `earning` SHALL todos expor a mesma chave composta `(symbol, fiscaldateending, report_type)` como colunas de nível superior, padronizando o grain entre demonstrativos.
2. THE `Intermediate_Model` SHALL incluir um comentário SQL no início do arquivo documentando a semântica do grain — distinguindo demonstrativos de fluxo (income, cash flow) de demonstrativos de posição (balance sheet).
3. THE `Mart_Model` SHALL usar `int_income_statement` como tabela âncora (driving table) com LEFT JOIN para `int_balance_sheet`, `int_cash_flow`, `int_earning` e `int_overview`. Períodos que existam apenas no `int_balance_sheet` ou outros demonstrativos, mas não no `int_income_statement`, NÃO aparecerão na OBT.

---

### Requisito 8: Marts — One Big Table (OBT) com KPIs fundamentalistas

**User Story:** Como analista financeiro, quero uma tabela única com grain `(symbol, fiscaldateending, report_type)` contendo todas as colunas financeiras e KPIs calculados, para que eu possa analisar qualquer empresa sem construir joins manuais.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL ser nomeado `fct_fundamental_kpis` e materializado como `TABLE` no dataset `alphavantage` do BigQuery.
2. THE `Mart_Model` SHALL ter grain de exatamente um registro por `(symbol, fiscaldateending, report_type)`.
3. THE `Mart_Model` SHALL incluir as colunas de metadados `symbol STRING`, `fiscaldateending DATE`, `report_type STRING`, `reportedcurrency STRING` e `ingest_date DATE`.
4. THE `Mart_Model` SHALL incluir apenas as colunas brutas dos intermediates estritamente necessárias para calcular os KPIs definidos nos Requisitos 9–13, além das colunas de metadados. Colunas brutas não utilizadas em nenhum KPI NÃO devem ser incluídas na mart — o analista deve consultar os modelos intermediate diretamente para dados não-KPI.
5. THE `Mart_Model` SHALL ter um arquivo YAML de catálogo com `description` do modelo e `name`, `data_type` e `description` de cada coluna, incluindo as colunas de KPI.

---

### Requisito 9: Marts — KPIs de Rentabilidade

**User Story:** Como analista financeiro, quero que a OBT contenha os KPIs de rentabilidade calculados, para que eu possa avaliar a eficiência operacional de cada empresa por período.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL calcular `roe NUMERIC` como `SAFE_DIVIDE(inc_net_income, bs_total_shareholder_equity)`; IF o denominador for `NULL` ou `0`, THEN `roe` SHALL ser `NULL`.
2. THE `Mart_Model` SHALL calcular `net_margin NUMERIC` como `SAFE_DIVIDE(inc_net_income, inc_total_revenue)`; IF o denominador for `NULL` ou `0`, THEN `net_margin` SHALL ser `NULL`.
3. THE `Mart_Model` SHALL calcular `ebitda_margin NUMERIC` como `SAFE_DIVIDE(inc_ebitda_calc, inc_total_revenue)`; IF o denominador for `NULL` ou `0`, THEN `ebitda_margin` SHALL ser `NULL`.

---

### Requisito 10: Marts — KPIs de Saúde e Risco

**User Story:** Como analista financeiro, quero que a OBT contenha os KPIs de saúde financeira calculados, para que eu possa avaliar o nível de alavancagem e liquidez de cada empresa por período.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL calcular `net_debt_to_ebitda NUMERIC` como `SAFE_DIVIDE(bs_net_debt, inc_ebitda_calc)`; IF o denominador for `NULL` ou `0`, THEN `net_debt_to_ebitda` SHALL ser `NULL`.
2. THE `Mart_Model` SHALL calcular `current_ratio NUMERIC` como `SAFE_DIVIDE(bs_total_current_assets, bs_total_current_liabilities)`; IF o denominador for `NULL` ou `0`, THEN `current_ratio` SHALL ser `NULL`.

---

### Requisito 11: Marts — KPIs de Geração de Caixa

**User Story:** Como analista financeiro, quero que a OBT contenha os KPIs de geração de caixa calculados, para que eu possa avaliar a qualidade e quantidade do caixa gerado por cada empresa por período.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL incluir `free_cash_flow INT64` herdado diretamente de `int_cash_flow` (campo `free_cash_flow` já calculado na camada intermediate).
2. THE `Mart_Model` SHALL calcular `quality_of_earnings NUMERIC` como `SAFE_DIVIDE(cf_operating_cashflow, inc_net_income)`; IF o denominador for `NULL` ou `0`, THEN `quality_of_earnings` SHALL ser `NULL`.

---

### Requisito 12: Marts — KPIs de Crescimento

**User Story:** Como analista financeiro, quero que a OBT contenha indicadores de crescimento histórico calculados, para que eu possa identificar tendências de receita e surpresas de resultado por empresa.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL calcular `revenue_yoy_growth NUMERIC` comparando com o mesmo período do ano anterior: `LAG(4)` para registros com `report_type = 'quarterly'` e `LAG(1)` para registros com `report_type = 'annual'`, ambos `OVER (PARTITION BY symbol, report_type ORDER BY fiscaldateending)`. A fórmula é `SAFE_DIVIDE(inc_total_revenue - prior_revenue, prior_revenue)` onde `prior_revenue` é o valor do período correspondente; IF `prior_revenue` for `NULL` ou `0`, THEN `revenue_yoy_growth` SHALL ser `NULL`.
2. THE `Mart_Model` SHALL incluir `earnings_surprise_pct NUMERIC` herdado de `int_earning` (campo `surprise_percentage`) com join por `(symbol, fiscaldateending, report_type)` — chave completa, consistente com o grain da mart.
3. IF um período não possuir registro correspondente em `int_earning` para a chave `(symbol, fiscaldateending, report_type)`, THEN `earnings_surprise_pct` SHALL ser `NULL` sem descartar a linha da OBT. Isso é comportamento esperado, especialmente para períodos anuais.

---

### Requisito 13: Marts — KPIs de Valuation via Overview

**User Story:** Como analista financeiro, quero que a OBT contenha P/E Ratio e EV/EBITDA do snapshot mais recente do `OVERVIEW`, para que eu possa comparar valuation de mercado com os dados fundamentalistas históricos.

#### Critérios de Aceite

1. THE `Mart_Model` SHALL incluir `pe_ratio NUMERIC` e `ev_to_ebitda NUMERIC` extraídos de `int_overview`, usando o snapshot mais recente por `symbol` (conforme deduplicação já aplicada na camada intermediate).
2. IF um `symbol` não possuir registro em `int_overview`, THEN `pe_ratio` e `ev_to_ebitda` SHALL ser `NULL` sem descartar a linha da OBT.
3. THE `Mart_Model` SHALL incluir `overview_snapshot_date DATE` indicando qual `ingest_date` do overview foi usado para rastreabilidade.
4. THE `Mart_Model` SHALL incluir metadados descritivos do overview: `sector STRING`, `industry STRING`, `country STRING`, `exchange STRING`.

---

### Requisito 14: Qualidade de dados — Testes dbt nos modelos intermediate e marts

**User Story:** Como engenheiro de dados, quero que todos os modelos intermediate e marts possuam testes dbt declarados nos arquivos YAML, para que regressões de qualidade sejam detectadas automaticamente a cada execução do pipeline.

#### Critérios de Aceite

1. THE `Intermediate_Model` de cada demonstrativo SHALL declarar no seu arquivo YAML os testes `not_null` para `symbol` e `fiscaldateending`.
2. THE `Intermediate_Model` de cada demonstrativo SHALL declarar no seu arquivo YAML o teste `accepted_values` para `report_type` com valores `['annual', 'quarterly']`.
3. THE `Intermediate_Model` de cada demonstrativo SHALL declarar no seu arquivo YAML o teste de unicidade composta `dbt_utils.unique_combination_of_columns` para `(symbol, fiscaldateending, report_type)`.
4. THE `Mart_Model` SHALL declarar no seu arquivo YAML o teste de unicidade composta para `(symbol, fiscaldateending, report_type)`.
5. THE `Mart_Model` SHALL declarar no seu arquivo YAML testes `not_null` para `symbol`, `fiscaldateending` e `report_type`.
6. WHEN um KPI calculado com `SAFE_DIVIDE` retornar `NULL` por denominador zero ou nulo, O `Mart_Model` SHALL tratar o resultado como dado válido `NULL` e nenhum teste SHALL falhar por causa de `NULL` nos campos de KPI.

---

### Requisito 15: Materialização e configurações dbt

**User Story:** Como engenheiro de dados, quero que as configurações de materialização de cada camada estejam declaradas no `dbt_project.yml`, para que o pipeline seja reproduzível e as tabelas apareçam nos datasets corretos do BigQuery.

#### Critérios de Aceite

1. THE `Pipeline` SHALL manter a configuração existente de `staging` como `materialized: view` no `dbt_project.yml`, sem nenhuma alteração.
2. THE `Pipeline` SHALL adicionar configuração de `intermediate` como `materialized: view` no `dbt_project.yml`.
3. THE `Pipeline` SHALL adicionar configuração de `marts` como `materialized: table` no `dbt_project.yml`.
4. THE `Pipeline` SHALL usar o dataset BigQuery `alphavantage` como schema padrão para todos os modelos, conforme o profile `transformations` já configurado.
5. THE `Pipeline` SHALL garantir que `dbt run --select intermediate` execute apenas os cinco modelos intermediate sem dependência dos modelos de marts.
6. THE `Pipeline` SHALL garantir que `dbt run --select marts` execute o modelo `fct_fundamental_kpis` e todas as suas dependências intermediate na ordem correta.
