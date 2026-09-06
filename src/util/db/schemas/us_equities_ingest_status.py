from __future__ import annotations

import pandera.pandas as pa

us_equities_ingest_status_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, coerce=True),
        "exchange": pa.Column(str, coerce=True),
        "start_date": pa.Column("datetime64[ns]", coerce=True),
        "end_date": pa.Column("datetime64[ns]", coerce=True),
        "delisted": pa.Column(bool, coerce=True),
    },
    strict=True,
    coerce=True,
)
