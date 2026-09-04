---
name: investigate-payment-pipeline
description: "Activa esta skill para investigar diferencias, rechazos o reconciliaciones de batches de pagos de esta POC. No se activa para construir pipelines, escribir SQL, modificar datos, administrar DuckDB ni investigar sistemas reales."
---

# Investigar un batch de pagos

## Alcance

Esta skill guía una investigación reproducible del batch ficticio de pagos de esta POC. Se usa
cuando el usuario informa una diferencia entre registros esperados y publicados, pregunta por
rechazos o necesita reconciliar las capas de un período.

No se usa para construir o modificar el pipeline, escribir SQL, administrar DuckDB, cambiar
reglas de calidad ni investigar sistemas reales.

## Flujo obligatorio

1. Identifica el período solicitado y conserva el valor exacto en formato `YYYY-MM`.
2. Llama primero a `get_payment_batch` para confirmar el reporte y obtener los conteos agregados
   del batch.
3. Llama a `reconcile_payment_layers` para comprobar la conservación de registros entre RAW,
   STAGING, MART y QUARANTINE.
4. Llama a `get_rejection_reasons` para obtener las causas y cantidades agregadas de los
   rechazos.
5. Comprueba que las respuestas sean coherentes entre sí. Si falta evidencia, una herramienta
   falla o los resultados son inconsistentes, detén la investigación, describe la limitación y
   no presentes una causa como confirmada.
6. Formula una hipótesis únicamente a partir de la evidencia devuelta por las herramientas.
   No inventes causas, conteos ni relaciones entre capas.
7. Redacta el informe distinguiendo explícitamente hechos comprobados, inferencias y
   recomendaciones. Cita el nombre de la herramienta que respalda cada hecho.

## Responsabilidades

- La skill guía el procedimiento y el orden de las comprobaciones.
- El agente interpreta la evidencia, prueba la hipótesis y redacta la conclusión.
- El MCP entrega evidencia estructurada, agregada y de solo lectura.
- DuckDB permanece detrás del MCP y no forma parte de la interfaz de investigación.

## Restricciones

- No abras DuckDB directamente.
- No ejecutes SQL, Python ni shell para consultar los datos.
- No solicites registros individuales ni datos personales.
- No modifiques archivos, tablas ni datos.
- No ejecutes el replay. Solo puedes proponerlo como plan seguro.
- No trates el escenario ficticio como información real.
- No llames herramientas que no estén en el contrato MCP de esta POC.

## Formato obligatorio de respuesta

Usa estas secciones, en este orden:

1. **Alcance investigado**: período y pregunta analizada.
2. **Hechos comprobados**: resultados agregados, asociados explícitamente a las herramientas
   MCP que los devolvieron.
3. **Reconciliación de capas**: conteos, comprobaciones y cualquier primera diferencia.
4. **Causas de rechazo**: códigos, motivos y cantidades entregados por MCP.
5. **Inferencias**: interpretación razonada, separada de los hechos y marcada como inferencia.
6. **Recomendaciones**: acciones propuestas sin ejecutarlas.
7. **Propuesta de replay seguro**: pasos de un plan, sujeto a validación y aprobación; nunca
   ejecutes el replay durante esta investigación.

## Fixture educativa 2026-09

Para el período `2026-09`, la fixture espera que las herramientas puedan confirmar 10.000
registros esperados, 9.880 publicados y una diferencia de 120. También espera, si la evidencia
MCP lo confirma, 115 rechazos `MISSING_PERSON` y 5 `INVALID_AMOUNT`.

Estos valores son una expectativa de la fixture educativa, no una conclusión automática. La
conclusión debe usar únicamente los valores devueltos por `get_payment_batch`,
`reconcile_payment_layers` y `get_rejection_reasons`.