# Scoring Model

## Purpose

The scoring model converts delivery, quality, engineering, and governance signals into a project-level quality score.

The first implementation should be transparent and rule-based. This makes it easier to explain results to stakeholders before introducing advanced AI or machine learning.

## Planned Score Dimensions

The MVP scoring model will use four dimensions:

- Delivery
- Quality
- Engineering
- Governance

Each dimension contributes to the total project score.

## Placeholder Weights

| Dimension | Weight |
| --- | ---: |
| Delivery | 30% |
| Quality | 30% |
| Engineering | 25% |
| Governance | 15% |

These weights are placeholders and should be reviewed with delivery leadership, engineering leadership, and governance stakeholders.

## Risk Mapping

The project score will map to risk levels:

| Score Range | Risk Level |
| --- | --- |
| 85-100 | Low |
| 70-84 | Medium |
| 50-69 | High |
| 0-49 | Critical |

## Explainability Requirement

Every project score should include:

- Overall score
- Dimension scores
- Risk level
- Top negative contributors
- Recommended actions

## Future Enhancements

- Historical trend scoring
- Peer benchmark scoring
- Machine learning assisted risk prediction
- LLM-generated executive summaries
- Confidence scoring based on data completeness

