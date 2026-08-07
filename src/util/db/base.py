from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd
import pandera.pandas as pa
from sqlalchemy import Column, MetaData, Table
from sqlalchemy.engine import Engine

from .table import TableType1


class BaseTable:
    """Concrete base class for defining a database table.

    Not an interface/ABC — it is fully usable on its own (either directly,
    by passing table_name/pk_columns/columns to the constructor, or via a
    thin subclass that just sets class attributes). Standard behavior
    (read/upsert) already works out of the box and never needs to be
    redefined. Subclasses only need to override something when they want
    non-standard behavior, e.g.:
    - a different set of business columns (set `business_columns`, or
      override `_business_columns()` for columns that must be built
      dynamically)
    - an explicit pandera validation schema (set `validation_schema`,
      see `util.db.schemas`); if omitted, validation falls back to a
      schema auto-derived from the SQLAlchemy columns
    - a different upsert strategy (override `upsert_engine_cls` class
      attribute, or pass `upsert_engine_cls` to the constructor, e.g.
      `TableType2`); defaults to `TableType1`

    Knows nothing about audit columns — that's owned entirely by the
    upsert engine (default `TableType1`), so different tables can use
    different upsert strategies without changing this class.
    """

    table_name: str | None = None
    table_schema: str | None = None
    pk_columns: Sequence[str] = ()
    business_columns: Sequence[Column] = ()
    validation_schema: pa.DataFrameSchema | None = None
    upsert_engine_cls: type = TableType1

    def __init__(
        self,
        engine: Engine,
        table_name: str | None = None,
        schema: str | None = None,
        pk_columns: Sequence[str] | None = None,
        columns: Sequence[Column] | None = None,
        create_if_missing: bool = False,
        validation_schema: pa.DataFrameSchema | None = None,
        upsert_engine_cls: type | None = None,
    ) -> None:
        resolved_table_name = table_name or self.table_name
        if not resolved_table_name:
            raise ValueError(
                "table_name must be set (class attribute or constructor argument)"
            )

        resolved_pk_columns = (
            tuple(pk_columns) if pk_columns is not None else tuple(self.pk_columns)
        )
        if not resolved_pk_columns:
            raise ValueError(
                "pk_columns must be set (class attribute or constructor argument)"
            )

        resolved_columns = (
            list(columns) if columns is not None else list(self._business_columns())
        )
        if not resolved_columns:
            raise ValueError(
                "business columns must be set (business_columns attribute, "
                "_business_columns() override, or constructor argument)"
            )

        resolved_schema = schema if schema is not None else self.table_schema
        resolved_validation_schema = (
            validation_schema
            if validation_schema is not None
            else self.validation_schema
        )

        resolved_upsert_engine_cls = upsert_engine_cls or self.upsert_engine_cls

        metadata = MetaData(schema=resolved_schema)
        self.table = Table(
            resolved_table_name, metadata, *resolved_columns, schema=resolved_schema
        )
        self._engine = resolved_upsert_engine_cls(
            engine,
            table=self.table,
            primary_keys=resolved_pk_columns,
            create_if_missing=create_if_missing,
            validation_schema=resolved_validation_schema,
        )

    def _business_columns(self) -> list[Column]:
        """Return the table's real/business columns (no audit columns).

        Default implementation just returns `self.business_columns`.
        Override only if a subclass needs to build columns dynamically
        instead of declaring them as a class attribute.
        """
        return list(self.business_columns)

    def upsert(self, df: pd.DataFrame) -> None:
        return self._engine.upsert(df)

    def read(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._engine.read(limit)
