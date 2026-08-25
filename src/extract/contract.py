from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Union, Literal, List

# Nossos Tipos Customizados para converter as "strings numéricas" da API
AlphaInt = Union[int, Literal["None", "-", "", "N/A"]]
AlphaFloat = Union[float, Literal["None", "-", "", "N/A"]]

# ==========================================
# 1. CONTRATO DO OVERVIEW
# ==========================================
class OverviewSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    # 1. Informações Cadastrais
    Symbol: str
    AssetType: Optional[str] = None
    Name: Optional[str] = None
    Description: Optional[str] = None
    CIK: Optional[str] = None
    Exchange: Optional[str] = None
    Currency: Optional[str] = None
    Country: Optional[str] = None
    Sector: Optional[str] = None
    Industry: Optional[str] = None
    Address: Optional[str] = None
    OfficialSite: Optional[str] = None
    FiscalYearEnd: Optional[str] = None
    LatestQuarter: Optional[str] = None
    DividendDate: Optional[str] = None
    ExDividendDate: Optional[str] = None

    # 2. Números Inteiros (AlphaInt)
    MarketCapitalization: Optional[AlphaInt] = None
    EBITDA: Optional[AlphaInt] = None
    RevenueTTM: Optional[AlphaInt] = None
    GrossProfitTTM: Optional[AlphaInt] = None
    SharesOutstanding: Optional[AlphaInt] = None
    SharesFloat: Optional[AlphaInt] = None

    # 3. Decimais / Porcentagens / Multiplicadores (AlphaFloat)
    PERatio: Optional[AlphaFloat] = None
    PEGRatio: Optional[AlphaFloat] = None
    BookValue: Optional[AlphaFloat] = None
    DividendPerShare: Optional[AlphaFloat] = None
    DividendYield: Optional[AlphaFloat] = None
    EPS: Optional[AlphaFloat] = None
    RevenuePerShareTTM: Optional[AlphaFloat] = None
    ProfitMargin: Optional[AlphaFloat] = None
    OperatingMarginTTM: Optional[AlphaFloat] = None
    ReturnOnAssetsTTM: Optional[AlphaFloat] = None
    ReturnOnEquityTTM: Optional[AlphaFloat] = None
    DilutedEPSTTM: Optional[AlphaFloat] = None
    QuarterlyEarningsGrowthYOY: Optional[AlphaFloat] = None
    QuarterlyRevenueGrowthYOY: Optional[AlphaFloat] = None
    AnalystTargetPrice: Optional[AlphaFloat] = None
    AnalystRatingStrongBuy: Optional[AlphaFloat] = None
    AnalystRatingBuy: Optional[AlphaFloat] = None
    AnalystRatingHold: Optional[AlphaFloat] = None
    AnalystRatingSell: Optional[AlphaFloat] = None
    AnalystRatingStrongSell: Optional[AlphaFloat] = None
    TrailingPE: Optional[AlphaFloat] = None
    ForwardPE: Optional[AlphaFloat] = None
    PriceToSalesRatioTTM: Optional[AlphaFloat] = None
    PriceToBookRatio: Optional[AlphaFloat] = None
    EVToRevenue: Optional[AlphaFloat] = None
    EVToEBITDA: Optional[AlphaFloat] = None
    Beta: Optional[AlphaFloat] = None
    PercentInsiders: Optional[AlphaFloat] = None
    PercentInstitutions: Optional[AlphaFloat] = None

    # 4. Colunas problemáticas (Começam com número)
    week_high_52: Optional[AlphaFloat] = Field(default=None, alias='52WeekHigh')
    week_low_52: Optional[AlphaFloat] = Field(default=None, alias='52WeekLow')
    moving_average_50: Optional[AlphaFloat] = Field(default=None, alias='50DayMovingAverage')
    moving_average_200: Optional[AlphaFloat] = Field(default=None, alias='200DayMovingAverage')


# ==========================================
# 2. BALANCE SHEET
# ==========================================

