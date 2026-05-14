"""Aggregate Silver datasets into Gold analytical outputs.

Gold is the business-ready layer of the Medallion Architecture. In AI_AQD, the
Gold layer creates one project-level table that joins delivery, defect, code
quality, and governance metrics into a shape that scoring and dashboards can use.

This phase intentionally stops at metric aggregation. It does not calculate
quality scores, classify risk, or generate recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_aqd.ingestion.load_sources import (
    DEFAULT_CONFIG_PATH,
    load_data_paths_config,
    resolve_project_path,
)


PROJECT_COLUMNS = [
    "project_id",
    "project_name",
    "business_unit",
    "project_manager",
    "start_date",
    "target_end_date",
    "status",
]

GOLD_PROJECT_RISK_COLUMNS = [
    *PROJECT_COLUMNS,
    "total_committed_points",
    "total_completed_points",
    "delivery_completion_rate",
    "total_scope_change_points",
    "total_defects",
    "escaped_defects",
    "defect_escape_rate",
    "high_or_critical_defects",
    "test_coverage",
    "code_smells",
    "duplicated_code_percentage",
    "technical_debt_ratio",
    "security_hotspots",
    "documentation_completeness",
    "audit_compliance",
    "risk_review_current",
    "required_approvals_complete",
]


@dataclass(frozen=True)
class GoldAggregationResult:
    """Summary of one Silver-to-Gold aggregation output."""

    output_name: str
    output_path: Path
    row_count: int
    messages: list[str]


def silver_input_path(dataset_name: str, silver_dir: Path) -> Path:
    """Return the expected Silver Parquet input path for a dataset."""
    return silver_dir / f"{dataset_name}.parquet"


def read_silver_dataset(dataset_name: str, silver_dir: Path) -> pd.DataFrame:
    """Read one cleaned Silver Parquet dataset."""
    path = silver_input_path(dataset_name, silver_dir)
    if not path.exists():
        raise FileNotFoundError(f"Expected Silver dataset was not found: {path}")
    return pd.read_parquet(path)


def safe_rate(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Calculate a rate while avoiding division-by-zero errors."""
    denominator_as_float = denominator.astype("float64")
    numerator_as_float = numerator.astype("float64")
    rate = numerator_as_float / denominator_as_float.where(denominator_as_float.ne(0))
    return rate.fillna(0.0).round(4)


