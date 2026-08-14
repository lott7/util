from __future__ import annotations

import pandera.pandas as pa

us_equities_ingest_status_schema = pa.DataFrameSchema(
    {
        "symbol": pa.Column(str, nullable=False, coerce=True),
        "exchange": pa.Column(str, nullable=False, coerce=True),
        "start_date": pa.Column("datetime64[ns]", nullable=False, coerce=True),
        "end_date": pa.Column("datetime64[ns]", nullable=False, coerce=True),
    },
    strict=True,
    coerce=True,
)
