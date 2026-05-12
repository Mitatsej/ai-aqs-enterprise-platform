"""Reusable row-level quality checks for Silver transformations.

Silver validation focuses on making data usable and trustworthy for analytics:
business keys must be present, related datasets must point to known projects,
numeric values must be plausible, and important categorical values must be
standardized before Gold metrics are calculated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


VALID_DEFECT_SEVERITIES = {"Low", "Medium", "High", "Critical"}


@dataclass(frozen=True)
class QualityCheckResult:
    """A cleaned dataset plus human-readable validation messages."""

    data: pd.DataFrame
    messages: list[str]


def _message(dataset_name: str, text: str) -> str:
    return f"{dataset_name}: {text}"


def remove_duplicate_rows(
    dataset_name: str,
    data: pd.DataFrame,
    subset: list[str] | None = None,
) -> QualityCheckResult:
    """Remove duplicate rows or duplicate business keys, keeping the first record."""
    before = len(data)
    cleaned = data.drop_duplicates(subset=subset, keep="first").copy()
    removed = before - len(cleaned)

    messages = []
    if removed:
        key_description = "full row" if subset is None else ", ".join(subset)
        messages.append(
            _message(dataset_name, f"removed {removed} duplicate rows by {key_description}")
        )
    return QualityCheckResult(cleaned, messages)


def reject_null_project_ids(dataset_name: str, data: pd.DataFrame) -> QualityCheckResult:
    """Reject records that cannot be tied back to a project."""
    valid_mask = data["project_id"].notna() & data["project_id"].astype("string").str.strip().ne(
        ""
    )
    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        messages.append(_message(dataset_name, f"rejected {rejected} rows with null project_id"))
    return QualityCheckResult(cleaned, messages)


def reject_null_values(
    dataset_name: str,
    data: pd.DataFrame,
    columns: list[str],
    reason: str,
) -> QualityCheckResult:
    """Reject rows where required cleaned values are missing."""
    if not columns:
        return QualityCheckResult(data.copy(), [])

    valid_mask = data[columns].notna().all(axis=1)
    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        column_list = ", ".join(columns)
        messages.append(
            _message(
                dataset_name,
                f"rejected {rejected} rows with missing {reason}: {column_list}",
            )
        )
    return QualityCheckResult(cleaned, messages)


def validate_project_references(
    dataset_name: str,
    data: pd.DataFrame,
    valid_project_ids: set[str],
) -> QualityCheckResult:
    """Reject child records whose project_id does not exist in the Silver projects table."""
    if dataset_name == "projects":
        return QualityCheckResult(data.copy(), [])

    valid_mask = data["project_id"].isin(valid_project_ids)
    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        messages.append(_message(dataset_name, f"rejected {rejected} rows with unknown project_id"))
    return QualityCheckResult(cleaned, messages)


def validate_non_negative_metrics(
    dataset_name: str,
    data: pd.DataFrame,
    columns: list[str],
) -> QualityCheckResult:
    """Reject rows where populated numeric metrics are negative."""
    if not columns:
        return QualityCheckResult(data.copy(), [])

    valid_mask = pd.Series(True, index=data.index)
    for column in columns:
        values = pd.to_numeric(data[column], errors="coerce")
        valid_mask &= values.isna() | values.ge(0)

    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        messages.append(
            _message(dataset_name, f"rejected {rejected} rows with negative numeric metrics")
        )
    return QualityCheckResult(cleaned, messages)


def validate_percentage_ranges(
    dataset_name: str,
    data: pd.DataFrame,
    columns: list[str],
) -> QualityCheckResult:
    """Reject rows where populated percentage metrics fall outside 0 to 100."""
    if not columns:
        return QualityCheckResult(data.copy(), [])

    valid_mask = pd.Series(True, index=data.index)
    for column in columns:
        values = pd.to_numeric(data[column], errors="coerce")
        valid_mask &= values.isna() | values.between(0, 100)

    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        column_list = ", ".join(columns)
        messages.append(
            _message(
                dataset_name,
                f"rejected {rejected} rows with invalid percentages: {column_list}",
            )
        )
    return QualityCheckResult(cleaned, messages)


def validate_allowed_values(
    dataset_name: str,
    data: pd.DataFrame,
    column: str,
    allowed_values: set[Any],
) -> QualityCheckResult:
    """Reject rows where populated categorical values are outside an allowed set."""
    valid_mask = data[column].isin(allowed_values)
    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        allowed = ", ".join(str(value) for value in sorted(allowed_values))
        messages.append(
            _message(
                dataset_name,
                f"rejected {rejected} rows with invalid {column}; allowed: {allowed}",
            )
        )
    return QualityCheckResult(cleaned, messages)


def validate_date_order(
    dataset_name: str,
    data: pd.DataFrame,
    start_column: str,
    end_column: str,
    *,
    end_required: bool,
) -> QualityCheckResult:
    """Reject rows with invalid date ranges.

    When end_required is false, a missing end date is allowed. This supports open
    defects where resolved_date is intentionally blank.
    """
    start_present = data[start_column].notna()
    end_present = data[end_column].notna()
    end_validity = end_present if end_required else (end_present | data[end_column].isna())
    order_validity = data[end_column].ge(data[start_column]) | (~end_present & ~end_required)
    valid_mask = start_present & end_validity & order_validity

    rejected = int((~valid_mask).sum())
    cleaned = data.loc[valid_mask].copy()

    messages = []
    if rejected:
        messages.append(
            _message(
                dataset_name,
                f"rejected {rejected} rows with invalid date order: {start_column}, {end_column}",
            )
        )
    return QualityCheckResult(cleaned, messages)


def describe_sprint_point_variance(data: pd.DataFrame) -> list[str]:
    """Log sprint delivery variance without rejecting records."""
    messages: list[str] = []
    under_delivered = int(data["committed_points"].gt(data["completed_points"]).sum())
    over_delivered = int(data["completed_points"].gt(data["committed_points"]).sum())

    if under_delivered:
        messages.append(
            _message(
                "sprint_metrics",
                f"logged {under_delivered} sprints where committed_points exceed completed_points",
            )
        )
    if over_delivered:
        messages.append(
            _message(
                "sprint_metrics",
                f"logged {over_delivered} sprints where completed_points exceed committed_points",
            )
        )
    return messages