def aggregate_sprint_metrics(sprint_metrics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sprint delivery metrics to one row per project."""
    summary = (
        sprint_metrics.groupby("project_id", as_index=False)
        .agg(
            total_committed_points=("committed_points", "sum"),
            total_completed_points=("completed_points", "sum"),
            total_scope_change_points=("scope_change_points", "sum"),
        )
        .copy()
    )
    summary["delivery_completion_rate"] = safe_rate(
        summary["total_completed_points"],
        summary["total_committed_points"],
    )
    return summary[
        [
            "project_id",
            "total_committed_points",
            "total_completed_points",
            "delivery_completion_rate",
            "total_scope_change_points",
        ]
    ]


def aggregate_defect_metrics(defects: pd.DataFrame) -> pd.DataFrame:
    """Aggregate defect counts and escape metrics to one row per project."""
    defect_data = defects.copy()
    defect_data["escaped_defect_flag"] = (
        defect_data["escaped_to_production"].fillna(False).astype("bool")
    )
    defect_data["high_or_critical_flag"] = defect_data["severity"].isin(["High", "Critical"])

    summary = (
        defect_data.groupby("project_id", as_index=False)
        .agg(
            total_defects=("defect_id", "count"),
            escaped_defects=("escaped_defect_flag", "sum"),
            high_or_critical_defects=("high_or_critical_flag", "sum"),
        )
        .copy()
    )
    summary["defect_escape_rate"] = safe_rate(
        summary["escaped_defects"],
        summary["total_defects"],
    )
    return summary[
        [
            "project_id",
            "total_defects",
            "escaped_defects",
            "defect_escape_rate",
            "high_or_critical_defects",
        ]
    ]


def select_latest_code_quality(code_quality_metrics: pd.DataFrame) -> pd.DataFrame:
    """Use the latest code quality snapshot for each project."""
    latest = (
        code_quality_metrics.sort_values(["project_id", "measurement_date"])
        .drop_duplicates(subset=["project_id"], keep="last")
        .copy()
    )
    return latest[
        [
            "project_id",
            "test_coverage",
            "code_smells",
            "duplicated_code_percentage",
            "technical_debt_ratio",
            "security_hotspots",
        ]
    ]


def select_latest_governance_metrics(governance_metrics: pd.DataFrame) -> pd.DataFrame:
    """Use the latest governance review snapshot for each project."""
    latest = (
        governance_metrics.sort_values(["project_id", "review_date"])
        .drop_duplicates(subset=["project_id"], keep="last")
        .copy()
    )
    return latest[
        [
            "project_id",
            "documentation_completeness",
            "audit_compliance",
            "risk_review_current",
            "required_approvals_complete",
        ]
    ]


def fill_project_level_defaults(project_summary: pd.DataFrame) -> pd.DataFrame:
    """Fill metric defaults where a project has no child records in a metric domain."""
    cleaned = project_summary.copy()
    zero_default_columns = [
        "total_committed_points",
        "total_completed_points",
        "delivery_completion_rate",
        "total_scope_change_points",
        "total_defects",
        "escaped_defects",
        "defect_escape_rate",
        "high_or_critical_defects",
    ]

    for column in zero_default_columns:
        cleaned[column] = cleaned[column].fillna(0)

    integer_columns = [
        "total_committed_points",
        "total_completed_points",
        "total_scope_change_points",
        "total_defects",
        "escaped_defects",
        "high_or_critical_defects",
    ]
    for column in integer_columns:
        cleaned[column] = cleaned[column].astype("int64")

    return cleaned


def build_project_risk_summary(
    *,
    projects: pd.DataFrame,
    sprint_metrics: pd.DataFrame,
    defects: pd.DataFrame,
    code_quality_metrics: pd.DataFrame,
    governance_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Create the project-level Gold table used by future scoring and dashboards."""
    project_summary = projects[PROJECT_COLUMNS].copy()

    # Gold joins use project_id as the shared business key across all Silver
    # datasets. Projects remain the driving table to guarantee one output row per
    # project even when a child metric domain is missing.
    project_summary = project_summary.merge(
        aggregate_sprint_metrics(sprint_metrics),
        on="project_id",
        how="left",
    )
    project_summary = project_summary.merge(
        aggregate_defect_metrics(defects),
        on="project_id",
        how="left",
    )
    project_summary = project_summary.merge(
        select_latest_code_quality(code_quality_metrics),
        on="project_id",
        how="left",
    )
    project_summary = project_summary.merge(
        select_latest_governance_metrics(governance_metrics),
        on="project_id",
        how="left",
    )

    project_summary = fill_project_level_defaults(project_summary)
    return (
        project_summary[GOLD_PROJECT_RISK_COLUMNS]
        .sort_values("project_id")
        .reset_index(drop=True)
    )


def write_gold_project_risk_summary(
    data: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Write the Gold project summary table to Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output_path, index=False)
    return output_path


def run_silver_to_gold(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> GoldAggregationResult:
    """Read Silver datasets and write the project-level Gold summary output."""
    config = load_data_paths_config(config_path)
    silver_dir = resolve_project_path(config["layers"]["silver"])
    output_path = resolve_project_path(config["gold_outputs"]["project_risk_summary"])

    projects = read_silver_dataset("projects", silver_dir)
    sprint_metrics = read_silver_dataset("sprint_metrics", silver_dir)
    defects = read_silver_dataset("defects", silver_dir)
    code_quality_metrics = read_silver_dataset("code_quality_metrics", silver_dir)
    governance_metrics = read_silver_dataset("governance_metrics", silver_dir)

    project_summary = build_project_risk_summary(
        projects=projects,
        sprint_metrics=sprint_metrics,
        defects=defects,
        code_quality_metrics=code_quality_metrics,
        governance_metrics=governance_metrics,
    )
    write_gold_project_risk_summary(project_summary, output_path)

    return GoldAggregationResult(
        output_name="project_risk_summary",
        output_path=output_path,
        row_count=len(project_summary),
        messages=[
            "Gold output contains one row per project",
            "Gold aggregation calculated metrics only; scoring runs in the next pipeline step",
        ],
    )
