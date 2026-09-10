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

## Status de execução — atualizado em 2026-09-10

- **T001–T016 concluídas no código**: configurações, diretórios, dependência `dbt_utils` os cinco modelos Silver e a mart Gold com seus catálogos e testes declarados. Os checkpoints de execução no BigQuery continuam pendentes; checkbox de implementação não significa validação em produção.
- **Validação realizada**: `dbt parse` aprovado no dbt 1.12.2 sem o aviso de `meta`; Ruff e formatação aprovados; pytest com **64 aprovados no container Linux**. O build real no BigQuery aprovou os **30 testes unitários dbt**, os **27 testes de qualidade dbt**, os cinco modelos Silver e a mart Gold.
- **Erro `raw_data` resolvido**: `stg_overview` e `int_overview` foram recriados no BigQuery; os cinco testes de `int_overview` passaram.
- **Prioridade normativa**: `.specify/memory/constitution.md`. Datas fiscais inválidas permanecem como NULL para auditoria e falham no teste `not_null`; não são descartadas. Todos os campos de `contract.py` devem estar disponíveis na Silver.
- **Gold validada com dados reais**: a mart foi materializada com aproximadamente 1,2 mil linhas, o teste de grain e a consulta explícita retornaram zero duplicatas, e os KPIs de INTC foram reconciliados com os componentes Silver.
- **Manutenção**: atualizar esta lista após cada tarefa implementada ou validada, registrando o resultado efetivamente observado; não marcar execução de CI/BigQuery como concluída apenas por configurar o workflow ou passar no parse.
- **Round robin reforçado e simulado (T031–T038)**: seleção baseada no fim do intervalo Airflow no timezone `America/Sao_Paulo`, plano diário limitado a 25 chamadas, uma tentativa HTTP por chamada no lote completo, falha explícita para lote parcial e resumo auditável por endpoint. A simulação mockada confirmou 7 runs, 35 tickers únicos e 175 chamadas lógicas na semana. Validação: Ruff e formatação aprovados; pytest com **57 aprovados e 7 ignorados no Windows**; os **9 testes combinados de integridade do DAG e simulação semanal passaram no container Linux**.
- **Execução real controlada**: a primeira chamada (`INTC/OVERVIEW`) encontrou a cota Alpha Vantage já esgotada. O lote falhou sem retry, deixou quatro tickers pendentes e bloqueou extrações e dbt downstream. Após a run, somente o log de metadata de overview foi criado no GCS; não houve dados, quarentena nem alteração de watermark. Nenhum rerun será feito antes de uma nova janela de cota.
- **Runtime Airflow estabilizado**: telemetria Cosmos desativada e compatibilidade `anyio/httpcore` fixada; scheduler e webserver permanecem ativos com `restart_count=0`. O rebuild completo da imagem não foi repetido após o resolver de dependências exceder o limite operacional de cinco minutos; a configuração Compose foi validada.
- **Produção local preparada parcialmente**: segredos retirados do Compose e rotacionados, Airflow restrito a `127.0.0.1:8081`, PostgreSQL sem porta publicada, target dbt `prod` aprovado, três serviços saudáveis, backup validado e suíte Linux com 67 testes aprovados. Permanecem o build reproduzível (T056), a execução real após a renovação da cota (T059/T042) e o fechamento do release (T060).

---

## Phase 1: Setup (Infraestrutura Compartilhada)

**Purpose**: Configurações de projeto que habilitam todas as camadas downstream.

- [x] T001 Adicionar configurações de `intermediate` (view) e `marts` (table) em `src/transformations/dbt_project.yml`

**Checkpoint**: `dbt parse --project-dir src/transformations` deve passar sem erros.

---

## Phase 2: Fundacional (Pré-requisitos Bloqueantes)

**Purpose**: Estrutura de diretórios e verificação de dependências dbt que TODA fase downstream precisa.

⚠️ **CRÍTICO**: Nenhuma user story pode começar até esta fase estar completa.

- [x] T002 Criar o diretório `src/transformations/models/intermediate/` (pode ser criado com um `.gitkeep` ou diretamente com o primeiro arquivo SQL)
- [x] T003 Criar o diretório `src/transformations/models/marts/` (idem)
- [x] T004 Verificar que `dbt_utils` está disponível em `src/transformations/packages.yml` para o teste `unique_combination_of_columns` (adicionar se ausente)

