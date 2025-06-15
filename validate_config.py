# validate_config.py

import argparse
import os
import sys
from pathlib import Path
from typing import List

from utils.config import load_config, apply_cli_overrides


# ─────────────────────────────────────────────────────────────
# Section: CLI Argument Parsing
# ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate config.yaml for MLB Player Prediction Pipeline"
    )
    parser.add_argument(
        "--config", type=str, default="config.yaml",
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--set", action="append", default=[],
        help="Override config values via dotted paths (e.g. pipeline.concurrency=4)"
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────
# Section: Validation Logic
# ─────────────────────────────────────────────────────────────

def check_path_exists(path: str, must_be_file: bool = False) -> bool:
    path_obj = Path(path)
    if must_be_file:
        return path_obj.is_file()
    return path_obj.exists() or not path_obj.is_absolute()


def validate_paths(config_dict: dict) -> List[str]:
    bad_paths = []
    # Keys that are expected to be existing paths
    check_keys = [k for k in walk_keys(config_dict)
                  if k.endswith(("_csv", "_path", "_template", "_file", "_dir"))]

    for key in check_keys:
        value = get_nested_value(config_dict, key)
        if not value:
            continue
        is_file = key.endswith(("_csv", "_file", "_path", "_template"))
        if not check_path_exists(value, must_be_file=is_file):
            bad_paths.append(f"{key} = {value}")
    return bad_paths


def walk_keys(d, prefix="") -> List[str]:
    keys = []
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.extend(walk_keys(v, full))
        else:
            keys.append(full)
    return keys


def get_nested_value(d: dict, dotted_key: str):
    keys = dotted_key.split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, None)
        else:
            return None
    return d


# ─────────────────────────────────────────────────────────────
# Section: Entrypoint
# ─────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    try:
        config = load_config(args.config)
        config = apply_cli_overrides(config, args.set)
        config_dict = config.dict()
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)

    # Validate paths
    invalid_paths = validate_paths(config_dict)

    if invalid_paths:
        print("\n❌ Invalid paths detected:")
        for p in invalid_paths:
            print(f"   - {p}")
        print("\n⚠️  Fix the above paths or update your config.")
        sys.exit(1)
    else:
        print("✅ All config paths appear valid.")

    print("✅ Config structure is valid and all required fields are present.")
    sys.exit(0)


if __name__ == "__main__":
    main()
