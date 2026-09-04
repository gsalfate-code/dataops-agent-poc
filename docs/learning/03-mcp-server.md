# 03. Servidor MCP de solo lectura

## Propósito

MCP (Model Context Protocol) es un protocolo para que un cliente de IA descubra y
llame herramientas con contratos estructurados. En esta fase el servidor ofrece
evidencia agregada del pipeline de pagos; no modifica datos ni decide la causa raíz.

## Arquitectura

El servidor se divide en tres responsabilidades:

- `mcp_repository.py` abre DuckDB con `read_only=True` y ejecuta consultas fijas y
  parametrizadas.
- `mcp_business.py` valida `period`, calcula reconciliaciones y escribe auditoría
  JSONL sanitizada.
- `mcp_server.py` adapta esas funciones a exactamente tres herramientas MCP y define
  sus modelos de respuesta.

El transporte STDIO permite que el cliente inicie el servidor localmente y use
`stdin`/`stdout` para MCP sin abrir un puerto. Por eso los diagnósticos se escriben
en STDERR y las auditorías en la ruta externa `DATAOPS_AUDIT_PATH`.

## Contrato de herramientas

### `get_payment_batch(period)`

Acepta un período `YYYY-MM` y devuelve run, conteos expected/RAW/STAGING/publicados/
rechazados, estado, hash RAW, conteos de reglas y `created_at`.

### `reconcile_payment_layers(period)`

Devuelve conteos agregados y verifica `expected = RAW`, `RAW = STAGING` y
`STAGING = MART + QUARANTINE`. Si existe una diferencia, informa la primera y su
magnitud.

### `get_rejection_reasons(period)`

Devuelve código, motivo y cantidad de cada rechazo, además del total. Nunca entrega
registros individuales.

Todas son herramientas de lectura e idempotentes. No existe una herramienta de SQL
arbitrario ni de escritura.

## MCP y una API

Una API suele publicar endpoints diseñados para una aplicación concreta. MCP añade
descubrimiento de herramientas, esquemas y anotaciones para que un cliente de IA
pueda seleccionar operaciones compatibles de forma uniforme. Aquí el transporte es
STDIO, pero el principio importante es el contrato de herramienta, no una URL.

## Auditoría y mínimo privilegio

Cada llamada registra timestamp, herramienta, período, resultado y duración en JSONL.
No se guardan respuestas completas, pagos, personas ni SQL. La conexión DuckDB es
de solo lectura y la configuración externa define tanto la base como la auditoría.

## Ejercicio

Ejecuta las tres herramientas para `2026-09`. Predice qué primera diferencia debe
aparecer antes de llamar a la reconciliación y explica por qué los 120 rechazos se
pueden describir sin mostrar ningún pago individual.

## Verificación

```bash
uv run ruff check .
uv run pytest
```

El test de integración inicia el servidor real, lista exactamente las tres herramientas y las
invoca mediante MCP STDIO en el orden de investigación, además de comprobar conteos, causas,
limpieza de la base temporal y auditoría.

## Registro en Codex

Implementar un servidor significa escribir su código, sus consultas y sus contratos MCP.
Registrarlo significa indicar a un cliente cómo iniciarlo y qué herramientas puede descubrir.
`.codex/config.toml` realiza este segundo trabajo para este proyecto: define el comando STDIO,
las variables de entorno con rutas relativas, los timeouts, el modo de aprobación y la lista
cerrada de herramientas habilitadas. No contiene credenciales ni cambia el pipeline.

Después de crear o modificar esta configuración, reinicia Codex para que vuelva a leerla y
descubra `dataops_agent`. Verifica el registro solicitando la lista de herramientas MCP o
ejecutando la prueba de integración:

```bash
uv run pytest tests/test_mcp_server.py::test_real_mcp_stdio_call_returns_structured_evidence
uv run pytest tests/test_mcp_server.py::test_real_mcp_stdio_call_returns_structured_evidence
```

La lista esperada contiene exactamente `get_payment_batch`, `reconcile_payment_layers` y
`get_rejection_reasons`. Las anotaciones de solo lectura permiten el modo
`default_tools_approval_mode = "writes"` sin pedir aprobación de escritura para estas consultas.