**Checkpoint**: Estrutura de diretórios pronta; `dbt deps --project-dir src/transformations` passa.

---

## Phase 3: User Story 1 — Intermediate Income Statement (P1) 🎯 MVP

**Goal**: Modelo `int_income_statement` com flattening completo do JSON, tipagem, deduplicação e campo derivado `ebitda_calc`.

**Independent Test**: `dbt run --select int_income_statement` + `dbt test --select int_income_statement` passam; query no BigQuery retorna linhas com `symbol`, `fiscaldateending` e `ebitda_calc` populados.

- [x] T005 [US1] Criar `src/transformations/models/intermediate/int_income_statement.sql` com CTEs: `raw_parsed` (JSON_VALUE + NULLIF sentinels + SAFE_CAST), `unnested_reports` (UNNEST annualReports/quarterlyReports), `deduped` (ROW_NUMBER por ingest_date DESC), `filtered` (retenção do registro mais recente; datas inválidas preservadas como NULL conforme a constituição), campo derivado `ebitda_calc`
- [x] T006 [US1] Criar `src/transformations/models/intermediate/int_income_statement.yml` com description do modelo, `name`/`data_type`/`description` de todas as colunas, testes `not_null` (symbol, fiscaldateending), `accepted_values` (report_type), `dbt_utils.unique_combination_of_columns` (symbol, fiscaldateending, report_type)

**Checkpoint**: `dbt run --select int_income_statement` OK; `dbt test --select int_income_statement` OK.

---

## Phase 4: User Story 2 — Intermediate Balance Sheet (P1)

**Goal**: Modelo `int_balance_sheet` com todos os campos do balanço patrimonial, campos derivados `total_debt` e `net_debt`.

**Independent Test**: `dbt run --select int_balance_sheet` + `dbt test --select int_balance_sheet` passam; `net_debt` e `total_debt` calculados corretamente para ao menos um ticker.

- [x] T007 [US2] Criar `src/transformations/models/intermediate/int_balance_sheet.sql` com CTEs equivalentes ao int_income_statement, incluindo campos derivados `total_debt` (COALESCE) e `net_debt`
- [x] T008 [US2] Criar `src/transformations/models/intermediate/int_balance_sheet.yml` com catálogo completo de colunas, testes `not_null`, `accepted_values`, `unique_combination_of_columns`

**Checkpoint**: `dbt run --select int_balance_sheet` OK; `dbt test --select int_balance_sheet` OK.

---

## Phase 5: User Story 3 — Intermediate Cash Flow (P1)

**Goal**: Modelo `int_cash_flow` com fluxo de caixa tipado e campo derivado `free_cash_flow`.

**Independent Test**: `dbt run --select int_cash_flow` + `dbt test --select int_cash_flow` passam; `free_cash_flow` calculado (ou NULL quando componentes ausentes).

- [x] T009 [US3] Criar `src/transformations/models/intermediate/int_cash_flow.sql` com CTEs de parse e dedup (preservando datas inválidas como NULL) e campo derivado `free_cash_flow = operating_cashflow - capital_expenditures`
- [x] T010 [US3] Criar `src/transformations/models/intermediate/int_cash_flow.yml` com catálogo completo de colunas e testes

**Checkpoint**: `dbt run --select int_cash_flow` OK; `dbt test --select int_cash_flow` OK.

---

## Phase 6: User Story 4 — Intermediate Earning (P2)

**Goal**: Modelo `int_earning` com EPS e surpresa de resultados tipados, distinguindo registros anuais de trimestrais.

**Independent Test**: `dbt run --select int_earning` + `dbt test --select int_earning` passam; `reported_date` é NULL para registros anuais e populado para trimestrais.

- [x] T011 [US4] Criar `src/transformations/models/intermediate/int_earning.sql` com CTEs para `quarterlyEarnings` (report_type='quarterly', reported_date populado) e `annualEarnings` (report_type='annual', reported_date NULL), UNION ALL e dedup, preservando datas inválidas como NULL
- [x] T012 [US4] Criar `src/transformations/models/intermediate/int_earning.yml` com catálogo completo e testes

**Checkpoint**: `dbt run --select int_earning` OK; `dbt test --select int_earning` OK.

---

## Phase 7: User Story 5 — Intermediate Overview (P2)

