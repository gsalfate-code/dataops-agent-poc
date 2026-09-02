# Project brief

## Purpose

Build a public, educational proof of concept that demonstrates how a Codex agent, a
repository-scoped skill, and an MCP server work separately and together during a Data
Engineering incident investigation.

The project must be understandable by a self-directed learner. Codex may implement the full
solution from one goal, but it must explain each phase, verify it, and leave study material.

## Fictitious business scenario

A payment batch for period `2026-09` expects 10,000 records but publishes 9,880:

- 115 records reference people missing from the fictitious master table.
- 5 records contain invalid payment amounts.
- All 120 invalid records must remain traceable in quarantine.

No real personal, institutional, or production data may be used.

## User experience

The learner opens the repository in GitHub Codespaces, builds the deterministic scenario, and
asks Codex:

> Investigate why the September batch published 9,880 payments when 10,000 were expected. Do
> not modify data. Provide auditable evidence, root cause, impact, and a safe replay proposal.

Codex must activate the investigation skill, call read-only MCP tools, evaluate the returned
evidence, and produce a report. The learner must be able to inspect the observable tool calls
without requiring access to private model reasoning.

## Architecture and responsibilities

| Component | Responsibility |
| --- | --- |
| Data generator | Create deterministic fictitious inputs. |
| Pipeline | Load and transform RAW, STAGING, QUARANTINE, MART, and METADATA layers. |
| Quality module | Evaluate explicit data contracts and rules. |
| DuckDB | Persist local data and investigation evidence. |
| MCP server | Expose typed, read-only business tools backed by DuckDB. |
| Agent skill | Define the repeatable investigation workflow. |
| Codex agent | Choose actions, interpret evidence, and report conclusions. |
| Optional subagent | Complete one bounded, independent analysis for comparison. |
| Evaluation | Verify observable behavior and expected conclusions. |

Keep these responsibilities separate. The skill must not open DuckDB directly, and the MCP
server must not decide the business root cause.

## Functional requirements

### Pipeline

1. Generate the same 10,000 input records from a fixed seed and logical period.
2. Preserve the RAW input for an existing run without overwriting it.
3. Publish 9,880 valid payments to MART.
4. Store all 120 rejected records in QUARANTINE with rule code and run identifier.
5. Store run status, layer counts, hashes, rule results, and timestamps in METADATA.
6. Replaying the same run must not duplicate rows or change its business result.

### MCP server

Expose these initial tools using local `stdio` transport:

- `get_payment_batch(period)` returns expected, published, rejected, and status counts.
- `reconcile_payment_layers(period)` returns counts per layer and the first difference.
- `get_rejection_reasons(period)` returns rejection codes and counts.

The initial MCP server must be read-only. It must validate inputs, return structured responses,
avoid leaking full sensitive-looking records, and record sanitized tool-call audit events.

### Agent skill

Create `.agents/skills/investigate-payment-pipeline/SKILL.md`. It must guide Codex to:

1. confirm the reported difference;
2. reconcile layers;
3. inspect rejection reasons;
4. form and test a hypothesis;
5. separate facts, inferences, and recommendations;
6. cite tool evidence in the final report;
7. avoid modifying data.

Keep the skill focused. Add scripts or references only when they provide concrete value.

### Agent evaluation

Run the same incident investigation first with the main agent alone and then with one bounded
subagent task. Compare correctness, tool usage, duplication, duration, and evidence quality.

Persist sanitized artifacts under `evidence/generated/<investigation-id>/`:

- `prompt.md`
- `tool_calls.jsonl`
- `quality_results.json`
- `final_report.md`
- `evaluation.json`

## Engineering requirements

- Reproducibility: a fresh Codespace can rebuild the environment and scenario.
- Immutability: an existing RAW input is never overwritten.
- Idempotency: replaying a run does not add duplicate effects.
- Determinism: identical input, code, and configuration produce identical business outputs.
- Traceability: every result maps to its run, rules, counts, and input hash.
- Atomicity: MART is published only after validation succeeds for the publishable subset.
- Recoverability: rejected records remain available for a safe replay proposal.
- Least privilege: the initial MCP surface contains no write operation or arbitrary SQL tool.
- Separation of responsibilities: modules are independently testable.

## Autonomy and teaching requirements

Codex must follow `AGENTS.md`. In particular:

- Explain the purpose and decision before each phase, then continue automatically.
- Do not request approval for routine, reversible, local decisions.
- State and record reasonable assumptions instead of asking precautionary questions.
- Stop only for material ambiguity, destructive action, credentials, cost, production access,
  or external writes.
- Create concise learning notes under `docs/learning/` for environment, pipeline, MCP, skill,
  agents, and evaluation.
- Include a small learner exercise and verification command in each learning note.

## Verification

Automated checks must prove at least:

1. generation produces exactly 10,000 input rows;
2. MART contains exactly 9,880 rows;
3. QUARANTINE contains exactly 115 missing-person and 5 invalid-amount rows;
4. a second execution does not change counts or duplicate rows;
5. the RAW hash remains unchanged after replay;
6. repeated generation with the same seed produces the same hash;
7. MCP tools return the expected structured evidence;
8. MCP exposes no write or arbitrary SQL tool;
9. the skill has valid metadata and a discriminating trigger description;
10. the expected investigation identifies both causes and cites evidence.

GitHub Actions must run lint and tests for every push and pull request.

## Out of scope

- Real IPS or other institutional data.
- AWS, Airflow, dbt, Spark, or cloud deployment.
- A custom web chat interface.
- Production authentication and remote MCP hosting.
- Arbitrary SQL through MCP.
- Automatic correction or replay of payments.
- Publishing the skill as a plugin.
- GitHub Spec Kit.

## Definition of done

The project is complete when a fresh Codespace can reproduce the scenario, all automated checks
pass, Codex can investigate it through the repository skill and read-only MCP tools, the result
correctly explains the 115 plus 5 rejected records, and a learner can inspect the evidence and
repeat the exercises without copying unexplained code.

## Master goal for Codex

Use this after the repository is open in Codespaces:

```text
/goal Read AGENTS.md and docs/PROJECT_BRIEF.md, then implement the complete project.

Work phase by phase: environment, deterministic pipeline, read-only MCP server, investigation
skill, agent/subagent evaluation, CI, and learning documentation. Before each phase, explain its
purpose and key decision briefly, then continue without asking for routine local approvals. Run
the relevant checks after every phase, diagnose and correct failures, and do not finish until all
acceptance criteria and the definition of done in PROJECT_BRIEF.md are satisfied.
```
