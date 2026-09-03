import tempfile
from datetime import UTC, datetime
from decimal import Decimal

import duckdb
import pytest

from dataops_agent_poc import pipeline
from dataops_agent_poc.config import get_config
from dataops_agent_poc.generation import compute_raw_hash, generate_raw_rows
from dataops_agent_poc.pipeline import run_pipeline
from dataops_agent_poc.quality import classify_rows


def test_pipeline_generates_expected_business_output(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "warehouse.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")

    summary = run_pipeline()
    with duckdb.connect(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM raw_payments").fetchone()[0] == 10_000
        assert conn.execute("SELECT COUNT(*) FROM person_master").fetchone()[0] == 1_000
        assert conn.execute("SELECT COUNT(*) FROM staging_payments").fetchone()[0] == 10_000
        assert conn.execute("SELECT COUNT(*) FROM mart_payments").fetchone()[0] == 9_880
        assert conn.execute("SELECT COUNT(*) FROM quarantine_payments").fetchone()[0] == 120
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM quarantine_payments WHERE rejection_code = 'MISSING_PERSON'"
            ).fetchone()[0]
            == 115
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM quarantine_payments WHERE rejection_code = 'INVALID_AMOUNT'"
            ).fetchone()[0]
            == 5
        )
        assert conn.execute("SELECT COUNT(*) FROM metadata_runs").fetchone()[0] == 1

    assert summary["expected_count"] == 10_000
    assert summary["raw_count"] == 10_000
    assert summary["published_count"] == 9_880
    assert summary["rejected_count"] == 120
    assert summary["rule_counts"]["MISSING_PERSON"] == 115
    assert summary["rule_counts"]["INVALID_AMOUNT"] == 5
    assert summary["status"] == "PUBLISHED_WITH_REJECTIONS"
    assert summary["raw_hash"]


def test_payment_amounts_use_decimal_contract(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "decimal-contract.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))

    run_pipeline()
    with duckdb.connect(str(db_path)) as conn:
        for table_name in (
            "raw_payments",
            "staging_payments",
            "quarantine_payments",
            "mart_payments",
        ):
            amount_type = conn.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = ? AND column_name = 'amount'
                """,
                [table_name],
            ).fetchone()[0]
            assert amount_type == "DECIMAL(18,2)"


def test_payment_amount_round_trip_is_exact() -> None:
    amount = Decimal("1234.56")
    rows = [
        {
            "payment_id": "pay-1",
            "period": "2026-09",
            "person_id": 1,
            "amount": amount,
            "source_row_id": 1,
        }
    ]

    conn = duckdb.connect(":memory:")
    try:
        conn.execute("CREATE TABLE payments (amount DECIMAL(18,2))")
        conn.execute("INSERT INTO payments VALUES (?)", [amount])
        persisted_amount = conn.execute("SELECT amount FROM payments").fetchone()[0]
    finally:
        conn.close()

    assert persisted_amount == amount
    assert compute_raw_hash(rows) == compute_raw_hash(
        [{**rows[0], "amount": persisted_amount}]
    )


def test_second_run_is_idempotent_and_raw_is_immutable(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "repeat.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")

    first = run_pipeline()
    second = run_pipeline()

    assert first["run_id"] == second["run_id"]
    assert first["published_count"] == second["published_count"] == 9_880
    assert first["rejected_count"] == second["rejected_count"] == 120
    assert first["raw_count"] == second["raw_count"] == 10_000
    assert first["raw_hash"] == second["raw_hash"]
    with duckdb.connect(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM raw_payments").fetchone()[0] == 10_000
        assert conn.execute("SELECT COUNT(*) FROM mart_payments").fetchone()[0] == 9_880
        assert conn.execute("SELECT COUNT(*) FROM quarantine_payments").fetchone()[0] == 120


def test_repeated_run_preserves_created_at(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "created-at.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))

    before = datetime.now(UTC).replace(tzinfo=None)
    run_pipeline()
    after = datetime.now(UTC).replace(tzinfo=None)
    with duckdb.connect(str(db_path)) as conn:
        first_created_at = conn.execute(
            "SELECT created_at FROM metadata_runs"
        ).fetchone()[0]

    assert before <= first_created_at <= after

    run_pipeline()
    with duckdb.connect(str(db_path)) as conn:
        second_created_at = conn.execute(
            "SELECT created_at FROM metadata_runs"
        ).fetchone()[0]

    assert second_created_at == first_created_at


def test_config_reads_environment_values(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "env.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-08")
    monkeypatch.setenv("DATAOPS_SEED", "99")

    config = get_config()

    assert config["db_path"] == str(db_path)
    assert config["period"] == "2026-08"
    assert config["seed"] == 99


def test_missing_person_uses_master_membership_not_threshold() -> None:
    rows = generate_raw_rows("2026-09", 42)[:1]

    classified_rows, rule_counts = classify_rows(rows, {1_000_000})

    assert classified_rows[0]["validation_status"] == "VALID"
    assert classified_rows[0]["rejection_code"] is None
    assert rule_counts == {"MISSING_PERSON": 0, "INVALID_AMOUNT": 0}


def test_rollback_preserves_previous_run_completely(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "rollback.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    first = run_pipeline()

    with duckdb.connect(str(db_path)) as conn:
        before = {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()
            for table in (
                "person_master",
                "raw_payments",
                "staging_payments",
                "quarantine_payments",
                "mart_payments",
                "metadata_runs",
            )
        }

    original_copy = pipeline._copy_csv_rows

    def fail_after_copy(conn, table_name, rows):
        original_copy(conn, table_name, rows)
        raise RuntimeError("simulated intermediate failure")

    monkeypatch.setattr(pipeline, "_copy_csv_rows", fail_after_copy)
    with pytest.raises(RuntimeError, match="simulated intermediate failure"):
        run_pipeline()

    with duckdb.connect(str(db_path)) as conn:
        after = {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()
            for table in before
        }

    assert first["raw_hash"]
    assert after == before


def test_temporary_csv_is_removed_when_copy_fails(tmp_path, monkeypatch) -> None:
    original_temp_file = tempfile.NamedTemporaryFile

    def temp_file_in_test_dir(*args, **kwargs):
        kwargs["dir"] = tmp_path
        return original_temp_file(*args, **kwargs)

    monkeypatch.setattr(pipeline.tempfile, "NamedTemporaryFile", temp_file_in_test_dir)
    conn = duckdb.connect(":memory:")
    try:
        with pytest.raises(duckdb.Error):
            pipeline._copy_csv_rows(conn, "missing_table", [("value",)])
    finally:
        conn.close()

    assert list(tmp_path.iterdir()) == []


def test_seed_change_for_existing_period_is_rejected(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "seed-change.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")
    run_pipeline()

    monkeypatch.setenv("DATAOPS_SEED", "43")
    with pytest.raises(ValueError, match="RAW layer is immutable"):
        run_pipeline()


def test_same_hash_in_independent_databases(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")
    monkeypatch.setenv("DATAOPS_DB_PATH", str(tmp_path / "one.duckdb"))
    first = run_pipeline()
    monkeypatch.setenv("DATAOPS_DB_PATH", str(tmp_path / "two.duckdb"))
    second = run_pipeline()

    assert first["raw_hash"] == second["raw_hash"]
