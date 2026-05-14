"""Pipeline entry point for AI_AQD.

The current pipeline runs raw-to-Bronze ingestion, Bronze-to-Silver validation,
and Silver-to-Gold metric aggregation. Scoring, risk classification, and
recommendations will be added in later phases.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_aqd.ingestion.load_sources import ingest_expected_sources_to_bronze
from ai_aqd.transformation.bronze_to_silver import run_bronze_to_silver
from ai_aqd.transformation.silver_to_gold import run_silver_to_gold


def main() -> None:
    """Run the current AI_AQD pipeline phase."""
    bronze_results = ingest_expected_sources_to_bronze()

    print("Bronze ingestion complete.")
    for result in bronze_results:
        relative_output = result.bronze_path.relative_to(PROJECT_ROOT)
        print(
            f"- {result.dataset_name}: {result.row_count} rows "
            f"written to {relative_output} (batch_id={result.batch_id})"
        )

    silver_results = run_bronze_to_silver()

    print("Silver validation and transformation complete.")
    for result in silver_results:
        relative_output = result.silver_path.relative_to(PROJECT_ROOT)
        print(
            f"- {result.dataset_name}: {result.input_rows} input rows, "
            f"{result.output_rows} Silver rows, {result.dropped_rows} dropped; "
            f"written to {relative_output}"
        )
        for message in result.messages:
            print(f"  - {message}")

    gold_result = run_silver_to_gold()

    print("Gold metric aggregation complete.")
    relative_output = gold_result.output_path.relative_to(PROJECT_ROOT)
    print(f"- {gold_result.output_name}: {gold_result.row_count} rows written to {relative_output}")
    for message in gold_result.messages:
        print(f"  - {message}")


if __name__ == "__main__":
    main()
