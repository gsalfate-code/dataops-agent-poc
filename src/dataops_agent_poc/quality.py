from __future__ import annotations

from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Any, NamedTuple

MISSING_PERSON = "MISSING_PERSON"
INVALID_AMOUNT = "INVALID_AMOUNT"
VALID = "VALID"
REJECTED = "REJECTED"


class ValidationRule(NamedTuple):
    code: str
    reason: str
    predicate: Any


def is_missing_person(row: Mapping[str, Any], valid_person_ids: Collection[int]) -> bool:
    return int(row["person_id"]) not in valid_person_ids


def is_invalid_amount(row: Mapping[str, Any], valid_person_ids: Collection[int]) -> bool:
    del valid_person_ids
    return row["amount"] <= Decimal("0.00")


# Order is the rule priority: the first matching rule determines the rejection.
RULES = (
    ValidationRule(MISSING_PERSON, "missing person reference", is_missing_person),
    ValidationRule(INVALID_AMOUNT, "invalid payment amount", is_invalid_amount),
)


def classify_rows(
    raw_rows: list[dict[str, Any]], valid_person_ids: Collection[int]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    classified_rows: list[dict[str, Any]] = []
    rule_counts = {rule.code: 0 for rule in RULES}

    for raw_row in raw_rows:
        classified_row = dict(raw_row)
        classified_row["validation_status"] = VALID
        classified_row["rejection_code"] = None
        classified_row["rejection_reason"] = None

        for rule in RULES:
            if rule.predicate(raw_row, valid_person_ids):
                classified_row["validation_status"] = REJECTED
                classified_row["rejection_code"] = rule.code
                classified_row["rejection_reason"] = rule.reason
                rule_counts[rule.code] += 1
                break

        classified_rows.append(classified_row)

    return classified_rows, rule_counts
