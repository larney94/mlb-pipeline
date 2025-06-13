import pytest
import pandas as pd
import joblib
import subprocess
from unittest import mock
from pathlib import Path
from module_i import run_predictions, export_output, ensure_dir
from utils.config import load_config
from sklearn.dummy import DummyRegressor

# ---------------------------
# Test: Prediction Logic
# ---------------------------
def test_run_predictions_logic():
    dummy_model = mock.Mock()
    dummy_model.predict.return_value = [[1], [0]]
    dummy_df = pd.DataFrame([[5, 10], [2, 8]], columns=["feat1", "feat2"])

    result = run_predictions(dummy_model, dummy_df)
    assert "prediction" in result.columns
    assert len(result) == 2

# ---------------------------
# Test: Overwrite Policy
# ---------------------------
@pytest.mark.parametrize("policy", ["force", "warn", "error"])
def test_overwrite_policy(tmp_path, policy):
    from utils.cli_utils import resolve_output_path

    dummy_path = tmp_path / "output.parquet"
    dummy_path.write_text("existing")

    if policy == "error":
        with pytest.raises(FileExistsError):
            resolve_output_path(dummy_path, policy)
    else:
        resolved = resolve_output_path(dummy_path, policy)
        assert resolved.exists()

# ---------------------------
# Test: CLI Execution
# ---------------------------
def test_cli_run(tmp_path):
    config_path = tmp_path / "config.yaml"
    model_path = tmp_path / "dummy_model.joblib"
    features_path = tmp_path / "context.parquet"
    output_path = tmp_path / "predictions.parquet"

    # ✅ Updated dummy config using model_predictions
    config_path.write_text(f"""
inputs:
  context_features: {features_path}
outputs:
  model_predictions: {output_path}
model_path: {model_path}
required_features: ["x1", "x2"]
overwrite_policy: force
""")

    # Dummy context data
    df = pd.DataFrame({"x1": [1, 2], "x2": [3, 4]})
    df.to_parquet(features_path)

    # Dump a real sklearn DummyRegressor model with 2-feature input
    model = DummyRegressor(strategy="constant", constant=7)
    model.fit([[0, 0], [1, 1]], [0, 1])  # match 2-feature input
    joblib.dump(model, model_path)

    # Run subprocess
    result = subprocess.run([
        "python", "module_i.py",
        "--config-path", str(config_path),
        "--set", "cli.overwrite_policy=force"
    ], capture_output=True, text=True)
    
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)

    assert result.returncode == 0
    assert Path(output_path).exists()

# ---------------------------
# Test: Logger Output
# ---------------------------
def test_logger_output(caplog):
    from utils.logging_utils import get_rotating_logger
    logger = get_rotating_logger("test_logger")
    logger.warning("testing logger warning")
    assert "testing logger warning" in caplog.text

# ---------------------------
# Test: Schema Error
# ---------------------------
def test_missing_required_column(tmp_path):
    required = ["a", "b"]
    df = pd.DataFrame({"a": [1, 2]})
    missing = [col for col in required if col not in df.columns]
    assert missing == ["b"]

# ---------------------------
# Test: Config Error
# ---------------------------
def test_missing_config_key():
    bad_cfg = mock.Mock()
    del bad_cfg.outputs
    with pytest.raises(AttributeError):
        _ = bad_cfg.outputs.predictions

# ---------------------------
# Test: ensure_dir
# ---------------------------
def test_ensure_dir(tmp_path):
    test_path = tmp_path / "nested" / "output"
    ensure_dir(test_path)
    assert test_path.exists()
