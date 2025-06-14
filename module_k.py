"""
README_module_k.md

Module K — `module_k.py`
-------------------------
**Purpose**: Fetch vig-free player prop lines from Pinnacle API or backup and compute fair probabilities.

**Input**:
- Config keys: `true_line_sources.primary`, `true_line_sources.backup`, `outputs.dir`

**Output**:
- CSV: outputs/true_lines/true_lines_<DATE>.csv

**CLI Flags**:
- `--config-path <file>`
- `--overwrite-policy {force|warn|error}`
- `--set key=value` (repeatable)

**Logger**: logs/module_k.log

**Tests**:
- Unit logic
- CLI run
- Overwrite-policy enforcement
- Logger behavior
- Schema error
- Config error
- ensure_dir()

**Example**:
```bash
python module_k.py \
  --config-path config.yaml \
  --overwrite-policy force
```
"""

import argparse
import traceback
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger

class LineEntry(BaseModel):
    player: str
    market: str
    line_value: float
    over_odds: float
    under_odds: float

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def fetch_lines(cfg, logger):
    primary_url = cfg.true_line_sources.primary
    backup_url = cfg.true_line_sources.backup
    try:
        resp = requests.get(primary_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Fetched data from primary source.")
    except Exception as e:
        logger.warning(f"Primary source failed: {e}. Trying backup.")
        try:
            resp = requests.get(backup_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Fetched data from backup source.")
        except Exception as e2:
            logger.error(f"Backup source also failed: {e2}")
            raise

    lines = []
    for entry in data.get("lines", []):
        try:
            row = LineEntry(**entry)
            lines.append(row.model_dump())
        except Exception as err:
            logger.warning(f"Skipping invalid line entry: {entry} | {err}")
    df = pd.DataFrame(lines)
    return df

def compute_vig_free_probs(df: pd.DataFrame):
    def implied_prob(odds):
        return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
    df["prob_over"] = df["over_odds"].apply(implied_prob)
    df["prob_under"] = df["under_odds"].apply(implied_prob)
    total_prob = df["prob_over"] + df["prob_under"]
    df["vig_free_prob"] = df["prob_over"] / total_prob
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", default="config.yaml")
    parser.add_argument("--overwrite-policy", choices=["force", "warn", "error"])
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config_path)
        cfg = apply_cli_overrides(cfg, overrides=args.set)
        policy = (args.overwrite_policy or cfg.overwrite_policy).strip().lower()
        out_dir = Path(cfg.outputs.dir).resolve() / "true_lines"
        ensure_dir(out_dir)
        today_str = datetime.today().strftime("%Y-%m-%d")
        output_path = resolve_output_path(out_dir / f"true_lines_{today_str}.csv", policy)
        logger = get_rotating_logger(__name__, log_dir=cfg.logging.dir, level=cfg.logging.level)
        if args.debug: print("🧪 Starting module_k.py")

        df = fetch_lines(cfg, logger)
        df = compute_vig_free_probs(df)

        logger.info(f"Fetched {len(df)} lines. Columns: {list(df.columns)}")
        logger.debug(f"dtypes: {df.dtypes.to_dict()}")
        df.to_csv(output_path, index=False)
        logger.info(f"Wrote predictions to {output_path}")

    except Exception as e:
        logger = get_rotating_logger(__name__, log_dir="logs", level="DEBUG")
        logger.error("Fatal error in module_k.py", exc_info=True)
        if args.debug:
            print("🧪 Fatal error:", traceback.format_exc())

if __name__ == "__main__":
    main()