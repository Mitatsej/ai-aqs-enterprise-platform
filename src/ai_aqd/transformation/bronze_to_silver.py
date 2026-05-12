"""Transform Bronze datasets into cleaned Silver datasets.

Silver is the quality layer of the Medallion Architecture. It keeps Bronze
lineage metadata, but applies practical cleaning and validation so downstream
Gold scoring can trust keys, types, ranges, and categorical values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype

from ai_aqd.ingestion.load_sources import (
    DEFAULT_CONFIG_PATH,
    load_data_paths_config,
    resolve_project_path,
)
from ai_aqd.validation.quality_checks import (
    VALID_DEFECT_SEVERITIES,
    QualityCheckResult,
    describe_sprint_point_variance,
    reject_null_project_ids,
    reject_null_values,
    remove_duplicate_rows,
    validate_allowed_values,
    validate_date_order,
    validate_non_negative_metrics,
    validate_percentage_ranges,
    validate_project_references,
)
from ai_aqd.validation.schema_checks import ensure_required_columns


DATASET_ORDER = [
    "projects",
    "sprint_metrics",
    "defects",
    "code_quality_metrics",
    "governance_metrics",
]

DATE_COLUMNS = {
    "projects": ["start_date", "target_end_date"],
    "sprint_metrics": ["sprint_start_date", "sprint_end_date"],
    "defects": ["created_date", "resolved_date"],
    "code_quality_metrics": ["measurement_date"],
    "governance_metrics": ["review_date"],
}

REQUIRED_DATE_COLUMNS = {
    "projects": ["start_date", "target_end_date"],
    "sprint_metrics": ["sprint_start_date", "sprint_end_date"],
    "defects": ["created_date"],
    "code_quality_metrics": ["measurement_date"],
    "governance_metrics": ["review_date"],
}

BOOLEAN_COLUMNS = {
    "defects": ["escaped_to_production"],
    "governance_metrics": ["risk_review_current", "required_approvals_complete"],
}

NUMERIC_COLUMNS = {
    "sprint_metrics": ["committed_points", "completed_points", "scope_change_points"],
    "code_quality_metrics": [
        "test_coverage",
        "code_smells",
        "duplicated_code_percentage",
        "technical_debt_ratio",
        "security_hotspots",
    ],
    "governance_metrics": ["documentation_completeness", "audit_compliance"],
}

PERCENTAGE_COLUMNS = {
    "code_quality_metrics": ["test_coverage", "duplicated_code_percentage"],
    "governance_metrics": ["documentation_completeness", "audit_compliance"],
}

DEDUPLICATION_KEYS = {
    "projects": ["project_id"],
    "sprint_metrics": ["sprint_id"],
    "defects": ["defect_id"],
    "code_quality_metrics": ["project_id", "measurement_date"],
    "governance_metrics": ["project_id", "review_date"],
}

STATUS_MAPPING = {
    "active": "Active",
    "at risk": "At Risk",
    "atrisk": "At Risk",
    "critical": "Critical",
    "completed": "Completed",
    "complete": "Completed",
    "on hold": "On Hold",
}

SEVERITY_MAPPING = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}

BOOLEAN_MAPPING = {
    "true": True,
    "t": True,
    "yes": True,
    "y": True,
    "1": True,
    "false": False,
    "f": False,
    "no": False,
    "n": False,
    "0": False,
}


@dataclass(frozen=True)
class SilverTransformationResult:
    """Summary of one Bronze-to-Silver transformation."""

    dataset_name: str
    bronze_path: Path
    silver_path: Path
    input_rows: int
    output_rows: int
    dropped_rows: int
    messages: list[str]


def bronze_input_path(dataset_name: str, bronze_dir: Path) -> Path:
    """Return the expected Bronze Parquet input path for a dataset."""
    return bronze_dir / f"{dataset_name}.parquet"


def silver_output_path(dataset_name: str, silver_dir: Path) -> Path:
    """Return the Silver Parquet output path for a dataset."""
    return silver_dir / f"{dataset_name}.parquet"


def _append_result(
    result: QualityCheckResult,
    messages: list[str],
) -> pd.DataFrame:
    messages.extend(result.messages)
    return result.data


def strip_string_values(data: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace in text-like columns without changing the column set."""
    cleaned = data.copy()
    for column in cleaned.columns:
        if is_object_dtype(cleaned[column]) or is_string_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].astype("string").str.strip()
    return cleaned


