from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# A Alpha Vantage envia valores financeiros como strings e usa estes valores
# sentinela quando uma informação não está disponível.
AlphaInt = int | Literal["None", "-", "", "N/A"]
AlphaFloat = float | Literal["None", "-", "", "N/A"]


def has_extra_fields(model: BaseModel) -> bool:
    """
    Verifica se a resposta da API continha campos não mapeados no contrato.
    Retorna True se houver campos extras — o extractor deve rotear o arquivo
    para a pasta de quarentena no GCS em vez do caminho Bronze normal.
    """
    return bool(model.model_extra)


# Todos os contratos usam `extra='allow'` para que novos campos da API não
# derrubem o pipeline. Campos desconhecidos são capturados em `model.model_extra`
# e a função `has_extra_fields` é usada pelos extractors para rotear o arquivo
# para quarentena quando campos inesperados são detectados.
STRICT_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


# ==========================================
# 1. CONTRATO DO OVERVIEW
# ==========================================
class OverviewSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    # 1. Informações Cadastrais
    Symbol: str
    AssetType: str | None = None
    Name: str | None = None
    Description: str | None = None
    CIK: str | None = None
    Exchange: str | None = None
    Currency: str | None = None
    Country: str | None = None
    Sector: str | None = None
    Industry: str | None = None
    Address: str | None = None
    OfficialSite: str | None = None
    FiscalYearEnd: str | None = None
    LatestQuarter: str | None = None
    DividendDate: str | None = None
    ExDividendDate: str | None = None

    # 2. Números Inteiros (AlphaInt)
    MarketCapitalization: AlphaInt | None = None
    EBITDA: AlphaInt | None = None
    RevenueTTM: AlphaInt | None = None
    GrossProfitTTM: AlphaInt | None = None
    SharesOutstanding: AlphaInt | None = None
    SharesFloat: AlphaInt | None = None

    # 3. Decimais / Porcentagens / Multiplicadores (AlphaFloat)
    PERatio: AlphaFloat | None = None
    PEGRatio: AlphaFloat | None = None
    BookValue: AlphaFloat | None = None
    DividendPerShare: AlphaFloat | None = None
    DividendYield: AlphaFloat | None = None
    EPS: AlphaFloat | None = None
    RevenuePerShareTTM: AlphaFloat | None = None
    ProfitMargin: AlphaFloat | None = None
    OperatingMarginTTM: AlphaFloat | None = None
    ReturnOnAssetsTTM: AlphaFloat | None = None
    ReturnOnEquityTTM: AlphaFloat | None = None
    DilutedEPSTTM: AlphaFloat | None = None
    QuarterlyEarningsGrowthYOY: AlphaFloat | None = None
    QuarterlyRevenueGrowthYOY: AlphaFloat | None = None
    AnalystTargetPrice: AlphaFloat | None = None
    AnalystRatingStrongBuy: AlphaFloat | None = None
    AnalystRatingBuy: AlphaFloat | None = None
    AnalystRatingHold: AlphaFloat | None = None
    AnalystRatingSell: AlphaFloat | None = None
    AnalystRatingStrongSell: AlphaFloat | None = None
    TrailingPE: AlphaFloat | None = None
    ForwardPE: AlphaFloat | None = None
    PriceToSalesRatioTTM: AlphaFloat | None = None
    PriceToBookRatio: AlphaFloat | None = None
    EVToRevenue: AlphaFloat | None = None
    EVToEBITDA: AlphaFloat | None = None
    Beta: AlphaFloat | None = None
    PercentInsiders: AlphaFloat | None = None
    PercentInstitutions: AlphaFloat | None = None

    # 4. Colunas problemáticas (Começam com número)
    week_high_52: AlphaFloat | None = Field(default=None, alias="52WeekHigh")
    week_low_52: AlphaFloat | None = Field(default=None, alias="52WeekLow")
    moving_average_50: AlphaFloat | None = Field(default=None, alias="50DayMovingAverage")
    moving_average_200: AlphaFloat | None = Field(default=None, alias="200DayMovingAverage")


# ==========================================
# 2. BALANCE SHEET
# ==========================================


# A) Uma linha representa um relatório anual ou trimestral.
class BalanceSheetReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Valores Contábeis (Convertidos para Int)
    totalAssets: AlphaInt | None = None
    totalCurrentAssets: AlphaInt | None = None
    cashAndCashEquivalentsAtCarryingValue: AlphaInt | None = None
    cashAndShortTermInvestments: AlphaInt | None = None
    inventory: AlphaInt | None = None
    currentNetReceivables: AlphaInt | None = None
    totalNonCurrentAssets: AlphaInt | None = None
    propertyPlantEquipment: AlphaInt | None = None
    accumulatedDepreciationAmortizationPPE: AlphaInt | None = None
    intangibleAssets: AlphaInt | None = None
    intangibleAssetsExcludingGoodwill: AlphaInt | None = None
    goodwill: AlphaInt | None = None
    investments: AlphaInt | None = None
    longTermInvestments: AlphaInt | None = None
    shortTermInvestments: AlphaInt | None = None
    otherCurrentAssets: AlphaInt | None = None
    otherNonCurrentAssets: AlphaInt | None = None
    totalLiabilities: AlphaInt | None = None
    totalCurrentLiabilities: AlphaInt | None = None
    currentAccountsPayable: AlphaInt | None = None
    deferredRevenue: AlphaInt | None = None
    currentDebt: AlphaInt | None = None
    shortTermDebt: AlphaInt | None = None
    totalNonCurrentLiabilities: AlphaInt | None = None
    capitalLeaseObligations: AlphaInt | None = None
    longTermDebt: AlphaInt | None = None
    currentLongTermDebt: AlphaInt | None = None
    longTermDebtNoncurrent: AlphaInt | None = None
    shortLongTermDebtTotal: AlphaInt | None = None
    otherCurrentLiabilities: AlphaInt | None = None
    otherNonCurrentLiabilities: AlphaInt | None = None
    totalShareholderEquity: AlphaInt | None = None
    treasuryStock: AlphaInt | None = None
    retainedEarnings: AlphaInt | None = None
    commonStock: AlphaInt | None = None
    commonStockSharesOutstanding: AlphaInt | None = None


