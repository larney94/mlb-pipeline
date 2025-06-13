import pytest
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from utils.config import load_config
from module_c import consolidate_contextual_features
import shutil
import os

@pytest.fixture
def tmp_static_dir(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()

    df1 = pd.DataFrame({
        "teamID": ["NYA", "BOS"],
        "DATE": ["2024-07-01", "2024-07-01"],
        "park_factor": [1.02, 0.98]
    })
    df1.to_csv(static_dir / "park_factors.csv", index=False)

    df2 = pd.DataFrame({
        "Team": ["NYA", "BOS"],
        "DATE": ["2024-07-01", "2024-07-01"],
        "team_elo": [1550, 1510]
    })
    df2.to_csv(static_dir / "elo_ratings.csv", index=False)

    return static_dir

@pytest.fixture
def tmp_output_path(tmp_path):
    output_path = tmp_path / "context_features.parquet"
    return output_path

def test_successful_consolidation(tmp_static_dir, tmp_output_path):
    alias_map = {"teamID": "team_id", "Team": "team_id", "DATE": "date"}
    consolidate_contextual_features(tmp_static_dir, tmp_output_path, alias_map, overwrite="force")

    assert tmp_output_path.exists()
    table = pq.read_table(tmp_output_path)
    df = table.to_pandas()
    assert "team_id" in df.columns
    assert "date" in df.columns
    assert len(df) == 4

def test_missing_required_column(tmp_static_dir, tmp_output_path):
    bad_file = tmp_static_dir / "elo_ratings.csv"
    df = pd.read_csv(bad_file)
    df.drop(columns=["Team"], inplace=True)
    df.to_csv(bad_file, index=False)

    alias_map = {"teamID": "team_id", "Team": "team_id", "DATE": "date"}
    with pytest.raises(ValueError, match="Missing required columns"):
        consolidate_contextual_features(tmp_static_dir, tmp_output_path, alias_map, overwrite="force")

def test_skip_overwrite_policy(tmp_static_dir, tmp_output_path):
    pd.DataFrame({"dummy": [1]}).to_parquet(tmp_output_path)

    alias_map = {"teamID": "team_id", "Team": "team_id", "DATE": "date"}
    consolidate_contextual_features(tmp_static_dir, tmp_output_path, alias_map, overwrite="warn")

    table = pq.read_table(tmp_output_path)
    df = table.to_pandas()
    assert "dummy" in df.columns

def test_error_overwrite_policy(tmp_static_dir, tmp_output_path):
    pd.DataFrame({"dummy": [1]}).to_parquet(tmp_output_path)

    alias_map = {"teamID": "team_id", "Team": "team_id", "DATE": "date"}
    with pytest.raises(FileExistsError):
        consolidate_contextual_features(tmp_static_dir, tmp_output_path, alias_map, overwrite="error")