# A) Estrutura base de uma linha (Relatório)
class BalanceSheetSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    fiscalDateEnding: str
    reportedCurrency: str
    
    # Valores Contábeis (Convertidos para Int)
    totalAssets: Optional[AlphaInt] = None
    totalCurrentAssets: Optional[AlphaInt] = None
    cashAndCashEquivalentsAtCarryingValue: Optional[AlphaInt] = None
    cashAndShortTermInvestments: Optional[AlphaInt] = None
    inventory: Optional[AlphaInt] = None
    currentNetReceivables: Optional[AlphaInt] = None
    totalNonCurrentAssets: Optional[AlphaInt] = None
    propertyPlantEquipment: Optional[AlphaInt] = None
    accumulatedDepreciationAmortizationPPE: Optional[AlphaInt] = None
    intangibleAssets: Optional[AlphaInt] = None
    intangibleAssetsExcludingGoodwill: Optional[AlphaInt] = None
    goodwill: Optional[AlphaInt] = None
    investments: Optional[AlphaInt] = None
    longTermInvestments: Optional[AlphaInt] = None
    shortTermInvestments: Optional[AlphaInt] = None
    otherCurrentAssets: Optional[AlphaInt] = None
    otherNonCurrentAssets: Optional[AlphaInt] = None
    totalLiabilities: Optional[AlphaInt] = None
    totalCurrentLiabilities: Optional[AlphaInt] = None
    currentAccountsPayable: Optional[AlphaInt] = None
    deferredRevenue: Optional[AlphaInt] = None
    currentDebt: Optional[AlphaInt] = None
    shortTermDebt: Optional[AlphaInt] = None
    totalNonCurrentLiabilities: Optional[AlphaInt] = None
    capitalLeaseObligations: Optional[AlphaInt] = None
    longTermDebt: Optional[AlphaInt] = None
    currentLongTermDebt: Optional[AlphaInt] = None
    longTermDebtNoncurrent: Optional[AlphaInt] = None
    shortLongTermDebtTotal: Optional[AlphaInt] = None
    otherCurrentLiabilities: Optional[AlphaInt] = None
    otherNonCurrentLiabilities: Optional[AlphaInt] = None
    totalShareholderEquity: Optional[AlphaInt] = None
    treasuryStock: Optional[AlphaInt] = None
    retainedEarnings: Optional[AlphaInt] = None
    commonStock: Optional[AlphaInt] = None
    commonStockSharesOutstanding: Optional[AlphaInt] = None

# B) Estrutura principal que agrupa as listas
class BalanceSheetSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    symbol: str
    annualReports: List[BalanceSheetSchema]
    quarterlyReports: List[BalanceSheetSchema]

# ==========================================
# 3. CASH FLOW
# ==========================================

# A) Estrutura base de uma linha (Relatório)
class CashFlowSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    fiscalDateEnding: str
    reportedCurrency: str
    
    # Valores de Fluxo de Caixa (Convertidos para Int via AlphaInt)
    operatingCashflow: Optional[AlphaInt] = None
    paymentsForOperatingActivities: Optional[AlphaInt] = None
    proceedsFromOperatingActivities: Optional[AlphaInt] = None
    changeInOperatingLiabilities: Optional[AlphaInt] = None
    changeInOperatingAssets: Optional[AlphaInt] = None
    depreciationDepletionAndAmortization: Optional[AlphaInt] = None
    capitalExpenditures: Optional[AlphaInt] = None
    changeInReceivables: Optional[AlphaInt] = None
    changeInInventory: Optional[AlphaInt] = None
    profitLoss: Optional[AlphaInt] = None
    cashflowFromInvestment: Optional[AlphaInt] = None
    cashflowFromFinancing: Optional[AlphaInt] = None
    proceedsFromRepaymentsOfShortTermDebt: Optional[AlphaInt] = None
    paymentsForRepurchaseOfCommonStock: Optional[AlphaInt] = None
    paymentsForRepurchaseOfEquity: Optional[AlphaInt] = None
    paymentsForRepurchaseOfPreferredStock: Optional[AlphaInt] = None
    dividendPayout: Optional[AlphaInt] = None
    dividendPayoutCommonStock: Optional[AlphaInt] = None
    dividendPayoutPreferredStock: Optional[AlphaInt] = None
    proceedsFromIssuanceOfCommonStock: Optional[AlphaInt] = None
    proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet: Optional[AlphaInt] = None
    proceedsFromIssuanceOfPreferredStock: Optional[AlphaInt] = None
    proceedsFromRepurchaseOfEquity: Optional[AlphaInt] = None
    proceedsFromSaleOfTreasuryStock: Optional[AlphaInt] = None
    stockBasedCompensation: Optional[AlphaInt] = None
    changeInCashAndCashEquivalents: Optional[AlphaInt] = None
    changeInExchangeRate: Optional[AlphaInt] = None # Ocasionalmente pode ser float, mas a Alpha Vantage costuma arredondar ou enviar vazio. Se quebrar, mudamos para AlphaFloat.
    netIncome: Optional[AlphaInt] = None

