# tests/test_module_a.py

import pytest
import pandas as pd
import shutil
from unittest.mock import patch, Mock
import argparse
from pathlib import Path

from module_a import fetch_gamelogs, write_csv, main


@pytest.fixture
def dummy_df():
    return pd.DataFrame({
        'playerID': ['player1', 'player2'],
        'date': ['2024-06-13', '2024-06-14'],
        'team': ['TeamA', 'TeamB'],
        'at_bats': [4, 3],
        'hits': [2, 1],
        'HR': [1, 0],
        'RBIs': [2, 1]
    })


@pytest.fixture
def test_dir(tmp_path):
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@patch('module_a.batting_stats')
@patch('module_a.pitching_stats')
def test_fetch_gamelogs(mock_pitching, mock_batting, dummy_df):
    mock_batting.return_value = dummy_df
    mock_pitching.return_value = dummy_df

    batting, pitching = fetch_gamelogs(2024, 10, logger=Mock())
    assert batting.equals(dummy_df)
    assert pitching.equals(dummy_df)


def test_write_csv(dummy_df, test_dir):
    path = test_dir / "test.csv"
    write_csv(dummy_df, path, 'error', logger=Mock())
    assert path.exists()

    with pytest.raises(SystemExit):
        write_csv(dummy_df, path, 'error', logger=Mock())

    write_csv(dummy_df, path, 'warn', logger=Mock())
    write_csv(dummy_df, path, 'force', logger=Mock())


def test_integration(tmp_path, monkeypatch):
    config = {
        'seasons': [2024],
        'outputs': {'gamelogs_dir': str(tmp_path)},
        'pybaseball_timeout': 10,
        'overwrite_policy': 'force'
    }

    monkeypatch.setattr('module_a.load_config', lambda x: config)
    monkeypatch.setattr('module_a.apply_cli_overrides', lambda x, y=None: x)
    monkeypatch.setattr(
        'module_a.get_rotating_logger',
        lambda name, log_dir=None, max_bytes=None, backup_count=None: Mock()
    )
    monkeypatch.setattr(
        'module_a.fetch_gamelogs',
        lambda season, timeout, logger: (pd.DataFrame(), pd.DataFrame())
    )
    monkeypatch.setattr(
        'module_a.resolve_output_path',
        lambda directory, filename: Path(directory) / filename
    )
    monkeypatch.setattr('argparse.ArgumentParser.parse_args', lambda self=None: argparse.Namespace(
        config_path='dummy.yaml',
        overwrite_policy='force',
        season=None,
        log_level='INFO'
    ))

    main()

    assert (tmp_path / "mlb_all_batting_gamelogs_2024.csv").exists()
    assert (tmp_path / "mlb_all_pitching_gamelogs_2024.csv").exists()
