import os
from pathlib import Path


def get_config() -> dict[str, object]:
    """Read configuration from environment variables without hardcoded business values."""
    db_path = Path(os.getenv("DATAOPS_DB_PATH", "data/generated/warehouse.duckdb"))
    audit_path = Path(os.getenv("DATAOPS_AUDIT_PATH", "evidence/generated/mcp_audit.jsonl"))
    period = os.getenv("DATAOPS_PERIOD", "2026-09")
    seed = int(os.getenv("DATAOPS_SEED", "42"))
    return {
        "db_path": str(db_path),
        "audit_path": str(audit_path),
        "period": period,
        "seed": seed,
    }
