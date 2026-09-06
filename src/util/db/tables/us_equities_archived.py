from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, Numeric, String

from ..base import BaseTable
from ..schemas.us_equities_archived import us_equities_archived_schema

# Raw quotes never need more than cent-level precision; adjusted_close gets
# extra scale because cumulative split/dividend adjustment factors on
# long-lived, deeply-split symbols can produce many decimal digits.
_PRICE = Numeric(12, 4)
_ADJUSTED_PRICE = Numeric(18, 6)


class UsEquitiesArchivedTable(BaseTable):
    """First concrete table: daily equity OHLCV prices."""

    table_name = "us_equities_archived"
    pk_columns = ("symbol", "exchange", "date")
    validation_schema = us_equities_archived_schema

    def _business_columns(self) -> list[Column]:
        return [
            Column("symbol", String(32), nullable=False, primary_key=True),
            Column("exchange", String(32), nullable=False, primary_key=True),
            Column("date", Date, primary_key=True),
            Column("open", _PRICE, nullable=False),
            Column("high", _PRICE, nullable=False),
            Column("low", _PRICE, nullable=False),
            Column("close", _PRICE, nullable=False),
            Column("adjusted_close", _ADJUSTED_PRICE, nullable=False),
            Column("volume", BigInteger, nullable=False),
        ]
