# Plano do Projeto: Fundamental Data Analysis

> Prévia de instruções e plano de execução para conduzir o projeto desde a extração até a primeira camada `mart`.
>
> Este arquivo é um rascunho de trabalho. Para instruções carregadas automaticamente pelo GitHub Copilot, avaliar a migração do conteúdo estável para `.github/copilot-instructions.md` ou `AGENTS.md` na raiz.

## 1. Objetivo

Construir um pipeline confiável de análise fundamentalista que:

- Extraia os cinco endpoints da Alpha Vantage: `OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW` e `EARNINGS`.
- Preserve os payloads brutos no GCS como camada Bronze, com particionamento por data de ingestão.
- Valide formato e conteúdo na entrada sem esconder respostas inválidas ou incompletas.
- Normalize os JSONs em modelos dbt de staging na camada Silver.
- Concilie o grain dos demonstrativos financeiros antes de fazer joins.
- Entregue uma camada Gold/Mart com KPIs documentados, testados e prontos para consumo analítico.

A implementação deve preservar a separação entre extração Python, carga, transformação dbt e consumo analítico.

## 2. Estado atual confirmado

- O dbt project está em `transformations/` e é reconhecido quando executado com `dbt --project-dir transformations`.
- `transformations/dbt_project.yml` usa caminhos relativos para `models`, `seeds` e `macros`; mover o projeto inteiro para `src/transformations/` é tecnicamente viável, desde que o novo `project-dir` seja usado em todos os pontos de execução.
- Existem cinco modelos SQL de staging e seus YAMLs em `transformations/models/staging/`.
- A pasta `transformations/models/marts/` está vazia; a camada Mart ainda precisa ser desenhada e implementada.
- Os testes Python em `tests/` ainda não estão implementados.
- A extração possui cinco módulos muito semelhantes, um cliente HTTP, contratos Pydantic e um loader GCS.
- O README descreve Airflow, Docker e CI/CD, mas esses componentes não estão presentes no estado de arquivos verificado; antes de depender deles, localizar ou criar suas implementações.
- O parse atual do dbt passa com um aviso de compatibilidade entre `dbt_external_tables` e a versão preview do dbt Fusion.

## 3. Princípios de trabalho do agente

- Ler configuração, contrato, consumidor e teste próximo antes de editar.
- Declarar o grain, chave, tipos, unidades, moeda, período fiscal e política de nulos antes de criar qualquer modelo.
- Corrigir a camada que possui a responsabilidade: contrato para formato de origem, staging para normalização, intermediate para regras reutilizáveis e mart para métricas de negócio.
- Preservar payloads brutos e evitar perda silenciosa de registros.
- Preferir mudanças pequenas, idempotentes, observáveis e compatíveis com as interfaces existentes.
- Não expor API keys, credenciais, payloads sensíveis ou dados de autenticação em logs, fixtures ou documentação.
- Usar SQL explícito, chaves estáveis, joins por período bem definido e tratamento explícito de denominadores nulos ou zero.
- Validar primeiro com o comando mais estreito e só depois executar verificações mais amplas.

## 4. Plano de execução

### Fase 0: Baseline e decisões

1. Registrar o comando oficial de execução dbt, o profile usado e o dataset de destino.
2. Confirmar o layout real do repositório e decidir se o projeto dbt será movido para `src/transformations/`.
3. Definir a convenção final do arquivo de instruções: manter este rascunho ou publicar instruções estáveis em `.github/copilot-instructions.md`.
4. Documentar o contrato de execução local, incluindo variáveis de ambiente, credenciais GCP, dependências e comandos.
5. Criar uma matriz endpoint -> contrato -> caminho GCS -> source dbt -> staging model.

**Saída:** baseline reproduzível e decisão registrada sobre o novo caminho do dbt.

### Fase 1: Correções prioritárias da extração