**Goal**: Modelo `int_overview` com metadados e múltiplos de mercado, deduplicado para um snapshot por empresa.

**Independent Test**: `dbt run --select int_overview` + `dbt test --select int_overview` passam; grain é exatamente um registro por `symbol`.

- [x] T013 [US5] Criar `src/transformations/models/intermediate/int_overview.sql` com parse de todos os campos STRING, INT64 e NUMERIC do contrato, dedup `ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ingest_date DESC)`, retenção do snapshot mais recente via `QUALIFY ROW_NUMBER() = 1`
- [x] T014 [US5] Criar `src/transformations/models/intermediate/int_overview.yml` com catálogo completo, teste `not_null` (symbol), teste `unique` (symbol)

**Checkpoint**: `dbt run --select int_overview` OK; `dbt test --select int_overview` OK; um registro por ticker.

---

## Phase 8: User Story 6 — Mart fct_fundamental_kpis (P1) 🏆 Gold Layer

**Goal**: OBT `fct_fundamental_kpis` com todos os KPIs calculados, materializada como TABLE no BigQuery.

**Independent Test**: `dbt run --select fct_fundamental_kpis` OK; `dbt test --select fct_fundamental_kpis` OK; query de duplicatas retorna 0 linhas; KPIs de IBM conferem com cálculo manual.

- [x] T015 [US6] Criar `src/transformations/models/marts/fct_fundamental_kpis.sql` com:
  - CTEs que referenciam `int_income_statement`, `int_balance_sheet`, `int_cash_flow`, `int_earning`, `int_overview`
  - LEFT JOINs ancorados em `int_income_statement` por `(symbol, fiscaldateending, report_type)`; join com `int_overview` apenas por `symbol`
  - CTE `revenue_with_lag` para calcular `LAG(4)` quarterly e `LAG(1)` annual
  - SELECT final com dimensões, `overview_snapshot_date`, todos os KPIs via `SAFE_DIVIDE`
- [x] T016 [US6] Criar `src/transformations/models/marts/fct_fundamental_kpis.yml` com description do modelo, catálogo completo de colunas (incluindo fórmula de cada KPI na description), testes `not_null` (symbol, fiscaldateending, report_type), `dbt_utils.unique_combination_of_columns` (symbol, fiscaldateending, report_type)

**Implementação concluída**: mart com 29 colunas documentadas, sete testes unitários dbt e cinco testes de qualidade. CI ampliado para preparar o dataset, testar Silver e Gold e construir `+marts` no target `ci`. `dbt parse` aprovado no dbt 1.12.2; Ruff aprovado; pytest com 48 aprovados e 3 ignorados. **Sete testes unitários Gold aprovados no BigQuery**. A materialização e a reconciliação com dados reais ainda precisam ser confirmadas; o checkpoint abaixo é critério de aceite, não resultado já obtido.

**Checkpoint**: `dbt run --select fct_fundamental_kpis` OK; `dbt test --select fct_fundamental_kpis` OK; grain único confirmado por query.

---

## Phase 9: User Story 7 — Validação End-to-End & Documentação (P2)

**Goal**: Pipeline completo executado e documentado; `dbt docs` sem nós sem descrição.

**Independent Test**: todos os passos do `quickstart.md` passam; lineage completo no `dbt docs serve`.

- [x] T017 [US7] Executar `dbt run --select intermediate marts --project-dir src/transformations` e confirmar que todos os 6 modelos constroem sem erros
- [x] T018 [US7] Executar `dbt test --select intermediate marts --project-dir src/transformations` e confirmar que todos os testes passam
- [x] T019 [US7] Executar query de validação de grain da mart (ver `quickstart.md` seção 5) e confirmar 0 duplicatas
- [x] T020 [US7] Executar validação manual de KPIs para ao menos 1 ticker (ver `quickstart.md` seção 6): conferir `net_margin`, `roe` e `revenue_yoy_growth` contra fonte Alpha Vantage
- [x] T021 [P] [US7] Executar `dbt docs generate --project-dir src/transformations` e verificar que todos os modelos intermediate e mart aparecem no lineage sem nós sem descrição

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Ajustes finais e verificação de conformidade com a constituição.

- [x] T022 [P] Verificar que nenhum modelo intermediate ou mart contém lógica de parse que deveria estar em outra camada (Princípio I da constituição)
- [x] T023 [P] Verificar que todos os arquivos SQL têm comentário de grain no início (Princípio II da constituição)
- [x] T024 Atualizar `README.md` com a nova estrutura de camadas (seção System Architecture) e os comandos de execução atualizados

