from __future__ import annotations

from sqlalchemy import Boolean, Column, String

from ..base import BaseTable
from ..schemas.us_tickers import us_tickers_schema


class UsTickersTable(BaseTable):
    """Curated NYSE/NASDAQ ticker universe.

    Populated by eodhd_client's periodic ticker-list sync; the `selected`
    column is a manual-curation flag the user edits directly via SQL to
    mark which symbols should actually be tracked by the EOD price ingest
    pipeline. Re-syncing must preserve existing `selected` values.
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
            Column("selected", Boolean, nullable=False, default=False),
        ]
