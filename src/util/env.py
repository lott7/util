"""Loads the central `.env` file (util repo root) into the process environment.

Central place for local, machine-specific paths (e.g. everything under
`.env`) so they're never hardcoded/committed in any repo's source —
`util`, `eodhd_client`, and `alpha_engine` all import this module (directly
or transitively) to pick up the same values.

`util/.env` itself is gitignored
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# util/src/util/env.py -> parents[2] is the util repo root.
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)