# B) O envelope representa a resposta completa de um ticker.
class BalanceSheetSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[BalanceSheetReport]
    quarterlyReports: list[BalanceSheetReport]


# ==========================================
# 3. CASH FLOW
# ==========================================


# A) Uma linha representa um relatório anual ou trimestral.
class CashFlowReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Valores de Fluxo de Caixa (Convertidos para Int via AlphaInt)
    operatingCashflow: AlphaInt | None = None
    paymentsForOperatingActivities: AlphaInt | None = None
    proceedsFromOperatingActivities: AlphaInt | None = None
    changeInOperatingLiabilities: AlphaInt | None = None
    changeInOperatingAssets: AlphaInt | None = None
    depreciationDepletionAndAmortization: AlphaInt | None = None
    capitalExpenditures: AlphaInt | None = None
    changeInReceivables: AlphaInt | None = None
    changeInInventory: AlphaInt | None = None
    profitLoss: AlphaInt | None = None
    cashflowFromInvestment: AlphaInt | None = None
    cashflowFromFinancing: AlphaInt | None = None
    proceedsFromRepaymentsOfShortTermDebt: AlphaInt | None = None
    paymentsForRepurchaseOfCommonStock: AlphaInt | None = None
    paymentsForRepurchaseOfEquity: AlphaInt | None = None
    paymentsForRepurchaseOfPreferredStock: AlphaInt | None = None
    dividendPayout: AlphaInt | None = None
    dividendPayoutCommonStock: AlphaInt | None = None
    dividendPayoutPreferredStock: AlphaInt | None = None
    proceedsFromIssuanceOfCommonStock: AlphaInt | None = None
    proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet: AlphaInt | None = None
    proceedsFromIssuanceOfPreferredStock: AlphaInt | None = None
    proceedsFromRepurchaseOfEquity: AlphaInt | None = None
    proceedsFromSaleOfTreasuryStock: AlphaInt | None = None
    stockBasedCompensation: AlphaInt | None = None
    changeInCashAndCashEquivalents: AlphaInt | None = None
    changeInExchangeRate: AlphaInt | None = (
        None  # Ocasionalmente pode ser float, mas a Alpha Vantage costuma arredondar ou enviar vazio. Se quebrar, mudamos para AlphaFloat.
    )
    netIncome: AlphaInt | None = None


# B) O envelope representa a resposta completa de um ticker.
class CashFlowSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[CashFlowReport]
    quarterlyReports: list[CashFlowReport]


# ==========================================
# 4. INCOME STATEMENT
# ==========================================


# A) Uma linha representa um relatório anual ou trimestral.
class IncomeStatementReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Valores da DRE (Convertidos para Int via AlphaInt)
    grossProfit: AlphaInt | None = None
    totalRevenue: AlphaInt | None = None
    costOfRevenue: AlphaInt | None = None
    costofGoodsAndServicesSold: AlphaInt | None = (
        None  # A Alpha Vantage manda esse "of" minúsculo mesmo, mantemos assim
    )
    operatingIncome: AlphaInt | None = None
    sellingGeneralAndAdministrative: AlphaInt | None = None
    researchAndDevelopment: AlphaInt | None = None
    operatingExpenses: AlphaInt | None = None
    investmentIncomeNet: AlphaInt | None = None
    netInterestIncome: AlphaInt | None = None
    interestIncome: AlphaInt | None = None
    interestExpense: AlphaInt | None = None
    nonInterestIncome: AlphaInt | None = None
    otherNonOperatingIncome: AlphaInt | None = None
    depreciation: AlphaInt | None = None
    depreciationAndAmortization: AlphaInt | None = None
    incomeBeforeTax: AlphaInt | None = None
    incomeTaxExpense: AlphaInt | None = None
    interestAndDebtExpense: AlphaInt | None = None
    netIncomeFromContinuingOperations: AlphaInt | None = None
    comprehensiveIncomeNetOfTax: AlphaInt | None = None
    ebit: AlphaInt | None = None
    ebitda: AlphaInt | None = None
    netIncome: AlphaInt | None = None


# B) O envelope representa a resposta completa de um ticker.
class IncomeStatementSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[IncomeStatementReport]
    quarterlyReports: list[IncomeStatementReport]


# ==========================================
# 5. EARNINGS (Lucro por Ação)
# ==========================================


# A) Estrutura do relatório Anual
class AnnualEarningsReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedEPS: AlphaFloat | None = None


# B) Estrutura do relatório Trimestral (Traz dados de expectativa do mercado)
class QuarterlyEarningsReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedDate: date | None = None
    reportedEPS: AlphaFloat | None = None
    estimatedEPS: AlphaFloat | None = None
    surprise: AlphaFloat | None = None
    surprisePercentage: AlphaFloat | None = None
    reportTime: str | None = None  # Geralmente é texto ("post-market", etc)


# C) Estrutura principal que agrupa as listas
class EarningSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualEarnings: list[AnnualEarningsReport]
    quarterlyEarnings: list[QuarterlyEarningsReport]
