"""Load raw source files into the Bronze layer.

Bronze is the landing layer of the Medallion Architecture. Its job is to keep
source-shaped data with only minimal technical additions, such as ingestion
metadata. Business cleaning, validation, joins, and scoring belong in later
Silver and Gold phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "data_paths.yaml"
DEFAULT_SOURCE_SYSTEM = "AI_AQD_SAMPLE_CSV"


@dataclass(frozen=True)
class BronzeIngestionResult:
    """Summary of one raw-to-Bronze ingestion operation."""

    dataset_name: str
    raw_path: Path
    bronze_path: Path
    row_count: int
    batch_id: str


def load_data_paths_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load data path configuration from YAML."""
    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def resolve_project_path(path_value: str | Path) -> Path:
    """Resolve repository-relative config paths into absolute filesystem paths."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def bronze_output_path(dataset_name: str, bronze_dir: Path) -> Path:
    """Return the Parquet output path for a Bronze dataset."""
    return bronze_dir / f"{dataset_name}.parquet"


def add_ingestion_metadata(
    data: pd.DataFrame,
    *,
    ingestion_timestamp: str,
    source_file: Path,
    source_system: str,
    batch_id: str,
) -> pd.DataFrame:
    """Add technical metadata while keeping source business columns unchanged."""
    bronze_data = data.copy()
    bronze_data["ingestion_timestamp"] = ingestion_timestamp
    bronze_data["source_file"] = str(source_file.relative_to(PROJECT_ROOT))
    bronze_data["source_system"] = source_system
    bronze_data["batch_id"] = batch_id
    return bronze_data


def ingest_source_to_bronze(
    *,
    dataset_name: str,
    raw_path: Path,
    bronze_dir: Path,
    ingestion_timestamp: str,
    source_system: str,
    batch_id: str,
) -> BronzeIngestionResult:
    """Read one raw CSV file and write its Bronze Parquet copy."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Expected raw source file was not found: {raw_path}")

    # Bronze intentionally performs minimal transformation: read the raw CSV,
    # add lineage metadata, and persist it in an analytics-friendly format.
    raw_data = pd.read_csv(raw_path)
    bronze_data = add_ingestion_metadata(
        raw_data,
        ingestion_timestamp=ingestion_timestamp,
        source_file=raw_path,
        source_system=source_system,
        batch_id=batch_id,
    )

    bronze_dir.mkdir(parents=True, exist_ok=True)
    output_path = bronze_output_path(dataset_name, bronze_dir)
    bronze_data.to_parquet(output_path, index=False)

    return BronzeIngestionResult(
        dataset_name=dataset_name,
        raw_path=raw_path,
        bronze_path=output_path,
        row_count=len(bronze_data),
        batch_id=batch_id,
    )


def ingest_expected_sources_to_bronze(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_system: str = DEFAULT_SOURCE_SYSTEM,
    batch_id: str | None = None,
) -> list[BronzeIngestionResult]:
    """Ingest all expected raw MVP sources defined in configs/data_paths.yaml."""
    config = load_data_paths_config(config_path)
    expected_sources = config["expected_sources"]
    bronze_dir = resolve_project_path(config["layers"]["bronze"])
    active_batch_id = batch_id or uuid4().hex
    ingestion_timestamp = pd.Timestamp.now(tz="UTC").isoformat()

    results: list[BronzeIngestionResult] = []
    for dataset_name, raw_path_value in expected_sources.items():
        results.append(
            ingest_source_to_bronze(
                dataset_name=dataset_name,
                raw_path=resolve_project_path(raw_path_value),
                bronze_dir=bronze_dir,
                ingestion_timestamp=ingestion_timestamp,
                source_system=source_system,
                batch_id=active_batch_id,
            )
        )

    return results