---

## Tarefas complementares identificadas durante a implementação

- [x] T025 Expor todos os campos de `src/extract/contract.py` nos cinco modelos Silver, incluindo os 66 campos inicialmente ausentes, com tipos, descrições e mapeamento da chave JSON nos YAMLs.
- [x] T026 Adicionar testes dbt com payloads completos dos contratos e verificação Python de cobertura em `tests/test_silver_contracts.py`.
- [x] T027 Atualizar `.github/workflows/ci_cd.yml` com verificação dos contratos, instalação de pacotes dbt, testes unitários Silver e build/testes de qualidade no target `ci` (`alphavantage_ci`); corrigir mocks GCS em `tests/conftest.py`. Execução remota do workflow ainda não confirmada.
- [x] T028 Executar validação local: `dbt parse`, Ruff e pytest (48 aprovados, 3 ignorados).
- [x] T029 Migrar `meta` das colunas para `config.meta` nos YAMLs e ajustar o teste de cobertura e a documentação para remover o aviso de depreciação observado no dbt 1.12.2.
- [x] T030 Atualizar `stg_overview` no BigQuery e reexecutar `int_overview` com seus ancestrais (`dbt run -s +int_overview --project-dir src/transformations`); confirmar resolução do erro `raw_data` e executar os testes do modelo.

---

## Phase 11: Ponto 1 — Hardening do Round Robin

**Goal**: garantir que a rotação semanal respeite o calendário operacional, a cota diária e interrompa o pipeline quando uma extração estiver incompleta.

- [x] T031 Corrigir a seleção diária para usar `data_interval_end` (com fallback para `logical_date`) no timezone `America/Sao_Paulo`; validar sete dias consecutivos, repetição no oitavo dia, rerun da mesma data e virada de timezone.
- [x] T032 Validar o plano antes da extração para impedir mais de 25 chamadas diárias e configurar uma única tentativa HTTP nas extrações agendadas, pois o lote de 5 tickers × 5 endpoints já consome toda a cota.
- [x] T033 Fazer lotes parciais, quarentena e erros de API falharem a task; interromper imediatamente os símbolos e endpoints seguintes quando houver rate limit; registrar `run_id`, lote planejado, concluídos, falhas, pendentes e total de chamadas planejadas.
- [x] T034 Ampliar os testes de round robin, cliente, extratores e DAG e adicionar uma etapa dedicada à validação da rotação no GitHub Actions. Resultado: Ruff e `ruff format --check` aprovados; pytest local com 55 testes aprovados e 7 ignorados por incompatibilidade Airflow/Windows; 7 testes de integridade do DAG aprovados no container Linux.

---

## Phase 12: Ponto 2 — Simulação semanal sem consumo da API

**Goal**: validar o comportamento operacional de uma semana completa usando API e GCS mockados, sem rede, credenciais ou consumo de cota.

- [x] T035 Criar um teste de simulação para sete DAG runs consecutivas e confirmar cinco tickers por run, 35 tickers únicos na semana, repetição correta no oitavo dia e exatamente 25 chamadas planejadas por run. Resultado: 175 chamadas lógicas mockadas, sem rede ou consumo de cota.
- [x] T036 Simular sucesso, falha parcial, quarentena e rate limit durante a semana; confirmar que os endpoints seguintes e a camada dbt ficam bloqueados quando o lote não é concluído.
- [x] T037 Validar os resumos de auditoria gerados na simulação: `run_id`, data, endpoint, tickers planejados, concluídos, falhos e pendentes, quantidade de chamadas e motivo da interrupção.
- [x] T038 Executar Ruff, formatação, pytest completo e testes do DAG no container Linux; atualizar este arquivo com os resultados observados. Resultado: Ruff e formatação aprovados, 57 testes locais aprovados e 7 ignorados no Windows, 9 testes aprovados no container Linux.

---

## Phase 13: Ponto 3 — Execução real controlada do Round Robin

**Goal**: comprovar uma execução real do lote diário na Alpha Vantage e no GCS sem exceder a cota gratuita.

