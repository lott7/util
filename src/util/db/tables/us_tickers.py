from __future__ import annotations

from sqlalchemy import Boolean, Column, String

from ..base import BaseTable
from ..schemas.us_tickers import us_tickers_schema


class UsTickersTable(BaseTable):
    """Curated NYSE/NASDAQ ticker universe.

    Populated by eodhd_client's periodic ticker-list sync. The `delisted`
    column records whether EODHD marks the ticker inactive; active rows
    keep it NULL so the ingest pipeline can treat NULL as "still active".
    """

    table_name = "us_tickers"
    pk_columns = ("symbol", "exchange")
    validation_schema = us_tickers_schema

    def _business_columns(self) -> list[Column]:
        return [
            Column("symbol", String(32), primary_key=True),
            Column("exchange", String(32), primary_key=True),
            Column("name", String(255), nullable=False),
            Column("country", String(64), nullable=False),
            Column("currency", String(16), nullable=False),
            Column("type", String(64), nullable=False),
            Column("isin", String(32), nullable=True),
            Column("delisted", Boolean, nullable=True),
        ]
