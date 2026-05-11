"""Generate realistic MVP source datasets for AI_AQD.

The generated data intentionally contains different project health patterns so
later Bronze/Silver/Gold, scoring, risk, and dashboard work has meaningful
signals to process.

Patterns included:
- Healthy projects: stable velocity, low escaped defects, strong test coverage,
  and complete governance evidence.
- Medium-risk projects: moderate delivery variance, some quality issues, and
  mostly complete governance evidence.
- High-risk projects: frequent under-delivery, elevated defects, weaker code
  quality, and incomplete governance controls.
- Critical-risk projects: unstable delivery, production escapes, weak code
  health, and missing or stale governance evidence.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


RAW_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


@dataclass(frozen=True)
class ProjectProfile:
    """Project reference data plus the synthetic health pattern to apply."""

    project_id: str
    project_name: str
    business_unit: str
    project_manager: str
    start_date: date
    target_end_date: date
    status: str
    health_pattern: str


PROJECTS: tuple[ProjectProfile, ...] = (
    ProjectProfile(
        "PRJ-001",
        "Customer 360 Data Platform",
        "Retail Banking",
        "Ariana Dervishi",
        date(2025, 9, 1),
        date(2026, 6, 30),
        "Active",
        "healthy",
    ),
    ProjectProfile(
        "PRJ-002",
        "Claims Automation AI",
        "Insurance",
        "Ben Carter",
        date(2025, 8, 18),
        date(2026, 7, 15),
        "Active",
        "healthy",
    ),
    ProjectProfile(
        "PRJ-003",
        "Finance Data Lake Modernization",
        "Corporate Finance",
        "Mira Hoxha",
        date(2025, 7, 7),
        date(2026, 5, 29),
        "Active",
        "medium",
    ),
    ProjectProfile(
        "PRJ-004",
        "Supplier Risk Analytics",
        "Procurement",
        "Jon Bell",
        date(2025, 10, 6),
        date(2026, 8, 28),
        "Active",
        "medium",
    ),
    ProjectProfile(
        "PRJ-005",
        "Core Payments Refactor",
        "Payments",
        "Elira Kola",
        date(2025, 6, 2),
        date(2026, 4, 24),
        "At Risk",
        "high",
    ),
    ProjectProfile(
        "PRJ-006",
        "Regulatory Reporting Hub",
        "Risk & Compliance",
        "Samir Patel",
        date(2025, 5, 19),
        date(2026, 5, 15),
        "At Risk",
        "high",
    ),
    ProjectProfile(
        "PRJ-007",
        "Legacy CRM Migration",
        "Sales Operations",
        "Nora Smith",
        date(2025, 4, 14),
        date(2026, 3, 31),
        "Critical",
        "critical",
    ),
    ProjectProfile(
        "PRJ-008",
        "Enterprise Identity Consolidation",
        "Technology Services",
        "Dritan Marku",
        date(2025, 3, 3),
        date(2026, 2, 27),
        "Critical",
        "critical",
    ),
)


SPRINT_PATTERNS = {
    "healthy": {
        "committed": (34, 38, 36, 40, 37, 39),
        "completion_ratio": (0.97, 1.00, 0.95, 1.02, 0.98, 1.00),
        "scope_change": (0, 1, 0, 2, 1, 0),
    },
    "medium": {
        "committed": (32, 35, 34, 37, 36, 38),
        "completion_ratio": (0.88, 0.92, 0.84, 0.90, 0.87, 0.93),
        "scope_change": (2, 3, 4, 2, 5, 3),
    },
    "high": {
        "committed": (36, 40, 38, 42, 39, 41),
        "completion_ratio": (0.74, 0.79, 0.68, 0.76, 0.71, 0.73),
        "scope_change": (5, 7, 6, 8, 7, 9),
    },
    "critical": {
        "committed": (40, 43, 41, 45, 42, 44),
        "completion_ratio": (0.55, 0.62, 0.48, 0.58, 0.52, 0.45),
        "scope_change": (10, 12, 9, 14, 13, 15),
    },
}

DEFECT_PATTERNS = {
    "healthy": {"count": 7, "escaped": 0, "severities": ("Low", "Low", "Medium")},
    "medium": {"count": 12, "escaped": 1, "severities": ("Low", "Medium", "Medium", "High")},
    "high": {"count": 18, "escaped": 3, "severities": ("Medium", "High", "High", "Critical")},
    "critical": {"count": 24, "escaped": 6, "severities": ("High", "High", "Critical", "Critical")},
}

CODE_QUALITY_PATTERNS = {
    "healthy": {
        "test_coverage": 86.0,
        "code_smells": 18,
        "duplicated_code_percentage": 2.4,
        "technical_debt_ratio": 3.5,
        "security_hotspots": 1,
    },
    "medium": {
        "test_coverage": 73.0,
        "code_smells": 48,
        "duplicated_code_percentage": 5.8,
        "technical_debt_ratio": 7.5,
        "security_hotspots": 4,
    },
    "high": {
        "test_coverage": 61.0,
        "code_smells": 96,
        "duplicated_code_percentage": 10.9,
        "technical_debt_ratio": 13.0,
        "security_hotspots": 9,
    },
    "critical": {
        "test_coverage": 42.0,
        "code_smells": 165,
        "duplicated_code_percentage": 18.5,
        "technical_debt_ratio": 24.0,
        "security_hotspots": 17,
    },
}

GOVERNANCE_PATTERNS = {
    "healthy": {
        "documentation_completeness": 96.0,
        "audit_compliance": 98.0,
        "risk_review_current": True,
        "required_approvals_complete": True,
    },
    "medium": {
        "documentation_completeness": 83.0,
        "audit_compliance": 86.0,
        "risk_review_current": True,
        "required_approvals_complete": True,
    },
    "high": {
        "documentation_completeness": 67.0,
        "audit_compliance": 72.0,
        "risk_review_current": False,
        "required_approvals_complete": True,
    },
    "critical": {
        "documentation_completeness": 49.0,
        "audit_compliance": 58.0,
        "risk_review_current": False,
        "required_approvals_complete": False,
    },
}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    """Write rows with a stable schema and predictable row ordering."""
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def iso(value: date | None) -> str:
    """Return ISO date text for CSV output, keeping unresolved dates blank."""
    return "" if value is None else value.isoformat()


def generate_projects() -> list[dict[str, object]]:
    """Create project reference records using the data dictionary schema."""
    return [
        {
            "project_id": project.project_id,
            "project_name": project.project_name,
            "business_unit": project.business_unit,
            "project_manager": project.project_manager,
            "start_date": iso(project.start_date),
            "target_end_date": iso(project.target_end_date),
            "status": project.status,
        }
        for project in PROJECTS
    ]


def generate_sprint_metrics() -> list[dict[str, object]]:
    """Create six two-week sprints per project with health-shaped delivery data."""
    rows: list[dict[str, object]] = []

    for project in PROJECTS:
        pattern = SPRINT_PATTERNS[project.health_pattern]
        sprint_start = project.start_date

        for sprint_number, committed_points in enumerate(pattern["committed"], start=1):
            completion_ratio = pattern["completion_ratio"][sprint_number - 1]
            completed_points = round(committed_points * completion_ratio)
            scope_change_points = pattern["scope_change"][sprint_number - 1]

            rows.append(
                {
                    "project_id": project.project_id,
                    "sprint_id": f"{project.project_id}-SPR-{sprint_number:02d}",
                    "sprint_start_date": iso(sprint_start),
                    "sprint_end_date": iso(sprint_start + timedelta(days=13)),
                    "committed_points": committed_points,
                    "completed_points": completed_points,
                    "scope_change_points": scope_change_points,
                }
            )
            sprint_start += timedelta(days=14)

    return rows


def generate_defects() -> list[dict[str, object]]:
    """Create defects across severities, including production escapes for risky projects."""
    rows: list[dict[str, object]] = []
    defect_sequence = 1

    for project in PROJECTS:
        pattern = DEFECT_PATTERNS[project.health_pattern]
        severities = pattern["severities"]

        for defect_index in range(pattern["count"]):
            created_date = project.start_date + timedelta(days=8 + defect_index * 7)
            severity = severities[defect_index % len(severities)]
            escaped_to_production = defect_index >= pattern["count"] - pattern["escaped"]

            if project.health_pattern == "critical" and defect_index % 5 == 0:
                resolved_date = None
            else:
                resolution_days = {
                    "Low": 10,
                    "Medium": 8,
                    "High": 6,
                    "Critical": 4,
                }[severity]
                resolved_date = created_date + timedelta(days=resolution_days)

            rows.append(
                {
                    "defect_id": f"DEF-{defect_sequence:04d}",
                    "project_id": project.project_id,
                    "severity": severity,
                    "created_date": iso(created_date),
                    "resolved_date": iso(resolved_date),
                    "escaped_to_production": escaped_to_production,
                }
            )
            defect_sequence += 1

    return rows


def generate_code_quality_metrics() -> list[dict[str, object]]:
    """Create one code quality snapshot per project aligned to project health."""
    rows: list[dict[str, object]] = []

    for project_index, project in enumerate(PROJECTS):
        pattern = CODE_QUALITY_PATTERNS[project.health_pattern]
        adjustment = project_index % 2

        rows.append(
            {
                "project_id": project.project_id,
                "measurement_date": iso(project.start_date + timedelta(days=84)),
                "test_coverage": round(pattern["test_coverage"] - adjustment * 2.5, 1),
                "code_smells": pattern["code_smells"] + adjustment * 8,
                "duplicated_code_percentage": round(
                    pattern["duplicated_code_percentage"] + adjustment * 0.7,
                    1,
                ),
                "technical_debt_ratio": round(pattern["technical_debt_ratio"] + adjustment * 1.2, 1),
                "security_hotspots": pattern["security_hotspots"] + adjustment,
            }
        )

    return rows


def generate_governance_metrics() -> list[dict[str, object]]:
    """Create governance snapshots with weaker evidence on high-risk projects."""
    rows: list[dict[str, object]] = []

    for project_index, project in enumerate(PROJECTS):
        pattern = GOVERNANCE_PATTERNS[project.health_pattern]
        adjustment = 2.0 if project_index % 2 else 0.0

        rows.append(
            {
                "project_id": project.project_id,
                "review_date": iso(project.start_date + timedelta(days=98)),
                "documentation_completeness": max(
                    0.0,
                    round(pattern["documentation_completeness"] - adjustment, 1),
                ),
                "audit_compliance": max(0.0, round(pattern["audit_compliance"] - adjustment, 1)),
                "risk_review_current": pattern["risk_review_current"],
                "required_approvals_complete": pattern["required_approvals_complete"],
            }
        )

    return rows


def main() -> None:
    """Generate all raw MVP datasets defined in docs/data_dictionary.md."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        RAW_DATA_DIR / "projects.csv",
        [
            "project_id",
            "project_name",
            "business_unit",
            "project_manager",
            "start_date",
            "target_end_date",
            "status",
        ],
        generate_projects(),
    )
    write_csv(
        RAW_DATA_DIR / "sprint_metrics.csv",
        [
            "project_id",
            "sprint_id",
            "sprint_start_date",
            "sprint_end_date",
            "committed_points",
            "completed_points",
            "scope_change_points",
        ],
        generate_sprint_metrics(),
    )
    write_csv(
        RAW_DATA_DIR / "defects.csv",
        [
            "defect_id",
            "project_id",
            "severity",
            "created_date",
            "resolved_date",
            "escaped_to_production",
        ],
        generate_defects(),
    )
    write_csv(
        RAW_DATA_DIR / "code_quality_metrics.csv",
        [
            "project_id",
            "measurement_date",
            "test_coverage",
            "code_smells",
            "duplicated_code_percentage",
            "technical_debt_ratio",
            "security_hotspots",
        ],
        generate_code_quality_metrics(),
    )
    write_csv(
        RAW_DATA_DIR / "governance_metrics.csv",
        [
            "project_id",
            "review_date",
            "documentation_completeness",
            "audit_compliance",
            "risk_review_current",
            "required_approvals_complete",
        ],
        generate_governance_metrics(),
    )

    print(f"Generated AI_AQD sample datasets in {RAW_DATA_DIR}")


if __name__ == "__main__":
    main()
