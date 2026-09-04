# Estado verificable

Esta POC usa únicamente datos ficticios del período `2026-09`. Los conteos de la fixture se
consideran evidencia solo cuando los devuelven el pipeline o las herramientas MCP durante una
ejecución.

## Comprobado

- Entorno reproducible con Python, `uv.lock`, DuckDB y comandos locales de Ruff y pytest.
- Pipeline determinista: 10.000 filas RAW, STAGING completo, 9.880 filas MART y 120 en QUARANTINE.
- Reglas ficticias comprobadas: 115 `MISSING_PERSON` y 5 `INVALID_AMOUNT`.
- Idempotencia del replay, RAW inmutable mediante hash, `Decimal` en Python y `DECIMAL(18,2)` en DuckDB.
- Transacción con rollback y limpieza de CSV temporales.
- Servidor MCP de solo lectura con exactamente tres herramientas, consultas fijas, respuestas agregadas y auditoría JSONL.
- Llamadas reales mediante un cliente MCP SDK sobre STDIO: listado de herramientas, tres invocaciones en orden, conteos, causas, auditoría y limpieza de base temporal.
- Skill validada: frontmatter, trigger discriminante, orden, límites, parada ante evidencia insuficiente y separación entre hechos, inferencias y recomendaciones.
- Ruff y suite automatizada pasan.

## No comprobado

- Invocación de las herramientas por una sesión autenticada del cliente Codex. `codex mcp list`
  encuentra `dataops_agent` y muestra su configuración local, pero informa estado `Unsupported`;
  no se inició autenticación. Esta limitación pertenece a la integración del cliente y su
  autenticación, no al protocolo MCP ni a DuckDB.

## Niveles de verificación

| Nivel | Qué demuestra | Estado |
| --- | --- | --- |
| Unitario | Funciones y reglas | Resultado real |
| Pipeline | Persistencia y garantías | Resultado real |
| Protocolo MCP | Cliente SDK llama al servidor STDIO | Resultado real |
| Skill | Metadatos, flujo y límites | Resultado real |
| Codex E2E | Codex decide e invoca MCP | No comprobado |

## Clientes y límites

`.codex/config.toml` es configuración del cliente Codex: registra `dataops_agent`, el comando
STDIO, el cwd del proyecto, las rutas relativas de DuckDB y auditoría, timeouts y la lista cerrada
de herramientas. La configuración MCP del IDE u otros agentes sería independiente y no se crea
ni se presenta como equivalente. La prueba SDK valida el protocolo MCP, no el comportamiento de
Codex.

## Reproducir

Desde `/workspaces/dataops-agent-poc`:

```bash
uv run ruff check .
uv run pytest
uv run pytest tests/test_mcp_server.py::test_real_mcp_stdio_call_returns_structured_evidence
```
