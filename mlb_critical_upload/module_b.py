import argparse
import requests
import tempfile
from pathlib import Path

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path, handle_overwrite
from utils.logging_utils import get_rotating_logger

LOGGER = get_rotating_logger("module_b")

def download_static_csvs(cfg: dict) -> None:
    static_dir = Path(cfg["outputs"]["static_dir"]).resolve()
    static_dir.mkdir(parents=True, exist_ok=True)

    static_csvs = cfg.get("static_csvs", [])
    if not static_csvs:
        raise ValueError("No static_csvs defined in config")

    for entry in static_csvs:
        name = entry.get("name")
        url = entry.get("url")

        if not name or not url:
            LOGGER.error(f"Invalid entry in static_csvs: {entry}")
            continue

        output_path = static_dir / f"{name}.csv"
        resolved_output = resolve_output_path(str(output_path), cfg.get("overwrite_policy", "error"))

        if not handle_overwrite(resolved_output, cfg):
            LOGGER.warning(f"Skipping existing file due to overwrite policy: {resolved_output}")
            continue

        LOGGER.info(f"Downloading {url} → {resolved_output}")
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            LOGGER.error(f"Failed to download {url}: {e}")
            continue

        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = Path(tmp_file.name)

            tmp_path.replace(resolved_output)
            LOGGER.info(f"Saved to {resolved_output}")
        except Exception as e:
            LOGGER.error(f"Failed to save {name}.csv: {e}")

def main():
    parser = argparse.ArgumentParser(description="Module B: Download static reference CSV datasets.")
    parser.add_argument("--config-path", type=str, default="config.yaml", help="Path to config YAML")
    parser.add_argument("--overwrite-policy", type=str, choices=["error", "warn", "force"], default=None)
    args = parser.parse_args()

    try:
        cfg = load_config(args.config_path)
        if args.overwrite_policy:
            cfg["overwrite_policy"] = args.overwrite_policy
        cfg = apply_cli_overrides(cfg)

        LOGGER.info(f"Starting Module B with config: {args.config_path}")
        download_static_csvs(cfg)
        LOGGER.info("Module B completed successfully.")
    except Exception as e:
        LOGGER.exception(f"Module B failed: {e}")
        raise

if __name__ == "__main__":
    main()
