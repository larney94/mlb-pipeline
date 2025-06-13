import pytest
import pandas as pd
from pathlib import Path
from unittest import mock
from utils.config import load_config
from module_f import filter_data

@pytest.fixture
def dummy_config():
    class DummyFilters:
        min_games_played = 5
        min_innings_pitched = 3.0
        valid_positions = ["P", "C", "1B", "2B", "3B"]
    return mock.Mock(filters=DummyFilters())

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "player_id": [1, 2, 3, None],
        "team_id": ["A", "B", "C", "D"],
        "game_date": ["2021-07-01"] * 4,
        "games_played": [10, 3, 6, 8],
        "innings_pitched": [5.0, 1.2, 4.0, 3.5],
        "position": ["P", "PH", "2B", "1B"]
    })

def test_filter_data_removes_nulls_and_applies_thresholds(sample_df, dummy_config):
    logger = mock.Mock()
    df_filtered = filter_data(sample_df, dummy_config, logger)
    assert all(df_filtered["games_played"] >= 5)
    assert all(df_filtered["innings_pitched"] >= 3.0)
    assert df_filtered["position"].isin(dummy_config.filters.valid_positions).all()
    assert "player_id" in df_filtered.columns and df_filtered["player_id"].notnull().all()
