import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from config.config import WEEKDAY_SYMBOLS, get_symbols_for_day
from src.extract.balance_sheet import extract_balance_sheet
from src.extract.overview import extract_overview


class TestRoundRobin(unittest.TestCase):
    def test_round_robin_schedule_structure(self):
        """Valida se a escala tem exatamente 7 dias com 5 tickers cada, somando 35 empresas únicas."""
        self.assertEqual(len(WEEKDAY_SYMBOLS), 7, "A escala semanal deve ter 7 dias (0 a 6)")

        all_symbols = []
        for day in range(7):
            day_symbols = WEEKDAY_SYMBOLS[day]
            self.assertEqual(len(day_symbols), 5, f"Dia {day} deve ter exatamente 5 tickers, tem {len(day_symbols)}")
            all_symbols.extend(day_symbols)

        self.assertEqual(len(all_symbols), 35, f"O total de símbolos deve ser 35, encontrado {len(all_symbols)}")
        self.assertEqual(len(set(all_symbols)), 35, "Não pode haver símbolos duplicados entre os dias da semana")

    def test_get_symbols_for_day_rotation(self):
        """Valida se a função retorna os símbolos corretos e cicla após 7 dias."""
        monday_symbols = get_symbols_for_day(0)
        self.assertEqual(monday_symbols, ["AAPL", "MSFT", "GOOGL", "AMZN", "META"])

        sunday_symbols = get_symbols_for_day(6)
        self.assertEqual(sunday_symbols, ["BA", "CAT", "GE", "C", "GS"])

        # Dia 7 deve ciclar de volta para segunda-feira (dia 0)
        next_monday_symbols = get_symbols_for_day(7)
        self.assertEqual(next_monday_symbols, monday_symbols)

    @patch("src.extract.overview.GCPSLoader")
    @patch("src.extract.overview.AlphaVantageAPIClient")
    @patch("src.extract.overview.upload_and_clean_log")
    def test_extract_overview_with_custom_symbols(self, mock_clean_log, mock_client_cls, mock_loader_cls):
        """Garante que o extrator respeita o parâmetro symbols fornecido."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "Symbol": "AAPL",
            "AssetType": "Common Stock",
            "Name": "Apple Inc",
            "Description": "Tech company",
            "CIK": "0000320193",
            "Exchange": "NASDAQ",
            "Currency": "USD",
            "Country": "USA",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
        }
        mock_client_cls.return_value = mock_client

        mock_loader = MagicMock()
        mock_loader_cls.return_value = mock_loader

        # Executa apenas para 1 símbolo customizado
        files = extract_overview(symbols=["AAPL"])

        self.assertEqual(len(files), 1)
        self.assertEqual(mock_client.get.call_count, 1)
        self.assertEqual(mock_loader.upload_file.call_count, 1)

    @patch("src.extract.balance_sheet.GCPSLoader")
    @patch("src.extract.balance_sheet.AlphaVantageAPIClient")
    @patch("src.extract.balance_sheet.upload_and_clean_log")
    def test_extract_balance_sheet_default_uses_day_batch(self, mock_clean_log, mock_client_cls, mock_loader_cls):
        """Garante que quando symbols=None, o extrator seleciona automaticamente o lote do dia (5 empresas)."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"symbol": "MOCK", "annualReports": [], "quarterlyReports": []}
        mock_client_cls.return_value = mock_client

        mock_loader = MagicMock()
        mock_loader_cls.return_value = mock_loader

        # Executa sem especificar símbolos
        files = extract_balance_sheet(symbols=None)

        # Deve ter chamado a API exatamente 5 vezes (o lote do dia atual)
        expected_count = len(get_symbols_for_day(date.today().weekday()))
        self.assertEqual(expected_count, 5)
        self.assertEqual(mock_client.get.call_count, 5)
        self.assertEqual(len(files), 5)


if __name__ == "__main__":
    unittest.main()
