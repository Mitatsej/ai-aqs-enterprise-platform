"""Project quality scoring engine for AI_AQD.

This module reads the Gold project summary, calculates transparent dimension
scores, blends them into an overall project score, classifies risk, and writes
the scored Gold output. Recommendations are intentionally left for a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_aqd.ingestion.load_sources import (
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    load_data_paths_config,
    resolve_project_path,
)
from ai_aqd.risk.classifier import classify_risk_levels
from ai_aqd.scoring.delivery_score import (
    clamp_score,
    inverse_ratio_score,
    metric_weight,
    calculate_delivery_score,
)
from ai_aqd.scoring.governance_score import calculate_governance_score


DEFAULT_SCORING_RULES_PATH = PROJECT_ROOT / "configs" / "scoring_rules.yaml"
DEFAULT_RISK_THRESHOLDS_PATH = PROJECT_ROOT / "configs" / "risk_thresholds.yaml"

DIMENSION_SCORE_COLUMNS = [
    "delivery_score",
    "quality_score",
    "engineering_score",
    "governance_score",
]


@dataclass(frozen=True)
class QualityScoringResult:
    """Summary of the project quality scoring output."""

    output_name: str
    output_path: Path
    row_count: int
    messages: list[str]


def dimension_weight(scoring_config: dict, dimension_name: str, default: float) -> float:
    """Read a dimension weight from scoring_rules.yaml with a safe fallback."""
    return float(
        scoring_config.get("dimensions", {}).get(dimension_name, {}).get("weight", default)
    )


def calculate_quality_score(project_summary: pd.DataFrame, scoring_config: dict) -> pd.Series:
    """Calculate quality_score from defect and test coverage metrics.

    Formula:
    - defect_density_score reaches 0 at 0.16 defects per completed point.
    - escaped_defects_score penalizes the percentage of defects that escaped.
    - test_coverage_score uses the test coverage percentage directly.
    """
    completed_points = project_summary["total_completed_points"].replace(0, pd.NA)
    defect_density = (
        project_summary["total_defects"].astype("float64") / completed_points
    ).fillna(0)

    defect_density_score = inverse_ratio_score(defect_density, worst_allowed_value=0.16)
    escaped_defects_score = inverse_ratio_score(
        project_summary["defect_escape_rate"].fillna(0).astype("float64"),
        worst_allowed_value=0.25,
    )
    test_coverage_score = clamp_score(project_summary["test_coverage"].fillna(0).astype("float64"))

    defect_density_weight = metric_weight(scoring_config, "quality", "defect_density", 0.35)
    escaped_defects_weight = metric_weight(scoring_config, "quality", "escaped_defects", 0.35)
    test_coverage_weight = metric_weight(scoring_config, "quality", "test_coverage", 0.30)

    score = (
        defect_density_score * defect_density_weight
        + escaped_defects_score * escaped_defects_weight
        + test_coverage_score * test_coverage_weight
    )
    return clamp_score(score).round(2)


def calculate_engineering_score(project_summary: pd.DataFrame, scoring_config: dict) -> pd.Series:
    """Calculate engineering_score from code quality metrics.

    Formula:
    - code_smells_score reaches 0 when code smells are at or above 200.
    - duplicated_code_score reaches 0 when duplicated code is at or above 20%.
    - technical_debt_score reaches 0 when technical debt ratio is at or above 25%.
    - security_hotspots_score reaches 0 when hotspots are at or above 20.
    """
    code_smells_score = inverse_ratio_score(
        project_summary["code_smells"].fillna(0).astype("float64"),
        worst_allowed_value=200,
    )
    duplicated_code_score = inverse_ratio_score(
        project_summary["duplicated_code_percentage"].fillna(0).astype("float64"),
        worst_allowed_value=20,
    )
    technical_debt_score = inverse_ratio_score(
        project_summary["technical_debt_ratio"].fillna(0).astype("float64"),
        worst_allowed_value=25,
    )
    security_hotspots_score = inverse_ratio_score(
        project_summary["security_hotspots"].fillna(0).astype("float64"),
        worst_allowed_value=20,
    )

    code_smells_weight = metric_weight(scoring_config, "engineering", "code_smells", 0.25)
    duplicated_code_weight = metric_weight(
        scoring_config,
        "engineering",
        "duplicated_code",
        0.25,
    )
    technical_debt_weight = metric_weight(
        scoring_config,
        "engineering",
        "technical_debt_ratio",
        0.30,
    )
    security_hotspots_weight = metric_weight(
        scoring_config,
        "engineering",
        "security_hotspots",
        0.20,
    )

    score = (
        code_smells_score * code_smells_weight
        + duplicated_code_score * duplicated_code_weight
        + technical_debt_score * technical_debt_weight
        + security_hotspots_score * security_hotspots_weight
    )
    return clamp_score(score).round(2)


def calculate_overall_project_score(
    scored_projects: pd.DataFrame,
    scoring_config: dict,
) -> pd.Series:
    """Blend dimension scores using configured dimension weights."""
    delivery_weight = dimension_weight(scoring_config, "delivery", 0.30)
    quality_weight = dimension_weight(scoring_config, "quality", 0.30)
    engineering_weight = dimension_weight(scoring_config, "engineering", 0.25)
    governance_weight = dimension_weight(scoring_config, "governance", 0.15)

    score = (
        scored_projects["delivery_score"] * delivery_weight
        + scored_projects["quality_score"] * quality_weight
        + scored_projects["engineering_score"] * engineering_weight
        + scored_projects["governance_score"] * governance_weight
    )
    return clamp_score(score).round(2)


def identify_top_negative_contributors(scored_projects: pd.DataFrame) -> pd.Series:
    """Describe the two lowest scoring dimensions for each project."""
    labels = {
        "delivery_score": "Delivery",
        "quality_score": "Quality",
        "engineering_score": "Engineering",
        "governance_score": "Governance",
    }

    contributors: list[str] = []
    for _, row in scored_projects[DIMENSION_SCORE_COLUMNS].iterrows():
        lowest_dimensions = row.sort_values(kind="stable").head(2)
        readable = [
            f"{labels[column]} ({float(score):.2f})"
            for column, score in lowest_dimensions.items()
        ]
        contributors.append("; ".join(readable))

    return pd.Series(contributors, index=scored_projects.index)


def calculate_project_quality_scores(
    project_summary: pd.DataFrame,
    scoring_config: dict,
    risk_config: dict,
) -> pd.DataFrame:
    """Calculate all Phase 6 scoring columns from the Gold project summary."""
    scored_projects = project_summary.copy()
    scored_projects["delivery_score"] = calculate_delivery_score(scored_projects, scoring_config)
    scored_projects["quality_score"] = calculate_quality_score(scored_projects, scoring_config)
    scored_projects["engineering_score"] = calculate_engineering_score(
        scored_projects,
        scoring_config,
    )
    scored_projects["governance_score"] = calculate_governance_score(
        scored_projects,
        scoring_config,
    )
    scored_projects["overall_project_score"] = calculate_overall_project_score(
        scored_projects,
        scoring_config,
    )
    scored_projects["risk_level"] = classify_risk_levels(
        scored_projects["overall_project_score"],
        risk_config,
    )
    scored_projects["top_negative_contributors"] = identify_top_negative_contributors(
        scored_projects
    )
    return scored_projects


def run_quality_scoring(
    *,
    data_paths_config_path: Path = DEFAULT_CONFIG_PATH,
    scoring_rules_path: Path = DEFAULT_SCORING_RULES_PATH,
    risk_thresholds_path: Path = DEFAULT_RISK_THRESHOLDS_PATH,
) -> QualityScoringResult:
    """Read Gold metrics, score projects, and write project_quality_scores."""
    data_paths_config = load_data_paths_config(data_paths_config_path)
    scoring_config = load_data_paths_config(scoring_rules_path)
    risk_config = load_data_paths_config(risk_thresholds_path)

    input_path = resolve_project_path(data_paths_config["gold_outputs"]["project_risk_summary"])
    output_path = resolve_project_path(data_paths_config["gold_outputs"]["project_quality_scores"])

    if not input_path.exists():
        raise FileNotFoundError(f"Expected Gold project summary was not found: {input_path}")

    project_summary = pd.read_parquet(input_path)
    scored_projects = calculate_project_quality_scores(
        project_summary,
        scoring_config,
        risk_config,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scored_projects.to_parquet(output_path, index=False)

    return QualityScoringResult(
        output_name="project_quality_scores",
        output_path=output_path,
        row_count=len(scored_projects),
        messages=[
            "Calculated delivery, quality, engineering, and governance scores",
            "Assigned risk levels from configured score thresholds",
            "Recommendations are not implemented yet",
        ],
    )
