from pathlib import Path

SKILL_PATH = (
    Path(__file__).parents[1]
    / ".agents"
    / "skills"
    / "investigate-payment-pipeline"
    / "SKILL.md"
)


def _read_skill() -> str:
    assert SKILL_PATH.is_file()
    return SKILL_PATH.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    closing_marker = lines.index("---", 1)
    values: dict[str, str] = {}
    for line in lines[1:closing_marker]:
        key, separator, value = line.partition(":")
        assert separator
        assert key.strip()
        value = value.strip()
        assert value
        if value.startswith('"'):
            assert value.endswith('"')
            value = value[1:-1]
        values[key.strip()] = value
    return values


def test_skill_frontmatter_has_valid_metadata() -> None:
    metadata = _parse_frontmatter(_read_skill())

    assert metadata["name"] == "investigate-payment-pipeline"
    description = metadata["description"].lower()
    assert "diferencias" in description
    assert "rechazos" in description
    assert "reconciliaciones" in description
    assert "batches de pagos" in description
    assert "no se activa" in description


def test_skill_requires_ordered_mcp_investigation() -> None:
    skill = _read_skill()

    tool_positions = [
        skill.index("`get_payment_batch`"),
        skill.index("`reconcile_payment_layers`"),
        skill.index("`get_rejection_reasons`"),
    ]
    assert tool_positions == sorted(tool_positions)
    assert "detén la investigación" in skill
    assert "No inventes causas, conteos" in skill


def test_skill_preserves_read_only_boundaries() -> None:
    skill = _read_skill()

    for prohibited_action in (
        "No abras DuckDB directamente",
        "No ejecutes SQL, Python ni shell",
        "No solicites registros individuales",
        "No modifiques archivos, tablas ni datos",
        "No ejecutes el replay",
    ):
        assert prohibited_action in skill
    assert "DuckDB permanece detrás del MCP" in skill
    assert "La skill guía el procedimiento" in skill
    assert "El agente interpreta la evidencia" in skill
    assert "El MCP entrega evidencia estructurada" in skill


def test_skill_defines_separate_report_sections() -> None:
    skill = _read_skill()

    expected_sections = (
        "**Alcance investigado**",
        "**Hechos comprobados**",
        "**Reconciliación de capas**",
        "**Causas de rechazo**",
        "**Inferencias**",
        "**Recomendaciones**",
        "**Propuesta de replay seguro**",
    )
    positions = [skill.index(section) for section in expected_sections]
    assert positions == sorted(positions)