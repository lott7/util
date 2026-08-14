from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, Table

from util.db.schema import AUDIT_COLUMNS, add_audit_columns


def _bare_table() -> Table:
    return Table("t", MetaData(), Column("id", Integer, primary_key=True))


def test_add_audit_columns_appends_all_four() -> None:
    table = _bare_table()
    add_audit_columns(table)

    assert set(AUDIT_COLUMNS) <= set(table.columns.keys())


def test_created_columns_are_not_nullable() -> None:
    table = _bare_table()
    add_audit_columns(table)

    assert table.c.audit_created_at.nullable is False
    assert table.c.audit_created_by.nullable is False


def test_updated_columns_are_nullable() -> None:
    table = _bare_table()
    add_audit_columns(table)

    assert table.c.audit_updated_at.nullable is True
    assert table.c.audit_updated_by.nullable is True
