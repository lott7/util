from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import pandas as pd
import pandera.pandas as pa
from sqlalchemy import Column, Float, MetaData, Numeric, String, Table
from sqlalchemy.engine import Connection, Engine

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
    chunksize: int | None = None
    float_precision: int = 6
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
        chunksize: int | None = None,
        float_precision: int | None = None,
        upsert_engine_cls: type | None = None,
    ) -> None:
        resolved_table_name = table_name or self.table_name
        if not resolved_table_name:
            raise ValueError("table_name must be set (class attribute or constructor argument)")

        resolved_pk_columns = (
            tuple(pk_columns) if pk_columns is not None else tuple(self.pk_columns)
        )
        if not resolved_pk_columns:
            raise ValueError("pk_columns must be set (class attribute or constructor argument)")

        resolved_columns = list(columns) if columns is not None else list(self._business_columns())
        if not resolved_columns:
            raise ValueError(
                "business columns must be set (business_columns attribute, "
                "_business_columns() override, or constructor argument)"
            )

        resolved_schema = schema if schema is not None else self.table_schema
        resolved_validation_schema = (
            validation_schema if validation_schema is not None else self.validation_schema
        )
        resolved_chunksize = chunksize if chunksize is not None else self.chunksize
        resolved_float_precision = (
            float_precision if float_precision is not None else self.float_precision
        )

        resolved_upsert_engine_cls = upsert_engine_cls or self.upsert_engine_cls

        metadata = MetaData(schema=resolved_schema)
        self.table = Table(resolved_table_name, metadata, *resolved_columns, schema=resolved_schema)
        self.pk_columns = resolved_pk_columns
        self.chunksize = resolved_chunksize
        self.float_precision = resolved_float_precision
        self._engine = resolved_upsert_engine_cls(
            engine,
            table=self.table,
            primary_keys=resolved_pk_columns,
            create_if_missing=create_if_missing,
            chunksize=resolved_chunksize,
            validation_schema=resolved_validation_schema,
        )

    def _business_columns(self) -> list[Column]:
        """Return the table's real/business columns (no audit columns).

        Default implementation just returns `self.business_columns`.
        Override only if a subclass needs to build columns dynamically
        instead of declaring them as a class attribute.
        """
        return list(self.business_columns)

    def prepare_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize values before validation — never coerces types pandera already handles.

        Only value-level cleanup that pandera's `coerce=True` can't do on its
        own: strip/uppercase String PK columns, round Float/Numeric columns.
        Bad values still raise (no `errors="coerce"`), so malformed input
        fails here with a clear pandas error instead of silently turning
        into NULL/NaN before validation ever sees it.
        """
        if df.empty:
            return df.copy()

        prepared_df = df.copy()
        for column in self.table.columns:
            if column.name not in prepared_df.columns:
                continue
            if column.name.startswith("audit_"):
                continue

            if isinstance(column.type, String) and column.name in self.pk_columns:
                prepared_df[column.name] = prepared_df[column.name].map(
                    lambda value: value.strip().upper() if isinstance(value, str) else value
                )
            elif isinstance(column.type, (Float, Numeric)):
                # A column's own Numeric(precision, scale) is the source of
                # truth for its decimal places; float_precision is only a
                # fallback for plain Float columns, which carry no scale.
                scale = getattr(column.type, "scale", None)
                precision = scale if scale is not None else self.float_precision
                non_null = prepared_df[column.name].notna()
                prepared_df.loc[non_null, column.name] = pd.to_numeric(
                    prepared_df.loc[non_null, column.name]
                ).round(precision)
        return prepared_df

    def upsert(self, df: pd.DataFrame, connection: Connection | None = None) -> None:
        df = self.prepare_df(df)
        self._engine.upsert(df, connection=connection)

    def read(self, limit: int | None = None) -> pd.DataFrame:
        return cast(pd.DataFrame, self._engine.read(limit))

    def read_date_range(
        self,
        date_column: str,
        start_date: Any | None = None,
        end_date: Any | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        return cast(
            pd.DataFrame,
            self._engine.read_date_range(
                date_column,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
                limit=limit,
            ),
        )
