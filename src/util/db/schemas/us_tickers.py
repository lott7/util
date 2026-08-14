from __future__ import annotations

import pandera.pandas as pa

# Explicit validation schema for the us_tickers table's business columns
# (no audit_* columns — those are system-managed and never caller-supplied).
# `delisted` mirrors EODHD's active/delisted flag: NULL means active,
# True means inactive/delisted.
us_tickers_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, nullable=False, coerce=True),
        "exchange": pa.Column(str, nullable=False, coerce=True),
        "name": pa.Column(str, nullable=False, coerce=True),
        "country": pa.Column(str, nullable=False, coerce=True),
        "currency": pa.Column(str, nullable=False, coerce=True),
        "type": pa.Column(str, nullable=False, coerce=True),
        "isin": pa.Column(str, nullable=True, coerce=True),
        "delisted": pa.Column(bool, nullable=True, coerce=True),
    },
    strict=True,
    coerce=True,
)
