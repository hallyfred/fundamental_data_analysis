# Code Review — Camada de Ingestão de Dados
> Projeto: `fundamental_data_analysis` · Data: 2026-09-02

---

## Resumo Executivo

A camada de ingestão tem uma base sólida: contratos Pydantic bem definidos, log estruturado em JSON, particionamento por data no GCS e tratamento de erros por símbolo. Porém, há **falhas críticas de processo** que podem causar perda de dado silenciosa, vazamentos de arquivo local, loops infinitos e inconsistência entre o que o DAG orquestra e o que o código realmente executa.

---

## 🔴 Críticos — Podem causar falha silenciosa ou perda de dado

### 1. `upload_failure` não lança exceção — arquivo local jamais é limpo

**Arquivo:** [`loader.py`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/load/loader.py) · [`overview.py L72-78`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/overview.py#L72-L78)

```python
# loader.py — retorna False em vez de propagar a exceção
except Exception as e:
    print(f"Error occurred while uploading...")
    return False

# overview.py — só remove o arquivo SE upload deu True
if files_to_upload:
    os.remove(file_name)

# MAS files_generated.append é chamado ANTES de verificar o resultado:
files_generated.append(destination_blob_name)  # L78 — appended mesmo com upload False!
```

**Consequências:**
- O blob é adicionado em `files_generated` mesmo que o upload tenha **falhado**.
- O arquivo local JSON permanece no disco indefinidamente se o upload falhar (acumulando entre execuções).
- O DAG acredita que o Bronze foi carregado e executa o dbt em cima de dados ausentes.

---

### 2. `upload_and_clean_log` tem variável potencialmente não inicializada

**Arquivo:** [`logger.py L42-47`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/utils/logger.py#L42-L47)

```python
def upload_and_clean_log(gcp_loader, local_log_file, destination_log_path):
    if os.path.exists(local_log_file):
        log_uploaded = gcp_loader.upload_file(...)  # só atribuído aqui

    if log_uploaded:  # NameError se o arquivo não existia!
        os.remove(local_log_file)
    print(f"Log successfully uploaded...")  # imprime mesmo com falha
```

Se o arquivo `extraction.log` não existir (ex: primeira execução com erro antes de qualquer log), a execução lança `NameError: name 'log_uploaded' is not defined`.

---

### 3. Arquivo local escrito no diretório de trabalho corrente (CWD)

**Todos os extractors** — ex: [`overview.py L58`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/overview.py#L58)

```python
with open(file_name, "w") as f:  # grava em CWD, não em /tmp ou path configurável
    json.dump(files, f)
```

Dentro do Airflow, o CWD pode ser `/opt/airflow` ou outro path imprevisível. O arquivo pode colidir com execuções paralelas de outros DAGs. Não há uso de `tempfile` ou path explícito.

---

### 4. `extra='forbid'` no contrato quebra o pipeline se a API adicionar campo novo

**Arquivo:** [`contract.py L13`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/contract.py#L13)

```python
STRICT_MODEL_CONFIG = ConfigDict(extra='forbid', ...)
```

Qualquer novo campo retornado pela Alpha Vantage causa `ValidationError` e **pula o símbolo inteiro** (`continue`). Isso é silencioso do ponto de vista do pipeline: o dado simplesmente não vai para o Bronze naquele dia. Para uma camada de ingestão, `extra='ignore'` ou `extra='allow'` com log de aviso seria mais resiliente, separando a responsabilidade de validação de negócio.

---

## 🟠 Altos — Duplicação, acoplamento e fragilidade

### 5. Código 100% duplicado entre os 5 extractors

**Arquivos:** `overview.py`, `balance_sheet.py`, `cash_flow.py`, `income_statement.py`, `earning.py`

O corpo das funções `extract_*()` é **praticamente idêntico** — ±95% de código copiado. Cada mudança (ex: adicionar retry, mudar partição, ajustar log) precisa ser replicada em 5 arquivos. Isso já gerou diferenças: `overview.py` e `balance_sheet.py` têm `from importlib_metadata import files` (importação desnecessária e que sobrescreve a variável `files` no escopo global do módulo!).

```python
# Presente em overview.py e balance_sheet.py — importação fantasma
from importlib_metadata import files  # L5 — nunca usado, mas polui o namespace
```

**Solução:** uma função genérica `extract_endpoint(endpoint_key, schema_class, entity_name)`.

---

### 6. `SYMBOLS` no `config.py` itera TODOS os 35 símbolos — ignora o round-robin

**Arquivo:** [`config.py L44`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/config/config.py#L44) · [`overview.py L26`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/overview.py#L26)

```python
# config.py
SYMBOLS = [symbol for group in WEEKDAY_SYMBOLS.values() for symbol in group]  # todos os 35

# overview.py
for symbol in SYMBOLS:  # itera todos os 35 por execução!
```

A lógica de round-robin está implementada (`WEEKDAY_SYMBOLS`, `get_symbols_for_day`), mas os extractors **ignoram-na completamente** e iteram todos os 35 símbolos × 5 endpoints = **175 requisições/dia**, quando o plano é 25. A cota da API free-tier seria estourada imediatamente.

O DAG faz `select_batch` via XCom, mas os `extract_*` tasks são `EmptyOperator` — eles não usam o batch selecionado de forma alguma.

---

### 7. Sem `timeout` nas chamadas HTTP

**Arquivo:** [`api_client.py L15`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/api_client.py#L15)

```python
response = requests.get(self.base_url, params=params)  # sem timeout!
```

Uma API lenta pode travar o processo indefinidamente. O `TIMEOUT = 30` está definido em `config.py` mas **nunca é passado** para o `requests.get`.

---

### 8. Sem retry/backoff na chamada à API

**Arquivo:** [`api_client.py`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/api_client.py)

Erros transitórios (HTTP 429, 503, timeout de rede) fazem o símbolo ser descartado sem nenhuma tentativa de reprocessamento. A Alpha Vantage impõe rate-limit e é comum receber `429 Too Many Requests`, especialmente com múltiplos símbolos sequenciais.

---

### 9. API key `None` não é detectada na inicialização

**Arquivo:** [`config.py L25`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/config/config.py#L25)

```python
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")  # retorna None se não setada
```

Se a variável de ambiente não estiver configurada, `ALPHA_VANTAGE_API_KEY` é `None` e a requisição é feita com `apikey=None`. A API retorna uma resposta de erro que passa pelo `status_code == 200` (pois a Alpha Vantage retorna 200 com corpo de erro), entra na validação Pydantic e falha ali — sem mensagem clara de "API key ausente".

---

### 10. Resposta de erro da Alpha Vantage não é verificada antes da validação

**Arquivo:** [`overview.py L45`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/extract/overview.py#L45)

A Alpha Vantage retorna HTTP 200 com corpo de erro em casos como limite de chamadas excedido ou símbolo inválido:
```json
{"Note": "Thank you for using Alpha Vantage! ..."}
{"Information": "The **demo** API key is for demo purposes only..."}
{"Error Message": "Invalid API call..."}
```

O código faz `if not files` (checa se o dict está vazio), mas esses dicts de erro **não são vazios**. Eles passam reto para `OverviewSchema.model_validate(files)` e geram `ValidationError` em vez de um erro semântico claro.

---

## 🟡 Médios — Qualidade e manutenibilidade

### 11. DAG usa `EmptyOperator` para todos os tasks de extração e carga

**Arquivo:** [`financial_pipeline_dag.py L36-41`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/dags/financial_pipeline_dag.py#L36-L41)

```python
extract_overview = EmptyOperator(task_id="extract_overview")  # não executa nada
load_bronze = EmptyOperator(task_id="load_bronze")  # não executa nada
```

O DAG está estruturalmente correto mas **funcionalmente vazio** — nenhuma extração real ocorre quando ele roda. Os `PythonOperator` precisam ser conectados às funções `extract_*` e o batch do XCom precisa ser passado para eles.

---

### 12. `setup_logger` usa logger nomeado global — risco de poluição entre execuções

**Arquivo:** [`logger.py L9`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/utils/logger.py#L9)

```python
logger = logging.getLogger("extraction_logger")  # singleton global
```

Dentro do Airflow (onde tarefas podem rodar em workers compartilhados), o logger `'extraction_logger'` é um singleton global do Python. Se dois tasks rodarem no mesmo processo, eles compartilham o mesmo handler e escrevem no mesmo `extraction.log`. Isso corrompe os logs de forma silenciosa.

---

### 13. `orchestration/config.py` e `orchestration/round_robin.py` são idênticos

**Arquivos:** [`orchestration/config.py`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/orchestration/config.py) · [`orchestration/round_robin.py`](file:///c:/Users/hally/OneDrive/Área%20de%20Trabalho/fundamental_data_analysis/src/orchestration/round_robin.py)

Ambos os arquivos têm conteúdo idêntico. Além disso, importam `enumerate_ticker_batches` e `get_batch_for_day` que existem em `config.py`, mas o `__init__.py` exporta `enumerate_batches` e `resolve_batch_for_day` (nomes que não existem). Isso indica que o módulo de orquestração está **quebrado e inconsistente**.

---

### 14. Mistura de `print()` e `logger.info()` — observabilidade fragmentada

**Todos os extractors**

O código usa `print()` para mensagens operacionais e `logger.info()` apenas para os registros estruturados finais. Em produção com Airflow, `print()` vai para o stdout do worker (difícil de agregar) enquanto os logs estruturados vão para o arquivo. Seria melhor centralizar tudo no logger.

---

## 📋 Resumo das Prioridades

| # | Severidade | Arquivo(s) | Problema |
|---|-----------|-----------|----------|
| 1 | 🔴 Crítico | `loader.py`, todos extractors | Upload failure silencioso + `files_generated` incorreto |
| 2 | 🔴 Crítico | `logger.py` | `NameError` em `upload_and_clean_log` |
| 3 | 🔴 Crítico | todos extractors | Arquivo local em CWD sem path controlado |
| 4 | 🔴 Crítico | `contract.py` | `extra='forbid'` quebra pipeline por campo novo na API |
| 5 | 🟠 Alto | todos extractors | 100% de código duplicado |
| 6 | 🟠 Alto | `config.py`, todos extractors | Round-robin ignorado — 175 req/dia vs. cota de 25 |
| 7 | 🟠 Alto | `api_client.py` | Sem timeout HTTP |
| 8 | 🟠 Alto | `api_client.py` | Sem retry/backoff |
| 9 | 🟠 Alto | `config.py` | API key `None` não detectada na inicialização |
| 10 | 🟠 Alto | todos extractors | Erros semânticos da Alpha Vantage passam como `ValidationError` |
| 11 | 🟡 Médio | `financial_pipeline_dag.py` | DAG sem implementação real (EmptyOperators) |
| 12 | 🟡 Médio | `logger.py` | Logger singleton — risco de colisão em Airflow |
| 13 | 🟡 Médio | `orchestration/` | Módulo duplicado e com imports inconsistentes |
| 14 | 🟡 Médio | todos extractors | `print()` misturado com logger estruturado |