- [x] T039 Fazer o preflight do ambiente: containers saudáveis, DAG carregada sem erros, credenciais disponíveis, lote/data esperados e cota diária ainda não utilizada. Resultado: infraestrutura e credenciais aprovadas, lote `INTC, AMD, NFLX, PFE, COST` confirmado; a indisponibilidade da cota só foi informada pela API na primeira chamada.
- [x] T040 Executar uma única DAG run controlada após T035–T038, sem retries nem execuções paralelas. Run `manual__round_robin_validation_2026-09-09` executada uma vez; `INTC/OVERVIEW` recebeu rate limit e encerrou o lote imediatamente.
- [x] T041 Conferir no GCS os cinco endpoints para os cinco tickers planejados, os arquivos de quarentena, os logs estruturados e os watermarks. Resultado: somente `financial/metadata/overview/year=2026/month=09/day=10/overview_extraction.log` foi alterado; nenhum dado, arquivo de quarentena ou watermark foi criado/alterado após a run.
- [ ] T042 Confirmar a idempotência do resultado no GCS/BigQuery e planejar o rerun para uma janela com cota disponível; bloqueada até uma nova janela diária porque a run não produziu payload válido. Não repetir chamadas em 2026-09-10.

---

## Phase 14: Ponto 4 — Validação final Silver e Gold com dados reais

**Goal**: concluir os checkpoints de modelagem no BigQuery e reconciliar a mart Gold com uma amostra conhecida.

- [x] T043 Concluir T030: `stg_overview` e `int_overview` recriados no BigQuery; build aprovado e cinco testes do modelo aprovados, resolvendo `Unrecognized name: raw_data`.
- [x] T044 Concluir T017–T018: build real aprovado com cinco views Silver, uma tabela Gold, 30 testes unitários e 27 testes de qualidade; total dbt `PASS=64`.
- [x] T045 Concluir T019: teste composto e consulta explícita confirmaram zero duplicatas no grain `(symbol, fiscaldateending, report_type)`.
- [x] T046 Concluir T020: INTC anual em 2007-12-31 reconciliado. `net_margin` 0.181979444, `roe` 0.163135494 e `revenue_yoy_growth` 0.083432254 conferem com os cálculos independentes a partir de receita, lucro, equity e receita anterior Silver.
- [x] T047 Confirmar que falhas bloqueiam a conclusão da DAG: a falha real de extração deixou toda a cadeia downstream como `upstream_failed`; o teste de integridade confirma que os leaves de testes Silver alimentam Gold e os leaves de testes Gold alimentam `finish_pipeline`.

---

## Phase 15: Ponto 5 — Documentação, manutenção e fechamento

**Goal**: remover pendências técnicas e deixar o projeto reproduzível e pronto para revisão final.

- [x] T048 Concluir T029: `source_field` migrado para `config.meta` nos cinco YAMLs; cobertura de contratos atualizada e aprovada (5 testes); `dbt parse` 1.12.2 aprovado sem o aviso de depreciação.
- [x] T049 Concluir T022–T023: responsabilidades das camadas, comentários de grain, deduplicação determinística, aritmética segura e observabilidade revisados conforme a constituição.
- [x] T050 Concluir T024: README atualizado com arquitetura Silver/Gold, tickers versionados em `config.py`, round robin serial, CI completa e release sem deployment automático.
- [x] T051 Concluir T021: `dbt docs generate --select intermediate marts` aprovado; lineage `ext_* → stg_* → int_* → fct_fundamental_kpis` confirmado; nenhum dos seis modelos ou suas colunas está sem descrição. A geração global continua exigindo a criação do dataset opcional `alphavantage_raw` usado pelos seeds.
- [x] T052 Validar novamente o workflow remoto do GitHub Actions. Resultado: lint, testes unitários e validação dbt aprovados no pull request com Airflow 2.9.3 e Cosmos 1.8.2. O job `release-validation` foi ignorado como esperado, pois só executa em `push` para `main`; nenhum deployment foi executado.
- [x] T053 Corrigir a resolução de dependências do CI para reproduzir o runtime Docker: fixar Airflow 2.9.3 e Cosmos 1.8.2, adicionar smoke test de importação e executar o workflow em PRs para `dev`. Resultado local: versões confirmadas, workflow YAML válido, Ruff/formatação aprovados e 64 testes aprovados no container Linux.

---

## Phase 16: Preparação para produção local com Docker

**Goal**: operar o pipeline de forma segura, reproduzível e observável em um host local antes do release na `main`.

