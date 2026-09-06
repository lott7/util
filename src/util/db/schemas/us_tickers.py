from __future__ import annotations

import pandera.pandas as pa

# Explicit validation schema for the us_tickers table's business columns
# (no audit_* columns — those are system-managed and never caller-supplied).
# `delisted` mirrors EODHD's active/delisted flag: NULL means active,
# True means inactive/delisted.
us_tickers_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, coerce=True),
        "exchange": pa.Column(str, coerce=True),
        "name": pa.Column(str, coerce=True),
        "country": pa.Column(str, coerce=True),
        "currency": pa.Column(str, coerce=True),
        "type": pa.Column(str, coerce=True),
        "isin": pa.Column(str, nullable=True, coerce=True),
        "delisted": pa.Column(bool, coerce=True),
        "archived": pa.Column(bool, coerce=True),
    },
    strict=True,
    coerce=True,
)
