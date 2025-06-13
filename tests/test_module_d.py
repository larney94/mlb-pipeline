import pytest
import pandas as pd
from pathlib import Path
import shutil
import tempfile

from utils.config import load_config
from module_d import main as combine_main


@pytest.fixture
def test_env(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    config_path = tmp_dir / "test_config.yaml"
    output_dir = tmp_dir / "output"
    context_dir = tmp_dir / "context"

    # Dummy files
    recent_gamelogs = tmp_dir / "recent_gamelogs.csv"
    static_player = tmp_dir / "static_player.csv"
    context_parquet = context_dir / "context_data.parquet"

    # Create dummy data
    output_dir.mkdir()
    context_dir.mkdir()

    pd.DataFrame({
        "player_id": [1],
        "date": ["2024-08-01"],
        "team_id": [100],
        "stat": [5]
    }).to_csv(recent_gamelogs, index=False)

    pd.DataFrame({
        "player_id": [1],
        "position": ["P"]
    }).to_csv(static_player, index=False)

    pd.DataFrame({
        "player_id": [1],
        "date": ["2024-08-01"],
        "ctx": [1.5]
    }).to_parquet(context_parquet, index=False)

    with open(config_path, "w") as f:
        f.write(f"""model: {{}}
paths: {{}}
cli: {{}}
flags: {{}}
inputs:
  recent_gamelogs_csv: {str(recent_gamelogs)}
  static_player_csv: {str(static_player)}
outputs:
  context_dir: {str(context_dir)}
  full_feature_set: {str(output_dir / 'full_feature_set.parquet')}
""")

    yield tmp_dir, config_path, output_dir
    shutil.rmtree(tmp_dir)


def test_combine_success(test_env, monkeypatch):
    tmp_dir, config_path, output_dir = test_env

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    combine_main()

    output_file = output_dir / "full_feature_set.parquet"
    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert "player_id" in df.columns
    assert "position" in df.columns
    assert "ctx" in df.columns


def test_missing_input_file(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    config_path = tmp_dir / "bad_config.yaml"

    with open(config_path, "w") as f:
        f.write("""model: {}
paths: {}
cli: {}
flags: {}
inputs:
  recent_gamelogs_csv: missing.csv
  static_player_csv: missing.csv
outputs:
  context_dir: ./missing_dir
  full_feature_set: ./bad_out.parquet
""")

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    with pytest.raises(SystemExit):
        combine_main()

    shutil.rmtree(tmp_dir)
    
def test_missing_join_column(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    config_path = tmp_dir / "bad_schema_config.yaml"
    output_dir = tmp_dir / "output"
    context_dir = tmp_dir / "context"

    recent_gamelogs = tmp_dir / "gamelogs.csv"
    static_player = tmp_dir / "players.csv"
    context_parquet = context_dir / "context.parquet"

    output_dir.mkdir()
    context_dir.mkdir()

    # Missing player_id on purpose
    pd.DataFrame({
        "date": ["2024-08-01"],
        "team_id": [100],
        "stat": [5]
    }).to_csv(recent_gamelogs, index=False)

    pd.DataFrame({
        "position": ["P"]
    }).to_csv(static_player, index=False)

    pd.DataFrame({
        "player_id": [1],
        "date": ["2024-08-01"],
        "ctx": [1.5]
    }).to_parquet(context_parquet, index=False)

    with open(config_path, "w") as f:
        f.write(f"""model: {{}}
paths: {{}}
cli: {{}}
flags: {{}}
inputs:
  recent_gamelogs_csv: {str(recent_gamelogs)}
  static_player_csv: {str(static_player)}
outputs:
  context_dir: {str(context_dir)}
  full_feature_set: {str(output_dir / 'full_feature_set.parquet')}
""")

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    with pytest.raises(SystemExit):
        combine_main()

    shutil.rmtree(tmp_dir)

def test_schema_mismatch_columns(test_env, monkeypatch):
    tmp_dir, config_path, output_dir = test_env

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    combine_main()

    df = pd.read_parquet(output_dir / "full_feature_set.parquet")

    required_columns = {"player_id", "date", "position", "ctx"}
    assert required_columns.issubset(set(df.columns)), \
        f"Missing columns: {required_columns - set(df.columns)}"

def test_row_count_expected_post_merge(test_env, monkeypatch):
    tmp_dir, config_path, output_dir = test_env

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    combine_main()

    df = pd.read_parquet(output_dir / "full_feature_set.parquet")

    # Expected: 1 row from gamelogs (and 1:1 merge)
    assert df.shape[0] == 1, f"Unexpected row count: {df.shape[0]}"

def test_duplicate_rows_detected_and_removed(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    config_path = tmp_dir / "dupe_config.yaml"
    output_dir = tmp_dir / "output"
    context_dir = tmp_dir / "context"

    recent_gamelogs = tmp_dir / "gamelogs.csv"
    static_player = tmp_dir / "players.csv"
    context_parquet = context_dir / "context.parquet"

    output_dir.mkdir()
    context_dir.mkdir()

    # Two identical rows = simulated duplication
    pd.DataFrame({
        "player_id": [1, 1],
        "date": ["2024-08-01", "2024-08-01"],
        "team_id": [100, 100],
        "stat": [5, 5]
    }).to_csv(recent_gamelogs, index=False)

    pd.DataFrame({
        "player_id": [1],
        "position": ["P"]
    }).to_csv(static_player, index=False)

    pd.DataFrame({
        "player_id": [1],
        "date": ["2024-08-01"],
        "ctx": [1.5]
    }).to_parquet(context_parquet, index=False)

    with open(config_path, "w") as f:
        f.write(f"""model: {{}}
paths: {{}}
cli: {{}}
flags: {{}}
inputs:
  recent_gamelogs_csv: {str(recent_gamelogs)}
  static_player_csv: {str(static_player)}
outputs:
  context_dir: {str(context_dir)}
  full_feature_set: {str(output_dir / 'full_feature_set.parquet')}
""")

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    combine_main()

    df = pd.read_parquet(output_dir / "full_feature_set.parquet")
    assert df.shape[0] == 1, "Duplicate rows were not removed properly"

def test_merge_key_null_check(test_env, monkeypatch):
    tmp_dir, config_path, output_dir = test_env

    monkeypatch.setattr("sys.argv", [
        "combine_features.py",
        "--config-path", str(config_path),
        "--overwrite-policy", "force"
    ])

    combine_main()

    df = pd.read_parquet(output_dir / "full_feature_set.parquet")
    assert df["player_id"].notnull().all(), "Null player_id found in merged output"
    assert df["date"].notnull().all(), "Null date found in merged output"
