from __future__ import annotations

import pandera.pandas as pa

# Explicit validation schema for the us_equities table's business columns
# (no audit_* columns — those are system-managed and never caller-supplied).
# Passed to UsEquitiesTable as `validation_schema`; if a table doesn't
# define one, validation.py falls back to auto-deriving a schema from the
# SQLAlchemy Table's columns instead.
us_equities_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, nullable=False, coerce=True),
        "trade_date": pa.Column("datetime64[ns]", nullable=False, coerce=True),
        "open": pa.Column(float, nullable=False, coerce=True),
        "high": pa.Column(float, nullable=False, coerce=True),
        "low": pa.Column(float, nullable=False, coerce=True),
        "close": pa.Column(float, nullable=False, coerce=True),
        "adjusted_close": pa.Column(float, nullable=False, coerce=True),
        "volume": pa.Column(int, nullable=False, coerce=True),
    },
    strict=True,
    coerce=True,
)
