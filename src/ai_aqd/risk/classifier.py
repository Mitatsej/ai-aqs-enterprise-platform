"""Risk classification for scored AI_AQD projects."""

from __future__ import annotations

import pandas as pd


def classify_score(score: float, risk_config: dict) -> str:
    """Assign a risk level using configured score thresholds.

    The MVP classifier uses score bands only. Configured override rules are kept
    for a later phase when explicit governance and defect overrides are added.
    """
    if pd.isna(score):
        return "Critical"

    risk_levels = risk_config.get("risk_levels", {})
    ordered_levels = sorted(
        risk_levels.items(),
        key=lambda item: item[1].get("minimum_score", 0),
        reverse=True,
    )

    for level_name, thresholds in ordered_levels:
        if float(score) >= float(thresholds["minimum_score"]):
            return level_name.title()

    return "Critical"


def classify_risk_levels(scores: pd.Series, risk_config: dict) -> pd.Series:
    """Classify many project scores into Low, Medium, High, or Critical."""
    return scores.apply(lambda score: classify_score(score, risk_config))
