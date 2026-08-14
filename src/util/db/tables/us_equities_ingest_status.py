from __future__ import annotations

from sqlalchemy import Column, Date, String

from ..base import BaseTable
from ..schemas.us_equities_ingest_status import us_equities_ingest_status_schema


class UsEquitiesIngestStatusTable(BaseTable):
    """Per-symbol ingest coverage summary for pulled EOD price ranges."""

    table_name = "us_equities_ingest_status"
    pk_columns = ("symbol", "exchange")
    validation_schema = us_equities_ingest_status_schema

    def _business_columns(self) -> list[Column]:
        return [
            Column("symbol", String(32), primary_key=True),
            Column("exchange", String(32), primary_key=True),
            Column("start_date", Date, nullable=False),
            Column("end_date", Date, nullable=False),
        ]
