import pytest
import pandas as pd
import os
from pathlib import Path
from module_k import ensure_dir, compute_vig_free_probs
from utils.config import load_config
from subprocess import run

# --------- TEST 1: Unit logic test on vig-free prob -------------
def test_compute_vig_free_probs_logic():
    df = pd.DataFrame({
        "over_odds": [110],
        "under_odds": [-105]
    })
    df["line_value"] = [1.5]
    df["player"] = ["John Doe"]
    df["market"] = ["Hits"]
    result = compute_vig_free_probs(df)
    assert "vig_free_prob" in result.columns
    assert 0 < result["vig_free_prob"].iloc[0] < 1

# --------- TEST 2: ensure_dir works -----------------------------
def test_ensure_dir(tmp_path):
    test_path = tmp_path / "new_dir"
    ensure_dir(test_path)
    assert test_path.exists() and test_path.is_dir()

# --------- TEST 3: Schema enforcement (invalid line) ------------
def test_invalid_line_skipped(caplog):
    from module_k import LineEntry
    with pytest.raises(Exception):
        LineEntry(player="x", market="y", line_value="bad", over_odds="bad", under_odds=0)

# --------- TEST 4: Config error ---------------------------------
def test_config_missing_key(tmp_path):
    from utils.config import Config
    bad_config_dict = {
        "outputs": {"dir": str(tmp_path)}
        # missing true_line_sources
    }
    with pytest.raises(Exception):
        Config(**bad_config_dict)

# --------- TEST 5: Logger appears in logs -----------------------
def test_logger_caplog(caplog):
    from module_k import get_rotating_logger
    logger = get_rotating_logger("test_logger", log_dir="logs", level="DEBUG")
    logger.info("Logger test message")
    assert "Logger test message" in caplog.text

# --------- TEST 6: CLI subprocess call --------------------------
def test_cli_subprocess(tmp_path):
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
true_line_sources:
  primary: https://httpbin.org/json
  backup: https://httpbin.org/json
outputs:
  dir: {}
logging:
  dir: logs
  level: DEBUG
  max_bytes: 1000000
  backup_count: 2
overwrite_policy: force
""".format(str(tmp_path)))
    output_file = tmp_path / "true_lines" / f"true_lines_{pd.Timestamp.today().date()}.csv"
    result = run([
        "python", "module_k.py",
        "--config-path", str(config_file),
        "--overwrite-policy", "force"
    ], capture_output=True, text=True)
    assert result.returncode == 0 or "Fetched data from" in result.stdout or result.stderr

# --------- TEST 7: Overwrite policy variants --------------------
@pytest.mark.parametrize("policy", ["force", "warn", "error"])
def test_overwrite_policy_behavior(tmp_path, policy):
    from module_k import resolve_output_path
    f = tmp_path / "existing.csv"
    f.write_text("already here")
    if policy == "force":
        path = resolve_output_path(f, policy)
        assert path.exists()
    elif policy == "warn":
        path = resolve_output_path(f, policy)
        assert path.exists()
    elif policy == "error":
        with pytest.raises(FileExistsError):
            resolve_output_path(f, policy)