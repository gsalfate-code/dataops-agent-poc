from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

EXPECTED_COUNT = 10_000
INVALID_MISSING_PERSON_COUNT = 115
INVALID_AMOUNT_COUNT = 5
MONEY_QUANTUM = Decimal("0.01")


def format_amount(amount: Decimal) -> str:
    return f"{amount.quantize(MONEY_QUANTUM):.2f}"


def generate_raw_rows(period: str, seed: int) -> list[dict[str, Any]]:
    """Generate a deterministic, fictitious payment batch for the given period."""
    rows: list[dict[str, Any]] = []
    for row_id in range(1, EXPECTED_COUNT + 1):
        if row_id <= INVALID_MISSING_PERSON_COUNT:
            person_id = 999_999 + row_id
            amount = Decimal("100.00")
        elif row_id <= INVALID_MISSING_PERSON_COUNT + INVALID_AMOUNT_COUNT:
            person_id = (row_id % 100) + 1
            amount = Decimal("-1.00")
        else:
            person_id = ((row_id * 17 + seed * 11) % 1000) + 1
            amount = Decimal((row_id * 37 + seed * 13) % 5000) + Decimal("10.00")

        rows.append(
            {
                "payment_id": f"pay-{period}-{row_id:05d}",
                "period": period,
                "person_id": person_id,
                "amount": amount.quantize(MONEY_QUANTUM),
                "source_row_id": row_id,
            }
        )
    return rows


def compute_raw_hash(raw_rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        (
            f"{row['payment_id']}|{row['period']}|{row['person_id']}|"
            f"{format_amount(row['amount'])}|"
            f"{row['source_row_id']}"
        )
        for row in raw_rows
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
