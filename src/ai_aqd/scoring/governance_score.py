"""Governance scoring logic for AI_AQD."""

from __future__ import annotations

import pandas as pd

from ai_aqd.scoring.delivery_score import clamp_score, metric_weight


def calculate_governance_score(project_summary: pd.DataFrame, scoring_config: dict) -> pd.Series:
    """Calculate governance_score from Gold governance metrics.

    Formula:
    - documentation_completeness contributes directly as a 0-100 score.
    - audit_compliance contributes directly as a 0-100 score.
    - risk_review_status is the average of two boolean controls:
      risk_review_current and required_approvals_complete.
    """
    documentation_score = clamp_score(
        project_summary["documentation_completeness"].fillna(0).astype("float64")
    )
    audit_score = clamp_score(project_summary["audit_compliance"].fillna(0).astype("float64"))
    risk_review_score = (
        project_summary[["risk_review_current", "required_approvals_complete"]]
        .fillna(False)
        .astype("bool")
        .mean(axis=1)
        * 100
    )

    documentation_weight = metric_weight(
        scoring_config,
        "governance",
        "documentation_completeness",
        0.30,
    )
    audit_weight = metric_weight(scoring_config, "governance", "audit_compliance", 0.40)
    review_weight = metric_weight(scoring_config, "governance", "risk_review_status", 0.30)

    score = (
        documentation_score * documentation_weight
        + audit_score * audit_weight
        + risk_review_score * review_weight
    )
    return clamp_score(score).round(2)
