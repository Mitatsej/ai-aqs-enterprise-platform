"""Rule-based recommendation engine for AI_AQD.

The MVP uses deterministic rules instead of LLM integration so every
recommendation is explainable, repeatable, and traceable to project scores.
This gives stakeholders confidence in the scoring model before generated
language or advanced AI is introduced.
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


WEAK_DIMENSION_THRESHOLD = 70.0
WATCH_DIMENSION_THRESHOLD = 85.0

IDENTIFIER_COLUMNS = [
    "project_id",
    "project_name",
    "business_unit",
    "project_manager",
    "status",
]

SCORE_COLUMNS = [
    "delivery_score",
    "quality_score",
    "engineering_score",
    "governance_score",
    "overall_project_score",
    "risk_level",
    "top_negative_contributors",
]

RECOMMENDATION_COLUMNS = [
    *IDENTIFIER_COLUMNS,
    *SCORE_COLUMNS,
    "executive_summary",
    "risk_explanation",
    "recommended_actions",
]

DIMENSION_LABELS = {
    "delivery_score": "delivery",
    "quality_score": "quality",
    "engineering_score": "engineering",
    "governance_score": "governance",
}

DIMENSION_ACTIONS = {
    "delivery_score": [
        "Improve sprint planning discipline",
        "Reduce scope changes during active sprints",
        "Stabilize delivery commitments against team capacity",
    ],
    "quality_score": [
        "Reduce escaped defects through stronger release gates",
        "Prioritize defect triage for high-impact issues",
        "Improve QA gates before production deployment",
    ],
    "engineering_score": [
        "Improve automated test coverage",
        "Reduce technical debt in high-change components",
        "Address security hotspots and maintainability issues",
    ],
    "governance_score": [
        "Improve required project documentation",
        "Complete outstanding approvals",
        "Refresh risk reviews and governance evidence",
    ],
}

RISK_OPENERS = {
    "Low": "Project is currently healthy and should stay on standard monitoring.",
    "Medium": "Project has manageable concerns that should be monitored closely.",
    "High": "Project has material risk and needs focused intervention.",
    "Critical": "Project requires immediate leadership attention and recovery planning.",
}


@dataclass(frozen=True)
class RecommendationResult:
    """Summary of the recommendation output."""

    output_name: str
    output_path: Path
    row_count: int
    messages: list[str]


def weak_dimensions(project: pd.Series) -> list[str]:
    """Return dimensions that are weak enough to trigger action recommendations."""
    weak = [
        column
        for column in DIMENSION_LABELS
        if float(project[column]) < WEAK_DIMENSION_THRESHOLD
    ]
    if weak:
        return sorted(weak, key=lambda column: float(project[column]))

    watch = [
        column
        for column in DIMENSION_LABELS
        if float(project[column]) < WATCH_DIMENSION_THRESHOLD
    ]
    return sorted(watch, key=lambda column: float(project[column]))[:2]


def executive_summary(project: pd.Series) -> str:
    """Create a short executive summary tied to risk and overall score."""
    opener = RISK_OPENERS.get(project["risk_level"], RISK_OPENERS["Critical"])
    return (
        f"{opener} Overall project score is {project['overall_project_score']:.2f}. "
        f"Primary weak areas: {project['top_negative_contributors']}."
    )


def risk_explanation(project: pd.Series) -> str:
    """Explain why the project received its current risk posture."""
    dimensions = {
        "delivery": project["delivery_score"],
        "quality": project["quality_score"],
        "engineering": project["engineering_score"],
        "governance": project["governance_score"],
    }
    dimension_text = ", ".join(
        f"{name}={float(score):.2f}" for name, score in dimensions.items()
    )
    return (
        f"Risk level is {project['risk_level']} based on the overall score band. "
        f"Dimension scores are {dimension_text}. "
        f"The lowest contributors are {project['top_negative_contributors']}."
    )


def recommended_actions(project: pd.Series) -> str:
    """Generate action recommendations from weak dimensions."""
    triggered_dimensions = weak_dimensions(project)
    actions: list[str] = []

    for dimension in triggered_dimensions:
        actions.extend(DIMENSION_ACTIONS[dimension])

    if not actions:
        actions = [
            "Continue standard project monitoring",
            "Maintain current delivery, quality, engineering, and governance practices",
        ]

    unique_actions = list(dict.fromkeys(actions))
    return "; ".join(unique_actions)


def build_recommendations(scored_projects: pd.DataFrame) -> pd.DataFrame:
    """Create recommendation text columns for each scored project."""
    recommendations = scored_projects.copy()
    recommendations["executive_summary"] = recommendations.apply(executive_summary, axis=1)
    recommendations["risk_explanation"] = recommendations.apply(risk_explanation, axis=1)
    recommendations["recommended_actions"] = recommendations.apply(recommended_actions, axis=1)
    return recommendations[RECOMMENDATION_COLUMNS].sort_values("project_id").reset_index(drop=True)


def run_recommendation_engine(
    *,
    data_paths_config_path: Path = DEFAULT_CONFIG_PATH,
) -> RecommendationResult:
    """Read scored Gold projects and write rule-based recommendations."""
    data_paths_config = load_data_paths_config(data_paths_config_path)
    input_path = resolve_project_path(data_paths_config["gold_outputs"]["project_quality_scores"])
    output_path = resolve_project_path(data_paths_config["gold_outputs"]["recommendations"])

    if not input_path.exists():
        raise FileNotFoundError(f"Expected scored project output was not found: {input_path}")

    scored_projects = pd.read_parquet(input_path)
    recommendations = build_recommendations(scored_projects)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_parquet(output_path, index=False)

    return RecommendationResult(
        output_name="recommendations",
        output_path=output_path,
        row_count=len(recommendations),
        messages=[
            "Generated deterministic recommendations from score dimensions",
            "No LLM integration is used in the MVP recommendation engine",
        ],
    )