# B) Estrutura principal que agrupa as listas
class CashFlowSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    symbol: str
    annualReports: List[CashFlowSchema]
    quarterlyReports: List[CashFlowSchema]


# ==========================================
# 4. INCOME STATEMENT
# ==========================================

# A) Estrutura base de uma linha (Relatório)
class IncomeStatementSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    fiscalDateEnding: str
    reportedCurrency: str
    
    # Valores da DRE (Convertidos para Int via AlphaInt)
    grossProfit: Optional[AlphaInt] = None
    totalRevenue: Optional[AlphaInt] = None
    costOfRevenue: Optional[AlphaInt] = None
    costofGoodsAndServicesSold: Optional[AlphaInt] = None # A Alpha Vantage manda esse "of" minúsculo mesmo, mantemos assim
    operatingIncome: Optional[AlphaInt] = None
    sellingGeneralAndAdministrative: Optional[AlphaInt] = None
    researchAndDevelopment: Optional[AlphaInt] = None
    operatingExpenses: Optional[AlphaInt] = None
    investmentIncomeNet: Optional[AlphaInt] = None
    netInterestIncome: Optional[AlphaInt] = None
    interestIncome: Optional[AlphaInt] = None
    interestExpense: Optional[AlphaInt] = None
    nonInterestIncome: Optional[AlphaInt] = None
    otherNonOperatingIncome: Optional[AlphaInt] = None
    depreciation: Optional[AlphaInt] = None
    depreciationAndAmortization: Optional[AlphaInt] = None
    incomeBeforeTax: Optional[AlphaInt] = None
    incomeTaxExpense: Optional[AlphaInt] = None
    interestAndDebtExpense: Optional[AlphaInt] = None
    netIncomeFromContinuingOperations: Optional[AlphaInt] = None
    comprehensiveIncomeNetOfTax: Optional[AlphaInt] = None
    ebit: Optional[AlphaInt] = None
    ebitda: Optional[AlphaInt] = None
    netIncome: Optional[AlphaInt] = None

# B) Estrutura principal que agrupa as listas
class IncomeStatementSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    symbol: str
    annualReports: List[IncomeStatementSchema]
    quarterlyReports: List[IncomeStatementSchema]

# ==========================================
# 5. EARNINGS (Lucro por Ação)
# ==========================================

# A) Estrutura do relatório Anual
class AnnualEarningsReport(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    fiscalDateEnding: str
    reportedEPS: Optional[AlphaFloat] = None

# B) Estrutura do relatório Trimestral (Traz dados de expectativa do mercado)
class QuarterlyEarningsReport(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    fiscalDateEnding: str
    reportedDate: Optional[str] = None
    reportedEPS: Optional[AlphaFloat] = None
    estimatedEPS: Optional[AlphaFloat] = None
    surprise: Optional[AlphaFloat] = None
    surprisePercentage: Optional[AlphaFloat] = None
    reportTime: Optional[str] = None  # Geralmente é texto ("post-market", etc)

# C) Estrutura principal que agrupa as listas
class EarningSchema(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    
    symbol: str
    annualEarnings: List[AnnualEarningsReport]
    quarterlyEarnings: List[QuarterlyEarningsReport]