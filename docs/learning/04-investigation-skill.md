# 04. Skill de investigación

## Propósito

Una **skill** es una instrucción reutilizable que orienta al agente para resolver una clase
concreta de tareas. En esta POC, `investigate-payment-pipeline` convierte una pregunta vaga
sobre un batch en una investigación ordenada y comprobable.

La skill no contiene una conclusión fija. Define qué evidencia pedir, en qué orden pedirla y
cómo informar los resultados sin inventar datos.

## Skill, agente y MCP

- La **skill** describe el procedimiento, sus límites y el formato de salida.
- El **agente** decide cómo aplicar ese procedimiento, interpreta las respuestas y redacta la
  conclusión separando hechos, inferencias y recomendaciones.
- El **MCP** expone herramientas con contratos estructurados. En esta POC entrega únicamente
  evidencia agregada y de solo lectura.

DuckDB es una dependencia interna del MCP. La skill y el agente no deben abrir la base ni
consultarla directamente.

## Cómo cambia el comportamiento del agente

Sin la skill, un agente podría saltar directamente a una explicación o pedir datos demasiado
detallados. Con ella, el agente debe:

1. fijar el período;
2. llamar primero a `get_payment_batch`;
3. reconciliar las capas con `reconcile_payment_layers`;
4. obtener las causas agregadas con `get_rejection_reasons`;
5. detenerse si la evidencia es incompleta o contradictoria;
6. presentar una respuesta trazable con hechos, inferencias y recomendaciones separados.

El orden reduce conclusiones prematuras. La herramienta no decide la causa raíz: devuelve los
datos agregados para que el agente los interprete.

## Qué no puede hacer

Esta skill no puede abrir DuckDB, ejecutar SQL, Python o shell para consultar datos, solicitar
registros individuales, modificar archivos o tablas, ni ejecutar un replay. Tampoco investiga
sistemas reales: todos los datos y resultados pertenecen a la fixture ficticia de la POC.

La propuesta de replay es solo un plan. Una futura fase podría evaluar cómo documentar o
simular ese plan, pero esta skill no lo ejecuta.

## Cómo probarla después

Cuando el agente y el registro MCP estén disponibles, prepara la fixture local y solicita una
investigación con un mensaje como:

> Investiga por qué el batch de pagos de `2026-09` publicó menos registros de los esperados.
> No modifiques datos. Devuelve evidencia MCP, causas, impacto y una propuesta de replay seguro.

Comprueba que el agente invoque las tres herramientas en el orden indicado y que el informe
incluya las siete secciones del formato obligatorio. Para una verificación automatizada del
servidor, sus contratos y el recorrido MCP STDIO completo, ejecuta:

```bash
uv run pytest tests/test_mcp_server.py::test_real_mcp_stdio_call_returns_structured_evidence
```

La fixture puede confirmar 10.000 esperados, 9.880 publicados, 120 rechazados, 115
`MISSING_PERSON` y 5 `INVALID_AMOUNT`; el agente debe atribuir esos números a las respuestas
MCP, nunca a valores codificados en la skill.

## Ejercicio

Antes de ejecutar una investigación, predice qué comprobación debería detectar la diferencia
entre RAW y MART. Después compara tu predicción con `reconcile_payment_layers` y explica por qué
la propuesta de replay debe conservar los registros rechazados en QUARANTINE.