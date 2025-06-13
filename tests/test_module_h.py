import pandas as pd
import pytest
import subprocess
from pathlib import Path
from module_h import compute_context_features, validate_input_schema

def test_compute_context_features():
    df = pd.DataFrame({
        "player_id": [1, 2],
        "team": ["A", "B"],
        "opponent": ["B", "A"],
        "game_date": ["2024-04-01", "2024-04-02"],
        "is_home": [1, 0],
        "batting_average": [0.300, 0.250],
        "runs": [1, 2],
        "hits": [2, 1],
        "rolling_runs_avg_5": [5.2, 4.8],
        "rolling_whip_10": [1.10, 1.20]
    })
    result = compute_context_features(df)
    assert "team_avg_runs_last_5" in result.columns
    assert "player_z_batting_avg" in result.columns
    assert result.shape[0] == 2

def test_missing_columns_raises():
    df = pd.DataFrame({"player_id": [1], "batting_average": [0.3]})
    with pytest.raises(ValueError):
        validate_input_schema(df)

def test_cli_run(tmp_path):
    config_path = Path("config.yaml").resolve()
    output_path = tmp_path / "context_features.parquet"
    result = subprocess.run([
        "python", "module_h.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ], capture_output=True, text=True)
    assert result.returncode == 0 or "Saved context features" in result.stdout
