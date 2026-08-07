from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = Path("logs")


def build_logging_config(
    app_name: str,
    log_dir: Path | str = DEFAULT_LOG_DIR,
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> dict[str, Any]:
    """Build a `logging.config.dictConfig`-compatible dict for `app_name`.

    Each repo should pass its own `app_name` (e.g. "etf_rep_strat") so it
    gets its own rotating log file (`<log_dir>/<app_name>.log`), isolated
    from other repos' logging. `log_dir` is typically an absolute path
    inside the calling repo (e.g. `<repo_root>/logs`) so log files land
    next to that repo's code rather than wherever the process happened
    to be launched from.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"{app_name}.log"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "level": level,
                "filename": str(log_file),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            app_name: {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
        },
    }


def configure_logging(
    app_name: str,
    log_dir: Path | str = DEFAULT_LOG_DIR,
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> logging.Logger:
    """Apply a dictConfig-based logging setup for `app_name` and return its logger.

    Example (called once from a repo's own config module):

        logger = configure_logging("etf_rep_strat", log_dir=REPO_ROOT / "logs")
        logger.info("started")
    """
    config = build_logging_config(app_name, log_dir, level, max_bytes, backup_count)
    logging.config.dictConfig(config)
    return logging.getLogger(app_name)
