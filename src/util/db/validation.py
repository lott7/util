from __future__ import annotations

from typing import Any, cast

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Table
from sqlalchemy.types import TypeEngine

from .schema import AUDIT_COLUMNS

# Ordered so more specific SQLAlchemy types are matched before their bases.
_SQLALCHEMY_TO_PANDERA: list[tuple] = [
    (Boolean, bool),
    (Integer, "Int64"),
    (Numeric, float),
    (Float, float),
    (DateTime, "datetime64[ns]"),
    (Date, "datetime64[ns]"),
    (String, str),
]


class ValidationError(ValueError):
    """Raised when row data does not match the target table's schema."""


def _pandera_dtype(sa_type: TypeEngine) -> Any:
    for sa_cls, pandera_dtype in _SQLALCHEMY_TO_PANDERA:
        if isinstance(sa_type, sa_cls):
            return pandera_dtype
    return object


def _build_schema(table: Table) -> pa.DataFrameSchema:
    """Build a pandera schema from a table's business columns.

    audit_* columns are intentionally excluded — they're system-managed by
    the upsert engine and must never be caller-supplied. Because the
    schema is `strict=True`, supplying an audit_* (or any other unknown)
    column raises a validation error.
    """
    columns: dict[str, pa.Column] = {}
    for column in table.columns:
        if column.name in AUDIT_COLUMNS:
            continue
        is_nullable = bool(column.nullable)
        required = not is_nullable and column.default is None and column.server_default is None
        columns[column.name] = pa.Column(
            _pandera_dtype(column.type),
            nullable=is_nullable,
            required=required,
            coerce=True,
        )
    return pa.DataFrameSchema(columns, strict=True, coerce=True)


def validate_rows(
    table: Table,
    df: pd.DataFrame,
    schema: pa.DataFrameSchema | None = None,
) -> list[dict[str, Any]]:
    """Validate a DataFrame of rows against a table's columns, using pandera.

    `schema` is an optional explicit pandera `DataFrameSchema` (see
    `util.db.schemas`); if omitted, a schema is auto-derived from the
    SQLAlchemy Table's columns instead.

    - Rejects unknown columns (pandera `strict=True`).
    - Rejects any caller-supplied audit_* column (excluded from an
      auto-derived schema, so they're treated as unknown columns).
    - Rejects rows missing a required (non-nullable, no default) column,
      excluding audit_* columns.
    """
    if df.empty:
        return []
    df = df.copy()

    if schema is None:
        schema = _build_schema(table)

    try:
        validated_df = schema.validate(df, lazy=True)
    except SchemaErrors as exc:
        raise ValidationError(
            f"Row validation failed for table {table.name!r}:\n{exc.failure_cases}"
        ) from exc

    validated_df = validated_df.astype(object).where(pd.notnull(validated_df), None)
    return cast(list[dict[str, Any]], validated_df.to_dict(orient="records"))
