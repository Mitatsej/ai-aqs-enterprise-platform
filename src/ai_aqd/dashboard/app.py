"""Executive Streamlit dashboard for AI_AQD.

The dashboard is a presentation layer over Gold outputs. It should not contain
pipeline transformation, scoring, or recommendation logic. Its responsibility is
to make the trusted Gold datasets easy for executives to scan, filter, compare,
and drill into.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATHS_CONFIG = PROJECT_ROOT / "configs" / "data_paths.yaml"

RISK_ORDER = ["Low", "Medium", "High", "Critical"]
RISK_SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
RISK_COLORS = ["#2E7D32", "#F9A825", "#EF6C00", "#C62828"]

DIMENSION_COLUMNS = [
    "delivery_score",
    "quality_score",
    "engineering_score",
    "governance_score",
]

DIMENSION_LABELS = {
    "delivery_score": "Delivery",
    "quality_score": "Quality",
    "engineering_score": "Engineering",
    "governance_score": "Governance",
}


def resolve_project_path(path_value: str | Path) -> Path:
    """Resolve a repository-relative path from configs/data_paths.yaml."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@st.cache_data(show_spinner=False)
def load_gold_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load scored project data and recommendation text from the Gold layer."""
    with DATA_PATHS_CONFIG.open("r", encoding="utf-8") as config_file:
        data_paths_config = yaml.safe_load(config_file)

    scored_path = resolve_project_path(
        data_paths_config["gold_outputs"]["project_quality_scores"]
    )
    recommendations_path = resolve_project_path(
        data_paths_config["gold_outputs"]["recommendations"]
    )

    if not scored_path.exists() or not recommendations_path.exists():
        missing_paths = [
            str(path)
            for path in [scored_path, recommendations_path]
            if not path.exists()
        ]
        raise FileNotFoundError(
            "Gold dashboard inputs are missing. Run the pipeline first: "
            + ", ".join(missing_paths)
        )

    scored_projects = pd.read_parquet(scored_path)
    recommendations = pd.read_parquet(recommendations_path)
    return scored_projects, recommendations


def risk_sort_key(risk_level: str) -> int:
    """Sort risk levels in executive severity order."""
    if risk_level in RISK_SEVERITY_ORDER:
        return RISK_SEVERITY_ORDER.index(risk_level)
    return len(RISK_SEVERITY_ORDER)


def apply_filters(
    scored_projects: pd.DataFrame,
    selected_risks: list[str],
    selected_units: list[str],
) -> pd.DataFrame:
    """Apply sidebar filters consistently across dashboard sections."""
    filtered = scored_projects.copy()
    if selected_risks:
        filtered = filtered[filtered["risk_level"].isin(selected_risks)]
    if selected_units:
        filtered = filtered[filtered["business_unit"].isin(selected_units)]
    return filtered


def render_kpis(filtered_projects: pd.DataFrame) -> None:
    """Render top-level executive health indicators."""
    total_projects = len(filtered_projects)
    average_score = filtered_projects["overall_project_score"].mean()
    risk_counts = filtered_projects["risk_level"].value_counts()

    columns = st.columns(6)
    columns[0].metric("Total Projects", f"{total_projects}")
    columns[1].metric("Average Score", f"{average_score:.1f}" if total_projects else "0.0")
    for index, risk_level in enumerate(RISK_ORDER, start=2):
        columns[index].metric(risk_level, f"{int(risk_counts.get(risk_level, 0))}")


def risk_distribution_chart(filtered_projects: pd.DataFrame) -> alt.Chart:
    """Build a risk level distribution chart."""
    distribution = (
        filtered_projects["risk_level"]
        .value_counts()
        .reindex(RISK_ORDER, fill_value=0)
        .rename_axis("risk_level")
        .reset_index(name="project_count")
    )
    return (
        alt.Chart(distribution)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("risk_level:N", sort=RISK_ORDER, title="Risk Level"),
            y=alt.Y("project_count:Q", title="Projects"),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(domain=RISK_ORDER, range=RISK_COLORS),
                legend=None,
            ),
            tooltip=["risk_level", "project_count"],
        )
        .properties(height=260)
    )


def score_comparison_chart(filtered_projects: pd.DataFrame) -> alt.Chart:
    """Build an overall project score comparison chart."""
    chart_data = filtered_projects.sort_values("overall_project_score", ascending=True)
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            x=alt.X(
                "overall_project_score:Q",
                title="Overall Score",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y("project_name:N", sort=None, title="Project"),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(domain=RISK_ORDER, range=RISK_COLORS),
                title="Risk",
            ),
            tooltip=["project_id", "project_name", "overall_project_score", "risk_level"],
        )
        .properties(height=max(280, len(chart_data) * 36))
    )


def dimension_comparison_chart(filtered_projects: pd.DataFrame) -> alt.Chart:
    """Build an average dimension score comparison chart for the filtered portfolio."""
    dimension_scores = (
        filtered_projects[DIMENSION_COLUMNS]
        .mean()
        .rename_axis("dimension")
        .reset_index(name="average_score")
    )
    dimension_scores["dimension"] = dimension_scores["dimension"].map(DIMENSION_LABELS)
    return (
        alt.Chart(dimension_scores)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("dimension:N", title="Dimension"),
            y=alt.Y("average_score:Q", title="Average Score", scale=alt.Scale(domain=[0, 100])),
            color=alt.value("#2F5D8C"),
            tooltip=["dimension", alt.Tooltip("average_score:Q", format=".2f")],
        )
        .properties(height=260)
    )


def selected_project_dimension_chart(project: pd.Series) -> alt.Chart:
    """Build a dimension score chart for the selected project."""
    dimension_scores = pd.DataFrame(
        {
            "dimension": [DIMENSION_LABELS[column] for column in DIMENSION_COLUMNS],
            "score": [float(project[column]) for column in DIMENSION_COLUMNS],
        }
    )
    return (
        alt.Chart(dimension_scores)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("dimension:N", title="Dimension"),
            y=alt.Y("score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
            color=alt.value("#4C78A8"),
            tooltip=["dimension", alt.Tooltip("score:Q", format=".2f")],
        )
        .properties(height=260)
    )


def render_project_overview(filtered_projects: pd.DataFrame) -> None:
    """Render the executive project overview table."""
    overview_columns = [
        "project_id",
        "project_name",
        "business_unit",
        "risk_level",
        "overall_project_score",
        "delivery_score",
        "quality_score",
        "engineering_score",
        "governance_score",
        "top_negative_contributors",
    ]
    st.dataframe(
        filtered_projects[overview_columns].sort_values(
            by=["risk_level", "overall_project_score"],
            key=lambda series: (
                series.map(risk_sort_key) if series.name == "risk_level" else series
            ),
        ),
        hide_index=True,
        use_container_width=True,
    )


def render_recommendations(recommendation: pd.Series) -> None:
    """Render recommendation text for a selected project."""
    st.subheader("Recommendations")
    st.markdown(f"**Executive Summary**  \n{recommendation['executive_summary']}")
    st.markdown(f"**Risk Explanation**  \n{recommendation['risk_explanation']}")
    st.markdown("**Recommended Actions**")
    for action in str(recommendation["recommended_actions"]).split(";"):
        cleaned_action = action.strip()
        if cleaned_action:
            st.markdown(f"- {cleaned_action}")


def main() -> None:
    """Render the AI_AQD executive dashboard."""
    st.set_page_config(
        page_title="AI_AQD Executive Dashboard",
        layout="wide",
    )

    st.title("AI_AQD Executive Dashboard")
    st.caption("Quality, delivery, engineering, and governance audit view")

    try:
        scored_projects, recommendations = load_gold_outputs()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    risk_options = [risk for risk in RISK_ORDER if risk in set(scored_projects["risk_level"])]
    business_unit_options = sorted(scored_projects["business_unit"].dropna().unique())

    with st.sidebar:
        st.header("Filters")
        selected_risks = st.multiselect("Risk Level", risk_options, default=risk_options)
        selected_units = st.multiselect("Business Unit", business_unit_options)

    filtered_projects = apply_filters(scored_projects, selected_risks, selected_units)

    if filtered_projects.empty:
        st.warning("No projects match the selected filters.")
        st.stop()

    st.subheader("Executive KPI Summary")
    render_kpis(filtered_projects)

    st.subheader("Project Risk Overview")
    render_project_overview(filtered_projects)

    left_column, right_column = st.columns(2)
    with left_column:
        st.subheader("Risk Distribution")
        st.altair_chart(risk_distribution_chart(filtered_projects), use_container_width=True)
    with right_column:
        st.subheader("Dimension Score Comparison")
        st.altair_chart(dimension_comparison_chart(filtered_projects), use_container_width=True)

    st.subheader("Overall Score Comparison")
    st.altair_chart(score_comparison_chart(filtered_projects), use_container_width=True)

    st.subheader("Project Detail Drill-Down")
    project_options = filtered_projects.sort_values("project_name")["project_name"].tolist()
    selected_project_name = st.selectbox("Project", project_options)
    selected_project = filtered_projects[
        filtered_projects["project_name"] == selected_project_name
    ].iloc[0]

    detail_left, detail_right = st.columns([1, 1])
    with detail_left:
        st.metric("Overall Score", f"{selected_project['overall_project_score']:.2f}")
        st.metric("Risk Level", selected_project["risk_level"])
        st.markdown(
            f"**Top Negative Contributors**  \n"
            f"{selected_project['top_negative_contributors']}"
        )
    with detail_right:
        st.altair_chart(
            selected_project_dimension_chart(selected_project),
            use_container_width=True,
        )

    selected_recommendation = recommendations[
        recommendations["project_id"] == selected_project["project_id"]
    ].iloc[0]
    render_recommendations(selected_recommendation)


if __name__ == "__main__":
    main()
