# AI_AQD

AI-Assisted Quality & Delivery Audit Platform.

AI_AQD is a professional data engineering and analytics project designed to ingest project delivery datasets, process them through a Medallion Architecture, calculate project quality scores, classify delivery and engineering risks, and generate recommendations and executive dashboards.

This repository is currently initialized as a project foundation only. Production business logic will be added incrementally in future development phases.

## Project Goals

- Ingest project-related datasets such as project metadata, sprint metrics, defects, code quality metrics, and governance metrics.
- Organize data processing using Bronze, Silver, and Gold layers.
- Validate and standardize incoming data before analytics usage.
- Calculate transparent project quality and delivery health scores.
- Classify project risk levels using explainable rules.
- Generate AI-assisted recommendations for delivery, quality, engineering, and governance improvements.
- Provide executive dashboards and audit-ready reporting.

## Current Status

Foundation initialized:

- Repository structure
- Python package layout
- Documentation placeholders
- Configuration placeholders
- Bronze ingestion pipeline
- Silver validation and transformation pipeline
- Gold metric aggregation pipeline
- Rule-based quality scoring pipeline
- Rule-based recommendation pipeline
- Streamlit executive dashboard
- Data layer folders

The MVP data pipeline and first executive dashboard are now available.

## Architecture Summary

```text
Source Data
   |
   v
Bronze Layer
Raw ingested data with minimal transformation
   |
   v
Silver Layer
Cleaned, validated, standardized data
   |
   v
Gold Layer
Business-ready metrics, scores, risk classifications
   |
   v
Recommendations and Dashboards
Executive and operational insights
```

## Repository Layout

```text
AI_AQD/
  configs/
  data/
    raw/
    bronze/
    silver/
    gold/
    sample/
  docs/
  notebooks/
  scripts/
  src/
    ai_aqd/
      ingestion/
      validation/
      transformation/
      scoring/
      risk/
      recommendations/
      dashboard/
      utils/
  tests/
```

## Development Principles

- Keep raw, cleaned, and business-ready data clearly separated.
- Prefer transparent rules before advanced automation.
- Keep business thresholds and scoring weights in configuration files.
- Treat documentation as part of the product.
- Add tests as pipeline behavior becomes real.
- Avoid putting production logic inside notebooks.

## Generate Sample Raw Data

Create the synthetic MVP source files in `data/raw/`:

```powershell
python scripts/generate_sample_data.py
```

This generates:

- `projects.csv`
- `sprint_metrics.csv`
- `defects.csv`
- `code_quality_metrics.csv`
- `governance_metrics.csv`

## Run Current Pipeline

Run the current pipeline:

```powershell
python scripts/run_pipeline.py
```

The current pipeline runs:

1. Raw CSV to Bronze Parquet ingestion
2. Bronze to Silver validation and transformation
3. Silver to Gold project-level metric aggregation
4. Gold metric scoring and risk classification
5. Rule-based recommendation generation

Bronze outputs:

- `data/bronze/projects.parquet`
- `data/bronze/sprint_metrics.parquet`
- `data/bronze/defects.parquet`
- `data/bronze/code_quality_metrics.parquet`
- `data/bronze/governance_metrics.parquet`

Bronze metadata columns:

- `ingestion_timestamp`
- `source_file`
- `source_system`
- `batch_id`

To verify the files were created:

```powershell
Get-ChildItem data/bronze
```

To inspect one Bronze dataset:

```powershell
python -c "import pandas as pd; print(pd.read_parquet('data/bronze/projects.parquet').head())"
```

Silver outputs:

- `data/silver/projects.parquet`
- `data/silver/sprint_metrics.parquet`
- `data/silver/defects.parquet`
- `data/silver/code_quality_metrics.parquet`
- `data/silver/governance_metrics.parquet`

Gold output:

- `data/gold/project_risk_summary.parquet`
- `data/gold/project_quality_scores.parquet`
- `data/gold/recommendations.parquet`

`project_risk_summary.parquet` contains aggregated project metrics only.
`project_quality_scores.parquet` adds rule-based dimension scores, the overall
project score, risk level, and top negative contributors.
`recommendations.parquet` adds executive summaries, risk explanations, and
recommended actions generated from transparent rules. No LLM integration is used
yet.

To inspect the Gold project summary:

```powershell
python -c "import pandas as pd; print(pd.read_parquet('data/gold/project_risk_summary.parquet'))"
```

To inspect the scored project output:

```powershell
python -c "import pandas as pd; print(pd.read_parquet('data/gold/project_quality_scores.parquet')[['project_id','delivery_score','quality_score','engineering_score','governance_score','overall_project_score','risk_level','top_negative_contributors']])"
```

To inspect recommendations:

```powershell
python -c "import pandas as pd; print(pd.read_parquet('data/gold/recommendations.parquet')[['project_id','risk_level','executive_summary','risk_explanation','recommended_actions']])"
```

## Run Executive Dashboard

Generate the latest Gold outputs first:

```powershell
python scripts/run_pipeline.py
```

Start the Streamlit dashboard:

```powershell
python -m streamlit run src/ai_aqd/dashboard/app.py
```

The dashboard uses:

- `data/gold/project_quality_scores.parquet`
- `data/gold/recommendations.parquet`

Dashboard sections:

- Executive KPI summary
- Project risk overview table
- Risk distribution chart
- Overall score comparison chart
- Dimension score comparison chart
- Project detail drill-down
- Recommendations section

## Next Implementation Steps

1. Add automated tests for scoring, risk classification, recommendations, and dashboard data loading.
2. Add dashboard styling refinements and optional export views.
