import os
from pathlib import Path


def get_config() -> dict[str, object]:
    """Read configuration from environment variables without hardcoded business values."""
    db_path = Path(os.getenv("DATAOPS_DB_PATH", "data/generated/warehouse.duckdb"))
    period = os.getenv("DATAOPS_PERIOD", "2026-09")
    seed = int(os.getenv("DATAOPS_SEED", "42"))
    return {
        "db_path": str(db_path),
        "period": period,
        "seed": seed,
    }
