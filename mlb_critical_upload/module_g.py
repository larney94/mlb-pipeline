import pandas as pd
import traceback
from pathlib import Path
from typing import List

from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def read_model_output(path: Path, expected_cols: List[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Model output file not found: {path}")
    df = pd.read_parquet(path)
    missing_cols = [col for col in expected_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns {missing_cols} in {path.name}")
    return df

def validate_input_schemas(dfs: List[pd.DataFrame]) -> None:
    try:
        base_cols = list(dfs[0][["player_id", "date"]].columns)
        for i, df in enumerate(dfs[1:], start=1):
            if list(df[["player_id", "date"]].columns) != base_cols:
                raise ValueError(f"Schema mismatch in input file {i}")
    except KeyError as e:
        raise ValueError(f"Required column missing: {e}")
def combine_predictions(dfs: List[pd.DataFrame], weights: List[float]) -> pd.DataFrame:
    base = dfs[0][["player_id", "date"]].copy()
    weighted_preds = sum(w * df["prediction"] for df, w in zip(dfs, weights))
    base["final_prediction"] = weighted_preds / sum(weights)
    return base

if __name__ == "__main__":
    try:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--config-path", required=True)
        parser.add_argument("--overwrite-policy", choices=["error", "warn", "force"], default="error")
        args = parser.parse_args()

        cfg = load_config(args.config_path)
        cfg = apply_cli_overrides(cfg, args)

        logger = get_rotating_logger("combine_predictions")

        input_paths = [
            Path(cfg.inputs.lightgbm_output).resolve(),
            Path(cfg.inputs.ridge_output).resolve()
        ]
        weights = cfg.ensemble.weights
        expected_cols = ["player_id", "date", "prediction"]

        logger.info(f"Reading model outputs from: {input_paths}")
        dfs = [read_model_output(path, expected_cols) for path in input_paths]
        validate_input_schemas(dfs)

        output_path = resolve_output_path(Path(cfg.outputs.ensemble_predictions), args.overwrite_policy)
        ensure_dir(output_path.parent)

        logger.info("Combining predictions using weights: %s", weights)
        combined_df = combine_predictions(dfs, weights)

        combined_df.to_parquet(output_path, index=False)
        logger.info(f"Saved ensemble predictions to: {output_path}")
        logger.info(f"Output schema: {combined_df.columns.tolist()} | Records: {len(combined_df)}")

    except Exception as e:
        logger = get_rotating_logger("combine_predictions_error")
        logger.error("An error occurred during prediction combination.")
        logger.error(traceback.format_exc())
        raise