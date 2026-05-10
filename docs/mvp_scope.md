# MVP Scope

## MVP Objective

The MVP should prove that AI_AQD can ingest project delivery data, transform it through Bronze, Silver, and Gold layers, calculate project quality scores, classify risks, and generate useful recommendations.

## In Scope

- Local batch ingestion from CSV files
- Bronze, Silver, and Gold folder-based data layers
- Sample datasets for development
- Basic data validation
- Project-level metric aggregation
- Rule-based scoring
- Rule-based risk classification
- Rule-based recommendation generation
- Simple executive dashboard
- Unit tests for core scoring and classification behavior

## Initial Input Datasets

- projects
- sprint_metrics
- defects
- code_quality_metrics
- governance_metrics

## Initial Outputs

- Project quality score
- Risk level
- Risk drivers
- Recommended actions
- Dashboard-ready project summary

## Out of Scope for MVP

- Real-time streaming
- Cloud deployment
- Airflow or enterprise orchestration
- Authentication and authorization
- LLM integration
- Advanced machine learning
- Multi-tenant support
- Production observability platform integration

## MVP Success Criteria

- The pipeline can run end-to-end on sample data.
- Each medallion layer has a clear purpose and output.
- Scoring logic is transparent and explainable.
- Risk classifications can be traced back to input metrics.
- Recommendations are useful and deterministic.
- The dashboard can support an executive quality review conversation.

