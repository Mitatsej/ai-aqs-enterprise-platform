"""Schema checks for AI_AQD datasets.

Schema validation answers a narrow but important question before transformation:
"Does this dataset contain the columns the pipeline contract requires?"
Missing columns are treated as fatal because the Silver layer cannot reliably
clean or validate data that does not match the expected source shape.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


BRONZE_METADATA_COLUMNS = [
    "ingestion_timestamp",
    "source_file",
    "source_system",
    "batch_id",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "projects": [
        "project_id",
        "project_name",
        "business_unit",
        "project_manager",
        "start_date",
        "target_end_date",
        "status",
        *BRONZE_METADATA_COLUMNS,
    ],
    "sprint_metrics": [
        "project_id",
        "sprint_id",
        "sprint_start_date",
        "sprint_end_date",
        "committed_points",
        "completed_points",
        "scope_change_points",
        *BRONZE_METADATA_COLUMNS,
    ],
    "defects": [
        "defect_id",
        "project_id",
        "severity",
        "created_date",
        "resolved_date",
        "escaped_to_production",
        *BRONZE_METADATA_COLUMNS,
    ],
    "code_quality_metrics": [
        "project_id",
        "measurement_date",
        "test_coverage",
        "code_smells",
        "duplicated_code_percentage",
        "technical_debt_ratio",
        "security_hotspots",
        *BRONZE_METADATA_COLUMNS,
    ],
    "governance_metrics": [
        "project_id",
        "review_date",
        "documentation_completeness",
        "audit_compliance",
        "risk_review_current",
        "required_approvals_complete",
        *BRONZE_METADATA_COLUMNS,
    ],
}


class SchemaValidationError(ValueError):
    """Raised when a dataset does not satisfy its required column contract."""


def required_columns_for(dataset_name: str) -> list[str]:
    """Return required columns for a known dataset."""
    try:
        return REQUIRED_COLUMNS[dataset_name]
    except KeyError as exc:
        raise SchemaValidationError(f"Unknown dataset: {dataset_name}") from exc


def find_missing_columns(columns: Iterable[str], required_columns: Iterable[str]) -> list[str]:
    """Compare actual columns with required columns."""
    actual = set(columns)
    return [column for column in required_columns if column not in actual]


def ensure_required_columns(dataset_name: str, data: pd.DataFrame) -> None:
    """Fail fast when a dataset is missing required columns."""
    missing_columns = find_missing_columns(data.columns, required_columns_for(dataset_name))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise SchemaValidationError(f"{dataset_name} is missing required columns: {missing}")
