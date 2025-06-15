import traceback
from pathlib import Path
import pandas as pd
from utils.config import load_config
from utils.cli_utils import apply_cli_overrides, resolve_output_path
from utils.logging_utils import get_rotating_logger

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def validate_input_schema(df: pd.DataFrame):
    required_columns = [
        "player_id", "team", "opponent", "game_date",
        "is_home", "batting_average", "runs", "hits",
        "rolling_runs_avg_5", "rolling_whip_10"
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required input columns: {missing}")

def compute_context_features(df: pd.DataFrame) -> pd.DataFrame:
    df["home_game_flag"] = df["is_home"].astype(bool)
    df["team_avg_runs_last_5"] = df["rolling_runs_avg_5"]
    df["opponent_whip_last_10"] = df["rolling_whip_10"]
    df["player_z_batting_avg"] = (df["batting_average"] - df["batting_average"].mean()) / df["batting_average"].std()
    df["context_hash_id"] = df["player_id"].astype(str) + "_" + df["game_date"].astype(str)
    return df

def export_output(df: pd.DataFrame, path: Path):
    df.to_parquet(path, engine="pyarrow", index=False)

def main():
    logger = get_rotating_logger(__name__)
    try:
        cfg = load_config()
        cfg = apply_cli_overrides(cfg)

        input_path = Path(cfg.inputs.consolidated_data).resolve()
        output_path = resolve_output_path(Path(cfg.outputs.context_features).resolve(), cfg.overwrite_policy)

        logger.info(f"Loading input file from {input_path}")
        df = pd.read_parquet(input_path)
        logger.info(f"Loaded {df.shape[0]} rows and {df.shape[1]} columns")

        validate_input_schema(df)
        df_features = compute_context_features(df)

        ensure_dir(output_path.parent)
        export_output(df_features, output_path)

        logger.info(f"Saved context features to {output_path} with shape {df_features.shape}")

    except Exception as e:
        logger.exception("An error occurred while generating context features.")
        traceback.print_exc()

if __name__ == "__main__":
    main()
