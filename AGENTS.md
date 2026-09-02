# Project instructions

## Mission

Build an educational, public proof of concept of a Data Engineering Reliability Agent. The
agent must investigate fictitious batch-pipeline incidents using a repository-scoped skill and
read-only MCP tools backed by DuckDB.

## Learning workflow

- Explain a concept and the engineering decision before implementing it.
- Work in small, testable increments and finish each increment with an observable check.
- Do not replace learning with large copy-and-paste solutions.
- Give the learner a small prediction, inspection, or modification exercise at each milestone.
- Define new terminology in plain language when it first appears.

Explanation is not an approval request. Continue after explaining when the action is local,
reversible, in scope, and testable.

## Autonomy boundaries

Proceed without asking for routine, reversible, local decisions. State a reasonable assumption,
record it when durable, and continue.

Stop and ask only when:

- missing information materially changes the result;
- the action is destructive or difficult to reverse;
- credentials, costs, production systems, or external writes are involved;
- a genuine business rule cannot be inferred from the fictitious specification.

Never access real personal or institutional data. Never commit credentials or generated database
files. Treat all business examples and datasets as fictitious.

## Engineering principles

- Reproducibility: rebuild the environment and results from versioned inputs and configuration.
- Immutability: never overwrite raw inputs for an existing run.
- Idempotency: replaying the same run must not duplicate or corrupt results.
- Determinism: identical inputs, code, and configuration must produce identical outputs.
- Separation of responsibilities: keep generation, pipeline, quality, persistence, MCP, skills,
  and evaluation independent.
- Traceability: retain run identifiers, counts, hashes, rule results, and evidence.
- Least privilege: MCP tools are read-only in the first version.

## Verification

Run these checks after relevant changes:

```bash
uv run ruff check .
uv run pytest
```

Do not claim completion when checks fail. Report the failure and its cause clearly.
