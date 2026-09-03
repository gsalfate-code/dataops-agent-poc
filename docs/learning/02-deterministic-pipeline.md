# 02. Deterministic pipeline

## Purpose

This phase introduces the first business logic: generate a deterministic batch of fictitious payments and validate it without modifying the raw input. The goal is to create a stable pipeline that can be replayed without changing the outcome or duplicating records.

## Architecture of layers

The pipeline separates responsibility into clear data layers:

- RAW: source input rows generated for the logical period.
- STAGING: all source rows with validation status and rejection classification.
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

The valid person reference is a deterministic fictitious `person_master` table containing person
IDs 1 through 1,000. `MISSING_PERSON` is determined by actual absence from that table, rather
than by a numeric threshold.

STAGING stores all 10,000 classified rows. Valid rows have status `VALID` and null rejection
fields; rejected rows have status `REJECTED`, a rule code, and a reason. MART and QUARANTINE are
SQL derivations from STAGING, producing 9,880 and 120 rows respectively.

Validation rules and their priority live in `quality.py`. The first matching rule wins, with
`MISSING_PERSON` evaluated before `INVALID_AMOUNT`.

Persistence for one run is enclosed by explicit `BEGIN`/`COMMIT` and rolled back on error.
Temporary CSV files are removed in a `finally` block, including when DuckDB `COPY` fails.

## Separation of responsibilities

The project keeps generation, quality, pipeline, and persistence independent:

- generation creates deterministic input rows,
- validation classifies rows by rule,
- the pipeline loads each layer into DuckDB,
- persistence stores the final state and metadata.

That separation makes the pipeline easier to test and easier to reason about during incident investigation.

## Business rules implemented in this phase

- exactly 10,000 raw records are generated for the 2026-09 period;
- the deterministic person master contains 1,000 valid person IDs;
- the expected published count is 9,880;
- all 10,000 rows are classified in STAGING;
- invalid rows are quarantined with a rule code;
- missing-person references are recorded as `MISSING_PERSON`;
- invalid amounts are recorded as `INVALID_AMOUNT`;
- every row remains traceable to a run identifier;
- a successful batch with expected rejections has status `PUBLISHED_WITH_REJECTIONS`;
- repeating a `run_id` preserves its original `created_at`.

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

The automated tests also cover the master table, membership-based classification, atomic
rollback, temporary-file cleanup, rejection of a changed seed for an existing period, equal
hashes in independent databases, the complete STAGING count, and the
`PUBLISHED_WITH_REJECTIONS` status.

## Expected result

A successful deterministic pipeline should produce:

- 10,000 raw rows,
- 9,880 published payments,
- 120 rejected rows,
- 115 `MISSING_PERSON`,
- 5 `INVALID_AMOUNT`,
- stable metadata and hashes across replay.
