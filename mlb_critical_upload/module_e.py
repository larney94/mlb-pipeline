"""
module_e.py – Fetch MLB starters from StatsAPI and write to file
"""

import argparse
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import statsapi
import time

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger

# Global logger so all functions can access it
logger = get_rotating_logger('module_e')


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def fetch_starters(target_date: str, timeout: int) -> list:
    """Fetch starting pitchers using MLB StatsAPI"""
    try:
        schedule = statsapi.schedule(date=target_date, sportId=1)
        time.sleep(timeout)
        starters = []
        for game in schedule:
            for slot in ('away', 'home'):
                pitcher = game.get(f'{slot}ProbablePitcher')
                team = game.get(f'{slot}Name')
                if pitcher:
                    starters.append({
                        'player_id': pitcher['id'],
                        'player_name': pitcher['fullName'],
                        'position': pitcher.get('primaryPosition', {}).get('abbreviation', 'SP'),
                        'team': team,
                        'slot': slot,
                        'game_date': target_date,
                    })
        return starters
    except Exception as e:
        logger.error(f"Failed to fetch starters for {target_date}: {e}")
        return []


def write_starters_file(data: list, output_path: Path, overwrite: str) -> None:
    if output_path.exists():
        if overwrite == 'error':
            raise FileExistsError(f"File {output_path} already exists.")
        elif overwrite == 'warn':
            logger.warning(f"File {output_path} exists. Skipping due to overwrite_policy=warn.")
            return
        elif overwrite != 'force':
            logger.error(f"Unknown overwrite_policy: {overwrite}")
            sys.exit(1)

    ensure_dir(output_path.parent)
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    logger.info(f"Wrote {len(df)} starter records to {output_path}")


if __name__ == '__main__':
    logger.info("Module E – Fetch Starters – started")

    cfg = load_config()
    cfg = apply_cli_overrides(cfg)

    target_date = cfg.get('date') or datetime.today().strftime('%Y-%m-%d')
    timeout = cfg.get('statsapi', {}).get('timeout', 5)
    overwrite = cfg.get('overwrite_policy', 'error')

    output_path = resolve_output_path(
        str(Path(cfg['outputs']['starters_dir']) / f'starters_{target_date}.csv'), cfg
    )

    logger.debug(f"Resolved output path: {output_path}")
    logger.info(f"Fetching starters for {target_date}")

    starters = fetch_starters(target_date, timeout)
    if not starters:
        logger.warning(f"No starters found for {target_date} – skipping file write.")
    else:
        write_starters_file(starters, output_path, overwrite)

    logger.info("Module E – completed")
