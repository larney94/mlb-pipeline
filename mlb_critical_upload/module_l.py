"""
✅ module_l.py — Final Stage: LLM Insight Generation for MLB Player Predictions

• Purpose: Join prediction + true line data and generate LLM insights per player.
• Inputs:
    - combined_predictions.parquet (from outputs.combined_preds_dir)
    - true_lines_<DATE>.csv (from outputs.true_lines_dir)
    - Jinja2 template (from llm.prompt_template)
• Outputs:
    - outputs.output_dir/mlb_llm_predictions_<DATE>.csv
        Columns: player, model_pred, line, llm_pred, flag, confidence, prompt_version
    - outputs.output_dir/mlb_llm_explanations_<DATE>.txt
        One line per player — natural language LLM-generated output
• Config keys: llm.*, outputs.*, overwrite_policy, logging.*
• CLI: --config-path, --overwrite-policy, --set key=value, --debug
"""

import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from jinja2 import Template

from utils.config import Config, load_config, apply_cli_overrides
from utils.cli_utils import parse_cli_args
from utils.logging_utils import setup_logger
from utils.io_utils import resolve_output_path, ensure_dir

LOGGER_NAME = "module_l"

def load_prompt_template(path: Path) -> Template:
    try:
        with open(path, "r") as f:
            return Template(f.read())
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt template from {path}: {e}")

def call_llm(endpoint: str, payload: dict) -> str:
    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"LLM ERROR: {e}"

def generate_flag(pred, line):
    if pd.isna(pred) or pd.isna(line):
        return ""
    return "over" if pred > line else "under"

def parse_llm_response(response: str, default_pred: float) -> tuple[float, str, str]:
    try:
        parts = [p.strip() for p in response.split(",")]
        dct = {k.strip().lower(): v.strip() for p in parts if ":" in p for k, v in [p.split(":", 1)]}
        pred = float(dct.get("prediction", default_pred))
        explanation = dct.get("explanation", response)
        flag = dct.get("flag", "").lower()
        return pred, explanation, flag
    except Exception:
        return default_pred, response, ""

def compute_confidence(pred: float, line: float) -> float:
    try:
        return round(1 - abs(pred - line) / max(abs(pred), 1), 4)
    except:
        return 0.0

def main():
    args = parse_cli_args()
    config: Config = load_config(args.config_path)
    config = apply_cli_overrides(config, args.set)
    overwrite = args.overwrite_policy or getattr(config, "overwrite_policy", "error")
    debug = args.debug or bool(os.getenv("CLI_DEBUG") == "1")

    logger = setup_logger(
        name=LOGGER_NAME,
        log_dir=config.logging.dir,
        level=config.logging.level,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count
    )
    logger.info("🚀 module_l starting")

    date_str = datetime.now().strftime("%Y-%m-%d")

    preds_path = Path(config.outputs.combined_preds_dir) / "combined_predictions.parquet"
    lines_path = Path(config.outputs.true_lines_dir) / f"true_lines_{date_str}.csv"
    output_csv = resolve_output_path(Path(config.outputs.output_dir) / f"mlb_llm_predictions_{date_str}.csv", overwrite)
    output_txt = resolve_output_path(Path(config.outputs.output_dir) / f"mlb_llm_explanations_{date_str}.txt", overwrite)
    prompt_path = Path(config.llm.prompt_template).resolve()
    endpoint = config.llm.endpoint

    ensure_dir(output_csv.parent)

    preds_df = pd.read_parquet(preds_path)
    lines_df = pd.read_csv(lines_path)

    required_pred_cols = {"player", "predicted_value", "stat", "game_date"}
    required_line_cols = {"player", "market", "line_value"}

    if not required_pred_cols.issubset(preds_df.columns):
        raise ValueError(f"Missing required columns in predictions: {required_pred_cols - set(preds_df.columns)}")
    if not required_line_cols.issubset(lines_df.columns):
        raise ValueError(f"Missing required columns in true lines: {required_line_cols - set(lines_df.columns)}")

    merged = pd.merge(preds_df, lines_df, how="left", on=["player", "market"])
    template = load_prompt_template(prompt_path)
    prompt_version = prompt_path.name

    llm_outputs = []
    explanations = []

    for _, row in merged.iterrows():
        safe_row = {
            "player": str(row["player"]),
            "predicted_value": f"{row['predicted_value']:.2f}" if not pd.isna(row['predicted_value']) else "N/A",
            "line_value": f"{row['line_value']:.2f}" if not pd.isna(row.get("line_value")) else "N/A",
            "stat": str(row.get("stat", "")),
            "game_date": str(row.get("game_date", ""))
        }

        prompt = template.render(**safe_row)
        if debug:
            print(f"🧪 Prompt:\n{prompt}\n---")

        payload = {
            "model": config.llm.model,
            "prompt": prompt,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "stream": False,
            "options": {"num_predict": config.llm.max_tokens}
        }

        raw_response = "[DEBUG MODE]" if debug else call_llm(endpoint, payload)
        parsed_pred, explanation, parsed_flag = parse_llm_response(raw_response, row["predicted_value"])

        if not debug and (parsed_pred == row["predicted_value"] and "LLM ERROR" in explanation):
            logger.warning(f"⚠️ Retry: Poor LLM response for {row['player']} — retrying...")
            raw_response = call_llm(endpoint, payload)
            parsed_pred, explanation, parsed_flag = parse_llm_response(raw_response, row["predicted_value"])

        confidence = compute_confidence(parsed_pred, row.get("line_value", parsed_pred))

        llm_outputs.append({
            "player": row["player"],
            "model_pred": row["predicted_value"],
            "line": row.get("line_value"),
            "llm_pred": parsed_pred,
            "flag": parsed_flag or generate_flag(row["predicted_value"], row.get("line_value")),
            "confidence": confidence,
            "prompt_version": prompt_version
        })

        explanations.append(f"{row['player']}: {explanation}")

    pd.DataFrame(llm_outputs).to_csv(output_csv, index=False)
    with open(output_txt, "w") as f:
        f.write("\n".join(explanations))

    logger.info(f"✅ Saved {len(llm_outputs)} predictions → {output_csv}")
    logger.info(f"✅ Saved natural language insights → {output_txt}")

if __name__ == "__main__":
    main()
