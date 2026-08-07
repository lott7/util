from __future__ import annotations

import pandera.pandas as pa

# Explicit validation schema for the us_tickers table's business columns
# (no audit_* columns — those are system-managed and never caller-supplied).
# `selected` is the manual-curation flag: eodhd_client.tickers.sync_tickers
# preserves existing values across re-syncs instead of overwriting them.
us_tickers_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, nullable=False, coerce=True),
        "exchange": pa.Column(str, nullable=False, coerce=True),
        "name": pa.Column(str, nullable=False, coerce=True),
        "country": pa.Column(str, nullable=False, coerce=True),
        "currency": pa.Column(str, nullable=False, coerce=True),
        "type": pa.Column(str, nullable=False, coerce=True),
        "isin": pa.Column(str, nullable=True, coerce=True),
        "selected": pa.Column(bool, nullable=False, coerce=True),
    },
    strict=True,
    coerce=True,
)
