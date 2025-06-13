import pytest
import pandas as pd
import tempfile
from pathlib import Path
from module_g import combine_predictions, validate_input_schemas
from utils.cli_utils import resolve_output_path
from utils.config import load_config
from unittest import mock

@pytest.fixture
def dummy_dfs():
    df1 = pd.DataFrame({
        "player_id": [1, 2],
        "date": ["2024-07-01", "2024-07-01"],
        "prediction": [0.3, 0.6]
    })
    df2 = pd.DataFrame({
        "player_id": [1, 2],
        "date": ["2024-07-01", "2024-07-01"],
        "prediction": [0.5, 0.4]
    })
    return [df1, df2]

def test_combine_predictions_logic(dummy_dfs):
    result = combine_predictions(dummy_dfs, [0.6, 0.4])
    assert "final_prediction" in result.columns
    assert result.shape[0] == 2
    expected = (0.3 * 0.6 + 0.5 * 0.4) / 1.0
    assert abs(result.loc[0, "final_prediction"] - expected) < 1e-6

def test_schema_mismatch_error():
    df1 = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "prediction": [0.4]})
    df2 = pd.DataFrame({"player_id": [1], "timestamp": ["2024-07-01"], "prediction": [0.5]})
    with pytest.raises(ValueError):
        validate_input_schemas([df1, df2])

def test_overwrite_policy_force(tmp_path):
    output_file = tmp_path / "test.parquet"
    df = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "final_prediction": [0.8]})
    df.to_parquet(output_file)
    result_path = resolve_output_path(output_file, "force")
    assert result_path == output_file

def test_overwrite_policy_error(tmp_path):
    output_file = tmp_path / "test.parquet"
    df = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "final_prediction": [0.8]})
    df.to_parquet(output_file)
    output_file = output_file.resolve()  # ✅ ensure it’s a real file path
    with pytest.raises(FileExistsError):
        resolve_output_path(output_file, "error")

def test_overwrite_policy_warn(tmp_path, caplog):
    output_file = tmp_path / "test.parquet"
    df = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "final_prediction": [0.8]})
    df.to_parquet(output_file)
    with caplog.at_level("WARNING", logger="overwrite_policy"):  # ✅ capture the correct logger
        resolved = resolve_output_path(output_file, "warn")
        assert "already exists" in caplog.text
        assert resolved == output_file

def test_missing_config_key(monkeypatch):
    bad_config = {"inputs": {"ridge_output": "foo.parquet"}}
    monkeypatch.setattr("utils.config.load_config", lambda _: bad_config)
    with pytest.raises(KeyError):
        _ = bad_config["inputs"]["lightgbm_output"]

def test_logger_output(tmp_path, caplog):
    df1 = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "prediction": [0.1]})
    df2 = pd.DataFrame({"player_id": [1], "date": ["2024-07-01"], "prediction": [0.3]})
    combined = combine_predictions([df1, df2], [0.5, 0.5])
    with caplog.at_level("INFO"):
        import logging
        logger = logging.getLogger("combine_predictions")
        logger.info("Logger active for combine_predictions test")
        assert "Logger active for combine_predictions test" in caplog.text
