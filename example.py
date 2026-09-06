# Connection config (server, database, driver, credentials if not using
# integrated auth) lives outside the repo at DB_CONNECTION_CONFIG_PATH,
# never committed to source control.
import pandas as pd

from util.db import UsEquitiesTable, get_engine


def main() -> None:
    engine = get_engine()
    table = UsEquitiesTable(engine, schema=None, create_if_missing=True)

    df = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "date": "2026-07-15",
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
    print("Upsert completed")

    data_df = table.read(limit=5)
    print("Read rows (DataFrame):", data_df)


if __name__ == "__main__":
    main()
