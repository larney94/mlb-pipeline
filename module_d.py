"""
Module D: combine_features.py
Purpose: Merge gamelogs, static player data, and context features into a single modeling dataset.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def load_file(path: Path, file_type: str):
    if file_type == "csv":
        return pd.read_csv(path)
    elif file_type == "parquet":
        return pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", required=True, help="Path to config.yaml")
    parser.add_argument("--overwrite-policy", choices=["error", "warn", "force"], default="error")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config_path)
        cfg = apply_cli_overrides(cfg)

        output_path = resolve_output_path(cfg.outputs.full_feature_set, cfg.model_dump(), args.overwrite_policy)
        ensure_dir(output_path.parent)

        logger = get_rotating_logger("combine_features", log_dir="logs")
        logger.info("Starting combine_features.py")
        logger.info(f"Config path: {args.config_path}")
        logger.info(f"Overwrite policy: {args.overwrite_policy}")

        # Load data
        gamelogs_path = Path(cfg.inputs.recent_gamelogs_csv).resolve()
        players_path = Path(cfg.inputs.static_player_csv).resolve()
        context_dir = Path(cfg.outputs.context_dir).resolve()

        logger.info(f"Reading gamelogs from: {gamelogs_path}")
        logger.info(f"Reading static player info from: {players_path}")
        logger.info(f"Reading context features from dir: {context_dir}")

        gamelogs_df = load_file(gamelogs_path, "csv")
        players_df = load_file(players_path, "csv")
        context_files = list(context_dir.glob("*.parquet"))

        if not context_files:
            raise FileNotFoundError(f"No .parquet files found in {context_dir}")
        context_df = pd.concat([pd.read_parquet(p) for p in context_files], ignore_index=True)

        logger.info(f"Loaded gamelogs: {gamelogs_df.shape[0]} rows")
        logger.info(f"Loaded static players: {players_df.shape[0]} rows")
        logger.info(f"Loaded context: {context_df.shape[0]} rows")

        # Merge step 1: gamelogs + players
        merged_df = gamelogs_df.merge(players_df, on="player_id", how="left", validate="many_to_one")

        # Merge step 2: + context
        merged_df = merged_df.merge(context_df, on=["player_id", "date"], how="left", validate="many_to_one")

        logger.info(f"Final merged row count (after join): {merged_df.shape[0]}")
        merged_df.drop_duplicates(inplace=True)

        logger.info(f"Writing output to: {output_path}")
        merged_df.to_parquet(output_path, index=False)
        logger.info("combine_features.py completed successfully")

    except Exception as e:
        logger = get_rotating_logger("combine_features", log_dir="logs")
        logger.exception(f"Error in combine_features.py: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
