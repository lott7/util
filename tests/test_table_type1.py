from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import Column, Float, MetaData, String, Table

from util.db.table import TableType1
from util.db.validation import ValidationError


def _make_engine_and_conn() -> tuple[MagicMock, MagicMock]:
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    return engine, conn


def _make_table() -> Table:
    return Table(
        "t",
        MetaData(),
        Column("symbol", String(10), primary_key=True),
        Column("price", Float, nullable=False),
    )


def _insert_calls(conn: MagicMock) -> list:
    return [
        call
        for call in conn.execute.call_args_list
        if len(call.args) > 1 and isinstance(call.args[1], list)
    ]


def test_duplicate_pk_raises_before_touching_the_engine() -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))
    df = pd.DataFrame([{"symbol": "AAA", "price": 1.0}, {"symbol": "AAA", "price": 2.0}])

    with pytest.raises(ValidationError):
        engine_instance.upsert(df)
    engine.begin.assert_not_called()


def test_upsert_batches_inserts_by_chunksize() -> None:
    engine, conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",), chunksize=2)
    df = pd.DataFrame([{"symbol": f"S{i}", "price": 1.0} for i in range(5)])

    engine_instance.upsert(df)

    insert_calls = _insert_calls(conn)
    assert len(insert_calls) == 3  # ceil(5 / 2)
    assert sum(len(call.args[1]) for call in insert_calls) == 5


def test_upsert_logs_row_count_and_target_table(caplog: pytest.LogCaptureFixture) -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))
    df = pd.DataFrame([{"symbol": "AAA", "price": 1.0}, {"symbol": "BBB", "price": 2.0}])

    with caplog.at_level("INFO", logger="util"):
        engine_instance.upsert(df)

    assert any(
        record.levelname == "INFO"
        and record.name == "util"
        and "Upserted 2 row(s) into [t]" in record.message
        for record in caplog.records
    )


def test_chunksize_is_clamped_to_the_sql_server_parameter_limit() -> None:
    engine, conn = _make_engine_and_conn()
    # 2 business columns -> max rows per batch is (2100 // 2) - 1 = 1049.
    engine_instance = TableType1(
        engine, table=_make_table(), primary_keys=("symbol",), chunksize=5000
    )
    df = pd.DataFrame([{"symbol": f"S{i}", "price": 1.0} for i in range(1200)])

    engine_instance.upsert(df)

    insert_calls = _insert_calls(conn)
    assert len(insert_calls) == 2
    assert sum(len(call.args[1]) for call in insert_calls) == 1200


def test_upsert_is_a_no_op_for_an_empty_dataframe() -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    engine_instance.upsert(pd.DataFrame())

    engine.begin.assert_not_called()
