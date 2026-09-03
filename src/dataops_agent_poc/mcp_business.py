from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dataops_agent_poc.config import get_config
from dataops_agent_poc.mcp_repository import PaymentRepository


def validate_period(period: str) -> str:
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:].isdigit():
        raise ValueError("period must use YYYY-MM format")
    year = int(period[:4])
    month = int(period[5:])
    if year < 1 or month < 1 or month > 12:
        raise ValueError("period must contain a real calendar month")
    return period


def _repository() -> PaymentRepository:
    return PaymentRepository(str(get_config()["db_path"]))


def _audit(tool: str, period: str, result: str, duration_ms: float) -> None:
    audit_path = Path(str(get_config()["audit_path"]))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": tool,
        "period": period,
        "result": result,
        "duration_ms": round(duration_ms, 3),
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def _run_audited[T](tool: str, period: str, operation: Callable[[], T]) -> T:
    started = time.perf_counter()
    try:
        result = operation()
    except Exception as error:
        _audit(
            tool,
            period,
            f"error:{type(error).__name__}",
            (time.perf_counter() - started) * 1000,
        )
        raise
    _audit(tool, period, "ok", (time.perf_counter() - started) * 1000)
    return result


def _validate_for_tool(tool: str, period: str) -> None:
    try:
        validate_period(period)
    except Exception as error:
        _audit(tool, period, f"error:{type(error).__name__}", 0.0)
        raise


def get_payment_batch(period: str) -> dict[str, Any]:
    _validate_for_tool("get_payment_batch", period)

    def operation() -> dict[str, Any]:
        batch = _repository().get_batch(period)
        if batch is None:
            raise ValueError(f"no payment batch found for period {period}")
        return batch

    return _run_audited("get_payment_batch", period, operation)


def reconcile_payment_layers(period: str) -> dict[str, Any]:
    _validate_for_tool("reconcile_payment_layers", period)

    def operation() -> dict[str, Any]:
        repository = _repository()
        batch = repository.get_batch(period)
        if batch is None:
            raise ValueError(f"no payment batch found for period {period}")
        counts = repository.layer_counts(period)
        checks = {
            "expected_equals_raw": counts["raw"] == batch["expected_count"],
            "raw_equals_staging": counts["raw"] == counts["staging"],
            "staging_equals_mart_plus_quarantine": counts["staging"]
            == counts["mart"] + counts["quarantine"],
        }
        differences = [
            ("expected_vs_raw", batch["expected_count"] - counts["raw"]),
            ("raw_vs_staging", counts["raw"] - counts["staging"]),
            (
                "staging_vs_mart_plus_quarantine",
                counts["staging"] - counts["mart"] - counts["quarantine"],
            ),
        ]
        first_difference = next(
            {"check": name, "magnitude": magnitude}
            for name, magnitude in differences
            if magnitude != 0
        ) if any(magnitude != 0 for _, magnitude in differences) else None
        return {
            "period": period,
            "counts": counts,
            "checks": checks,
            "first_difference": first_difference,
        }

    return _run_audited("reconcile_payment_layers", period, operation)


def get_rejection_reasons(period: str) -> dict[str, Any]:
    _validate_for_tool("get_rejection_reasons", period)

    def operation() -> dict[str, Any]:
        reasons = _repository().rejection_reasons(period)
        return {
            "period": period,
            "reasons": reasons,
            "total_rejected": sum(item["count"] for item in reasons),
        }

    return _run_audited("get_rejection_reasons", period, operation)
