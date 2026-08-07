# util

A small utility repository for database helpers.

## Package layout

- `src/util/`: top-level package source
- `src/util/db/`: database utilities
- `src/util/db/schema.py`: shared `audit_*` column helpers (`audit_created_at`, `audit_created_by`, `audit_updated_at`, `audit_updated_by`)
- `src/util/db/validation.py`: DataFrame validation against a table's columns, powered by [pandera](https://pandera.readthedocs.io/) (`DataFrameSchema`, `strict=True`) — rejects unknown columns, caller-supplied `audit_*` columns, and missing required columns. Uses an explicit `DataFrameSchema` if the table provides one (see `src/util/db/schemas/`), otherwise auto-derives one from the SQLAlchemy columns
- `src/util/db/table.py`: `TableType1`, the standard upsert engine — accepts a `pandas.DataFrame` only (bulk upserts), adds audit columns, and performs the upsert via a temporary staging table + a single `MERGE` statement (created and dropped per call)
- `src/util/db/base.py`: `BaseTable`, a reusable base class for defining a table's name/schema/primary keys/business columns/validation schema; delegates `upsert`/`read` to a pluggable engine (default `TableType1`)
- `src/util/db/tables/`: concrete `BaseTable` subclasses (one module per table), e.g. `src/util/db/tables/us_equities.py` defines `UsEquitiesTable`
- `src/util/db/schemas/`: explicit pandera `DataFrameSchema` definitions, one per table, e.g. `src/util/db/schemas/us_equities.py` defines `us_equities_schema` — set as a table's `validation_schema` to override the auto-derived schema
- `src/util/db/connection.py`: builds a SQLAlchemy engine (with `fast_executemany=True` for bulk inserts) from connection config stored outside the repo, at `DB_CONNECTION_CONFIG_PATH`

Audit columns: `audit_created_at`/`audit_created_by` are set once at insert time; `audit_updated_at`/`audit_updated_by` stay `NULL` until a row's first real update.

## Example

```python
import pandas as pd

from util.db import UsEquitiesTable
from util.db.connection import get_engine

engine = get_engine()
table = UsEquitiesTable(engine, schema=None, create_if_missing=True)

df = pd.DataFrame(
    [
        {
            "symbol": "AAPL",
            "trade_date": "2026-07-15",
            "open": 193.50,
            "high": 196.00,
            "low": 193.10,
            "close": 195.12,
            "adjusted_close": 195.12,
            "volume": 52_314_000,
        },
    ]
)
table.upsert(df)
```

## Connection config

Server/database/driver settings (and credentials, if not using a trusted connection) are kept out of the repo in `DB_CONNECTION_CONFIG_PATH`:

```json
{
  "driver": "<ODBC driver name, e.g. ODBC Driver 18 for SQL Server>",
  "server": "<server[\\instance]>",
  "database": "<database name>",
  "trusted_connection": true
}
```

The path to that file (and other local `DB_CONNECTION_CONFIG_PATH` paths used across this workspace, e.g. `eodhd_client`'s API
token config) is itself centralized in `util/.env` (gitignored — copy `util/.env.example` to get started), loaded
automatically via `util.env`. Override the default path by setting `DB_CONNECTION_CONFIG_PATH` there.

> Use the `src` layout when installing with `pip install -e .` or building the package.
