import logging
import re
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

    def _sanitize(self, message: str) -> str:
        """Remove qualquer ocorrência da API key do texto de logs/exceções."""
        if not message:
            return ""
        sanitized = message.replace(self.api_key, "***REDACTED_API_KEY***")
        return re.sub(r"(API key as )([A-Z0-9]+)", r"\1***REDACTED_API_KEY***", sanitized)

    def _check_semantic_errors(self, data: dict, symbol: str, function: str) -> None:
        """
        Fix #10 — detecta erros semânticos da Alpha Vantage antes de retornar o dado.
        A API retorna HTTP 200 com um dict de erro em vez de status 4xx/5xx.
        Todas as mensagens são sanitizadas para não expor a chave da API.
        """
        if "Note" in data:
            msg = self._sanitize(str(data["Note"]))
            raise AlphaVantageRateLimitError(
                f"Rate-limit atingido ao consultar '{function}' para '{symbol}'. Resposta da API: {msg}"
            )
        if "Information" in data:
            raw_info = str(data["Information"])
            msg = self._sanitize(raw_info)
            if "rate limit" in raw_info.lower():
                raise AlphaVantageRateLimitError(
                    f"Limite diário de requisições atingido ao consultar '{function}' para '{symbol}'. Resposta da API: {msg}"
                )
            raise AlphaVantageAPIError(
                f"Acesso bloqueado (plano free ou demo key) ao consultar '{function}' para '{symbol}'. Resposta da API: {msg}"
            )
        if "Error Message" in data:
            msg = self._sanitize(str(data["Error Message"]))
            raise AlphaVantageAPIError(
                f"Chamada inválida ao consultar '{function}' para '{symbol}'. Resposta da API: {msg}"
            )

    def get(self, function: str, symbol: str) -> dict:
        """
        Faz uma requisição GET para a Alpha Vantage com:
        - Fix #7: timeout configurável (TIMEOUT de config.py)
        - Fix #8: retry com backoff exponencial para erros transitórios
        - Fix #10: detecção de erros semânticos no corpo da resposta com sanitização
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

            except AlphaVantageRateLimitError as e:
                # Se for limite diário (25/dia), falha imediatamente para não desperdiçar tempo em retentativas
                err_msg = str(e).lower()
                if "25 requests per day" in err_msg or "limite diário" in err_msg:
                    _logger.error(
                        f"[{symbol}/{function}] Limite diário da Alpha Vantage atingido. Interrompendo execução."
                    )
                    raise

                # Rate-limit por minuto transitório: aguarda e tenta novamente
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
