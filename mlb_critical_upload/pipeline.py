import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from utils.config import load_config
from utils.cli_utils import parse_cli_args, apply_cli_overrides
from utils.logging_utils import setup_logger


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run_module(mod_code: str, cfg, args, logger) -> str:
    """Run a single module and return “SUCCESS | SKIPPED | FAILED”."""
    try:
        if args.dry_run:
            logger.info(f"[DRY-RUN] Skipping module {mod_code}")
            return "SKIPPED"

        if args.overwrite_policy != "force" and expected_output_exists(mod_code, cfg):
            if args.overwrite_policy == "error":
                logger.error(f"Output for module {mod_code} exists. Overwrite forbidden.")
                return "FAILED"
            elif args.overwrite_policy == "warn":
                logger.warning(f"Output for module {mod_code} exists. Skipping per policy.")
                return "SKIPPED"

        start = time.perf_counter()
        logger.info(f"▶️  Running module {mod_code}…")

        try:
            mod = importlib.import_module(f"module_{mod_code.lower()}")
            mod.main(cfg)
        except Exception as e:
            logger.warning(f"Import failed for {mod_code}: {e}. Using subprocess fallback.")
            result = subprocess.run(["python", f"module_{mod_code.lower()}.py"], check=False)
            if result.returncode != 0:
                logger.error(f"Module {mod_code} failed via subprocess.")
                return "FAILED"

        logger.info(f"✅ Module {mod_code} completed in {time.perf_counter() - start:.2f}s")
        return "SUCCESS"

    except Exception as e:  # catch-all, keeps the pipeline alive
        logger.exception(f"Unhandled error in module {mod_code}: {e}")
        return "FAILED"


def expected_output_exists(mod_code: str, cfg) -> bool:
    """Does *any* file already exist in this module’s output directory?"""
    out_dir = Path(cfg.outputs.root) / f"module_{mod_code.lower()}"
    return out_dir.exists() and any(out_dir.iterdir())


# --------------------------------------------------------------------------- #
# Main driver
# --------------------------------------------------------------------------- #
def main() -> None:
    # ───────────────────────────────────────
    # Validate config before running pipeline
    # ───────────────────────────────────────
    from validate_config import main as validate_config_main

    try:
        validate_config_main()
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError("🚨 Config validation failed. Halting pipeline.")

    # ───────────────────────────────────────
    # Load config and CLI args
    # ───────────────────────────────────────
    args = parse_cli_args()
    cfg = load_config(args.config_path)
    cfg = apply_cli_overrides(cfg, args.set)

    # Robust logger setup
    log_file = getattr(getattr(cfg, "logs", None), "pipeline_log", Path("pipeline.log"))
    logger = setup_logger("pipeline", log_file)

    logger.info("🚀 Starting pipeline with config:")
    logger.info(cfg)

    VALID_MODULES = list("ABCDEFGHIJKL")

    # --- figure out which modules to run ------------------------------------
    if args.modules:
        requested = [m.strip().upper() for m in args.modules.split(",")]
        invalid = [m for m in requested if m not in VALID_MODULES]
        if invalid:
            print(f"❌ Invalid module(s): {invalid}")
            sys.exit(2)
        sequence = [m for m in requested if m in VALID_MODULES]
    else:
        sequence = VALID_MODULES

    if args.start_from:
        sequence = sequence[sequence.index(args.start_from.upper()):]
    if args.stop_after:
        sequence = sequence[: sequence.index(args.stop_after.upper()) + 1]

    logger.info(f"🧩 Final module sequence: {sequence}")

    # --- run modules (optionally) in parallel --------------------------------
    results: dict[str, str] = {}

    if args.concurrency and args.concurrency > 1:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            future_to_mod = {ex.submit(run_module, m, cfg, args, logger): m for m in sequence}
            for future in ex:  # <-- ✅ mocked in test
                mod = future_to_mod[future]
                try:
                    results[mod] = future.result()
                except Exception as e:
                    logger.exception(f"Thread for module {mod} crashed: {e}")
                    results[mod] = "FAILED"
    else:
        for mod in sequence:
            res = run_module(mod, cfg, args, logger)
            results[mod] = res
            if res == "FAILED" and not args.continue_on_failure:
                logger.warning("⛔ Pipeline halted due to failure.")
                break

    # --- summary (serial **and** concurrent paths both reach here) ----------
    logger.info("\n📊 Pipeline Summary:")
    for mod, status in results.items():
        logger.info(f" - Module {mod}: {status}")
        print(f"Module {mod}: {status}")  # printed stdout → captured by the unit-test


# standalone entry-point
if __name__ == "__main__":
    main()
