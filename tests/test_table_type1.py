from __future__ import annotations

import datetime as dt
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import Column, Float, MetaData, String, Table
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.dml import Insert

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


def _make_dated_table() -> Table:
    return Table(
        "prices",
        MetaData(),
        Column("symbol", String(10), primary_key=True),
        Column("date", String(10), primary_key=True),
        Column("price", Float, nullable=False),
    )


def _insert_calls(conn: MagicMock) -> list:
    return [
        call
        for call in conn.execute.call_args_list
        if call.args and isinstance(call.args[0], Insert)
    ]


def _rows_in_insert_call(call: object) -> int:
    insert_stmt = call.args[0]
    return len(insert_stmt._multi_values[0])


def _compiled_sql(stmt: object) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


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
    assert sum(_rows_in_insert_call(call) for call in insert_calls) == 5


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
    assert sum(_rows_in_insert_call(call) for call in insert_calls) == 1200


def test_upsert_is_a_no_op_for_an_empty_dataframe() -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    engine_instance.upsert(pd.DataFrame())

    engine.begin.assert_not_called()


def test_upsert_reuses_a_supplied_connection() -> None:
    engine, _conn = _make_engine_and_conn()
    supplied_connection = MagicMock()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    engine_instance.upsert(
        pd.DataFrame([{"symbol": "AAA", "price": 1.0}]), connection=supplied_connection
    )

    engine.begin.assert_not_called()
    assert supplied_connection.execute.call_count == 4


def test_upsert_sqlalchemy_failures_write_a_full_debug_dump(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))
    monkeypatch.setattr("util.db.table.EXTERNAL_LOG_ROOT", tmp_path)
    monkeypatch.setattr(
        engine_instance,
        "_run_upsert_statements",
        MagicMock(side_effect=SQLAlchemyError("boom")),
    )

    with pytest.raises(RuntimeError, match="Upsert failure dump:") as exc_info:
        engine_instance.upsert(pd.DataFrame([{"symbol": "AAA", "price": 1.25}]))

    dump_files = sorted((tmp_path / "util" / "upsert_failures").glob("*.json"))
    assert len(dump_files) == 1
    dump_payload = json.loads(dump_files[0].read_text(encoding="utf-8"))
    assert dump_payload["table"] == "t"
    assert dump_payload["row_count"] == 1
    assert dump_payload["normalized_rows"] == [{"symbol": "AAA", "price": 1.25}]


@patch("util.db.table.pd.read_sql")
def test_read_applies_limit(mock_read_sql: MagicMock) -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    engine_instance.read(limit=5)

    stmt = mock_read_sql.call_args.args[0]
    sql = _compiled_sql(stmt)
    assert "LIMIT 5" in sql


@patch("util.db.table.pd.read_sql")
def test_read_date_range_applies_inclusive_bounds_and_filters(mock_read_sql: MagicMock) -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(
        engine,
        table=_make_dated_table(),
        primary_keys=("symbol", "date"),
    )

    engine_instance.read_date_range(
        "date",
        start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 1, 31),
        filters={"symbol": ["AAA", "BBB"]},
        limit=10,
    )

    stmt = mock_read_sql.call_args.args[0]
    sql = _compiled_sql(stmt)
    assert "date >= '2026-01-01'" in sql
    assert "date <= '2026-01-31'" in sql
    assert "symbol IN ('AAA', 'BBB')" in sql
    assert "LIMIT 10" in sql


def test_read_date_range_rejects_unknown_columns() -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    with pytest.raises(ValueError, match="Unknown column 'date'"):
        engine_instance.read_date_range("date", start_date=dt.date(2026, 1, 1))


@patch("util.db.table.pd.read_sql")
def test_read_supports_equality_filters(mock_read_sql: MagicMock) -> None:
    engine, _conn = _make_engine_and_conn()
    engine_instance = TableType1(engine, table=_make_table(), primary_keys=("symbol",))

    engine_instance._read(filters={"symbol": "AAA"})

    stmt = mock_read_sql.call_args.args[0]
    sql = _compiled_sql(stmt)
    assert "symbol = 'AAA'" in sql
