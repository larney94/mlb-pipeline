"""
module_i.py  ·  Production-grade “run model” entrypoint for the MLB pipeline

Key features
------------
✓ Loads YAML config (via utils.config.load_config)
✓ Accepts CLI overrides:
      --config-path <file>
      --overwrite-policy <force|warn|error>
      --set key=value        (dotted deep-merge)
✓ Validates overwrite-policy
✓ Loads context features, model, runs predictions
✓ Writes Parquet output respecting overwrite policy
✓ Robust logging + test-visible debug / traceback prints
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import joblib
import pandas as pd

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path, extract_set_overrides
from utils.logging_utils import get_rotating_logger


# -----------------------------------------------------------------------------#
# Helper functions
# -----------------------------------------------------------------------------#
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def load_model(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return joblib.load(model_path)


def run_predictions(model, features_df: pd.DataFrame) -> pd.DataFrame:
    try:
        preds = model.predict(features_df)
        return pd.DataFrame(preds, columns=["prediction"])
    except Exception as exc:
        raise ValueError(f"Prediction failed: {exc}") from exc


def export_output(df: pd.DataFrame, out_path: Path):
    ensure_dir(out_path.parent)
    df.to_parquet(out_path, engine="pyarrow")


# -----------------------------------------------------------------------------#
# Main routine
# -----------------------------------------------------------------------------#
def main() -> None:
    # ------------------------------------------------------------------ CLI ----
    parser = argparse.ArgumentParser(description="Run MLB model predictions", add_help=True)
    parser.add_argument("--config-path", type=str, help="Path to YAML config")
    parser.add_argument("--overwrite-policy", type=str, choices=["force", "warn", "error"])
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Dotted YAML override (may be repeated)",
    )
    args, _ = parser.parse_known_args(sys.argv[1:])

    # ----------------------------------------------------------- Load config ----
    cfg = load_config(args.config_path or "config.yaml")

    # Dotted --set overrides (supports nested keys)
    if args.set:
        cfg = apply_cli_overrides(cfg, overrides=args.set)

    # Plain --overwrite-policy flag (highest priority)
    if args.overwrite_policy:
        # Ensure the cli section exists
        if "cli" not in cfg or not isinstance(cfg.cli, dict):
            cfg.cli = {}  # type: ignore[attr-defined]
        cfg.cli["overwrite_policy"] = args.overwrite_policy

    # ------------------------------------------------------------- Logging -----
    logger = get_rotating_logger("run_mlb_model")
    logger.info("🚀 Starting module_i: run_mlb_model.py")
    logger.info("Active config: %s", cfg)

    # 🧪 Debug prints for the pytest subprocess
    print("🧪 cfg.cli:", cfg.cli)
    print("🧪 cfg.overwrite_policy (top-level):", getattr(cfg, "overwrite_policy", ""))
    overwrite = (
        cfg.cli.get("overwrite_policy")  # type: ignore[index]
        or getattr(cfg, "overwrite_policy", "")
        or "error"
    ).strip().lower()
    print("🧪 Resolved overwrite:", overwrite)

    # ----------------------------------------------------- Validate policy -----
    if overwrite not in {"force", "warn", "error"}:
        raise ValueError(f"Invalid overwrite policy: {overwrite}")

    # ---------------------------------------------------- Path resolution ------
    output_path = resolve_output_path(cfg.outputs.model_predictions, overwrite)

    # ---------------------------------------------------- Load data / model ----
    ctx_path = Path(cfg.inputs.context_features).expanduser().resolve()
    if not ctx_path.exists():
        raise FileNotFoundError(f"Context features file not found: {ctx_path}")

    ctx_df = pd.read_parquet(ctx_path)
    logger.info("✅ Context features loaded: %s rows  %s cols", *ctx_df.shape)

    # Column validation
    missing = [c for c in cfg.required_features if c not in ctx_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    model_path = Path(cfg.model_path).expanduser().resolve()
    model = load_model(model_path)

    # ----------------------------------------------------------- Predict -------
    preds_df = run_predictions(model, ctx_df[cfg.required_features])
    logger.info("✅ Predictions generated: %s rows", len(preds_df))

    # ------------------------------------------------------------- Export ------
    export_output(preds_df, output_path)
    logger.info("📦 Predictions written to %s", output_path)


# -----------------------------------------------------------------------------#
# Entrypoint wrapper with robust traceback logging
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger = get_rotating_logger("run_mlb_model")
        logger.error("❌ Unhandled exception:\n%s", traceback.format_exc())
        # Also show in subprocess STDOUT so pytest captures it
        print("❌ Unhandled exception:\n", traceback.format_exc())
        sys.exit(1)
