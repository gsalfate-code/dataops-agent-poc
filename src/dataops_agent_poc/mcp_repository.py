from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


class PaymentRepository:
    """Read-only, fixed-query access to payment batch evidence."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path, read_only=True)

    def get_batch(self, period: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                  SELECT run_id, period, expected_count, raw_count,
                      (SELECT COUNT(*) FROM staging_payments s
                       WHERE s.period = metadata_runs.period) AS staging_count,
                      published_count,
                       rejected_count, status, raw_hash, rule_counts, created_at
                FROM metadata_runs
                WHERE period = ?
                ORDER BY run_id DESC
                LIMIT 1
                """,
                [period],
            ).fetchone()
        if row is None:
            return None
        result = dict(
            zip(
                (
                    "run_id",
                    "period",
                    "expected_count",
                    "raw_count",
                    "staging_count",
                    "published_count",
                    "rejected_count",
                    "status",
                    "raw_hash",
                    "rule_counts",
                    "created_at",
                ),
                row,
                strict=True,
            )
        )
        result["rule_counts"] = json.loads(result["rule_counts"])
        result["created_at"] = result["created_at"].isoformat()
        return result

    def layer_counts(self, period: str) -> dict[str, int]:
        queries = {
            "raw": "SELECT COUNT(*) FROM raw_payments WHERE period = ?",
            "staging": "SELECT COUNT(*) FROM staging_payments WHERE period = ?",
            "mart": "SELECT COUNT(*) FROM mart_payments WHERE period = ?",
            "quarantine": """
                SELECT COUNT(*) FROM quarantine_payments
                WHERE period = ?
            """,
        }
        with self._connect() as conn:
            return {
                layer: int(conn.execute(query, [period]).fetchone()[0])
                for layer, query in queries.items()
            }

    def rejection_reasons(self, period: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT rejection_code, rejection_reason, COUNT(*) AS count
                FROM quarantine_payments
                WHERE period = ?
                GROUP BY rejection_code, rejection_reason
                ORDER BY rejection_code
                """,
                [period],
            ).fetchall()
        return [
            {"code": row[0], "reason": row[1], "count": int(row[2])}
            for row in rows
        ]