1. Corrigir a nomenclatura dos contratos Pydantic: separar claramente schemas de linha, envelopes e relatórios anual/trimestral.
2. Confirmar o payload real de cada endpoint com fixtures locais e testes de validação.
3. Tornar os campos obrigatórios e opcionais coerentes com a origem; validar `symbol`, datas, moeda, listas de relatórios e campos numéricos.
4. Definir uma política para strings como `None`, `-`, vazio e `N/A`, sem transformar erro estrutural em dado válido silenciosamente.
5. Adicionar timeout configurável ao cliente HTTP, retry com backoff limitado para falhas transitórias e tratamento específico para HTTP 429, erros HTTP e mensagens de limite da Alpha Vantage.
6. Validar a chave de API e configurações obrigatórias antes de iniciar chamadas.
7. Extrair a lógica repetida dos cinco módulos para um fluxo comum parametrizado por endpoint, contrato, nome do arquivo e prefixo GCS.
8. Usar `pathlib`, encoding explícito e escrita atômica de arquivos temporários.
9. Tornar a operação idempotente: definir comportamento para rerun do mesmo ticker e dia, duplicidade de blob e restatement de demonstrações.
10. Garantir que o arquivo local só seja removido após upload confirmado; corrigir o fluxo de log quando o upload falhar ou quando o arquivo de log não existir.
11. Substituir `print` por logging estruturado consistente e incluir run id, endpoint, ticker, status, duração, quantidade, tamanho e motivo da rejeição.
12. Separar registros rejeitados de falhas de transporte e produzir uma saída observável para quarentena ou dead-letter.
13. Remover imports não utilizados e alinhar o uso da constante `TIMEOUT`, que hoje não é aplicada pelo cliente.

**Saída:** extrator reutilizável, testável, idempotente e capaz de distinguir dado inválido, falha transitória e limite de API.

### Fase 2: Testes da extração e da carga

Adicionar testes unitários sem chamadas reais à Alpha Vantage ou ao GCP para:

- Respostas válidas dos cinco endpoints.
- Resposta vazia, resposta com mensagem de erro e resposta parcial.
- Campos opcionais ausentes e valores sentinela.
- Datas e valores numéricos inválidos.
- Status 429, 5xx, timeout e erro de JSON.
- Retry limitado e não-retry para erros permanentes.
- Nome e prefixo de cada arquivo/blob.
- Exclusão local apenas depois de upload bem-sucedido.
- Contagem de linhas e registros rejeitados.
- Ausência de segredos nos logs.
- Reexecução no mesmo dia sem duplicação não intencional.

**Saída:** suíte mínima de regressão em `tests/`, com mocks para HTTP, Pydantic e GCS.

### Fase 3: Decisão e migração do diretório dbt

A migração recomendada é mover o projeto completo para `src/transformations/`, mantendo internamente a mesma estrutura:

```text
src/transformations/
├── dbt_project.yml
├── packages.yml
├── package-lock.yml
├── macros/
├── models/
├── seeds/
└── target/              # gerado, preferencialmente fora do versionamento
```

Checklist da migração:

1. Atualizar todos os comandos para usar `--project-dir src/transformations` ou executar com esse diretório como `cwd`.
2. Atualizar profile/integração do dbt no VS Code, se houver configuração específica.
3. Atualizar Docker, Airflow, CI/CD e scripts quando forem adicionados ou localizados.
4. Atualizar README e referências a `transformations/models/source.yml`.
5. Não alterar nomes de modelos, schemas BigQuery, sources ou relações sem decisão explícita.
6. Limpar e recriar `target/` e `dbt_packages/` no novo local, em vez de transportar artefatos gerados sem necessidade.
7. Executar `dbt parse`, `dbt deps`, `dbt compile` e, com credenciais disponíveis, `dbt run` e `dbt test` no novo caminho.

**Risco principal:** não é o dbt interno, pois seus paths são relativos ao `dbt_project.yml`; o risco está nos chamadores externos e em comandos que hoje assumem `transformations/` na raiz.

### Fase 4: Fortalecimento da camada staging

1. Documentar o grain de cada staging:
   - `stg_overview`: um snapshot por ticker e data de ingestão.
   - Demonstrativos: um registro por ticker, `report_type` e `fiscaldateending`, preservando a data de ingestão.
2. Definir se restatements geram versões por data de ingestão ou se a camada Silver mantém apenas a versão mais recente.
3. Adicionar testes dbt para `not_null`, `accepted_values`, unicidade composta, validade de datas e consistência de partições.
4. Confirmar que os cinco SQLs e YAMLs têm exatamente as mesmas colunas e tipos esperados.
5. Padronizar casts BigQuery e tratamento de `None`, `-`, `N/A` e strings vazias.
6. Criar modelos intermediate quando a regra de deduplicação, seleção da versão mais recente ou alinhamento de períodos for reutilizada.
7. Revisar a configuração de external tables, particionamento, custo de leitura e compatibilidade da versão de `dbt_external_tables`.

**Saída:** Silver com grain explícito, contratos documentados e qualidade verificável.

### Fase 5: Desenho e implementação da camada Mart

Antes de escrever SQL, registrar a especificação do modelo OBT:

- Chave natural ou técnica.
- Grain final: recomendação inicial de um registro por ticker, período fiscal e `report_type`, com data de ingestão/versionamento definido.
- Política para alinhar fluxo de período com snapshot de balanço.
- Moeda, escala, sinais contábeis e tratamento de valores ausentes.
- Fonte de cada coluna e regra de precedência em caso de duplicidade.

Implementar em ordem:

1. Criar o modelo base da mart com joins explícitos entre income statement, balance sheet, cash flow, earnings e overview.
2. Resolver duplicidades por ticker/período antes dos joins.
3. Calcular:
   - margem líquida;
   - margem EBITDA;
   - ROE;
   - current ratio;
   - net debt/EBITDA;
   - free cash flow;
   - quality of earnings;
   - crescimento de receita via `LAG()`;
   - earnings surprise percentage;
   - P/E e EV/EBITDA quando a granularidade do overview permitir.
4. Proteger todas as divisões contra denominador zero ou nulo e expor o resultado como nulo/status quando não for calculável.
5. Diferenciar métricas TTM, anuais e trimestrais; não misturar snapshot atual de `OVERVIEW` com histórico sem documentar a limitação.
6. Adicionar YAML de modelo e colunas, testes de chave, integridade, valores e regras de negócio.
7. Comparar amostras da mart contra cálculos manuais e fontes de staging.

**Saída:** primeira mart documentada, reproduzível e adequada para análise, com limitações temporais explícitas.

### Fase 6: Operação, documentação e entrega

1. Executar `dbt docs generate` e revisar lineage e descrições.
2. Criar um comando único para validação local da extração e do dbt.
3. Integrar pytest, parse/compile e dbt test no CI quando a automação existir.
4. Definir alertas para falha de endpoint, quota, queda de volume, ausência de ticker e atraso de atualização.
5. Documentar backfill, rerun, restatement e recuperação de falhas.
6. Atualizar README com a estrutura final, comandos e limitações conhecidas.
7. Fazer uma revisão final de segurança, custo, qualidade, idempotência e compatibilidade.

## 5. Backlog priorizado

### P0: bloqueia confiança no pipeline

- Corrigir contratos Pydantic e testar payloads reais.
- Implementar timeout, retry e tratamento de quota.
- Criar testes unitários dos extratores e loader.
- Definir grain/versionamento dos demonstrativos.
- Garantir que falha de upload não seja registrada como sucesso.

### P1: necessário antes da mart

- Consolidar código duplicado de extração.
- Implementar logging estruturado e quarentena.
- Adicionar testes dbt de grain, chaves e campos críticos.
- Decidir e executar a migração para `src/transformations/`, atualizando todos os chamadores.
- Corrigir documentação divergente entre README e estrutura real.

### P2: entrega da primeira mart

- Criar intermediate de deduplicação/alinhamento.
- Implementar OBT e KPIs.
- Documentar métricas, unidades, períodos e limitações.
- Adicionar testes de negócio e reconciliação.

### P3: operação contínua

- Airflow e rotação de tickers observáveis.
- CI/CD completo.
- Freshness, volume checks e alertas.
- Otimização de partição, clustering e custo BigQuery.

## 6. Critérios de aceite

O trabalho estará pronto para a primeira mart quando:

- Um endpoint inválido não produzir um arquivo Bronze tratado como sucesso.
- Uma falha transitória for retentada com limite e uma resposta de quota for identificada claramente.
- O rerun de uma mesma execução tiver comportamento documentado e não gerar duplicidade acidental.
- Todos os extratores tiverem testes automatizados sem depender de rede ou credenciais reais.
- O projeto dbt passar por parse e compile no caminho final, e seus comandos estiverem documentados.
- Cada staging tiver grain, chaves, tipos e testes definidos.
- Joins da mart não multiplicarem linhas silenciosamente.
- KPIs tiverem fórmula, unidade, período e tratamento de nulos/zero documentados.
- `dbt test` passar para os modelos envolvidos, salvo exceções registradas.
- Nenhum segredo aparecer em código, logs, fixtures ou documentação.

## 7. Comandos de validação previstos

Ajustar os caminhos conforme a decisão de migração:

```powershell
pytest

dbt parse --project-dir transformations
dbt deps --project-dir transformations
dbt compile --project-dir transformations
dbt test --project-dir transformations
dbt docs generate --project-dir transformations
```

Depois da migração:

```powershell
dbt parse --project-dir src/transformations
dbt deps --project-dir src/transformations
dbt compile --project-dir src/transformations
dbt test --project-dir src/transformations
```

`dbt run` e operações que criam external tables devem ser executados somente com credenciais, perfil e permissões GCP configurados.