- [x] T054 Externalizar segredos e configurações sensíveis do `docker-compose.yml`, rotacionar as credenciais expostas, padronizar o caminho da credencial GCP e limitar as portas do Airflow/PostgreSQL ao acesso necessário no host local. Resultado: senhas PostgreSQL/web e Fernet key movidas para `.env`; senha persistida e Fernet recriptografadas; credencial padronizada em `/opt/airflow/gcp_key.json` somente leitura; Airflow em `127.0.0.1:8081` devido ao Apache local na 8080; PostgreSQL sem porta publicada.
- [x] T055 Separar os targets dbt de desenvolvimento e produção e configurar a DAG para usar explicitamente o target de produção, evitando gravações acidentais durante o desenvolvimento. Resultado: `dev=alphavantage_dev`, `prod=alphavantage`, `ci=alphavantage_ci`; DAG carregou `dbt_target=prod` e `dbt parse --target prod --no-partial-parse` foi aprovado.
- [ ] T056 Tornar a imagem Docker reproduzível com dependências compatíveis e travadas, executar um build limpo do zero e validar importação da DAG, Ruff, pytest e dbt no container resultante. Pendente: dois builds limpos identificaram incompatibilidades entre os constraints do Airflow 2.9.3 e dbt 1.10 (`protobuf` e `google-cloud-aiplatform`); a tentativa seguinte foi interrompida. Não repetir o build nesta etapa; as demais tarefas não dependem dele.
- [x] T057 Adicionar healthchecks, política de reinício, persistência e procedimentos de backup/restauração do PostgreSQL, além de retenção e rotação dos logs locais. Resultado: PostgreSQL, webserver e scheduler saudáveis; restart permanente; volume preservado; logs Docker limitados; limpeza local de 30 dias preparada; backup real aprovado por SHA-256 e catálogo `pg_restore` com 301 objetos.
- [x] T058 Configurar observabilidade e alertas de falha/rate limit e preparar o host para operação contínua: Docker na inicialização, energia sem suspensão, rede disponível e verificação do agendamento às 06:00 em `America/Sao_Paulo`. Resultado: callback estruturado e webhook opcional cobertos por testes; Docker Desktop registrado na inicialização; plano Alto desempenho sem suspensão em AC/bateria; schedule/timezone e healthcheck local confirmados; suíte Linux com 67 testes aprovados.
- [ ] T059 Concluir T042 em uma janela com cota: executar um lote real controlado, confirmar idempotência no GCS/BigQuery e acompanhar ao menos um ciclo completo de sete dias do round robin.
- [ ] T060 Documentar e validar o procedimento local de release e rollback (`git pull`, build, subida, healthcheck, migração e retorno à versão anterior) antes do merge final `dev → main`. Progresso: runbook, backup/restore, inicialização, healthcheck e rollback documentados; `start_local_stack.ps1` aprovado. O fechamento depende do build limpo da T056 e do merge final.

---

## Dependencies & Execution Order

### Dependências entre Fases

- **Phase 1 (Setup)**: Sem dependências — pode começar imediatamente
- **Phase 2 (Fundacional)**: Depende de Phase 1 — **bloqueia todas as user stories**
- **Phases 3–7 (Intermediates)**: Dependem de Phase 2 — podem rodar em **paralelo entre si**
- **Phase 8 (Mart)**: Depende de **todas** as Phases 3–7 estarem completas
- **Phase 9 (Validação)**: Depende de Phase 8
- **Phase 10 (Polish)**: Depende de Phase 9
- **Phase 11 (Ponto 1 — Hardening)**: Concluída no código e nos testes locais/Linux
- **Phase 12 (Ponto 2 — Simulação)**: Concluída após Phase 11, sem consumo da API
- **Phase 13 (Ponto 3 — Execução real)**: Execução única realizada; T042 aguarda nova janela de cota e um payload válido
- **Phase 14 (Ponto 4 — Validação dbt real)**: Concluída com os dados Bronze já disponíveis no BigQuery/GCS
- **Phase 15 (Ponto 5 — Fechamento)**: Concluída; workflow remoto aprovado e release sem deployment confirmado
- **Phase 16 (Produção local)**: T054, T055, T057 e T058 concluídas; T056 aguarda a resolução reproduzível de dependências, T059 aguarda nova janela de cota e T060 depende desses gates antes do release na `main`

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
