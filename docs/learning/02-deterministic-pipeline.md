# 02. Deterministic pipeline

## Purpose

This phase introduces the first business logic: generate a deterministic batch of fictitious payments and validate it without modifying the raw input. The goal is to create a stable pipeline that can be replayed without changing the outcome or duplicating records.

## Architecture of layers

The pipeline separates responsibility into clear data layers:

- RAW: source input rows generated for the logical period.
- STAGING: validation and rejection classification.
- QUARANTINE: all rejected rows, preserved with rule codes and run metadata.
- MART: only valid payment rows published after validation.
- METADATA: run status, counts, hashes, and rule results.

This layering keeps the pipeline inspectable: each step can be checked independently for row counts, rule counts, and persistence behavior.

## Determinism, idempotence, and immutability

### Determinism

The pipeline is deterministic because the generator depends on a fixed seed and period. For the same inputs, it produces the same values, counts, and hashes.

### Idempotence

Replay behavior is controlled by deleting existing stage, quarantine, and mart tables before reinsertions and by reusing the same run identity. The same run must not create duplicates or change the business result.

### Immutability

The raw input is kept as a preserved artifact. Instead of overwriting raw rows in place, the pipeline rebuilds the normalized run state from the fixed source data and leaves the raw layer stable for comparison and auditing.

## Separation of responsibilities

The project keeps generation, quality, pipeline, and persistence independent:

- generation creates deterministic input rows,
- validation classifies rows by rule,
- the pipeline loads each layer into DuckDB,
- persistence stores the final state and metadata.

That separation makes the pipeline easier to test and easier to reason about during incident investigation.

## Business rules implemented in this phase

- exactly 10,000 raw records are generated for the 2026-09 period;
- the expected published count is 9,880;
- invalid rows are quarantined with a rule code;
- missing-person references are recorded as `MISSING_PERSON`;
- invalid amounts are recorded as `INVALID_AMOUNT`;
- every row remains traceable to a run identifier.

## Verification commands

```bash
uv run ruff check .
uv run pytest
```

## Learner exercise

Run the pipeline twice in the same environment and compare the summary values:

1. call the pipeline once;
2. call it a second time with the same environment variables;
3. compare raw hashes, published counts, and rejected counts;
4. explain why the result should remain stable.

Prediction: the counts and hashes remain the same because the process is deterministic and the raw layer is immutable.

## Expected result

A successful deterministic pipeline should produce:

- 10,000 raw rows,
- 9,880 published payments,
- 120 rejected rows,
- 115 `MISSING_PERSON`,
- 5 `INVALID_AMOUNT`,
- stable metadata and hashes across replay.
