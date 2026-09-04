from datetime import date

import pytest
from pydantic import ValidationError

from src.extract.contract import (
    BalanceSheetSchema,
    CashFlowSchema,
    EarningSchema,
    IncomeStatementSchema,
    OverviewSchema,
    has_extra_fields,
)

REPORT = {"fiscalDateEnding": "2023-09-30", "reportedCurrency": "USD", "operatingCashflow": 100, "totalRevenue": 200}
VALID_CASES = [
    (OverviewSchema, {"Symbol": "AAPL", "AssetType": "Common Stock", "MarketCapitalization": 3000, "PERatio": 30.5}),
    (BalanceSheetSchema, {"symbol": "AAPL", "annualReports": [REPORT], "quarterlyReports": []}),
    (IncomeStatementSchema, {"symbol": "AAPL", "annualReports": [REPORT], "quarterlyReports": []}),
    (CashFlowSchema, {"symbol": "AAPL", "annualReports": [REPORT], "quarterlyReports": []}),
    (EarningSchema, {"symbol": "AAPL", "annualEarnings": [], "quarterlyEarnings": []}),
]


@pytest.mark.parametrize(("schema_cls", "payload"), VALID_CASES)
def test_schemas_accept_valid_payloads(schema_cls, payload):
    model = schema_cls.model_validate(payload)
    assert not has_extra_fields(model)
    if hasattr(model, "annualReports") and model.annualReports:
        assert model.annualReports[0].fiscalDateEnding == date(2023, 9, 30)


def test_schema_detects_extra_fields():
    model = OverviewSchema.model_validate({"Symbol": "AAPL", "NewMetric": 123})
    assert has_extra_fields(model)
    assert "NewMetric" in model.model_extra


@pytest.mark.parametrize("schema_cls", [OverviewSchema, BalanceSheetSchema])
def test_schema_requires_symbol(schema_cls):
    with pytest.raises(ValidationError):
        schema_cls.model_validate({})
