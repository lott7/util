from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from util.env import ENV_PATH  # noqa: F401  (imported for its .env-loading side effect)

# Connection config lives outside the repo, so no server/database
# details (or credentials, if a non-trusted connection is ever needed) are
# committed to source control. The path itself comes from util/.env's
# DB_CONNECTION_CONFIG_PATH.
DEFAULT_CONNECTION_CONFIG_PATH = Path(
    os.environ.get("DB_CONNECTION_CONFIG_PATH", default="")
)


def load_connection_config(path: Path | None = None) -> dict[str, Any]:
    """Load DB connection settings from a JSON file under DB_CONNECTION_CONFIG_PATH.

    Expected keys: driver, server, database, trusted_connection
    (plus username/password if trusted_connection is false).
    Optional key: trust_server_certificate (default True) — ODBC Driver 18+
    encrypts connections by default and rejects self-signed/untrusted
    certificates, which a local SQL Server Express instance typically has;
    this bypasses that check for such local/dev instances.
    """
    config_path = path or DEFAULT_CONNECTION_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(
            f"Database connection config not found at {config_path}. "
            "Create it with keys: driver, server, database, trusted_connection "
            "(and username/password if not using a trusted connection)."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_connection_url(config: dict[str, Any]) -> str:
    driver = config["driver"].replace(" ", "+")
    server = config["server"]
    database = config["database"]
    trust_cert = "yes" if config.get("trust_server_certificate", True) else "no"
    if config.get("trusted_connection", True):
        return (
            f"mssql+pyodbc://@{server}/{database}?trusted_connection=yes"
            f"&driver={driver}&TrustServerCertificate={trust_cert}"
        )
    username = config["username"]
    password = config["password"]
    return (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}"
        f"?driver={driver}&TrustServerCertificate={trust_cert}"
    )


def get_engine(path: Path | None = None) -> Engine:
    """Build a SQLAlchemy Engine from the DB_CONNECTION_CONFIG_PATH connection config.

    `fast_executemany=True` batches parameter arrays into a single ODBC
    call for executemany-style statements (e.g. the staging-table insert
    in TableType1.upsert), instead of pyodbc's default of one round trip
    per row — this is the difference between a multi-thousand-row upsert
    taking under a second vs. tens of seconds or more.
    """
    config = load_connection_config(path)
    return create_engine(build_connection_url(config), fast_executemany=True)
