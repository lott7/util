from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

from util.db.validation import ValidationError, validate_rows


def _table() -> Table:
    return Table(
        "t",
        MetaData(),
        Column("symbol", String(10), nullable=False),
        Column("note", String(50), nullable=True),
        Column("qty", Integer, nullable=False),
    )


def test_valid_rows_round_trip() -> None:
    df = pd.DataFrame([{"symbol": "AAPL", "note": "x", "qty": 5}])

    rows = validate_rows(_table(), df)

    assert rows == [{"symbol": "AAPL", "note": "x", "qty": 5}]


def test_nullable_column_can_be_missing_value() -> None:
    df = pd.DataFrame([{"symbol": "AAPL", "note": None, "qty": 5}])

    rows = validate_rows(_table(), df)

    assert rows[0]["note"] is None


def test_missing_required_column_raises() -> None:
    df = pd.DataFrame([{"symbol": "AAPL", "note": "x"}])

    with pytest.raises(ValidationError):
        validate_rows(_table(), df)


def test_unknown_column_raises() -> None:
    df = pd.DataFrame([{"symbol": "AAPL", "note": "x", "qty": 5, "extra": 1}])

    with pytest.raises(ValidationError):
        validate_rows(_table(), df)


def test_caller_supplied_audit_column_raises() -> None:
    df = pd.DataFrame([{"symbol": "AAPL", "note": "x", "qty": 5, "audit_created_by": "someone"}])

    with pytest.raises(ValidationError):
        validate_rows(_table(), df)


def test_empty_dataframe_returns_no_rows() -> None:
    assert validate_rows(_table(), pd.DataFrame()) == []
