"""Pipeline entry point for AI_AQD.

Phase 3 runs only raw-to-Bronze ingestion. Silver validation, Gold aggregation,
scoring, risk classification, and recommendations will be added in later phases.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_aqd.ingestion.load_sources import ingest_expected_sources_to_bronze


def main() -> None:
    """Run the current AI_AQD pipeline phase."""
    results = ingest_expected_sources_to_bronze()

    print("Bronze ingestion complete.")
    for result in results:
        relative_output = result.bronze_path.relative_to(PROJECT_ROOT)
        print(
            f"- {result.dataset_name}: {result.row_count} rows "
            f"written to {relative_output} (batch_id={result.batch_id})"
        )


if __name__ == "__main__":
    main()
