import logging
import time

import requests

from config.config import TIMEOUT

_logger = logging.getLogger(__name__)


# =============================================================================
# Exceções semânticas da Alpha Vantage
# A API retorna HTTP 200 mesmo para erros. Essas exceções tornam a distinção
# explícita e permitem tratamento diferenciado (ex: retry só no rate-limit).
# =============================================================================


class AlphaVantageRateLimitError(Exception):
    """
    Levantada quando a Alpha Vantage retorna um corpo com 'Note',
    indicando que o limite de requisições por minuto/dia foi atingido.
    Passível de retry com backoff.
    """


class AlphaVantageAPIError(Exception):
    """
    Levantada para erros semânticos não-retriáveis da Alpha Vantage:
    - 'Information': acesso bloqueado (plano free / demo key)
    - 'Error Message': chamada inválida (símbolo inexistente, parâmetro errado)
    """


# =============================================================================
# Cliente HTTP com timeout, retry/backoff e detecção de erros semânticos
# =============================================================================


class AlphaVantageAPIClient:
    MAX_RETRIES = 3
    BACKOFF_BASE_SECONDS = 2  # delays: 2s, 4s, 8s

    def __init__(self, base_url: str, api_key: str):
        # Fix #9 — falha imediata com mensagem clara se a key não estiver configurada
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY não está configurada. "
                "Defina a variável de ambiente no arquivo .env antes de executar o pipeline."
            )
        self.base_url = base_url
        self.api_key = api_key

    def _check_semantic_errors(self, data: dict, symbol: str, function: str) -> None:
        """
        Fix #10 — detecta erros semânticos da Alpha Vantage antes de retornar o dado.
        A API retorna HTTP 200 com um dict de erro em vez de status 4xx/5xx.
        """
        if "Note" in data:
            raise AlphaVantageRateLimitError(
                f"Rate-limit atingido ao consultar '{function}' para '{symbol}'. Resposta da API: {data['Note']}"
            )
        if "Information" in data:
            raise AlphaVantageAPIError(
                f"Acesso bloqueado (plano free ou demo key) ao consultar '{function}' para '{symbol}'. "
                f"Resposta da API: {data['Information']}"
            )
        if "Error Message" in data:
            raise AlphaVantageAPIError(
                f"Chamada inválida ao consultar '{function}' para '{symbol}'. Resposta da API: {data['Error Message']}"
            )

    def get(self, function: str, symbol: str) -> dict:
        """
        Faz uma requisição GET para a Alpha Vantage com:
        - Fix #7: timeout configurável (TIMEOUT de config.py)
        - Fix #8: retry com backoff exponencial para erros transitórios
        - Fix #10: detecção de erros semânticos no corpo da resposta
        """
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = requests.get(self.base_url, params=params, timeout=TIMEOUT)
                response.raise_for_status()
                data = response.json()

                # Detecta erros semânticos antes de retornar
                self._check_semantic_errors(data, symbol, function)

                return data

            except AlphaVantageRateLimitError:
                # Rate-limit: vale a pena aguardar e tentar novamente
                if attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        f"[{symbol}/{function}] Rate-limit (tentativa {attempt}/{self.MAX_RETRIES}). "
                        f"Aguardando {wait}s antes de nova tentativa..."
                    )
                    time.sleep(wait)
                else:
                    _logger.error(f"[{symbol}/{function}] Rate-limit persistente após {self.MAX_RETRIES} tentativas.")
                    raise

            except AlphaVantageAPIError:
                # Erro não-retriável (símbolo inválido, plano free, etc.) — falha imediata
                raise

            except requests.exceptions.Timeout:
                if attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        f"[{symbol}/{function}] Timeout na tentativa {attempt}/{self.MAX_RETRIES}. "
                        f"Aguardando {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                # Erros de rede genéricos (conexão recusada, DNS, etc.)
                if attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        f"[{symbol}/{function}] Erro de rede na tentativa {attempt}/{self.MAX_RETRIES}: {e}. "
                        f"Aguardando {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    raise
