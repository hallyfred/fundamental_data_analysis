"""Prevent extraction contracts from outgrowing the Silver public schema."""

import json
import re
from datetime import date
from pathlib import Path
from typing import get_args

import pytest
import yaml

from src.extract.contract import (
    AnnualEarningsReport,
    BalanceSheetReport,
    CashFlowReport,
    IncomeStatementReport,
    OverviewSchema,
    QuarterlyEarningsReport,
)

MODELS = Path(__file__).resolve().parents[1] / "src/transformations/models/intermediate"
CONTRACTS = [
    ("overview", (OverviewSchema,)),
    ("balance_sheet", (BalanceSheetReport,)),
    ("cash_flow", (CashFlowReport,)),
    ("income_statement", (IncomeStatementReport,)),
    ("earning", (AnnualEarningsReport, QuarterlyEarningsReport)),
]


@pytest.mark.parametrize(("endpoint", "schemas"), CONTRACTS)
def test_silver_exposes_every_contract_field(endpoint, schemas):
    catalog = yaml.safe_load((MODELS / f"int_{endpoint}.yml").read_text(encoding="utf-8"))
    columns = catalog["models"][0]["columns"]

    def source_field(column):
        return column.get("config", {}).get("meta", {}).get("source_field")

    mapped = {source_field(column): column for column in columns if source_field(column)}
    assert len({c["name"] for c in columns}) == len(columns), "Duplicate catalog column"
    assert len(mapped) == sum(bool(source_field(column)) for column in columns)
    sql = (MODELS / f"int_{endpoint}.sql").read_text(encoding="utf-8")
    unit = next(t for t in catalog["unit_tests"] if t["name"] == f"{endpoint}_all_contract_fields")
    # The native dbt test executes these inputs and checks every public field.
    raw = json.loads(re.search(r"select '(.*?)' as raw_data", unit["given"][0]["rows"]).group(1))
    for schema in schemas:
        if endpoint == "overview":
            payload, expected = raw, unit["expect"]["rows"][0]
        else:
            frequency = "annual" if schema is AnnualEarningsReport else "quarterly"
            array = "Earnings" if endpoint == "earning" else "Reports"
            payload = raw[frequency + array][0]
            expected = next(r for r in unit["expect"]["rows"] if r["report_type"] == frequency)
        schema.model_validate(payload)
        for name, field in schema.model_fields.items():
            source = field.alias or name
            assert source in mapped, f"{endpoint}: contract field {source} missing from Silver"
            column = mapped[source]
            types = get_args(field.annotation) or (field.annotation,)
            expected_type = (
                "int64" if int in types else "numeric" if float in types else "date" if date in types else "string"
            )
            assert column["data_type"] == expected_type, source
            assert column["description"], source
            assert f"$.{source}'" in sql, f"{source} is documented but never extracted"
            assert source in payload, f"{source} has no full-contract test input"
            assert column["name"] in expected, f"{source} has no dbt output assertion"
        if endpoint != "overview":
            assert mapped["symbol"]["data_type"] == "string"
            assert raw["symbol"] == expected["symbol"]
