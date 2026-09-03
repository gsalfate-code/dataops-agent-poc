import json
import os
from datetime import datetime
from pathlib import Path

import anyio
import duckdb
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dataops_agent_poc.mcp_business import (
    get_payment_batch,
    get_rejection_reasons,
    reconcile_payment_layers,
    validate_period,
)
from dataops_agent_poc.mcp_repository import PaymentRepository
from dataops_agent_poc.pipeline import run_pipeline


def _configure_database(tmp_path, monkeypatch) -> tuple[Path, Path]:
    db_path = tmp_path / "mcp.duckdb"
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("DATAOPS_DB_PATH", str(db_path))
    monkeypatch.setenv("DATAOPS_AUDIT_PATH", str(audit_path))
    monkeypatch.setenv("DATAOPS_PERIOD", "2026-09")
    monkeypatch.setenv("DATAOPS_SEED", "42")
    run_pipeline()
    return db_path, audit_path


def test_mcp_business_responses_are_structured_and_aggregated(tmp_path, monkeypatch) -> None:
    _configure_database(tmp_path, monkeypatch)

    batch = get_payment_batch("2026-09")
    reconciliation = reconcile_payment_layers("2026-09")
    rejections = get_rejection_reasons("2026-09")

    assert batch["expected_count"] == 10_000
    assert batch["raw_count"] == 10_000
    assert batch["staging_count"] == 10_000
    assert batch["published_count"] == 9_880
    assert batch["rejected_count"] == 120
    assert batch["rule_counts"] == {"MISSING_PERSON": 115, "INVALID_AMOUNT": 5}
    assert batch["created_at"]
    assert reconciliation["counts"] == {
        "raw": 10_000,
        "staging": 10_000,
        "mart": 9_880,
        "quarantine": 120,
    }
    assert reconciliation["first_difference"] is None
    assert rejections["total_rejected"] == 120
    assert rejections["reasons"] == [
        {"code": "INVALID_AMOUNT", "reason": "invalid payment amount", "count": 5},
        {"code": "MISSING_PERSON", "reason": "missing person reference", "count": 115},
    ]


def test_mcp_exposes_exactly_three_read_only_tools() -> None:
    from dataops_agent_poc.mcp_server import mcp

    tools = anyio.run(mcp.list_tools)
    assert {tool.name for tool in tools} == {
        "get_payment_batch",
        "reconcile_payment_layers",
        "get_rejection_reasons",
    }
    assert all(tool.annotations.readOnlyHint for tool in tools)
    assert all(tool.annotations.idempotentHint for tool in tools)
    assert all(not tool.annotations.destructiveHint for tool in tools)
    assert "sql" not in {tool.name.lower() for tool in tools}
    assert not any("write" in tool.name.lower() for tool in tools)


def test_period_validation_rejects_invalid_and_nonexistent_months() -> None:
    for period in ("2026-9", "202609", "2026-00", "2026-13", "abcd-09", "2026-02-01"):
        with pytest.raises(ValueError):
            validate_period(period)
    assert validate_period("2026-09") == "2026-09"


def test_repository_uses_read_only_connection_and_cannot_write(tmp_path) -> None:
    db_path = tmp_path / "read-only.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("CREATE TABLE sample (value INTEGER)")

    repository = PaymentRepository(db_path)
    connection = repository._connect()
    try:
        with pytest.raises(duckdb.Error):
            connection.execute("INSERT INTO sample VALUES (1)")
    finally:
        connection.close()


def test_responses_and_audit_do_not_contain_individual_records(tmp_path, monkeypatch) -> None:
    _, audit_path = _configure_database(tmp_path, monkeypatch)

    responses = [
        get_payment_batch("2026-09"),
        reconcile_payment_layers("2026-09"),
        get_rejection_reasons("2026-09"),
    ]
    serialized_responses = json.dumps(responses)
    assert "pay-2026-09" not in serialized_responses
    assert "Person " not in serialized_responses

    events = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert len(events) == 3
    for event in events:
        assert set(event) == {"timestamp", "tool", "period", "result", "duration_ms"}
        assert event["period"] == "2026-09"
        assert event["result"] == "ok"
        assert isinstance(event["duration_ms"], float)
        datetime.fromisoformat(event["timestamp"])
        assert "pay-" not in json.dumps(event)


def test_real_mcp_stdio_call_returns_structured_evidence(tmp_path, monkeypatch) -> None:
    db_path, audit_path = _configure_database(tmp_path, monkeypatch)
    environment = os.environ | {
        "DATAOPS_DB_PATH": str(db_path),
        "DATAOPS_AUDIT_PATH": str(audit_path),
    }
    server_parameters = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "dataops_agent_poc.mcp_server"],
        env=environment,
    )

    async def call_tool() -> dict:
        async with stdio_client(server_parameters) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool("get_payment_batch", {"period": "2026-09"})
                assert result.isError is False
                return result.structuredContent

    response = anyio.run(call_tool)
    assert response["expected_count"] == 10_000
    assert response["published_count"] == 9_880
    assert response["rejected_count"] == 120
