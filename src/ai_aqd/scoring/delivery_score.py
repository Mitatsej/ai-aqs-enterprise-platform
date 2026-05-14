"""Delivery scoring logic for AI_AQD.

Delivery scoring converts Gold delivery metrics into a transparent 0-100 score.
The formulas are intentionally simple for the MVP so business users can inspect
and challenge them before more advanced scoring is introduced.
"""

from __future__ import annotations

import pandas as pd


def clamp_score(values: pd.Series) -> pd.Series:
    """Keep score-like values inside the 0-100 range."""
    return values.clip(lower=0, upper=100)


def metric_weight(
    scoring_config: dict,
    dimension_name: str,
    metric_name: str,
    default: float,
) -> float:
    """Read a metric weight from scoring_rules.yaml with a safe fallback."""
    return float(
        scoring_config.get("dimensions", {})
        .get(dimension_name, {})
        .get("metrics", {})
        .get(metric_name, {})
        .get("weight", default)
    )


def inverse_ratio_score(values: pd.Series, worst_allowed_value: float) -> pd.Series:
    """Score a metric where larger values are worse.

    A value of 0 receives 100. A value at or above worst_allowed_value receives 0.
    """
    return clamp_score(100 - (values / worst_allowed_value * 100))


def calculate_delivery_score(project_summary: pd.DataFrame, scoring_config: dict) -> pd.Series:
    """Calculate delivery_score from project-level Gold metrics.

    Formula:
    - sprint_predictability_score rewards completed work versus committed work.
    - velocity_stability_score is an MVP proxy that penalizes deviation from 100%
      completion. Later phases can replace this with true sprint-level variance.
    - scope_change_score penalizes high scope change relative to committed work.
    """
    completion_rate = project_summary["delivery_completion_rate"].fillna(0).astype("float64")
    committed_points = project_summary["total_committed_points"].replace(0, pd.NA)
    scope_change_rate = (
        project_summary["total_scope_change_points"].astype("float64") / committed_points
    ).fillna(0)

    sprint_predictability_score = clamp_score(completion_rate * 100)
    velocity_stability_score = clamp_score(100 - (completion_rate.sub(1).abs() * 200))
    scope_change_score = inverse_ratio_score(scope_change_rate, worst_allowed_value=0.30)

    predictability_weight = metric_weight(
        scoring_config,
        "delivery",
        "sprint_predictability",
        0.40,
    )
    stability_weight = metric_weight(scoring_config, "delivery", "velocity_stability", 0.30)
    scope_weight = metric_weight(scoring_config, "delivery", "scope_change_rate", 0.30)

    score = (
        sprint_predictability_score * predictability_weight
        + velocity_stability_score * stability_weight
        + scope_change_score * scope_weight
    )
    return clamp_score(score).round(2)
