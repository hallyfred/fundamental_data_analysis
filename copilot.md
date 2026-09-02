# Copilot.md — Guia rápido do projeto

Este documento é um rascunho para orientar desenvolvedores e operadores sobre como executar, desenvolver e manter o pipeline "Pipeline Financial Fundamental Analysis".

Resumo do projeto
- Objetivo: extrair dados fundamentais (Overview, Income Statement, Balance Sheet, Cash Flow, Earnings) da API Alpha Vantage, validar com Pydantic, armazenar JSONs brutos em Google Cloud Storage (camada bronze) e transformar/modelar com dbt (camada silver/gold) para calcular métricas financeiras.
- Principais componentes: src/extract (extratores), src/load (upload para GCS), src/utils (helpers e logger), config/config.py (variáveis do projeto) e transformations/ (projeto dbt).

Rápido início (Quickstart)
1. Pré-requisitos
   - Python 3.10+ (recomendado)
   - gcloud CLI (para autenticar com GCP) ou variável de ambiente GOOGLE_APPLICATION_CREDENTIALS apontando para a chave de serviço
   - Conta Alpha Vantage e chave de API

2. Instalar dependências
   Na raiz do repositório:
   - Recomendado (ambiente virtual):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1    # PowerShell
     # ou .\.venv\Scripts\activate   # cmd.exe

   - Instalar dependências:
     pip install -r requirements.txt

3. Criar arquivo .env (exemplo)
   Colocar na raiz do repositório um arquivo chamado .env com as variáveis necessárias:

   ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_API_KEY
   GCP_PROJECT_ID=your-gcp-project
   BUCKET_BRONZE=your-gcs-bucket-name

   Observações GCP:
   - Autenticar com Google Cloud: gcloud auth application-default login
   - Ou exportar GOOGLE_APPLICATION_CREDENTIALS (caminho para json da chave de serviço):
     setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\service-account.json"

Executando os extratores
- Cada extractor tem um script standalone em src/extract e pode ser executado como módulo.
- Exemplo (PowerShell / Windows):
  $Env:ALPHA_VANTAGE_API_KEY = 'SUA_CHAVE'
  python -m src.extract.overview

- Comandos para cada endpoint (executar da raiz do repositório):
  python -m src.extract.overview
  python -m src.extract.balance_sheet
  python -m src.extract.income_statement
  python -m src.extract.cash_flow
  python -m src.extract.earning

- Nota sobre PYTHONPATH: os módulos usam import src..., então executar com python -m a partir da raiz do repositório costuma funcionar. Se necessário, exportar PYTHONPATH=. antes de executar.

Configurações importantes
- config/config.py
  - SYMBOLS: lista de tickers que serão processados (por padrão contém ["AAPL"]). Editar essa lista para testar mais tickers localmente, ou integrar com Airflow para rotações.
  - ALPHA_VANTAGE_API_KEY, PROJECT_ID, BUCKET_BRONZE: lidos do .env
  - ENDPOINTS_API: mapeamento dos endpoints usados.

- transformations/ (dbt)
  - Models de `staging` (stg_overview) esperam que os JSONs brutos estejam registrados em uma fonte chamada `camada_bronze.ext_overview` — revisar configuração de fontes e profiles do dbt.
  - Comandos comuns:
    cd transformations
    dbt debug
    dbt deps
    dbt run
    dbt test
    dbt docs generate && dbt docs serve

Observabilidade: logs e upload
- Os extratores usam um logger que escreve em extraction.log e, ao final do processo, o arquivo é enviado para GCS e removido localmente.
- Padrões de caminhos GCS (ver código src/extract/*.py):
  financial/{endpoint}/year={YYYY}/month={MM}/day={DD}/{file_name}
  e logs para: financial/metadata/{endpoint}/year=.../.../.../..._extraction.log

Rate limits e orquestração
- Alpha Vantage (free tier) tem limite baixo (ex.: ~25 requisições/dia). O repositório adota uma estratégia de Round-Robin via Airflow (descrita no README) para evitar ultrapassar limites: dividir tickers em batches diários.

Inferências técnicas e pontos a observar
- Pydantic v2: o projeto usa model_validate / model_dump (Pydantic v2 API). Garantir pydantic>=2.0 no requirements.
- upload para GCP: usa google-cloud-storage. Necessário autenticação adequada (Application Default Credentials ou credenciais via variável de ambiente).
- O client HTTP é requests simples. O código atual não implementa backoff nem retries robustos — considerar adicionar retry com backoff exponencial (requests + tenacity) se for executar em produção.
- count_real_rows: utilitário para calcular linhas reais dentro dos JSONs (funciona para estruturas planas e aninhadas).

Como adicionar um novo ticker ou alterar o pool
- Localmente: editar config/config.py -> SYMBOLS
- Em produção com Airflow: atualizar a variável no Airflow (conforme README) para alterar batches e rotação

Como adicionar um novo extractor/endpoint
1. Adicionar o schema Pydantic em src/extract/contract.py (seguir padrões AlphaInt/AlphaFloat).
2. Criar arquivo src/extract/<endpoint>.py copiando um dos existentes (overview.py) e ajustar ENDPOINTS_API e schema.
3. Testar localmente com uma chamada única e revisar logs.

Sugestões de melhoria (prioridade)
- (Alta) Implementar retries com backoff e tratamento de rate-limit (HTTP 429) ao chamar a API.
- (Alta) Externalizar SYMBOLS e rotação para configuração (já há suporte em README/Airflow; garantir integração local para testes).
- (Média) Adicionar testes unitários para os validadores Pydantic e para count_real_rows.
- (Média) Validar e documentar profiles do dbt (profiles.yml) para facilitar execução local do dbt.

Onde documentar mudanças e padrões
- Este arquivo copilot.md (na raiz) deve conter:
  - Comandos essenciais (instalação, execução local, dbt)
  - Template .env e notas de autenticação
  - Padrões de logging e paths de dados
  - Guia rápido para desenvolvedores estarem prontos para contribuir

Próximos passos sugeridos
- Confirmar se deseja que eu:
  1) Gere um README mais detalhado para execução local (com exemplos passo-a-passo e debug)
  2) Adicione um script wrapper (ex: scripts/run_extract_all.py) que chame os extratores em sequência com delays para respeitar rate limit
  3) Implementar retries/backoff no cliente HTTP

--
Este é um rascunho inicial. Atualize ou peça ajustes (por exemplo, preferências de comandos Windows vs Linux, exemplos de Airflow DAGs, ou inclusão de instruções Docker) e eu adapto o arquivo.
