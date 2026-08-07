from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, Float, String

from ..base import BaseTable
from ..schemas.us_equities import us_equities_schema


class UsEquitiesTable(BaseTable):
    """First concrete table: daily equity OHLCV prices."""

    table_name = "us_equities"
    pk_columns = ("symbol", "trade_date")
    validation_schema = us_equities_schema

    def _business_columns(self) -> list[Column]:
        return [
            Column("symbol", String(32), primary_key=True),
            Column("trade_date", Date, primary_key=True),
            Column("open", Float, nullable=False),
            Column("high", Float, nullable=False),
            Column("low", Float, nullable=False),
            Column("close", Float, nullable=False),
            Column("adjusted_close", Float, nullable=False),
            Column("volume", BigInteger, nullable=False),
        ]
