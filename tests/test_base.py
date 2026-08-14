from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import Column, Float, Numeric, String

from util.db.base import BaseTable


def _make_table(**overrides: object) -> BaseTable:
    defaults: dict[str, object] = {
        "table_name": "t",
        "pk_columns": ("symbol",),
        "columns": [
            Column("symbol", String(10), primary_key=True),
            Column("price", Numeric(12, 4), nullable=False),
            Column("amount", Float, nullable=False),
        ],
    }
    defaults.update(overrides)
    return BaseTable(MagicMock(), **defaults)  # type: ignore[arg-type]


def test_missing_table_name_raises() -> None:
    with pytest.raises(ValueError, match="table_name"):
        BaseTable(MagicMock(), pk_columns=("id",), columns=[Column("id", String(10))])


def test_missing_pk_columns_raises() -> None:
    with pytest.raises(ValueError, match="pk_columns"):
        BaseTable(MagicMock(), table_name="t", columns=[Column("id", String(10))])


def test_missing_business_columns_raises() -> None:
    with pytest.raises(ValueError, match="business columns"):
        BaseTable(MagicMock(), table_name="t", pk_columns=("id",))


def test_prepare_df_strips_and_uppercases_string_pk_columns() -> None:
    table = _make_table()
    df = pd.DataFrame([{"symbol": " aapl ", "price": 1.0, "amount": 1.0}])

    prepared = table.prepare_df(df)

    assert prepared.loc[0, "symbol"] == "AAPL"


def test_prepare_df_rounds_numeric_column_to_its_own_scale() -> None:
    table = _make_table()
    df = pd.DataFrame([{"symbol": "AAPL", "price": 1.23456789, "amount": 1.0}])

    prepared = table.prepare_df(df)

    assert prepared.loc[0, "price"] == 1.2346


def test_prepare_df_falls_back_to_float_precision_for_plain_float_column() -> None:
    table = _make_table(float_precision=3)
    df = pd.DataFrame([{"symbol": "AAPL", "price": 1.0, "amount": 1.23456789}])

    prepared = table.prepare_df(df)

    assert prepared.loc[0, "amount"] == 1.235


def test_prepare_df_leaves_nulls_alone() -> None:
    table = _make_table()
    df = pd.DataFrame([{"symbol": "AAPL", "price": None, "amount": 1.0}])

    prepared = table.prepare_df(df)

    assert pd.isna(prepared.loc[0, "price"])