def parse_date_columns(
    dataset_name: str,
    data: pd.DataFrame,
    messages: list[str],
) -> pd.DataFrame:
    """Parse configured date columns into pandas datetime values."""
    cleaned = data.copy()
    for column in DATE_COLUMNS.get(dataset_name, []):
        before_nulls = int(cleaned[column].isna().sum())
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
        after_nulls = int(cleaned[column].isna().sum())
        newly_invalid = after_nulls - before_nulls
        if newly_invalid:
            messages.append(
                f"{dataset_name}: parsed {column}; {newly_invalid} values became invalid dates"
            )
    return cleaned


def convert_numeric_columns(dataset_name: str, data: pd.DataFrame) -> pd.DataFrame:
    """Convert metric columns to numeric types for validation and downstream aggregation."""
    cleaned = data.copy()
    for column in NUMERIC_COLUMNS.get(dataset_name, []):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def normalize_boolean_columns(
    dataset_name: str,
    data: pd.DataFrame,
    messages: list[str],
) -> pd.DataFrame:
    """Normalize common boolean text values into nullable boolean columns."""
    cleaned = data.copy()
    for column in BOOLEAN_COLUMNS.get(dataset_name, []):
        normalized = cleaned[column].astype("string").str.strip().str.lower().map(BOOLEAN_MAPPING)
        invalid_values = int(normalized.isna().sum() - cleaned[column].isna().sum())
        if invalid_values:
            messages.append(
                f"{dataset_name}: normalized {column}; {invalid_values} values became unknown"
            )
        cleaned[column] = normalized.astype("boolean")
    return cleaned


def standardize_project_status(data: pd.DataFrame, messages: list[str]) -> pd.DataFrame:
    """Standardize project status labels while keeping unknown labels readable."""
    cleaned = data.copy()
    normalized_status = (
        cleaned["status"].astype("string").str.strip().str.lower().str.replace("_", " ")
    )
    standardized = normalized_status.map(STATUS_MAPPING)
    unknown_count = int(standardized.isna().sum())

    readable_status = cleaned["status"].astype("string").str.strip().str.title()
    cleaned["status"] = standardized.fillna(readable_status)
    if unknown_count:
        messages.append(
            f"projects: standardized status values; {unknown_count} unknown labels kept"
        )
    return cleaned


def standardize_defect_severity(data: pd.DataFrame) -> pd.DataFrame:
    """Standardize defect severity capitalization before allowed-value validation."""
    cleaned = data.copy()
    normalized_severity = cleaned["severity"].astype("string").str.strip().str.lower()
    cleaned["severity"] = normalized_severity.map(SEVERITY_MAPPING)
    return cleaned


def apply_general_cleaning(
    dataset_name: str,
    data: pd.DataFrame,
    messages: list[str],
) -> pd.DataFrame:
    """Apply common Silver cleaning: trim text, type dates, booleans, and numerics."""
    cleaned = strip_string_values(data)
    cleaned = parse_date_columns(dataset_name, cleaned, messages)
    cleaned = convert_numeric_columns(dataset_name, cleaned)
    cleaned = normalize_boolean_columns(dataset_name, cleaned, messages)
    return cleaned


def apply_common_validations(
    dataset_name: str,
    data: pd.DataFrame,
    valid_project_ids: set[str],
    messages: list[str],
) -> pd.DataFrame:
    """Apply validations shared by all datasets."""
    cleaned = _append_result(reject_null_project_ids(dataset_name, data), messages)
    cleaned = _append_result(
        reject_null_values(
            dataset_name,
            cleaned,
            REQUIRED_DATE_COLUMNS.get(dataset_name, []),
            "required dates",
        ),
        messages,
    )
    cleaned = _append_result(
        validate_project_references(dataset_name, cleaned, valid_project_ids),
        messages,
    )
    cleaned = _append_result(
        validate_non_negative_metrics(dataset_name, cleaned, NUMERIC_COLUMNS.get(dataset_name, [])),
        messages,
    )
    cleaned = _append_result(
        validate_percentage_ranges(dataset_name, cleaned, PERCENTAGE_COLUMNS.get(dataset_name, [])),
        messages,
    )
    cleaned = _append_result(
        remove_duplicate_rows(dataset_name, cleaned, DEDUPLICATION_KEYS.get(dataset_name)),
        messages,
    )
    return cleaned


