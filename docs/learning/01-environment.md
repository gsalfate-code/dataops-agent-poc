# 01. Environment bootstrap

## Purpose

This is the first phase of the project: establish a repeatable local development environment for an educational Data Engineering reliability agent. The environment supports the deterministic pipeline, read-only MCP server, investigation skill, and their local validation commands.

## What "bootstrap" means

"Bootstrap" means the setup work that prepares a project so it can run. In practice, this phase configures:

- the Python version and package metadata,
- the dependency manager and lock file,
- the local tooling for linting and tests,
- the developer environment variables,
- the ignore rules for generated artifacts.

For this repository, the bootstrap is intentionally minimal and explicit. It provides a stable base for deterministic data generation, DuckDB persistence, read-only MCP tools, and the investigation workflow.

## Why GitHub Codespaces improves reproducibility

Codespaces makes the environment reproducible because it standardizes the runtime and tooling for every learner. The devcontainer definition pins the base image, installs the project tooling, and runs a consistent post-create step:

```bash
uv sync
```

That matters because it reduces drift between machines. Without a controlled environment, a project might work on one machine and fail on another due to a different Python version, missing package, or local file state. With Codespaces, the same configuration can be rebuilt from versioned inputs, making the project easier to teach and easier to verify.

## Configuration files and their role

### pyproject.toml

This file is the project contract. It defines:

- the package name and version,
- the supported Python range,
- the build backend,
- the dependency groups,
- the linting and test settings.

It is the main source of truth for Python package metadata and dev tooling configuration.

### uv.lock

This file locks the exact dependency versions used by the environment. It is generated from `uv sync` and then reused with `uv sync --frozen` to avoid accidental dependency changes across machines or future runs. This is important for deterministic environment rebuilds.

### .env.example

This file documents the expected environment variables without storing secrets. It is the public configuration contract for local development. A local `.env` file may be created by a learner, but it is intentionally ignored by Git so that secrets or local state are not committed.

### .gitignore

This file keeps local and generated artifacts out of version control. It prevents caches, virtual environments, local database files, and generated evidence from polluting the repository. That keeps the project clean and avoids accidental commits of state that should be recreated from inputs.

## Engineering decisions in this phase

### 1. Keep the bootstrap intentionally narrow

The environment phase establishes the base while keeping pipeline, MCP server, and investigation skill responsibilities separate. This makes failures easier to diagnose.

### 2. Keep the repo deterministic

The project favors a reproducible setup over ad hoc local convenience. A frozen dependency lock and pinned Python version help maintain the same result across clones and Codespaces.

### 3. Keep generated state untracked

Files such as DuckDB databases and evidence outputs are deliberately ignored so a fresh environment can rebuild them from code and configuration without mixing them into source control.

## Verification for this phase

This phase is considered complete only when the environment can be created and the quality checks can run successfully:

```bash
uv sync
uv run ruff check .
uv run pytest
```

The checks confirm:

- the Python environment resolves correctly,
- the project metadata is valid,
- the configured linter runs without errors,
- the project test suite passes.

## Learner exercise

Try this quick check in the Codespace:

1. Run `uv sync`.
2. Confirm that `uv.lock` is created or updated.
3. Inspect `pyproject.toml` and explain which tool configuration it contains.
4. Compare `.env.example` and `.gitignore` and describe why both matter for reproducibility.

Prediction: if the environment is configured correctly, the project can be rebuilt from the repo without needing any hidden local state.

## Expected result of the phase

The repository should be in a clean bootstrap state:

- Python version and tooling defined,
- dependencies locked,
- environment variables documented,
- generated data ignored,
- lint and tests runnable.

The pipeline, MCP surface, and investigation skill are documented in their own learning notes. This phase remains intentionally limited to the environment itself.
