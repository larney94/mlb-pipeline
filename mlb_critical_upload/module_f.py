"""
Module F – filter_input_data.py
Purpose: Filter consolidated MLB gamelogs to remove invalid, incomplete, or ineligible entries.
"""

import sys
import pandas as pd
from pathlib import Path
from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def filter_data(df: pd.DataFrame, cfg: dict, logger):
    filters = cfg.filters
    required_fields = ["player_id", "team_id", "game_date"]
    for col in required_fields:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            raise ValueError(f"Required column missing: {col}")
        df = df[df[col].notnull()]

    if "games_played" in df.columns:
        df = df[df["games_played"] >= filters.min_games_played]
    if "innings_pitched" in df.columns:
        df = df[df["innings_pitched"] >= filters.min_innings_pitched]
    if "position" in df.columns:
        df = df[df["position"].isin(filters.valid_positions)]

    logger.info(f"Filtered dataframe shape: {df.shape}")
    return df

def main():
    try:
        cfg = load_config()
        cfg = apply_cli_overrides(cfg)
        logger = get_rotating_logger("module_f", cfg)

        input_path = Path(cfg.outputs.consolidated_gamelogs_path).resolve()
        output_path = resolve_output_path(cfg.outputs.filtered_gamelogs_path, cfg.overwrite_policy)
        ensure_dir(output_path.parent)

        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            sys.exit(1)

        df = pd.read_parquet(input_path)
        logger.info(f"Loaded input: {input_path} with shape {df.shape}")

        df_filtered = filter_data(df, cfg, logger)
        df_filtered.to_parquet(output_path, index=False)

        logger.info(f"Filtered gamelogs saved to: {output_path}")
        logger.info(f"Records written: {df_filtered.shape[0]}")

    except Exception as e:
        logger = get_rotating_logger("module_f", None)
        logger.exception("Unhandled exception occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()