def apply_dataset_specific_validations(
    dataset_name: str,
    data: pd.DataFrame,
    messages: list[str],
) -> pd.DataFrame:
    """Apply validations that only make sense for one dataset."""
    cleaned = data

    if dataset_name == "projects":
        cleaned = standardize_project_status(cleaned, messages)
        cleaned = _append_result(
            validate_date_order(
                dataset_name,
                cleaned,
                "start_date",
                "target_end_date",
                end_required=True,
            ),
            messages,
        )

    if dataset_name == "sprint_metrics":
        messages.extend(describe_sprint_point_variance(cleaned))
        cleaned = _append_result(
            validate_date_order(
                dataset_name,
                cleaned,
                "sprint_start_date",
                "sprint_end_date",
                end_required=True,
            ),
            messages,
        )

    if dataset_name == "defects":
        cleaned = standardize_defect_severity(cleaned)
        cleaned = _append_result(
            validate_allowed_values(
                dataset_name,
                cleaned,
                "severity",
                VALID_DEFECT_SEVERITIES,
            ),
            messages,
        )
        cleaned = _append_result(
            validate_date_order(
                dataset_name,
                cleaned,
                "created_date",
                "resolved_date",
                end_required=False,
            ),
            messages,
        )

    return cleaned


def transform_bronze_dataset(
    dataset_name: str,
    bronze_data: pd.DataFrame,
    valid_project_ids: set[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Clean and validate one Bronze dataset for the Silver layer."""
    ensure_required_columns(dataset_name, bronze_data)

    messages = [f"{dataset_name}: schema validation passed"]
    cleaned = apply_general_cleaning(dataset_name, bronze_data, messages)
    cleaned = apply_dataset_specific_validations(dataset_name, cleaned, messages)
    cleaned = apply_common_validations(dataset_name, cleaned, valid_project_ids, messages)
    messages.append(f"{dataset_name}: Silver output contains {len(cleaned)} rows")
    return cleaned, messages


def read_bronze_dataset(dataset_name: str, bronze_dir: Path) -> pd.DataFrame:
    """Read one Bronze Parquet dataset."""
    path = bronze_input_path(dataset_name, bronze_dir)
    if not path.exists():
        raise FileNotFoundError(f"Expected Bronze dataset was not found: {path}")
    return pd.read_parquet(path)


def write_silver_dataset(dataset_name: str, silver_dir: Path, data: pd.DataFrame) -> Path:
    """Write one cleaned Silver Parquet dataset."""
    silver_dir.mkdir(parents=True, exist_ok=True)
    path = silver_output_path(dataset_name, silver_dir)
    data.to_parquet(path, index=False)
    return path


def run_bronze_to_silver(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> list[SilverTransformationResult]:
    """Read all Bronze datasets, validate them, and write Silver Parquet outputs."""
    config = load_data_paths_config(config_path)
    bronze_dir = resolve_project_path(config["layers"]["bronze"])
    silver_dir = resolve_project_path(config["layers"]["silver"])

    results: list[SilverTransformationResult] = []
    valid_project_ids: set[str] = set()

    for dataset_name in DATASET_ORDER:
        bronze_path = bronze_input_path(dataset_name, bronze_dir)
        bronze_data = read_bronze_dataset(dataset_name, bronze_dir)
        input_rows = len(bronze_data)

        silver_data, messages = transform_bronze_dataset(
            dataset_name,
            bronze_data,
            valid_project_ids,
        )
        silver_path = write_silver_dataset(dataset_name, silver_dir, silver_data)

        if dataset_name == "projects":
            valid_project_ids = set(silver_data["project_id"].astype("string"))

        results.append(
            SilverTransformationResult(
                dataset_name=dataset_name,
                bronze_path=bronze_path,
                silver_path=silver_path,
                input_rows=input_rows,
                output_rows=len(silver_data),
                dropped_rows=input_rows - len(silver_data),
                messages=messages,
            )
        )

    return results
