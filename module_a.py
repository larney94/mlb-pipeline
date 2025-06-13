# module_a.py

import argparse
from pathlib import Path
import pandas as pd
from pybaseball import batting_stats, pitching_stats

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger


def fetch_gamelogs(season: int, timeout: int, logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info(f"Fetching batting stats for season {season}")
    batting = batting_stats(season)
    logger.info(f"Fetching pitching stats for season {season}")
    pitching = pitching_stats(season)
    return batting, pitching


def write_csv(df: pd.DataFrame, path: Path, policy: str, logger):
    if path.exists():
        if policy == "error":
            logger.error(f"File {path} already exists.")
            raise SystemExit(1)
        elif policy == "warn":
            logger.warning(f"File {path} already exists. Overwriting.")
        elif policy == "force":
            logger.info(f"File {path} exists. Overwriting due to force policy.")
    else:
        logger.info(f"Writing new file to {path}")

    df.to_csv(path, index=False)
    logger.info(f"Successfully wrote data to {path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB gamelogs for specified seasons.")
    parser.add_argument("--config-path", type=str, default="config.yaml", help="Path to config YAML file")
    parser.add_argument("--overwrite-policy", type=str, default=None, choices=["error", "warn", "force"])
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--log-level", type=str, default="INFO")

    args = parser.parse_args()
    config = load_config(args.config_path)
    config = apply_cli_overrides(config, args)

    logger = get_rotating_logger("module_a", log_dir="logs")
    logger.info(f"Loaded config: {config}")

    seasons = [args.season] if args.season else config["seasons"]
    output_dir = Path(config["outputs"]["gamelogs_dir"])
    timeout = config.get("pybaseball_timeout", 10)
    overwrite_policy = config["overwrite_policy"]

    output_dir.mkdir(parents=True, exist_ok=True)

    for season in seasons:
        logger.info(f"Processing season {season}")
        batting_df, pitching_df = fetch_gamelogs(season, timeout, logger)

        batting_path = resolve_output_path(output_dir, f"mlb_all_batting_gamelogs_{season}.csv")
        pitching_path = resolve_output_path(output_dir, f"mlb_all_pitching_gamelogs_{season}.csv")

        write_csv(batting_df, batting_path, overwrite_policy, logger)
        write_csv(pitching_df, pitching_path, overwrite_policy, logger)


if __name__ == "__main__":
    main()
