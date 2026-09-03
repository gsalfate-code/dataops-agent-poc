from __future__ import annotations

import csv
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from dataops_agent_poc.config import get_config
from dataops_agent_poc.generation import (
    EXPECTED_COUNT,
    INVALID_AMOUNT_COUNT,
    INVALID_MISSING_PERSON_COUNT,
    compute_raw_hash,
    generate_raw_rows,
)
from dataops_agent_poc.quality import classify_rows

PUBLISHED_COUNT = 9_880
REJECTED_COUNT = 120


def _ensure_dirs(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS person_master (
            person_id BIGINT PRIMARY KEY,
            person_name VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_payments (
            payment_id VARCHAR PRIMARY KEY,
            period VARCHAR,
            person_id BIGINT,
            amount DOUBLE,
            source_row_id BIGINT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_payments (
            payment_id VARCHAR PRIMARY KEY,
            period VARCHAR,
            person_id BIGINT,
            amount DOUBLE,
            source_row_id BIGINT,
            validation_status VARCHAR,
            rejection_code VARCHAR,
            rejection_reason VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quarantine_payments (
            payment_id VARCHAR PRIMARY KEY,
            period VARCHAR,
            person_id BIGINT,
            amount DOUBLE,
            source_row_id BIGINT,
            rejection_code VARCHAR,
            rejection_reason VARCHAR,
            run_id VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mart_payments (
            payment_id VARCHAR PRIMARY KEY,
            period VARCHAR,
            person_id BIGINT,
            amount DOUBLE,
            source_row_id BIGINT,
            run_id VARCHAR
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata_runs (
            run_id VARCHAR PRIMARY KEY,
            period VARCHAR,
            expected_count BIGINT,
            raw_count BIGINT,
            published_count BIGINT,
            rejected_count BIGINT,
            status VARCHAR,
            raw_hash VARCHAR,
            rule_counts JSON,
            created_at TIMESTAMP
        )
        """
    )


def _classify_rows(
    conn: duckdb.DuckDBPyConnection,
    raw_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    valid_person_ids = {
        row[0]
        for row in conn.execute("SELECT person_id FROM person_master").fetchall()
    }
    return classify_rows(raw_rows, valid_person_ids)


def _copy_csv_rows(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    rows: list[tuple[Any, ...]],
) -> None:
    path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            suffix=".csv",
            delete=False,
        ) as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
            path = handle.name
        conn.execute(f"COPY {table_name} FROM '{path}' (FORMAT CSV, HEADER FALSE)")
    finally:
        if path is not None:
            Path(path).unlink(missing_ok=True)


def _persist_person_master(conn: duckdb.DuckDBPyConnection) -> None:
    if conn.execute("SELECT COUNT(*) FROM person_master").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO person_master VALUES (?, ?)",
            [(person_id, f"Person {person_id:04d}") for person_id in range(1, 1001)],
        )


def _persist_raw_if_needed(
    conn: duckdb.DuckDBPyConnection,
    period: str,
    raw_rows: list[dict[str, Any]],
) -> str:
    raw_count = conn.execute(
        "SELECT COUNT(*) FROM raw_payments WHERE period = ?",
        [period],
    ).fetchone()[0]
    if raw_count == 0:
        _copy_csv_rows(
            conn,
            "raw_payments",
            [
                (
                    row["payment_id"],
                    row["period"],
                    row["person_id"],
                    row["amount"],
                    row["source_row_id"],
                )
                for row in raw_rows
            ],
        )
        return compute_raw_hash(raw_rows)

    current_hash = conn.execute(
        "SELECT raw_hash FROM metadata_runs WHERE period = ? ORDER BY run_id DESC LIMIT 1",
        [period],
    ).fetchone()
    expected_hash = compute_raw_hash(raw_rows)
    if current_hash is not None:
        existing_hash = current_hash[0]
        if existing_hash != expected_hash:
            raise ValueError(
                "RAW layer is immutable and differs from the expected deterministic input."
            )
        return expected_hash

    current_rows = conn.execute(
        """
        SELECT payment_id, period, person_id, amount, source_row_id
        FROM raw_payments
        WHERE period = ?
        ORDER BY source_row_id
        """,
        [period],
    ).fetchall()
    existing_hash = compute_raw_hash(
        [
            {
                "payment_id": row[0],
                "period": row[1],
                "person_id": row[2],
                "amount": float(row[3]),
                "source_row_id": row[4],
            }
            for row in current_rows
        ]
    )
    if existing_hash != expected_hash:
        raise ValueError(
            "RAW layer is immutable and differs from the expected deterministic input."
        )
    return expected_hash


def _persist_run_results(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    period: str,
    classified_rows: list[dict[str, Any]],
    rule_counts: dict[str, int],
    raw_hash: str,
) -> dict[str, Any]:
    conn.execute("DELETE FROM staging_payments WHERE period = ?", [period])
    conn.execute("DELETE FROM quarantine_payments WHERE run_id = ?", [run_id])
    conn.execute("DELETE FROM mart_payments WHERE run_id = ?", [run_id])

    _copy_csv_rows(
        conn,
        "staging_payments",
        [
            (
                row["payment_id"],
                row["period"],
                row["person_id"],
                row["amount"],
                row["source_row_id"],
                row["validation_status"],
                row["rejection_code"],
                row["rejection_reason"],
            )
            for row in classified_rows
        ],
    )
    conn.execute(
        """
        INSERT INTO quarantine_payments
        SELECT payment_id, period, person_id, amount, source_row_id,
               rejection_code, rejection_reason, ?
        FROM staging_payments
        WHERE period = ? AND validation_status = 'REJECTED'
        """,
        [run_id, period],
    )
    conn.execute(
        """
        INSERT INTO mart_payments
        SELECT payment_id, period, person_id, amount, source_row_id, ?
        FROM staging_payments
        WHERE period = ? AND validation_status = 'VALID'
        """,
        [run_id, period],
    )

    published_count = conn.execute(
        "SELECT COUNT(*) FROM mart_payments WHERE run_id = ?", [run_id]
    ).fetchone()[0]
    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM quarantine_payments WHERE run_id = ?", [run_id]
    ).fetchone()[0]
    status = (
        "PUBLISHED_WITH_REJECTIONS"
        if published_count == PUBLISHED_COUNT and rejected_count == REJECTED_COUNT
        else "REJECTED"
    )
    existing_created_at = conn.execute(
        "SELECT created_at FROM metadata_runs WHERE run_id = ?", [run_id]
    ).fetchone()

    metadata = {
        "run_id": run_id,
        "period": period,
        "expected_count": EXPECTED_COUNT,
        "raw_count": EXPECTED_COUNT,
        "published_count": published_count,
        "rejected_count": rejected_count,
        "status": status,
        "raw_hash": raw_hash,
        "rule_counts": rule_counts,
        "created_at": (
            existing_created_at[0]
            if existing_created_at is not None
            else datetime.now(UTC).replace(tzinfo=None)
        ),
    }

    conn.execute(
        "INSERT OR REPLACE INTO metadata_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            metadata["run_id"],
            metadata["period"],
            metadata["expected_count"],
            metadata["raw_count"],
            metadata["published_count"],
            metadata["rejected_count"],
            metadata["status"],
            metadata["raw_hash"],
            json.dumps(metadata["rule_counts"], separators=(",", ":")),
            metadata["created_at"],
        ),
    )
    return metadata


def run_pipeline() -> dict[str, Any]:
    config = get_config()
    db_path = Path(str(config["db_path"]))
    period = str(config["period"])
    seed = int(config["seed"])

    _ensure_dirs(str(db_path))
    conn = duckdb.connect(str(db_path))
    _init_schema(conn)
    try:
        conn.execute("BEGIN")
        _persist_person_master(conn)
        raw_rows = generate_raw_rows(period, seed)
        raw_hash = _persist_raw_if_needed(conn, period, raw_rows)
        classified_rows, rule_counts = _classify_rows(conn, raw_rows)
        run_id = f"{period}-seed-{seed}"
        summary = _persist_run_results(
            conn, run_id, period, classified_rows, rule_counts, raw_hash
        )
        summary["rule_counts"] = rule_counts
        summary["raw_hash"] = raw_hash
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    assert summary["expected_count"] == EXPECTED_COUNT
    assert summary["raw_count"] == EXPECTED_COUNT
    assert summary["published_count"] == PUBLISHED_COUNT
    assert summary["rejected_count"] == REJECTED_COUNT
    assert summary["rule_counts"]["MISSING_PERSON"] == INVALID_MISSING_PERSON_COUNT
    assert summary["rule_counts"]["INVALID_AMOUNT"] == INVALID_AMOUNT_COUNT

    return summary
