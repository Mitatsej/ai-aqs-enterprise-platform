# Data Dictionary

This document defines the planned input datasets and important fields for the MVP. Field names and types are placeholders until sample data is finalized.

## projects

Project-level reference data.

| Field | Type | Description |
| --- | --- | --- |
| project_id | string | Unique project identifier. |
| project_name | string | Human-readable project name. |
| business_unit | string | Owning business unit. |
| project_manager | string | Project manager or delivery owner. |
| start_date | date | Project start date. |
| target_end_date | date | Planned completion date. |
| status | string | Current project status. |

## sprint_metrics

Sprint-level delivery metrics.

| Field | Type | Description |
| --- | --- | --- |
| project_id | string | Related project identifier. |
| sprint_id | string | Unique sprint identifier. |
| sprint_start_date | date | Sprint start date. |
| sprint_end_date | date | Sprint end date. |
| committed_points | number | Work committed at sprint planning. |
| completed_points | number | Work completed by sprint close. |
| scope_change_points | number | Work added or removed during the sprint. |

## defects

Defect and quality incident data.

| Field | Type | Description |
| --- | --- | --- |
| defect_id | string | Unique defect identifier. |
| project_id | string | Related project identifier. |
| severity | string | Defect severity. |
| created_date | date | Date the defect was created. |
| resolved_date | date | Date the defect was resolved. |
| escaped_to_production | boolean | Whether the defect escaped to production. |

## code_quality_metrics

Engineering quality metrics.

| Field | Type | Description |
| --- | --- | --- |
| project_id | string | Related project identifier. |
| measurement_date | date | Date metrics were captured. |
| test_coverage | number | Automated test coverage percentage. |
| code_smells | integer | Count of code smell findings. |
| duplicated_code_percentage | number | Percentage of duplicated code. |
| technical_debt_ratio | number | Estimated technical debt ratio. |
| security_hotspots | integer | Count of security hotspots. |

## governance_metrics

Governance and audit readiness metrics.

| Field | Type | Description |
| --- | --- | --- |
| project_id | string | Related project identifier. |
| review_date | date | Date governance metrics were reviewed. |
| documentation_completeness | number | Percentage of required documentation completed. |
| audit_compliance | number | Percentage compliance with audit controls. |
| risk_review_current | boolean | Whether risk review is current. |
| required_approvals_complete | boolean | Whether required approvals are complete. |

