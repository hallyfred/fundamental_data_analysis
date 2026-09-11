from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Alpha Vantage sends financial values as strings and uses these sentinel values
# when information is unavailable.
AlphaInt = int | Literal["None", "-", "", "N/A"]
AlphaFloat = float | Literal["None", "-", "", "N/A"]


def has_extra_fields(model: BaseModel) -> bool:
    """
    Check whether the API response contains fields not mapped by the contract.
    Return True for extra fields so the extractor can route the file
    to the GCS quarantine prefix instead of the regular Bronze prefix.
    """
    return bool(model.model_extra)


# Every contract uses `extra='allow'` so newly introduced API fields do not
# crash the pipeline. Unknown fields are captured in `model.model_extra`,
# and `has_extra_fields` lets extractors route the payload
# to quarantine when unexpected fields are detected.
STRICT_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


# ==========================================
# 1. OVERVIEW CONTRACT
# ==========================================
class OverviewSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    # 1. Company information
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

    # 2. Integer values (AlphaInt)
    MarketCapitalization: AlphaInt | None = None
    EBITDA: AlphaInt | None = None
    RevenueTTM: AlphaInt | None = None
    GrossProfitTTM: AlphaInt | None = None
    SharesOutstanding: AlphaInt | None = None
    SharesFloat: AlphaInt | None = None

    # 3. Decimals, percentages, and multipliers (AlphaFloat)
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

    # 4. API fields whose names begin with a number
    week_high_52: AlphaFloat | None = Field(default=None, alias="52WeekHigh")
    week_low_52: AlphaFloat | None = Field(default=None, alias="52WeekLow")
    moving_average_50: AlphaFloat | None = Field(default=None, alias="50DayMovingAverage")
    moving_average_200: AlphaFloat | None = Field(default=None, alias="200DayMovingAverage")


# ==========================================
# 2. BALANCE SHEET
# ==========================================


# A) One row represents an annual or quarterly report.
class BalanceSheetReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Accounting values converted through AlphaInt
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


# B) The envelope represents the complete response for one ticker.
class BalanceSheetSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[BalanceSheetReport]
    quarterlyReports: list[BalanceSheetReport]


# ==========================================
# 3. CASH FLOW
# ==========================================


# A) One row represents an annual or quarterly report.
class CashFlowReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Cash-flow values converted through AlphaInt
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
        None  # Occasionally returned as a float, although the API usually rounds it or sends an empty value.
    )
    netIncome: AlphaInt | None = None


# B) The envelope represents the complete response for one ticker.
class CashFlowSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[CashFlowReport]
    quarterlyReports: list[CashFlowReport]


# ==========================================
# 4. INCOME STATEMENT
# ==========================================


# A) One row represents an annual or quarterly report.
class IncomeStatementReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedCurrency: str

    # Income-statement values converted through AlphaInt
    grossProfit: AlphaInt | None = None
    totalRevenue: AlphaInt | None = None
    costOfRevenue: AlphaInt | None = None
    costofGoodsAndServicesSold: AlphaInt | None = (
        None  # Preserve the lowercase 'of' used by the Alpha Vantage field name.
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


# B) The envelope represents the complete response for one ticker.
class IncomeStatementSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualReports: list[IncomeStatementReport]
    quarterlyReports: list[IncomeStatementReport]


# ==========================================
# 5. EARNINGS
# ==========================================


# A) Annual report structure
class AnnualEarningsReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedEPS: AlphaFloat | None = None


# B) Quarterly report structure, including market expectations
class QuarterlyEarningsReport(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    fiscalDateEnding: date
    reportedDate: date | None = None
    reportedEPS: AlphaFloat | None = None
    estimatedEPS: AlphaFloat | None = None
    surprise: AlphaFloat | None = None
    surprisePercentage: AlphaFloat | None = None
    reportTime: str | None = None  # Usually text such as 'post-market'


# C) Top-level response containing both report lists
class EarningSchema(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    symbol: str
    annualEarnings: list[AnnualEarningsReport]
    quarterlyEarnings: list[QuarterlyEarningsReport]
