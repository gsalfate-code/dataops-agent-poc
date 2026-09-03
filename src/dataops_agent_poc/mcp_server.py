from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from dataops_agent_poc.mcp_business import (
    get_payment_batch,
    get_rejection_reasons,
    reconcile_payment_layers,
)

mcp = FastMCP("dataops-reliability")
READ_ONLY_IDEMPOTENT = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


class PaymentBatchResponse(BaseModel):
    run_id: str
    period: str
    expected_count: int
    raw_count: int
    staging_count: int
    published_count: int
    rejected_count: int
    status: str
    raw_hash: str
    rule_counts: dict[str, int]
    created_at: str


class LayerDifference(BaseModel):
    check: str
    magnitude: int


class LayerReconciliationResponse(BaseModel):
    period: str
    counts: dict[str, int]
    checks: dict[str, bool]
    first_difference: LayerDifference | None


class RejectionReason(BaseModel):
    code: str
    reason: str
    count: int


class RejectionReasonsResponse(BaseModel):
    period: str
    reasons: list[RejectionReason]
    total_rejected: int


@mcp.tool(
    name="get_payment_batch",
    description="Return aggregated metadata and counts for a payment batch.",
    annotations=READ_ONLY_IDEMPOTENT,
    structured_output=True,
)
def payment_batch(period: str) -> PaymentBatchResponse:
    return PaymentBatchResponse.model_validate(get_payment_batch(period))


@mcp.tool(
    name="reconcile_payment_layers",
    description="Compare aggregated counts across payment layers.",
    annotations=READ_ONLY_IDEMPOTENT,
    structured_output=True,
)
def payment_layers(period: str) -> LayerReconciliationResponse:
    return LayerReconciliationResponse.model_validate(reconcile_payment_layers(period))


@mcp.tool(
    name="get_rejection_reasons",
    description="Return aggregated rejection reasons for a payment batch.",
    annotations=READ_ONLY_IDEMPOTENT,
    structured_output=True,
)
def rejection_reasons(period: str) -> RejectionReasonsResponse:
    return RejectionReasonsResponse.model_validate(get_rejection_reasons(period))


if __name__ == "__main__":
    mcp.run("stdio")
