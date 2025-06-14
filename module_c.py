import argparse
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger, ensure_dir
import sys
import os
import pyarrow as pa

LOGGER = get_rotating_logger("module_c")

def normalize_columns(df, alias_map):
    return df.rename(columns=alias_map)

def validate_required_columns(df, required_cols, context):
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {context}: {missing}")

def consolidate_contextual_features(static_dir: Path, output_path: Path, alias_map: dict, overwrite: str):
    if output_path.exists():
        if overwrite == "error":
            raise FileExistsError(f"Output file {output_path} already exists and overwrite policy is 'error'.")
        elif overwrite == "warn":
            LOGGER.warning(f"Output file {output_path} exists. Skipping due to 'warn' policy.")
            return
        elif overwrite == "force":
            LOGGER.info(f"Overwriting existing file {output_path} due to 'force' policy.")
        else:
            raise ValueError(f"Invalid overwrite policy: {overwrite}")

    static_files = list(static_dir.glob("*.csv"))
    if not static_files:
        raise FileNotFoundError(f"No static CSV files found in {static_dir}")

    context_dfs = []
    for csv_file in static_files:
        try:
            df = pd.read_csv(csv_file)
            df = normalize_columns(df, alias_map)
            validate_required_columns(df, ["team_id", "date"], csv_file.name)
            context_dfs.append(df)
            LOGGER.info(f"Loaded {csv_file.name} with {len(df)} records.")
        except Exception as e:
            LOGGER.error(f"Error processing {csv_file.name}: {e}")
            raise

    if not context_dfs:
        raise ValueError("No contextual features could be consolidated.")

    merged_df = pd.concat(context_dfs, axis=0, ignore_index=True)
    LOGGER.info(f"Merged context features: {merged_df.shape[0]} records.")

    table = pa.Table.from_pandas(merged_df)
    pq.write_table(table, output_path)
    LOGGER.info(f"Wrote consolidated contextual features to: {output_path.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate contextual MLB data features.")
    parser.add_argument("--config-path", type=str, required=False, default="config.yaml")
    parser.add_argument("--overwrite-policy", type=str, choices=["error", "warn", "force"], default="error")
    args = parser.parse_args()

    cfg = load_config(args.config_path)
    cfg = apply_cli_overrides(cfg)

    static_dir = Path(cfg["outputs"]["static_dir"]).resolve()
    context_dir = Path(cfg["outputs"]["context_dir"]).resolve()
    ensure_dir(context_dir)

    output_path = resolve_output_path(context_dir / "context_features.parquet", cfg.overwrite_policy)

    alias_map = {
        "teamID": "team_id",
        "Team": "team_id",
        "DATE": "date",
        "teamId": "team_id",
    }

    try:
        consolidate_contextual_features(static_dir, output_path, alias_map, args.overwrite_policy)
    except Exception as e:
        LOGGER.error(f"Module C failed: {e}")
        sys.exit(1)
    LOGGER.info("Module C completed successfully.")
    sys.exit(0)
