# AI_AQD Architecture

## Overview

AI_AQD is designed as a modular data engineering platform for auditing project delivery quality, engineering quality, governance maturity, and delivery risk.

The platform follows a Medallion Architecture:

- Bronze: raw ingested data
- Silver: cleaned and standardized data
- Gold: business-ready metrics, scores, risks, and recommendations

## Logical Architecture

```text
Project Source Files
   |
   v
Ingestion Module
   |
   v
Bronze Data Layer
   |
   v
Validation and Standardization
   |
   v
Silver Data Layer
   |
   v
Metric Aggregation and Scoring
   |
   v
Gold Data Layer
   |
   v
Risk Classification and Recommendations
   |
   v
Dashboard and Reporting
```

## Bronze Layer

The Bronze layer stores source-aligned data with minimal transformation. It should preserve what was received so that data lineage and auditability remain possible.

Future implementation should include:

- Raw file ingestion
- Load metadata
- Source file tracking
- Basic schema capture
- Conversion to a consistent storage format such as Parquet

## Silver Layer

The Silver layer stores cleaned, validated, typed, deduplicated, and standardized data.

Future implementation should include:

- Schema validation
- Type normalization
- Null handling
- Duplicate detection
- Project identifier standardization
- Date standardization
- Referential checks across datasets

## Gold Layer

The Gold layer stores business-ready analytical outputs.

Future implementation should include:

- Project-level KPI tables
- Quality score outputs
- Risk classification outputs
- Recommendation outputs
- Dashboard-ready aggregates

## Design Principles

- Keep ingestion, validation, transformation, scoring, risk, recommendations, and dashboard code separate.
- Keep business rules in configuration where practical.
- Make pipeline behavior repeatable and testable.
- Keep notebooks exploratory only.
- Preserve data lineage from source to final outputs.

