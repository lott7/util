from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Table, func

AUDIT_COLUMN_PREFIX = "audit_"
AUDIT_COLUMNS = (
    "audit_created_at",
    "audit_created_by",
    "audit_updated_at",
    "audit_updated_by",
)


def add_audit_columns(table: Table) -> None:
    """Append the standard audit columns to a SQLAlchemy Core Table, in place.

    - audit_created_at / audit_created_by are set once, at insert time.
    - audit_updated_at / audit_updated_by stay NULL until a row's first
      real update.
    """
    table.append_column(
        Column("audit_created_at", DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    table.append_column(Column("audit_created_by", String(128), nullable=False))
    table.append_column(Column("audit_updated_at", DateTime(timezone=True), nullable=True))
    table.append_column(Column("audit_updated_by", String(128), nullable=True))
