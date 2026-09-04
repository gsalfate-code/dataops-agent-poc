# dataops-agent-poc

Educational proof of concept for learning how a Codex agent, an agent skill, and an MCP server
work separately and together in a Data Engineering incident investigation.

## Target scenario

A fictitious payment batch expects 10,000 records but publishes 9,880. The agent must use a
repeatable investigation workflow and read-only MCP tools to identify the 120 rejected records,
support the conclusion with evidence, and propose a safe replay.

## Learning milestones

1. Reproducible GitHub Codespace.
2. Deterministic and idempotent DuckDB pipeline.
3. Read-only MCP server with business-oriented tools.
4. Repository-scoped investigation skill.
5. Main-agent and subagent comparison.
6. Auditable evidence and automated checks.

## Current checkpoint

The repository contains a deterministic DuckDB pipeline, quality rules, a read-only MCP server,
the repository-scoped investigation skill, and an automated MCP STDIO walking skeleton. The
pipeline and protocol checks are reproducible locally; an authenticated Codex E2E invocation is
not claimed as verified. See [`docs/STATUS.md`](docs/STATUS.md) for the evidence matrix.

The repository contains only the reproducible Python development environment and project rules.
The data pipeline, MCP server, and skill will be added as separate, observable increments.

The complete outcome, constraints, and definition of done are recorded in
[`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md). Codex can use its master goal to implement the
project phase by phase without precautionary approval questions.

## Bootstrap

Inside the Codespace:

```bash
uv sync
uv run ruff check .
uv run pytest
```

The first successful `uv sync` creates `uv.lock`. Commit that file, then use
`uv sync --frozen` in subsequent environments to prevent silent dependency changes.

## Configuration and secrets

`.env.example` is the public configuration contract: it documents the variables understood by
the project without containing credentials. A local `.env` is optional and ignored by Git. Real
credentials, if a future external integration requires them, must be stored as repository-scoped
GitHub Codespaces secrets and exposed to the application as environment variables.

The initial local DuckDB and MCP implementation requires no credentials.
