import duckdb

from dataops_agent_poc.config import get_config
from dataops_agent_poc.pipeline import run_pipeline


def test_pipeline_generates_expected_business_output(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "warehouse.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")

    summary = run_pipeline()
    with duckdb.connect(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM raw_payments").fetchone()[0] == 10_000
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
    assert summary["status"] == "PUBLISHED"
    assert summary["raw_hash"]


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


def test_config_reads_environment_values(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "env.duckdb"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-08")
    monkeypatch.setenv("DATAOPS_SEED", "99")

    config = get_config()

    assert config["db_path"] == str(db_path)
    assert config["period"] == "2026-08"
    assert config["seed"] == 99
