from __future__ import annotations

import datetime as dt
import getpass
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pandas as pd
import pandera.pandas as pa
from sqlalchemy import Column, MetaData, Table, insert, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable, DropTable

from .schema import AUDIT_COLUMNS, add_audit_columns
from .validation import ValidationError, validate_rows


class TableType1:
    """Standard upsert engine.

    Owns all audit-column mechanics: extends a bare business-columns-only
    Table with the audit_* columns, and performs a bulk upsert via a
    session-scoped SQL Server temporary staging table + a single MERGE
    statement, dropping the temp table again once the merge is done.
    """

    def __init__(
        self,
        engine: Engine,
        table: Table,
        primary_keys: Sequence[str],
        create_if_missing: bool = False,
        chunksize: int | None = None,
        validation_schema: pa.DataFrameSchema | None = None,
    ) -> None:
        self.engine = engine
        self.table = table
        add_audit_columns(self.table)
        self.primary_keys = tuple(primary_keys)
        self.chunksize = chunksize
        self.validation_schema = validation_schema
        if create_if_missing:
            self.table.metadata.create_all(self.engine, checkfirst=True, tables=[self.table])

    def read(self, limit: int | None = None) -> pd.DataFrame:
        stmt = select(self.table)
        if limit is not None:
            stmt = stmt.limit(limit)
        return pd.read_sql(stmt, self.engine)

    def upsert(self, df: pd.DataFrame) -> None:
        """Bulk-upsert a DataFrame of rows into the table.

        Raises ValidationError if the batch contains duplicate primary-key
        values (the underlying MERGE would otherwise fail, or silently
        pick an arbitrary row, since the target table has no PK/unique
        constraint enforcing this at the database level).
        """
        rows_list = validate_rows(self.table, df, schema=self.validation_schema)
        if not rows_list:
            return

        pk_columns = list(self.primary_keys)

        duplicate_mask = df.duplicated(subset=pk_columns, keep=False)
        if duplicate_mask.any():
            duplicate_keys = (
                df.loc[duplicate_mask, pk_columns].drop_duplicates().to_dict(orient="records")
            )
            raise ValidationError(
                f"Duplicate primary key value(s) {duplicate_keys} for table {self.table.name!r} "
                f"(primary keys: {pk_columns}) in the DataFrame passed to upsert()."
            )

        user = getpass.getuser()
        now = dt.datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0)

        business_columns = [c for c in self.table.columns if c.name not in AUDIT_COLUMNS]
        update_columns = [c.name for c in business_columns if c.name not in pk_columns]
        num_columns = len(business_columns)
        max_by_params = max(1, (2100 // num_columns) - 1)
        if self.chunksize is None:
            effective_chunksize = min(1000, max_by_params)
        else:
            effective_chunksize = min(max(1, self.chunksize), max_by_params)

        # Normalize so every row has the same keys (required for a single
        # batched executemany insert into the staging table).
        normalized_rows = [{c.name: row.get(c.name) for c in business_columns} for row in rows_list]

        temp_table_name = f"#upsert_{self.table.name}"
        temp_table = Table(
            temp_table_name,
            MetaData(),
            *[Column(c.name, c.type) for c in business_columns],
        )

        try:
            with self.engine.begin() as conn:
                conn.execute(CreateTable(temp_table))
                for start in range(0, len(normalized_rows), effective_chunksize):
                    conn.execute(
                        insert(temp_table),
                        normalized_rows[start : start + effective_chunksize],
                    )
                conn.execute(
                    text(self._merge_sql(temp_table_name, pk_columns, update_columns)),
                    {
                        "audit_created_at": now,
                        "audit_created_by": user,
                        "audit_updated_at": now,
                        "audit_updated_by": user,
                    },
                )
                conn.execute(DropTable(temp_table, if_exists=True))
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Upsert failed for table {self.table.name!r}: {exc}") from exc

    def _qualified_name(self) -> str:
        if self.table.schema:
            return f"[{self.table.schema}].[{self.table.name}]"
        return f"[{self.table.name}]"

    def _merge_sql(
        self,
        temp_table_name: str,
        pk_columns: Sequence[str],
        update_columns: Sequence[str],
    ) -> str:
        target = self._qualified_name()
        source = f"[{temp_table_name}]"
        on_clause = " AND ".join(f"target.[{c}] = source.[{c}]" for c in pk_columns)

        set_parts = [f"target.[{c}] = source.[{c}]" for c in update_columns]
        set_parts.append("target.[audit_updated_at] = :audit_updated_at")
        set_parts.append("target.[audit_updated_by] = :audit_updated_by")
        set_clause = ", ".join(set_parts)

        insert_columns = list(pk_columns) + list(update_columns)
        insert_col_list = (
            ", ".join(f"[{c}]" for c in insert_columns) + ", [audit_created_at], [audit_created_by]"
        )
        insert_val_list = (
            ", ".join(f"source.[{c}]" for c in insert_columns)
            + ", :audit_created_at, :audit_created_by"
        )

        return (
            f"MERGE {target} AS target "
            f"USING {source} AS source "
            f"ON {on_clause} "
            f"WHEN MATCHED THEN UPDATE SET {set_clause} "
            f"WHEN NOT MATCHED THEN INSERT ({insert_col_list}) VALUES ({insert_val_list});"
        )


class TableType2:
    """Placeholder for an alternative upsert engine strategy.

    Not implemented yet; exists so callers can already wire up code
    against this class ahead of the real implementation.
    """

    def __init__(
        self,
        engine: Engine,
        table: Table,
        primary_keys: Sequence[str],
        create_if_missing: bool = False,
        chunksize: int | None = None,
        validation_schema: pa.DataFrameSchema | None = None,
    ) -> None:
        raise NotImplementedError

    def read(self, limit: int | None = None) -> pd.DataFrame:
        raise NotImplementedError

    def upsert(self, df: pd.DataFrame) -> None:
        raise NotImplementedError
